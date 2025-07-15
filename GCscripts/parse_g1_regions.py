#!/usr/bin/env python3
"""
Enhanced G1 Log Parser with Time-based Sizing Support

This enhanced version supports traditional G1 region parsing plus new time-based
heap sizing analysis. It maintains compatibility with the original parse_g1_regions
while adding comprehensive sizing activity extraction.

Features:
- Traditional G1 region parsing (Eden, Survivor, Old, Humongous)
- Time-based heap sizing analysis (uncommit-only mode)
- Modern log format support ([timestamp][pid][tid])
- Automatic mode detection and timestamp normalization
- Comprehensive sizing event extraction
- JSON export capabilities

Dependencies:
- Standard library only (re, json, datetime, dataclasses)

Usage:
    from parse_g1_regions import G1EnhancedParser, plot_regions
    
    parser = G1EnhancedParser()
    parser.parse_log_content(log_content)
    
    if parser.has_sizing_data:
        print("G1 Time-Based Heap Sizing detected")

Author: mo-beck
Enhanced: July 2025
Version: 2.0
"""

import re
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import plotly.graph_objs as go


@dataclass
class SizingEntry:
    """Data class for sizing activity entries"""
    timestamp: str
    sizing_type: str
    sizing_mode: Optional[str] = None
    evaluation_interval_ms: Optional[int] = None
    uncommit_delay_ms: Optional[int] = None
    inactive_regions: Optional[int] = None
    uncommit_regions: Optional[int] = None
    uncommit_mb: Optional[float] = None
    shrink_mb: Optional[float] = None
    heap_size_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class G1EnhancedParser:
    """Enhanced G1 log parser with time-based sizing support"""
    
    def __init__(self):
        self.region_data = {'Eden': [], 'Survivor': [], 'Old': [], 'Humongous': []}
        self.sizing_entries: List[SizingEntry] = []
        self.has_pid_tid = False
        self.has_sizing_data = False
        self._region_size = 0
        
        # Define regex patterns for different log formats
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for parsing"""
        # Traditional format patterns
        self.traditional_runtime_pattern = r"\[(\d+\.\d+)s\]"
        self.traditional_region_pattern = r"GC\(\d+\) (\w+) regions: (\d+)->(\d+)"
        
        # Modern format patterns  
        self.modern_timestamp_pattern = r"\[([0-9T:\-\.+]+)\]\[(\d+)\]\[(\d+)\]\[(\w+)\]\[gc.*?\]"
        self.modern_region_pattern = r"GC\((\d+)\) (\w+) regions: (\d+)->(\d+)"
        
        # Sizing patterns
        self.sizing_init_pattern = r"Heap sizing initialized \(mode: ([^)]+)\)"
        self.sizing_params_pattern = r"Heap sizing parameters: evaluation_interval_ms=(\d+), uncommit_delay_ms=(\d+)"
        self.uncommit_pattern = r"Time-based uncommit: (\d+) regions \((\d+\.\d+)MB\) uncommitted \(inactive: (\d+), total: \d+ regions\)"
        self.shrink_eval_pattern = r"Time-based evaluation: shrink by (\d+)MB"
        self.no_uncommit_pattern = r"Time-based evaluation: no uncommit needed"
        self.shrink_completed_pattern = r"Heap shrink completed.*heap: (\d+)M"
        
        # Common patterns
        self.region_size_pattern = r"Heap Region Size: (\d+)M"
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse timestamp to seconds since epoch"""
        try:
            if 'T' in timestamp_str:
                # ISO format timestamp
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00').replace('+0000', '+00:00'))
                return dt.timestamp()
            else:
                # Traditional format
                return float(timestamp_str)
        except:
            return 0.0
    
    def parse_log_content(self, log_content: str):
        """Parse GC log content and extract data"""
        lines = log_content.splitlines()
        
        # First pass: detect format
        for line in lines:
            if re.search(self.modern_timestamp_pattern, line):
                self.has_pid_tid = True
                break
        
        # Second pass: parse data
        for line in lines:
            self._parse_line(line)
        
        # Post-processing
        if self.sizing_entries:
            self.has_sizing_data = True
    
    def _parse_line(self, line: str):
        """Parse a single line from the log"""
        # Check for region size
        size_match = re.search(self.region_size_pattern, line)
        if size_match:
            self._region_size = int(size_match.group(1))
            return
        
        # Parse based on detected format
        if self.has_pid_tid:
            self._parse_modern_line(line)
        else:
            self._parse_traditional_line(line)
        
        # Parse sizing events (both formats)
        self._parse_sizing_line(line)
    
    def _parse_traditional_line(self, line: str):
        """Parse traditional format line"""
        runtime_match = re.search(self.traditional_runtime_pattern, line)
        region_match = re.search(self.traditional_region_pattern, line)
        
        if runtime_match and region_match:
            runtime = float(runtime_match.group(1))
            region_type, before, after = region_match.groups()
            before, after = int(before), int(after)
            
            if region_type in self.region_data:
                self.region_data[region_type].append((runtime, before, after))
    
    def _parse_modern_line(self, line: str):
        """Parse modern format line"""
        timestamp_match = re.search(self.modern_timestamp_pattern, line)
        region_match = re.search(self.modern_region_pattern, line)
        
        if timestamp_match and region_match:
            timestamp_str = timestamp_match.group(1)
            runtime = self._parse_timestamp(timestamp_str)
            gc_id, region_type, before, after = region_match.groups()
            before, after = int(before), int(after)
            
            if region_type in self.region_data:
                self.region_data[region_type].append((runtime, before, after))
    
    def _parse_sizing_line(self, line: str):
        """Parse sizing-related events from line"""
        timestamp = self._extract_timestamp(line)
        if not timestamp:
            return
        
        # Heap sizing initialization
        init_match = re.search(self.sizing_init_pattern, line)
        if init_match:
            mode = init_match.group(1)
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='heap_sizing_init',
                sizing_mode=mode
            ))
            return
        
        # Sizing parameters
        params_match = re.search(self.sizing_params_pattern, line)
        if params_match:
            eval_interval, uncommit_delay = map(int, params_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='sizing_parameters',
                evaluation_interval_ms=eval_interval,
                uncommit_delay_ms=uncommit_delay
            ))
            return
        
        # Time-based uncommit
        uncommit_match = re.search(self.uncommit_pattern, line)
        if uncommit_match:
            regions, mb, inactive = uncommit_match.groups()
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_uncommit',
                uncommit_regions=int(regions),
                uncommit_mb=float(mb),
                inactive_regions=int(inactive)
            ))
            return
        
        # Shrink evaluation
        shrink_match = re.search(self.shrink_eval_pattern, line)
        if shrink_match:
            shrink_mb = int(shrink_match.group(1))
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_shrink',
                shrink_mb=shrink_mb
            ))
            return
        
        # No uncommit needed
        if re.search(self.no_uncommit_pattern, line):
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit'
            ))
            return
        
        # Heap shrink completed
        shrink_completed_match = re.search(self.shrink_completed_pattern, line)
        if shrink_completed_match:
            heap_size = int(shrink_completed_match.group(1))
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='heap_shrink_completed',
                heap_size_mb=heap_size
            ))
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from line based on format"""
        if self.has_pid_tid:
            match = re.search(self.modern_timestamp_pattern, line)
            return match.group(1) if match else None
        else:
            match = re.search(self.traditional_runtime_pattern, line)
            return match.group(1) if match else None
    
    def has_uncommit_only_sizing(self) -> bool:
        """Check if uncommit-only mode is detected"""
        init_entries = [e for e in self.sizing_entries if e.sizing_type == 'heap_sizing_init']
        return any('uncommit-only' in e.sizing_mode for e in init_entries if e.sizing_mode)
    
    def get_region_data(self) -> Dict[str, List]:
        """Get traditional region data for backward compatibility"""
        return self.region_data
    
    def to_json(self) -> str:
        """Export all parsed data as JSON"""
        data = {
            'format_info': {
                'has_pid_tid': self.has_pid_tid,
                'has_sizing_data': self.has_sizing_data,
                'region_size_mb': self._region_size
            },
            'region_data': self.region_data,
            'sizing_entries': [entry.to_dict() for entry in self.sizing_entries]
        }
        return json.dumps(data, indent=2)


# Original function for backward compatibility
def parse_g1_log(log_content):
    """Original parse_g1_log function for backward compatibility"""
    parser = G1EnhancedParser()
    parser.parse_log_content(log_content)
    return parser.get_region_data()


# Enhanced plotting function
def plot_regions(region_data):
    """Enhanced plot_regions function with improved visualization"""
    fig = go.Figure()

    for region_type, data_points in region_data.items():
        if not data_points:
            continue
            
        runtime, before, after = zip(*data_points)

        fig.add_trace(go.Scatter(
            x=runtime,
            y=before,
            mode='lines+markers',
            name=f'{region_type} Before GC',
            line=dict(shape='hv'),
            marker=dict(size=6)
        ))

        fig.add_trace(go.Scatter(
            x=runtime,
            y=after,
            mode='lines+markers',
            name=f'{region_type} After GC',
            line=dict(shape='hv', dash='dot'),
            marker=dict(size=6, symbol='diamond')
        ))

    fig.update_layout(
        title='G1 Region States Over Time',
        xaxis_title='Runtime (s)',
        yaxis_title='Total Count of Regions',
        legend_title='Region States',
        legend=dict(
            itemsizing='constant',
            traceorder='normal',
            font=dict(size=12),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.2)',
            borderwidth=1,
        ),
        height=600
    )
    return fig

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
    inactive_required: Optional[int] = None
    requested_regions: Optional[int] = None
    total_empty_regions: Optional[int] = None
    uncommit_regions: Optional[int] = None
    uncommit_mb: Optional[float] = None
    shrink_mb: Optional[float] = None
    heap_size_mb: Optional[float] = None
    heap_bytes: Optional[int] = None
    min_heap_bytes: Optional[int] = None
    region_id: Optional[int] = None
    last_access_ms: Optional[int] = None
    transition_state: Optional[str] = None
    notes: Optional[str] = None
    
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
        self._current_eval: Dict[str, Any] = {}
        
        # Define regex patterns for different log formats
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for parsing"""
        # Traditional format patterns
        self.traditional_runtime_pattern = r"\[(\d+\.\d+)s\]"
        self.traditional_region_pattern = r"GC\(\d+\) (\w+) regions: (\d+)->(\d+)"
        
        # Modern format patterns  
        self.modern_timestamp_pattern = r"\[([0-9T:\-\.+]+)\]\[(\d+)\]\[(\d+)\]\[([^\]]+)\]\[gc.*?\]"
        self.modern_region_pattern = r"GC\((\d+)\) (\w+) regions: (\d+)->(\d+)"
        
        # Sizing patterns
        self.sizing_status_pattern = r"G1 Time-Based Heap Sizing (enabled|disabled)(?: \(([^)]+)\))?"
        self.sizing_init_pattern = r"Heap sizing initialized \(mode: ([^)]+)\)"
        self.sizing_params_pattern = r"Heap sizing parameters: evaluation_interval_ms=(\d+), uncommit_delay_ms=(\d+)"
        self.sizing_params_pattern_new = r"Evaluation Interval: (\d+)s, Uncommit Delay: (\d+)s, Min Regions To Uncommit: (\d+)"
        self.uncommit_pattern = r"Time-based uncommit: (\d+) regions \((\d+\.\d+)MB\) uncommitted \(inactive: (\d+), total: \d+ regions\)"
        self.shrink_eval_pattern = r"Time-based evaluation: shrink by (\d+)MB"
        self.no_uncommit_pattern = r"Time-based evaluation: no uncommit needed"
        self.shrink_completed_pattern = r"Heap shrink completed.*heap: (\d+)M"
        self.heap_shrink_details_pattern = r"Heap shrink details: uncommitted (\d+) regions \((\d+)MB\), heap size now (\d+)MB"

        # New time-based uncommit format patterns (2025+)
        self.eval_start_pattern = r"Starting (?:uncommit|heap) evaluation"
        self.eval_scan_pattern = r"Full region scan: counting uncommit candidates"
        self.eval_scan_result_pattern = r"Full region scan: found (\d+) inactive regions out of (\d+) total regions"
        self.eval_found_pattern = r"Time-based uncommit evaluation: found (\d+) inactive regions \(requested (\d+)\)"
        self.eval_found_min_pattern = r"Uncommit evaluation: found (\d+) inactive candidates \(min required: (\d+)\)"
        self.eval_found_uncommitting_pattern = r"Uncommit evaluation: found (\d+) inactive regions, uncommitting (\d+) regions \((\d+)MB\)"
        self.eval_summary_pattern = r"Uncommit evaluation: shrinking heap by (\d+)MB using time-based selection"
        self.eval_no_action_pattern = r"Uncommit evaluation: no heap uncommit needed \(inactive=(\d+) min_required=(\d+) heap=(\d+)B min=(\d+)B\)"
        self.eval_no_action_simple_pattern = r"Uncommit evaluation: no heap uncommit needed \(evaluation #(\d+)\)"
        self.heap_eval_no_action_pattern = r"Time-based heap evaluation: no uncommit needed \(inactive=(\d+) min_required=(\d+) heap=(\d+)B min=(\d+)B\)"
        self.heap_eval_shrink_pattern = r"Time-based heap evaluation: shrinking heap by (\d+)MB \(inactive=(\d+) min_required=(\d+) heap=(\d+)B min=(\d+)B\)"
        self.time_based_request_pattern = r"Time-based shrink: requesting (\d+)MB based on (\d+) time-based candidates"
        self.time_based_processing_pattern = r"Time-based shrink: processing (\d+) oldest regions out of (\d+) empty regions"
        self.time_based_deactivated_pattern = r"Time-based shrink: deactivated (\d+) oldest empty regions"
        self.time_based_uncommitted_pattern = r"Time-based shrink: uncommitted (\d+) oldest regions \((\d+)MB\), heap size now (\d+)MB"
        self.time_based_candidate_pattern = r"Time-based shrink: identified region (\d+) as candidate \(last_access=(\d+)ms ago\)"
        self.time_based_deactivating_region_pattern = r"Time-based shrink: deactivating region (\d+) \(last_access=(\d+)ms ago\)"
        self.region_transition_pattern = r"Region state transition: Region (\d+) transitioning from (\w+) to (\w+) after (\d+)ms idle"
        
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
        status_match = re.search(self.sizing_status_pattern, line)
        if status_match:
            status, mode = status_match.groups()
            sizing_type = 'heap_sizing_enabled' if status == 'enabled' else 'heap_sizing_disabled'
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type=sizing_type,
                sizing_mode=mode or status
            ))
            return

        init_match = re.search(self.sizing_init_pattern, line)
        if init_match:
            mode = init_match.group(1)
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='heap_sizing_init',
                sizing_mode=mode
            ))
            return
        
        # Sizing parameters (old format)
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
        
        # Sizing parameters (new format: "Evaluation Interval: 60s, Uncommit Delay: 300s, Min Regions To Uncommit: 10")
        params_match_new = re.search(self.sizing_params_pattern_new, line)
        if params_match_new:
            eval_interval_s, uncommit_delay_s, min_regions = map(int, params_match_new.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='sizing_parameters',
                evaluation_interval_ms=eval_interval_s * 1000,  # Convert to ms
                uncommit_delay_ms=uncommit_delay_s * 1000,  # Convert to ms
                inactive_required=min_regions
            ))
            return
        
        # Legacy time-based uncommit summary
        uncommit_match = re.search(self.uncommit_pattern, line)
        if uncommit_match:
            regions, mb, inactive = uncommit_match.groups()
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_uncommit',
                uncommit_regions=int(regions),
                uncommit_mb=float(mb),
                inactive_regions=int(inactive)
            )
            self._current_eval.clear()
            self.sizing_entries.append(entry)
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
        
        # No uncommit needed (legacy wording)
        if re.search(self.no_uncommit_pattern, line):
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit'
            ))
            self._current_eval.clear()
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
            return

        # Heap shrink details summary
        shrink_details_match = re.search(self.heap_shrink_details_pattern, line)
        if shrink_details_match:
            regions, mb, heap_size = map(int, shrink_details_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='heap_shrink_details',
                uncommit_regions=regions,
                uncommit_mb=float(mb),
                heap_size_mb=heap_size
            ))
            self._current_eval.clear()
            return

        # Time-based shrink uncommitted summary
        time_based_uncommitted_match = re.search(self.time_based_uncommitted_pattern, line)
        if time_based_uncommitted_match:
            regions, mb, heap_size = map(int, time_based_uncommitted_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='heap_shrink_details',  # Use same type so it appears in the graph
                uncommit_regions=regions,
                uncommit_mb=float(mb),
                heap_size_mb=heap_size
            ))
            self._current_eval.clear()
            return

        # ---- New format handling ----

        # Evaluation start markers
        if re.search(self.eval_start_pattern, line):
            self._current_eval = {
                'timestamp': timestamp
            }
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='uncommit_evaluation_start'
            ))
            return

        if re.search(self.eval_scan_pattern, line):
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='uncommit_evaluation_scan'
            ))
            return

        scan_result_match = re.search(self.eval_scan_result_pattern, line)
        if scan_result_match:
            inactive, total = map(int, scan_result_match.groups())
            self._current_eval.setdefault('timestamp', timestamp)
            self._current_eval['inactive_regions'] = inactive
            self._current_eval['total_empty_regions'] = total
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_scan_result',
                inactive_regions=inactive,
                total_empty_regions=total
            ))
            return

        # Evaluation result with requested candidates (new wording)
        eval_found_match = re.search(self.eval_found_pattern, line)
        if eval_found_match:
            inactive, requested = map(int, eval_found_match.groups())
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_shrink' if inactive else 'time_based_evaluation_no_uncommit',
                inactive_regions=inactive,
                requested_regions=requested
            )
            self.sizing_entries.append(entry)
            self._current_eval = {
                'timestamp': timestamp,
                'inactive_regions': inactive,
                'requested_regions': requested,
                'entry': entry
            }
            if inactive == 0:
                self._current_eval.clear()
            return

        # Evaluation result referencing minimum threshold
        eval_found_min_match = re.search(self.eval_found_min_pattern, line)
        if eval_found_min_match:
            inactive, required = map(int, eval_found_min_match.groups())
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit' if inactive < required else 'time_based_evaluation_shrink',
                inactive_regions=inactive,
                inactive_required=required,
                requested_regions=required if inactive >= required else None
            )
            self.sizing_entries.append(entry)
            if inactive >= required:
                self._current_eval = {
                    'timestamp': timestamp,
                    'inactive_regions': inactive,
                    'inactive_required': required,
                    'requested_regions': required,
                    'entry': entry
                }
            else:
                self._current_eval.clear()
            return

        # Evaluation with uncommit decision (found X inactive, uncommitting Y regions)
        eval_found_uncommitting_match = re.search(self.eval_found_uncommitting_pattern, line)
        if eval_found_uncommitting_match:
            inactive, uncommit_regions, uncommit_mb = map(int, eval_found_uncommitting_match.groups())
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_shrink',
                inactive_regions=inactive,
                requested_regions=uncommit_regions,
                shrink_mb=uncommit_mb
            )
            self.sizing_entries.append(entry)
            self._current_eval = {
                'timestamp': timestamp,
                'inactive_regions': inactive,
                'requested_regions': uncommit_regions,
                'shrink_mb': uncommit_mb,
                'entry': entry
            }
            return

        heap_eval_shrink_match = re.search(self.heap_eval_shrink_pattern, line)
        if heap_eval_shrink_match:
            shrink_mb, inactive, required, heap_bytes, min_bytes = heap_eval_shrink_match.groups()
            shrink_mb = int(shrink_mb)
            inactive = int(inactive)
            required = int(required)
            heap_bytes = int(heap_bytes)
            min_bytes = int(min_bytes)
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_shrink',
                inactive_regions=inactive,
                inactive_required=required,
                shrink_mb=shrink_mb,
                heap_bytes=heap_bytes,
                min_heap_bytes=min_bytes
            )
            self.sizing_entries.append(entry)
            self._current_eval = {
                'timestamp': timestamp,
                'inactive_regions': inactive,
                'inactive_required': required,
                'heap_bytes': heap_bytes,
                'min_heap_bytes': min_bytes,
                'shrink_mb': shrink_mb,
                'entry': entry
            }
            return

        heap_eval_no_action_match = re.search(self.heap_eval_no_action_pattern, line)
        if heap_eval_no_action_match:
            inactive, required, heap_bytes, min_bytes = map(int, heap_eval_no_action_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit',
                inactive_regions=inactive,
                inactive_required=required,
                heap_bytes=heap_bytes,
                min_heap_bytes=min_bytes
            ))
            self._current_eval.clear()
            return

        # Evaluation shrink summary (MB)
        eval_summary_match = re.search(self.eval_summary_pattern, line)
        if eval_summary_match:
            shrink_mb = int(eval_summary_match.group(1))
            eval_entry = self._current_eval.get('entry')

            if eval_entry:
                eval_entry.shrink_mb = shrink_mb
            else:
                eval_entry = SizingEntry(
                    timestamp=timestamp,
                    sizing_type='time_based_evaluation_shrink',
                    shrink_mb=shrink_mb
                )
                self.sizing_entries.append(eval_entry)
                self._current_eval['entry'] = eval_entry

            self._current_eval['shrink_mb'] = shrink_mb
            self._current_eval.setdefault('timestamp', timestamp)
            return

        # Explicit "no uncommit" summary line (detailed)
        eval_no_action_match = re.search(self.eval_no_action_pattern, line)
        if eval_no_action_match:
            inactive, required, heap_bytes, min_bytes = map(int, eval_no_action_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit',
                inactive_regions=inactive,
                inactive_required=required,
                heap_bytes=heap_bytes,
                min_heap_bytes=min_bytes
            ))
            self._current_eval.clear()
            return

        # Explicit "no uncommit" summary line (simple: evaluation #N)
        eval_no_action_simple_match = re.search(self.eval_no_action_simple_pattern, line)
        if eval_no_action_simple_match:
            eval_number = int(eval_no_action_simple_match.group(1))
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_evaluation_no_uncommit'
            ))
            self._current_eval.clear()
            return

        # Requested shrink amount and candidate count
        request_match = re.search(self.time_based_request_pattern, line)
        if request_match:
            shrink_mb, candidates = map(int, request_match.groups())

            eval_entry = self._current_eval.get('entry')
            if eval_entry:
                eval_entry.shrink_mb = shrink_mb
                if eval_entry.requested_regions is None:
                    eval_entry.requested_regions = candidates
            else:
                eval_entry = SizingEntry(
                    timestamp=timestamp,
                    sizing_type='time_based_evaluation_shrink',
                    shrink_mb=shrink_mb,
                    requested_regions=candidates
                )
                self.sizing_entries.append(eval_entry)
                self._current_eval['entry'] = eval_entry

            self._current_eval['shrink_mb'] = shrink_mb
            self._current_eval['requested_regions'] = candidates
            self._current_eval.setdefault('timestamp', timestamp)

            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_request',
                shrink_mb=shrink_mb,
                requested_regions=candidates
            ))
            return

        # Processing detail (how many will be uncommitted)
        processing_match = re.search(self.time_based_processing_pattern, line)
        if processing_match:
            uncommit_regions, total_empty = map(int, processing_match.groups())
            self._current_eval['uncommit_regions'] = uncommit_regions
            self._current_eval['total_empty_regions'] = total_empty
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_processing',
                uncommit_regions=uncommit_regions,
                total_empty_regions=total_empty
            ))
            return

        # Finalized deactivation summary
        deactivated_match = re.search(self.time_based_deactivated_pattern, line)
        if deactivated_match:
            deactivated = int(deactivated_match.group(1))
            inactive = self._current_eval.get('inactive_regions')
            shrink_mb = self._current_eval.get('shrink_mb')
            requested = self._current_eval.get('requested_regions')
            if inactive is None:
                inactive = deactivated
            if shrink_mb is None:
                shrink_mb = deactivated * self._region_size if self._region_size else 0
            if requested is None and self._current_eval.get('inactive_required'):
                requested = self._current_eval.get('inactive_required')
            entry = SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_uncommit',
                inactive_regions=inactive,
                requested_regions=requested,
                uncommit_regions=deactivated,
                uncommit_mb=float(shrink_mb) if shrink_mb is not None else 0.0,
                total_empty_regions=self._current_eval.get('total_empty_regions')
            )
            self.sizing_entries.append(entry)
            self._current_eval.clear()
            return

        # Candidate identification lines (optional detail)
        candidate_match = re.search(self.time_based_candidate_pattern, line)
        if candidate_match:
            region_id, last_access = map(int, candidate_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_candidate',
                region_id=region_id,
                last_access_ms=last_access
            ))
            return

        # Region deactivation detail lines
        deactivating_region_match = re.search(self.time_based_deactivating_region_pattern, line)
        if deactivating_region_match:
            region_id, last_access = map(int, deactivating_region_match.groups())
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='time_based_deactivate_region',
                region_id=region_id,
                last_access_ms=last_access
            ))
            return

        # Region state transitions (new trace level)
        region_transition_match = re.search(self.region_transition_pattern, line)
        if region_transition_match:
            region_id, from_state, to_state, idle_ms = region_transition_match.groups()
            self.sizing_entries.append(SizingEntry(
                timestamp=timestamp,
                sizing_type='region_state_transition',
                region_id=int(region_id),
                transition_state=f"{from_state}->{to_state}",
                last_access_ms=int(idle_ms)
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
        if any('uncommit-only' in e.sizing_mode for e in init_entries if e.sizing_mode):
            return True

        # Fallback: detect presence of time-based evaluation data even if init logs are missing
        time_based_markers = {
            'time_based_evaluation_shrink',
            'time_based_evaluation_no_uncommit',
            'time_based_uncommit',
            'time_based_request',
            'time_based_processing',
            'time_based_scan_result'
        }
        return any(entry.sizing_type in time_based_markers for entry in self.sizing_entries)
    
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

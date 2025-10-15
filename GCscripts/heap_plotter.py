#!/usr/bin/env python3
"""
Enhanced Heap Plotter with G1 Time-based Sizing Support

This enhanced version supports traditional G1 region plotting plus new time-based
heap sizing visualizations. It maintains compatibility with the original heap_plotter
while adding comprehensive sizing activity analysis.

Features:
- Traditional GC log analysis (heap occupancy, pause duration, scaling)
- G1 region transitions visualization
- Time-based heap sizing analysis (uncommit-only mode)
- Sizing activity summary with synchronized timelines
- Heap evaluation process visualization
- Region state transitions and uncommit rate analysis
- Interactive Dash web interface

Dependencies:
- dash, plotly, pandas, numpy
- parse_g1_regions (for G1 sizing data)

Usage:
    python heap_plotter.py
    
Then navigate to http://localhost:8051 and upload a GC log file.

Supported Log Formats:
- Traditional GC logs ([time]s format)
- Modern GC logs ([timestamp][pid][tid] format)
- G1 logs with time-based heap sizing data

Author: mo-beck
Enhanced: July 2025
Version: 2.0
"""

import base64
import io
import re
import pandas as pd
import numpy as np
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration constants
DEFAULT_PORT = 8051
CHART_HEIGHT = 700
EVALUATION_TIMELINE_HEIGHT = 900
REGION_TRANSITIONS_HEIGHT = 800

# Import enhanced G1 parser
try:
    from parse_g1_regions import G1EnhancedParser, plot_regions
    ENHANCED_PARSER_AVAILABLE = True
except ImportError:
    # Create fallback plot_regions function
    ENHANCED_PARSER_AVAILABLE = False
    print("Warning: Enhanced parser not available, using basic functionality")
    
    def plot_regions(region_data):
        """Fallback plot_regions function"""
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(title="Enhanced parser not available")
        return fig
    
    def parse_g1_log(log_content):
        """Fallback parse_g1_log function"""
        return {'Eden': [], 'Survivor': [], 'Old': [], 'Humongous': []}

# Define colors and markers for both G1 and Parallel GCs
colors = {
    'Prepare Mixed G1 Evacuation Pause': 'grey',
    'Mixed G1 Evacuation Pause': 'blue',
    'Mixed GCLocker Initiated GC': 'purple',
    'Young Metadata GC Threshold': 'black',
    'Young SystemGC': 'red',
    'Young Allocation Failure': 'brown',
    'Young GCLocker Initiated GC': 'cyan',
    'Young G1 Preventive Collection': 'indigo',
    'Young G1 Evacuation Pause': 'teal',   
    'Full G1 Compaction Pause': 'light green',
    'Full SystemGC': 'green',
    'Full Metadata GC Threshold': 'pink',
    'Concurrent Start G1 Humongous Allocation': 'plum',
    'Concurrent Start GCLocker Initiated GC': 'light blue',
    'Concurrent Start G1 Evacuation Pause': 'magenta',
    'Remark': 'violet',
    'Cleanup': 'red',
    'TotalHeap': 'orange'
}

markers = {
    'Prepare Mixed G1 Evacuation Pause': 'circle-dot',
    'Mixed G1 Evacuation Pause': 'star-open',
    'Mixed GCLocker Initiated GC': 'cross',
    'Young Metadata GC Threshold': 'arrow-up-open',
    'Young SystemGC': 'diamond',
    'Young Allocation Failure': 'hash-open',
    'Young GCLocker Initiated GC': 'arrow-down-open',
    'Young G1 Preventive Collection': 'triangle-up',
    'Young G1 Evacuation Pause': 'hash-open',   
    'Full G1 Compaction Pause': 'circle-dot',
    'Full SystemGC': 'star-open',
    'Full Metadata GC Threshold': 'arrow-up-open',
    'Concurrent Start G1 Humongous Allocation': 'diamond',
    'Concurrent Start GCLocker Initiated GC': 'hash-open',
    'Concurrent Start G1 Evacuation Pause': 'triangle-up',
    'Remark': 'star-open',
    'Cleanup': 'square-open',
    'TotalHeap': 'hash-open'
}

custom_marker_size = {
    'cross': 6  # Smaller size for the 'cross' marker
}

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    # File Upload Component
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select GC Log File(s)')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=True
        ),
    ]),
    
    html.Div(id='filename-display'),

    # Sidebar with Dropdown Menu
    html.Div([
        dcc.Dropdown(
            id='menu-selection',
            options=[
                {'label': 'Heap Occupancy Before GC', 'value': 'before'},
                {'label': 'Heap Occupancy After GC', 'value': 'after'},
                {'label': 'Pause Duration', 'value': 'duration'},
                {'label': 'GC Scaling Plot', 'value': 'scaling'},
                {'label': 'Pause Summary', 'value': 'summary'}
            ],
            value='before',
            style={'width': '100%'}
        )
    ], style={'width': '20%', 'float': 'left', 'padding': '10px'}),

    # Main content area
    html.Div([
        dcc.Graph(id='main-graph')
    ], style={'width': '75%', 'float': 'right', 'padding': '10px'})

])

@app.callback(
    [Output('main-graph', 'figure'),
     Output('filename-display', 'children'),
     Output('menu-selection', 'options')],
    [Input('menu-selection', 'value'),
     Input('upload-data', 'contents'),
     Input('upload-data', 'filename')]
)
def update_output(selected_value, contents, filename):
    if contents is None:
        return dash.no_update, "No file selected", dash.no_update

    try:
        # Normalise Dash upload payload into a list of (decoded_text, filename)
        if isinstance(contents, (list, tuple)):
            content_items = list(contents)
        else:
            content_items = [contents]

        if isinstance(filename, (list, tuple)):
            filenames = list(filename)
        elif filename is None:
            filenames = []
        else:
            filenames = [filename]

        decoded_entries = []
        for idx, raw_content in enumerate(content_items):
            if raw_content is None:
                continue

            name = filenames[idx] if idx < len(filenames) else None

            if isinstance(raw_content, bytes):
                decoded_text = raw_content.decode('utf-8', errors='replace')
            else:
                content_str = raw_content
                if isinstance(content_str, str) and ',' in content_str:
                    content_str = content_str.split(',', 1)[1]
                try:
                    decoded_bytes = base64.b64decode(content_str)
                    decoded_text = decoded_bytes.decode('utf-8', errors='replace')
                except Exception:
                    decoded_text = str(content_str)

            decoded_entries.append((decoded_text, name))

        if not decoded_entries:
            return dash.no_update, "Uploaded file(s) could not be read", dash.no_update

        # Prioritise primary GC log ahead of dedicated sizing logs for parsing order
        decoded_entries.sort(key=lambda item: 1 if item[1] and 'gc-sizing' in item[1].lower() else 0)

        combined_log_content = "\n".join(entry for entry, _ in decoded_entries if entry)

        filenames_for_display = [name for _, name in decoded_entries if name]
        if filenames_for_display:
            filename_display = f"Selected file(s): {', '.join(filenames_for_display)}"
        else:
            filename_display = "Selected file(s): <unnamed upload>"

        if len(decoded_entries) > 1:
            filename_display += f" | Combined {len(decoded_entries)} files"

        # Parse the GC log content using enhanced parser if available
        if ENHANCED_PARSER_AVAILABLE:
            enhanced_parser = G1EnhancedParser()
            enhanced_parser.parse_log_content(combined_log_content)

            data_df, scaling_data_df, is_g1, jdk_version = parse_gc_log_enhanced(
                combined_log_content, enhanced_parser
            )
            
            # Check if we have sizing data AND uncommit-only mode
            has_sizing_data = enhanced_parser.has_sizing_data and enhanced_parser.has_uncommit_only_sizing()
        else:
            data_df, scaling_data_df, is_g1, jdk_version = parse_gc_log(combined_log_content)
            has_sizing_data = False
            enhanced_parser = None

        # Validate the parsed data
        if data_df.empty or scaling_data_df.empty:
            return dash.no_update, "The log file could not be parsed. Please check the file format and ensure it contains GC log entries.", dash.no_update
        
        # Setup the dropdown options based on the log type
        dropdown_options = [
            {'label': 'Heap Occupancy Before GC', 'value': 'before'},
            {'label': 'Heap Occupancy After GC', 'value': 'after'},
            {'label': 'Pause Duration', 'value': 'duration'},
            {'label': 'GC Scaling Plot', 'value': 'scaling'},
            {'label': 'Pause Summary', 'value': 'summary'}
        ]
        
        if is_g1:
            dropdown_options.append({'label': 'G1 GC Region', 'value': 'g1-regions'})
            
        # Add sizing options if available
        if has_sizing_data:
            dropdown_options.extend([
                {'label': 'Sizing Activity Summary', 'value': 'sizing-summary'},
                {'label': 'Heap Evaluation Timeline', 'value': 'heap-evaluation'},
                {'label': 'Region Transitions', 'value': 'region-transitions'}
            ])

        # Generate the appropriate plot based on the selected value
        if is_g1 and selected_value == 'g1-regions':
            if ENHANCED_PARSER_AVAILABLE:
                region_data = enhanced_parser.get_region_data()
            else:
                region_data = parse_g1_log(combined_log_content)
            fig = plot_regions(region_data)
        elif has_sizing_data and selected_value in ['sizing-summary', 'heap-evaluation', 'region-transitions']:
            fig = generate_sizing_plot(enhanced_parser, selected_value)
        else:
            fig = generate_plot(data_df, scaling_data_df, selected_value)

        if jdk_version:
            filename_display += f" | JDK Version: {jdk_version}"
        if has_sizing_data:
            filename_display += " | Enhanced with Uncommit-Only Sizing Data"
            # Add sizing configuration info
            init_entries = [e for e in enhanced_parser.sizing_entries if e.sizing_type == 'heap_sizing_init']
            param_entries = [e for e in enhanced_parser.sizing_entries if e.sizing_type == 'sizing_parameters']
            if init_entries:
                filename_display += f" | Sizing Mode: {init_entries[0].sizing_mode}"
            if param_entries:
                param = param_entries[0]
                filename_display += f" | Eval: {param.evaluation_interval_ms}ms, Delay: {param.uncommit_delay_ms}ms"

        return fig, filename_display, dropdown_options
    except Exception as e:
        # Handle unexpected errors during file processing
        return dash.no_update, f"An error occurred while processing the file: {e}", dash.no_update


def parse_gc_log_enhanced(log_content, enhanced_parser):
    """Enhanced log parsing that handles both traditional and new formats"""
    # Check if we have PID/TID format
    if enhanced_parser.has_pid_tid:
        # Use enhanced parser for all data extraction when PID/TID format is detected
        data_df, scaling_data_df, is_g1, jdk_version = parse_modern_gc_log(log_content, enhanced_parser)
    else:
        # Use the existing parse_gc_log function for traditional format
        data_df, scaling_data_df, is_g1, jdk_version = parse_gc_log(log_content)
    
    return data_df, scaling_data_df, is_g1, jdk_version


def parse_modern_gc_log(log_content, enhanced_parser):
    """Parse modern GC log format with PID/TID timestamps"""
    # Modern format patterns
    pause_pattern = r"\[([0-9T:\-\.+]+)\]\[(\d+)\]\[(\d+)\]\[(\w+)\]\[gc\s*\] GC\((\d+)\) Pause (\w+)(?: \((.*?)\))?(?: \((.*?)\))? (\d+)M->(\d+)M\((\d+)M\) ([\d\.]+)ms"
    scaling_pattern = r"\[([0-9T:\-\.+]+)\]\[(\d+)\]\[(\d+)\]\[(\w+)\]\[gc,cpu\s*\] GC\((\d+)\) User=([\d\.]+)s Sys=([\d\.]+)s Real=([\d\.]+)s"
    jdk_version_pattern = re.compile(r"\[([0-9T:\-\.+]+)\]\[(\d+)\]\[(\d+)\]\[(\w+)\]\[gc,init\] Version: ([^\s]+)")
    
    # Initialize variables
    is_g1 = False
    scaling_data = []
    gc_data = []
    jdk_version = None
    prev_total_heap = 0  # Track previous total heap for "before" values
    
    # Process each line
    lines = log_content.splitlines()
    for line in lines:
        # Check for G1 collector usage
        if "Using G1" in line:
            is_g1 = True
        
        # Match and process scaling information
        scaling_match = re.search(scaling_pattern, line)
        if scaling_match:
            timestamp_str, pid, tid, level, gc_id, user_time, sys_time, real_time = scaling_match.groups()
            timestamp = enhanced_parser._parse_timestamp(timestamp_str)
            user_time, sys_time, real_time = map(float, [user_time, sys_time, real_time])
            scaling_factor = user_time / real_time if real_time else float('inf')
            scaling_data.append({
                "Runtime": timestamp,
                "UserTime": user_time,
                "SysTime": sys_time,
                "RealTime": real_time,
                "ScalingFactor": scaling_factor
            })
        
        # Match and process GC pause information
        pause_match = re.search(pause_pattern, line)
        if pause_match:
            timestamp_str, pid, tid, level, gc_id, pause_type, description, pause_cause, heap_before, heap_after, total_heap, duration = pause_match.groups()
            timestamp = enhanced_parser._parse_timestamp(timestamp_str)
            
            # Build pause name
            if description:
                if "Mixed" in description or "Concurrent Start" in description:
                    pause_type = description
                if "System.gc()" in description:
                    pause_cause = "SystemGC"
            
            if pause_cause:
                pause_name = f"{pause_type} {pause_cause}"
            elif description:
                pause_name = f"{pause_type} {description}"
            else:
                pause_name = pause_type
            
            current_total_heap = int(total_heap)
            gc_data.append({
                "Runtime": timestamp,
                "HeapBefore": int(heap_before),
                "HeapAfter": int(heap_after),
                "TotalHeap": current_total_heap,  # Total heap AFTER this GC
                "TotalHeapBefore": prev_total_heap,  # Total heap BEFORE this GC
                "PauseName": pause_name,
                "Duration": float(duration)
            })
            prev_total_heap = current_total_heap  # Update for next iteration
        
        # Look for JDK version
        version_match = jdk_version_pattern.search(line)
        if version_match:
            jdk_version = version_match.group(5)  # Changed from group(4) to group(5)
    
    # Convert to DataFrames
    if not gc_data:
        # Fallback: create minimal data to prevent empty DataFrame error
        gc_data = [{
            "Runtime": 0.0,
            "HeapBefore": 0,
            "HeapAfter": 0,
            "TotalHeap": 0,
            "TotalHeapBefore": 0,
            "PauseName": "No GC Data",
            "Duration": 0.0
        }]
    
    if not scaling_data:
        scaling_data = [{
            "Runtime": 0.0,
            "UserTime": 0.0,
            "SysTime": 0.0,
            "RealTime": 0.0,
            "ScalingFactor": 0.0
        }]
    
    data_df = pd.DataFrame(gc_data)
    scaling_data_df = pd.DataFrame(scaling_data)
    
    # Normalize timestamps to relative runtime (seconds since start)
    if not data_df.empty and 'Runtime' in data_df.columns:
        start_time = data_df['Runtime'].min()
        data_df['Runtime'] = data_df['Runtime'] - start_time
    
    if not scaling_data_df.empty and 'Runtime' in scaling_data_df.columns:
        start_time = scaling_data_df['Runtime'].min()
        scaling_data_df['Runtime'] = scaling_data_df['Runtime'] - start_time
    
    return data_df, scaling_data_df, is_g1, jdk_version


def generate_sizing_plot(enhanced_parser, plot_type):
    """Generate sizing-related plots"""
    if not enhanced_parser or not enhanced_parser.has_sizing_data:
        return go.Figure().update_layout(title="No sizing data available")
    
    if plot_type == 'sizing-summary':
        return create_sizing_parameters_summary(enhanced_parser.sizing_entries)
    
    elif plot_type == 'heap-evaluation':
        return create_heap_evaluation_timeline(enhanced_parser.sizing_entries)
    
    elif plot_type == 'region-transitions':
        return create_region_transitions_plot(enhanced_parser.sizing_entries)
    
    return go.Figure().update_layout(title=f"Plot type '{plot_type}' not implemented")


def create_sizing_parameters_summary(sizing_entries):
    """Create summary of sizing configuration and statistics"""
    init_entries = [e for e in sizing_entries if e.sizing_type == 'heap_sizing_init']
    param_entries = [e for e in sizing_entries if e.sizing_type == 'sizing_parameters']
    uncommit_entries = [e for e in sizing_entries if e.sizing_type == 'time_based_uncommit']
    no_uncommit_entries = [e for e in sizing_entries if e.sizing_type == 'time_based_evaluation_no_uncommit']
    shrink_entries = [e for e in sizing_entries if e.sizing_type == 'heap_shrink_completed']
    
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "domain"}]],
        subplot_titles=('Memory Uncommit Over Time', 'Memory Reclaimed Distribution', 
                       'Uncommit Operations Over Time', 'Evaluation Summary')
    )
    
    # Parse timestamps once and use consistently for both plots
    common_timestamps = []
    memory_reclaimed = []
    regions_uncommitted = []
    
    if uncommit_entries:
        for e in uncommit_entries:
            if isinstance(e.timestamp, str) and 'T' in e.timestamp:
                # Parse ISO timestamp to datetime for proper time axis
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(e.timestamp.replace('Z', '+00:00').replace('+0000', '+00:00'))
                    common_timestamps.append(dt)
                    memory_reclaimed.append(e.uncommit_mb)
                    regions_uncommitted.append(e.uncommit_regions)
                except:
                    # Fallback to simple float conversion
                    timestamp_float = float(e.timestamp) if str(e.timestamp).replace('.', '').isdigit() else 0
                    common_timestamps.append(timestamp_float)
                    memory_reclaimed.append(e.uncommit_mb)
                    regions_uncommitted.append(e.uncommit_regions)
            else:
                timestamp_float = float(e.timestamp) if str(e.timestamp).replace('.', '').isdigit() else 0
                common_timestamps.append(timestamp_float)
                memory_reclaimed.append(e.uncommit_mb)
                regions_uncommitted.append(e.uncommit_regions)
    
    # Memory uncommit timeline using shared timestamps
    if common_timestamps:
        fig.add_trace(
            go.Bar(x=common_timestamps, y=memory_reclaimed,
                   name='Memory Reclaimed (MB)',
                   marker=dict(color='green')),
            row=1, col=1
        )
    
    # Uncommit operations over time (regions count) using shared timestamps
    if common_timestamps:
        fig.add_trace(
            go.Scatter(x=common_timestamps, y=regions_uncommitted,
                      mode='markers+lines', name='Regions Uncommitted',
                      marker=dict(size=8, color='red')),
            row=2, col=1
        )
    
    # Memory reclaimed distribution
    if uncommit_entries:
        memory_values = [e.uncommit_mb for e in uncommit_entries]
        fig.add_trace(
            go.Histogram(x=memory_values, name='Memory Reclaimed (MB)', nbinsx=15,
                        marker=dict(color='lightblue')),
            row=1, col=2
        )
    
    # Evaluation summary pie chart - show uncommits vs no-uncommits
    if uncommit_entries or no_uncommit_entries:
        total_uncommit_mb = sum(e.uncommit_mb for e in uncommit_entries)
        uncommit_count = len(uncommit_entries)
        # Each "no uncommit needed" log entry represents 10 consecutive evaluations
        no_uncommit_count = len(no_uncommit_entries) * 10
        
        # Clean pie chart with just percentages
        labels = ['Uncommits', 'No Action Needed']
        values = [uncommit_count, no_uncommit_count]
        
        # Add hover text with detailed information
        hover_text = [
            f'{uncommit_count} Uncommit Events<br>{total_uncommit_mb}MB Total Reclaimed', 
            f'{no_uncommit_count}+ No Action Events<br>No Memory Reclaimed'
        ]
        
        fig.add_trace(
            go.Pie(labels=labels, values=values, name='Evaluation Results',
                   hovertext=hover_text, hoverinfo='text',
                   textinfo='percent',  # Show only percentages, no labels
                   marker=dict(colors=['lightcoral', 'lightgreen'])),
            row=2, col=2
        )
    
    # Update axis labels - simple and clean
    fig.update_yaxes(title_text="Memory (MB)", row=1, col=1)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)
    fig.update_yaxes(title_text="Region Count", row=2, col=1)
    
    fig.update_xaxes(title_text="Time", row=1, col=1)
    fig.update_xaxes(title_text="Memory Reclaimed (MB)", row=1, col=2)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    
    # Synchronize x-axis range for the two time-based plots with padding
    if common_timestamps:
        x_min = min(common_timestamps)
        x_max = max(common_timestamps)
        
        # Add padding (5% buffer on each side)
        if isinstance(x_min, (int, float)) and isinstance(x_max, (int, float)):
            # Numeric timestamps
            time_range = x_max - x_min
            buffer = time_range * 0.05 if time_range > 0 else 1
            x_range = [x_min - buffer, x_max + buffer]
        else:
            # DateTime timestamps - add time buffer
            from datetime import timedelta
            buffer = timedelta(minutes=5)  # 5-minute buffer on each side
            x_range = [x_min - buffer, x_max + buffer]
        
        fig.update_xaxes(range=x_range, row=1, col=1)
        fig.update_xaxes(range=x_range, row=2, col=1)
    
    fig.update_layout(title_text="G1 Heap Sizing Activity Analysis", height=CHART_HEIGHT)
    return fig


def create_heap_evaluation_timeline(sizing_entries):
    """Create timeline focused on the heap sizing evaluation process and decision-making"""
    eval_entries = [e for e in sizing_entries 
                   if e.sizing_type in ['time_based_evaluation_shrink', 'time_based_evaluation_no_uncommit']]
    uncommit_entries = [e for e in sizing_entries if e.sizing_type == 'time_based_uncommit']
    shrink_entries = [e for e in sizing_entries if e.sizing_type in ['heap_shrink_completed', 'heap_shrink_details']]
    
    if not eval_entries and not uncommit_entries and not shrink_entries:
        return go.Figure().update_layout(title="No heap evaluation data available")
    
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=('Heap Sizing Evaluation Decisions', 'Evaluation Outcomes & Actions', 'Heap Size After Shrink Operations'),
        vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # Helper function to parse timestamps properly
    def parse_timestamp_properly(timestamp):
        if isinstance(timestamp, str) and 'T' in timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+0000', '+00:00'))
                return dt
            except:
                return float(timestamp) if str(timestamp).replace('.', '').isdigit() else 0
        else:
            return float(timestamp) if str(timestamp).replace('.', '').isdigit() else 0
    
    # Plot 1: Evaluation Decisions Timeline
    all_eval_timestamps = []
    
    # Plot shrink evaluations
    shrink_events = [e for e in eval_entries if e.sizing_type == 'time_based_evaluation_shrink']
    if shrink_events:
        timestamps = [parse_timestamp_properly(e.timestamp) for e in shrink_events]
        shrink_amounts = []
        for e in shrink_events:
            value = getattr(e, 'shrink_mb', None)
            if value is None:
                value = 0
            shrink_amounts.append(value)
        all_eval_timestamps.extend(timestamps)
        
        fig.add_trace(
            go.Scatter(x=timestamps, y=shrink_amounts,
                      mode='markers+text', name='Shrink Evaluations',
                      marker=dict(color='red', size=15, symbol='triangle-down'),
                      text=[f'{mb}MB' for mb in shrink_amounts],
                      textposition='top center'),
            row=1, col=1
        )
    
    # Plot no-uncommit evaluations
    no_uncommit_events = [e for e in eval_entries if e.sizing_type == 'time_based_evaluation_no_uncommit']
    if no_uncommit_events:
        timestamps = [parse_timestamp_properly(e.timestamp) for e in no_uncommit_events]
        all_eval_timestamps.extend(timestamps)
        
        fig.add_trace(
            go.Scatter(x=timestamps, y=[0]*len(timestamps),
                      mode='markers', name='No Action Needed (10 evaluations each)',
                      marker=dict(color='green', size=12, symbol='circle')),
            row=1, col=1
        )
    
    # Plot 2: Evaluation Outcomes & Actions
    if uncommit_entries:
        timestamps = [parse_timestamp_properly(e.timestamp) for e in uncommit_entries]
        memory_reclaimed = []
        for e in uncommit_entries:
            value = getattr(e, 'uncommit_mb', None)
            if value is None:
                value = 0
            memory_reclaimed.append(value)
        
        # Memory reclaimed as bars
        fig.add_trace(
            go.Bar(x=timestamps, y=memory_reclaimed,
                   name='Memory Actually Reclaimed',
                   marker=dict(color='lightgreen', opacity=0.8)),
            row=2, col=1
        )
        
        # Add annotations for each action
        for i, (timestamp, memory) in enumerate(zip(timestamps, memory_reclaimed)):
            fig.add_annotation(
                x=timestamp,
                y=memory + (max(memory_reclaimed) * 0.05),
                text=f"{memory}MB",
                showarrow=False,
                font=dict(size=12, color='darkgreen', family='Arial'),
                xref=f"x{2}",
                yref=f"y{2}"
            )
    
    # Plot 3: Heap Size After Shrink Operations
    if shrink_entries:
        shrink_timestamps = [parse_timestamp_properly(e.timestamp) for e in shrink_entries]
        heap_sizes = []
        for e in shrink_entries:
            value = getattr(e, 'heap_size_mb', None)
            if value is None:
                value = 0
            heap_sizes.append(value)
        
        # Show the progression of heap sizes after each shrink operation
        fig.add_trace(
            go.Scatter(x=shrink_timestamps, y=heap_sizes,
                      mode='lines+markers', name='Heap Size After Shrink (MB)',
                      marker=dict(color='blue', size=10),
                      line=dict(width=3)),
            row=3, col=1
        )
        
        # Add trend line to show overall direction
        if len(heap_sizes) > 2:
            import numpy as np
            x_numeric = list(range(len(heap_sizes)))
            z = np.polyfit(x_numeric, heap_sizes, 1)
            p = np.poly1d(z)
            trend_values = [p(x) for x in x_numeric]
            
            slope_direction = "shrinking" if z[0] < 0 else "growing"
            fig.add_trace(
                go.Scatter(x=shrink_timestamps, y=trend_values,
                          mode='lines', name=f'Overall Trend ({slope_direction})',
                          line=dict(color='darkblue', width=2, dash='dash')),
                row=3, col=1
            )
    else:
        # If no shrink data, show a message
        fig.add_annotation(
            text="No heap shrink completion data available<br>Shrink operations may not be logged in this format",
            x=0.5, y=0.5,
            xref=f"x{3}", yref=f"y{3}",
            showarrow=False,
            font=dict(size=14, color='gray'),
            bgcolor="rgba(240,240,240,0.8)",
            bordercolor="gray",
            borderwidth=1
        )
    
    # Update layout with data source note
    fig.update_layout(
        title_text="G1 Heap Evaluation Process Timeline<br><sub>Focus: Decision-making process and evaluation outcomes</sub>", 
        height=EVALUATION_TIMELINE_HEIGHT,
        showlegend=True,
        margin=dict(t=90, b=80),  # Increased top margin for data source note
        legend=dict(
            orientation="v", 
            yanchor="top", 
            y=1, 
            xanchor="left", 
            x=1.02,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        )
    )
    
    # Add prominent data source note at the top
    fig.add_annotation(
        text="<b>📊 Data Source Note:</b> The 'Heap Size After Shrink Operations' plot contains significantly more data points <br>than other plots because it shows ALL shrink completion events from various GC triggers,<br>while other plots only show periodic time-based evaluation events.",
        xref="paper", yref="paper",
        x=0.70, y=1.05, xanchor='center', yanchor='bottom',
        showarrow=False,
        font=dict(size=12, color="darkred", family="Arial"),
        bgcolor="rgba(255,248,220,0.95)",
        bordercolor="orange",
        borderwidth=2,
        align="center"
    )
    
    # Update y-axis labels
    fig.update_yaxes(title_text="Shrink Amount (MB)", row=1, col=1)
    fig.update_yaxes(title_text="Memory Reclaimed (MB)", row=2, col=1)
    fig.update_yaxes(title_text="Heap Size (MB)", row=3, col=1)
    
    # Improve headroom for the first subplot (Heap Sizing Evaluation Decisions)
    # Set y-axis range to provide proper space for markers and text labels
    if shrink_events:
        shrink_amounts = []
        for e in shrink_events:
            value = getattr(e, 'shrink_mb', None)
            if value is None:
                value = 0
            shrink_amounts.append(value)
        max_shrink = max(shrink_amounts) if shrink_amounts else 100
        # Add 50% headroom above the highest shrink value for text labels
        y_max = max_shrink * 1.2
        fig.update_yaxes(range=[-10, y_max], row=1, col=1)
    else:
        # Default range when no shrink events, ensuring space for "No Action" markers
        fig.update_yaxes(range=[-10, 50], row=1, col=1)
    
    # Only show x-axis title on the bottom plot, and sync x-axis ranges for consistency
    if all_eval_timestamps or (shrink_entries and len(shrink_entries) > 0):
        # Determine the overall time range from all data sources
        all_timestamps = []
        if all_eval_timestamps:
            all_timestamps.extend(all_eval_timestamps)
        if uncommit_entries:
            uncommit_timestamps = [parse_timestamp_properly(e.timestamp) for e in uncommit_entries]
            all_timestamps.extend(uncommit_timestamps)
        if shrink_entries:
            shrink_timestamps = [parse_timestamp_properly(e.timestamp) for e in shrink_entries]
            all_timestamps.extend(shrink_timestamps)
        
        if all_timestamps:
            x_range = [min(all_timestamps), max(all_timestamps)]
            fig.update_xaxes(range=x_range, row=1, col=1)
            fig.update_xaxes(range=x_range, row=2, col=1)
            fig.update_xaxes(range=x_range, title_text="Time", row=3, col=1)
        else:
            fig.update_xaxes(title_text="Time", row=3, col=1)
    else:
        fig.update_xaxes(title_text="Time", row=3, col=1)
    
    return fig


def create_region_transitions_plot(sizing_entries):
    """Create focused plot showing actual region state transitions and their efficiency"""
    uncommit_entries = [e for e in sizing_entries if e.sizing_type == 'time_based_uncommit']
    eval_entries = [e for e in sizing_entries if e.sizing_type in ['time_based_evaluation_shrink', 'time_based_evaluation_no_uncommit']]
    
    # Data validation
    if not sizing_entries:
        return go.Figure().update_layout(title="No sizing data available")
    
    if not uncommit_entries:
        return go.Figure().update_layout(title="No region transition data available")
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Region State Transitions', 'G1 Uncommit Rate Analysis', 'Cumulative Memory Reclaimed'),
        vertical_spacing=0.10,
        row_heights=[0.35, 0.35, 0.3],
        specs=[[{"secondary_y": False}],
               [{"secondary_y": True}],  # Enable secondary y-axis for row 2
               [{"secondary_y": False}]]
    )
    
    # Helper function to parse timestamps properly
    def parse_timestamp_properly(timestamp):
        if isinstance(timestamp, str) and 'T' in timestamp:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00').replace('+0000', '+00:00'))
                return dt
            except:
                return float(timestamp) if str(timestamp).replace('.', '').isdigit() else 0
        else:
            return float(timestamp) if str(timestamp).replace('.', '').isdigit() else 0
    
    # Common data processing for uncommit entries
    timestamps = [parse_timestamp_properly(e.timestamp) for e in uncommit_entries]
    inactive_regions = [e.inactive_regions for e in uncommit_entries]
    uncommitted_regions = [e.uncommit_regions for e in uncommit_entries]
    memory_values = [e.uncommit_mb for e in uncommit_entries]
    
    # Plot 1: Region State Transitions (Stacked Area Chart)
    # Calculate regions that remained inactive (didn't get uncommitted)
    remained_inactive = [inactive - uncommitted for inactive, uncommitted in zip(inactive_regions, uncommitted_regions)]
    
    # Stacked area chart showing G1's uncommit strategy
    fig.add_trace(
        go.Scatter(x=timestamps, y=uncommitted_regions,
                  mode='lines', name='Regions Uncommitted',
                  fill='tozeroy', fillcolor='rgba(255,0,0,0.6)',
                  line=dict(color='red', width=0)),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=timestamps, y=inactive_regions,
                  mode='lines', name='Inactive Regions (over min regions to uncommit threshold)',
                  fill='tonexty', fillcolor='rgba(255,165,0,0.4)',
                  line=dict(color='orange', width=2)),
        row=1, col=1
    )
    
    # Add markers with text labels for uncommitted region counts
    fig.add_trace(
        go.Scatter(x=timestamps, y=uncommitted_regions,
                  mode='markers+text', name='Uncommit Count',
                  marker=dict(color='darkred', size=8, symbol='circle'),
                  text=[str(int(val)) for val in uncommitted_regions],
                  textposition='middle center',
                  textfont=dict(size=10, color='white'),
                  showlegend=False),
        row=1, col=1
    )
    
    # Plot 2: G1 Uncommit Rate Analysis with detailed hover info
    uncommit_rate = [
        (uncommitted / inactive * 100) if inactive > 0 else 0 
        for uncommitted, inactive in zip(uncommitted_regions, inactive_regions)
    ]
    
    # Create hover text with detailed info
    hover_texts = [
        f"Rate: {rate:.1f}%<br>Inactive Found: {inactive}<br>Uncommitted: {uncommitted}"
        for rate, inactive, uncommitted in zip(uncommit_rate, inactive_regions, uncommitted_regions)
    ]
    
    # Uncommit rate line
    fig.add_trace(
        go.Scatter(x=timestamps, y=uncommit_rate,
                  mode='lines+markers', name='G1 Uncommit Rate (%)',
                  marker=dict(color='purple', size=10),
                  line=dict(color='purple', width=3),
                  hovertext=hover_texts,
                  hoverinfo='text'),
        row=2, col=1
    )
    
    # Add memory reclaimed as bars on the same subplot (secondary y-axis)
    fig.add_trace(
        go.Bar(x=timestamps, y=memory_values,
               name='Memory Reclaimed (MB)',
               marker=dict(color='lightgreen', opacity=0.7)),
        row=2, col=1, secondary_y=True
    )
    
    # Plot 3: Cumulative Memory Reclaimed
    cumulative_memory = []
    total = 0
    for memory in memory_values:
        total += memory
        cumulative_memory.append(total)
    
    fig.add_trace(
        go.Scatter(x=timestamps, y=cumulative_memory,
                  mode='lines+markers', name='Cumulative Memory Reclaimed',
                  marker=dict(color='green', size=6),
                  line=dict(width=3),
                  fill='tozeroy', fillcolor='rgba(0,255,0,0.2)'),
        row=3, col=1
    )
    
    # Add individual reclaim events as bars
    fig.add_trace(
        go.Bar(x=timestamps, y=memory_values,
               name='Per-Event Memory Reclaimed',
               marker=dict(color='lightblue', opacity=0.6)),
        row=3, col=1
    )
    
    # Configure layout
    fig.update_layout(
        height=REGION_TRANSITIONS_HEIGHT,
        showlegend=True,
        margin=dict(t=100, b=150),
        legend=dict(
            orientation="v", 
            yanchor="top", 
            y=0.98,
            xanchor="left", 
            x=1.02,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        )
    )
    
    # Update axis labels with G1 context
    fig.update_yaxes(title_text="Region Count", row=1, col=1)
    fig.update_yaxes(title_text="G1 Uncommit Rate (%)", row=2, col=1)
    fig.update_yaxes(title_text="Memory Reclaimed (MB)", row=2, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Memory Reclaimed (MB)", row=3, col=1)
    
    # Only show x-axis title on the bottom plot, and sync x-axis ranges for consistency
    if timestamps:
        # Use the same time range for all subplots to ensure consistent scaling
        x_range = [min(timestamps), max(timestamps)]
        fig.update_xaxes(range=x_range, row=1, col=1)
        fig.update_xaxes(range=x_range, row=2, col=1)
        fig.update_xaxes(range=x_range, title_text="Time", row=3, col=1)
    
    # Set clean main title
    fig.update_layout(title_text="G1 Region Transitions Analysis")
    
    return fig


def parse_gc_log(log_content):
    """Original parse_gc_log function (preserved for compatibility)"""
    # Define regex patterns for matching various log details
    pause_pattern = r"\[(\d+\.\d+)s\].*?Pause (\w+)(?: \((.*?)\))? ?(?:\((.*?)\))? (\d+)M->(\d+)M\((\d+)M\) (\d+\.\d+)ms"
    scaling_pattern = r"\[(\d+\.\d+)s\].*?GC\(\d+\) User=(\d+\.\d+)s Sys=(\d+\.\d+)s Real=(\d+\.\d+)s"
    jdk_version_pattern = re.compile(r"\[\d+\.\d+s\]\[info\]\[gc,init\] Version: (\d+\.\d+\.\d+\+\d+-LTS(?:-\d+)?) \(release\)")
    g1_patterns = [
        re.compile(r'\[.*\]\[.*G1.*\]'),  # Identifies G1 collector usage
        re.compile(r'garbage-first heap')  # Identifies 'garbage-first heap' phrase
    ]
    
    # Initialize variables to store parsed data and G1 collector status
    is_g1 = False
    scaling_data = []
    gc_data = []
    jdk_version = None
    prev_total_heap = 0  # Track previous total heap for "before" values
    
    # Process each line of the log content
    lines = log_content.splitlines()
    for line in lines:
        # Check for G1 collector usage
        if any(pattern.search(line) for pattern in g1_patterns):
            is_g1 = True
        
        # Match and process scaling information
        scaling_match = re.search(scaling_pattern, line)
        if scaling_match:
            runtime, user_time, sys_time, real_time = map(float, scaling_match.groups())
            scaling_factor = user_time / real_time if real_time else float('inf')
            scaling_data.append({
                "Runtime": runtime,
                "UserTime": user_time,
                "SysTime": sys_time,
                "RealTime": real_time,
                "ScalingFactor": scaling_factor
            })
        
        # Match and process GC pause information
        pause_match = re.search(pause_pattern, line)
        if pause_match:
            runtime, pause_type, description, pause_cause, heap_before, heap_after, total_heap, duration = pause_match.groups()
            if description: 
                if "Mixed" in description or "Concurrent Start" in description:
                    pause_type = description  
                if "System.gc()" in description:
                    pause_cause = "SystemGC"

            if pause_cause: 
                pause_name = f"{pause_type} {pause_cause}"
            elif description: 
                pause_name = f"{pause_type} {description}"
            else: 
                pause_name = pause_type
            
            current_total_heap = int(total_heap)
            gc_data.append({
                "Runtime": float(runtime),
                "HeapBefore": int(heap_before),
                "HeapAfter": int(heap_after),
                "TotalHeap": current_total_heap,  # Total heap AFTER this GC
                "TotalHeapBefore": prev_total_heap,  # Total heap BEFORE this GC
                "PauseName": pause_name,
                "Duration": float(duration)
            })
            prev_total_heap = current_total_heap  # Update for next iteration
        
        # Look for JDK version
        version_match = jdk_version_pattern.search(line)
        if version_match:
            jdk_version = version_match.group(1)

    # Convert parsed data into DataFrames
    if not gc_data:
        raise ValueError("Parsed data is empty. The log file may not contain expected GC log entries.")
    data_df = pd.DataFrame(gc_data)
    scaling_data_df = pd.DataFrame(scaling_data)
    
    return data_df, scaling_data_df, is_g1, jdk_version


def generate_plot(data_df, scaling_data_df, selected_value):
    """Original generate_plot function (preserved for compatibility)"""
    fig = go.Figure()
    title = ''
    y_value = None

    # Handle the 'scaling' plot option
    if selected_value == 'scaling':
        if not scaling_data_df.empty:
            fig.add_trace(go.Scatter(
                x=scaling_data_df['Runtime'],
                y=scaling_data_df['ScalingFactor'],
                mode='lines+markers',
                name='GC Scaling Factor',
                marker=dict(color='purple', size=10)
            ))
            fig.add_trace(go.Scatter(
                x=scaling_data_df['Runtime'],
                y=scaling_data_df['SysTime'],
                mode='lines+markers',
                name='System Time',
                marker=dict(color='orange', size=10)
            ))
            fig.update_layout(
                title='GC Scaling and System Time Over Runtime',
                xaxis_title='Runtime (seconds)',
                yaxis_title='Scaling Factor & System Time',
                legend_title='Data Points'
            )
        else:
            fig.update_layout(
                title='No scaling data available'
            )
        return fig

    # Handle the 'before' and 'after' plot options
    elif selected_value == 'before':
        y_value = 'HeapBefore'
        title = 'Heap Occupancy Before GC'
        # For "before" view, show TotalHeapBefore (capacity before GC)
        total_heap_column = 'TotalHeapBefore'
    elif selected_value == 'after':
        y_value = 'HeapAfter'
        title = 'Heap Occupancy After GC'
        # For "after" view, show TotalHeap (capacity after GC)
        total_heap_column = 'TotalHeap'

    # Handle the 'duration' plot option
    elif selected_value == 'duration':
        title = 'GC Pause Durations Over Runtime'
        for pause, color in colors.items():
            if pause != "TotalHeap":
                subset = data_df[data_df['PauseName'] == pause]
                if not subset.empty:
                    fig.add_trace(go.Scatter(
                        x=subset['Runtime'],
                        y=subset['Duration'],
                        mode='markers',
                        name=pause,
                        marker=dict(color=color, size=10, symbol=markers[pause])
                    ))
        fig.update_layout(
            title=title,
            xaxis_title='Runtime (seconds)',
            yaxis_title='Pause Duration (ms)'
        )
        return fig

    # Handle the 'summary' plot option
    elif selected_value == 'summary':
        # Calculate stats and overhead
        pause_summary = data_df.groupby('PauseName')['Duration'].agg(['count', 'min', 'max', 'sum'])
        total_runtime = data_df['Runtime'].max()
        total_runtime_ms = total_runtime * 1000
        pause_summary['Overhead'] = (pause_summary['sum'] / total_runtime_ms) * 100
        
        # Format overhead values for readability
        overhead_threshold = 0.01
        pause_summary['Overhead'] = pause_summary['Overhead'].apply(
            lambda x: f"~0" if x < overhead_threshold else f"{x:.2f}"
        )
        
        # Sort the summary by 'sum' in descending order
        pause_summary = pause_summary.sort_values(by='sum', ascending=False)

        fig = make_subplots(
            rows=1, cols=2, 
            column_widths=[0.5, 0.5],
            specs=[[{"type": "table"}, {"type": "domain"}]],
            subplot_titles=('Pause Summary', 'Pause Type Contribution')
        )
        
        # Add the table to the first column
        table_trace = go.Table(
            header=dict(values=['Pause Name', 'Count', 'Min Time (ms)', 'Max Time (ms)', 'Total Time (ms)', 'Overhead (%)']),
            cells=dict(values=[
                pause_summary.index, 
                pause_summary['count'],
                pause_summary['min'].round(3),
                pause_summary['max'].round(3),
                pause_summary['sum'].round(3),
                pause_summary['Overhead']
            ]),
            columnwidth=[1, 0.5, 0.5, 0.5, 0.5, 0.5]
        )
        fig.add_trace(table_trace, row=1, col=1)

        # Add the pie chart to the second column
        pie_trace = go.Pie(
            labels=pause_summary.index,
            values=pause_summary['sum'],
            name='Pause Type Contribution'
        )
        fig.add_trace(pie_trace, row=1, col=2)

        fig.update_layout(
            title_text='GC Pause Summary and Contribution',
            showlegend=False
        )
        return fig

    # Plotting the TotalHeap line (use appropriate column based on before/after)
    # Default to TotalHeap if total_heap_column wasn't set
    if 'total_heap_column' not in locals():
        total_heap_column = 'TotalHeap'
    
    fig.add_trace(go.Scatter(
        x=data_df['Runtime'], 
        y=data_df[total_heap_column], 
        mode='lines+markers', 
        name='Total Heap', 
        line=dict(color=colors['TotalHeap'])
    ))

    # Add markers for each GC pause event, excluding the total heap line
    for pause, color in colors.items():
        if pause != "TotalHeap":
            subset = data_df[data_df['PauseName'] == pause]
            if not subset.empty:
                fig.add_trace(go.Scatter(
                    x=subset['Runtime'], 
                    y=subset[y_value],
                    mode='markers', 
                    name=pause, 
                    marker=dict(color=color, symbol=markers[pause])
                ))

    fig.update_layout(
        title=title, 
        xaxis_title='Runtime (seconds)', 
        yaxis_title='Memory (MB)'
    )
    return fig


if __name__ == '__main__':
    print(f"Enhanced Heap Plotter v2.0")
    print(f"Starting Dash server on http://localhost:{DEFAULT_PORT}")
    if ENHANCED_PARSER_AVAILABLE:
        print("Enhanced G1 sizing support: ENABLED")
    else:
        print("Enhanced G1 sizing support: DISABLED (parse_g1_regions not found)")
    app.run(debug=True, port=DEFAULT_PORT)

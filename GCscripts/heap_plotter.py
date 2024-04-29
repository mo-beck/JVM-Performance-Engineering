import base64
import io
import re
import os
import pandas as pd
import subprocess
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from parse_g1_regions import plot_rates, parse_g1_log

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
                html.A('Select GC Log File')
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
            multiple=False
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
                {'label': 'Pause Duration', 'value': 'duration'},  # New option for pause duration
                {'label': 'GC Scaling Plot', 'value': 'scaling'},  # New option for GC scaling plot
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
     Output('menu-selection', 'options')],  # Add the output for the dropdown options
    [Input('menu-selection', 'value'),
     Input('upload-data', 'contents'),
     Input('upload-data', 'filename')]
)
def update_output(selected_value, contents, filename):
    if contents is None or filename is None:
        return dash.no_update, "No file selected", dash.no_update

    try:
        # Decode the file content based on its format
        if ',' in contents:
            _, content_string = contents.split(',')
            log_content = base64.b64decode(content_string).decode('utf-8')
        else:
            log_content = contents

        # Parse the GC log content
        data_df, scaling_data_df, is_g1, jdk_version = parse_gc_log(log_content)

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
            dropdown_options.append({'label': 'G1 GC Region Rates', 'value': 'g1-rates'})

        # Generate the appropriate plot based on the selected value
        if is_g1 and selected_value == 'g1-rates':
            g1_rates = parse_g1_log(log_content) 
            fig = plot_rates(g1_rates)
        else:
            fig = generate_plot(data_df, scaling_data_df, selected_value)

        # Display the name of the selected file
        filename_display = f"Selected file: {filename}"
        if jdk_version:
            filename_display += f" | JDK Version: {jdk_version}"

        return fig, filename_display, dropdown_options
    except Exception as e:
        # Handle unexpected errors during file processing
        return dash.no_update, f"An error occurred while processing the file: {e}", dash.no_update

def parse_gc_log(log_content):
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
            # runtime, pause_type, heap_before, heap_after, total_heap, duration = pause_match.groups()
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
                                   
            gc_data.append({
                "Runtime": float(runtime),
                "HeapBefore": int(heap_before),
                "HeapAfter": int(heap_after),
                "TotalHeap": int(total_heap),
                "PauseName": pause_name,
                "Duration": float(duration)
            })
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
    fig = go.Figure()
    # Initialize variables for later use
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
        # Return the figure early for the 'scaling' option
        return fig

    # Handle the 'before' and 'after' plot options
    elif selected_value == 'before':
        y_value = 'HeapBefore'
        title = 'Heap Occupancy Before GC'
    elif selected_value == 'after':
        y_value = 'HeapAfter'
        title = 'Heap Occupancy After GC'

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
        # Return the figure early for the 'duration' option
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
            column_widths=[0.5, 0.5],  # Adjust the width of the columns if needed
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
        # Return the figure early for the 'summary' option
        return fig

    # Plotting the TotalHeap line
    fig.add_trace(go.Scatter(
        x=data_df['Runtime'], 
        y=data_df['TotalHeap'], 
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
    app.run_server(debug=True, port=8051)


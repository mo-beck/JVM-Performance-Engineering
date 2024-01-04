import base64 
import io
import re
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
                html.A('Select Z GC Log File')
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
    html.Div(id='jdk-version-display'),

    # Sidebar with Dropdown Menu
    html.Div([
        dcc.Dropdown(
            id='menu-selection',
            options=[
                {'label': 'GC Pause Duration', 'value': 'pause'},
                {'label': 'GC Concurrent Phase Duration', 'value': 'concurrent'},
                {'label': 'GC Page Sizes', 'value': 'pgsz'},
                {'label': 'GC Cause', 'value': 'cause'}
            ],
            value='pause',
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
     Output('filename-display', 'children')],
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename'),
     Input('menu-selection', 'value')]
)

def update_output(contents, filename, selected_value):
    if contents is None:
        return dash.no_update, "No file selected"

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    log_content = io.StringIO(decoded.decode('utf-8')).read()

    # Parse the GC log content
    gc_pause_df, concurrent_phase_df, gc_pgsz_df, gc_cause_df, jdk_version = parse_gc_log(log_content) 
    
    fig = generate_plot(gc_pause_df, concurrent_phase_df, gc_pgsz_df, gc_cause_df, selected_value)
   
    # Update the filename display
    filename_display = f"Selected file: {filename}"
    if jdk_version:
        filename_display += f" | JDK Version: {jdk_version}"

    return fig, filename_display      

def parse_gc_log(log_content):

    # Initialize an empty list to store the parsed data
    gc_pause_data = []
    concurrent_phase_data = []
    gc_pgsz_data = []
    gc_cause_data = []

    # Regular expression patterns for GC pause and concurrent phase log lines
    gc_pause_pattern = re.compile(r"\[(\d+\.\d+)s\].*\bGC\((\d+)\) Pause (\w+)(?: Start| End)? (\d+\.\d+)ms")
    gc_concurrent_pattern = re.compile(r"\[(\d+\.\d+)s\].*GC\((\d+)\) Concurrent (\w+) (\d+\.\d+)ms")
    gc_pgsz_pattern = re.compile(r"\[(\d+\.\d+)s\].*GC\((\d+)\) (\w+) Pages: (\d+) / (\d+)M, Empty: (\d+)M, Relocated: (\d+)M, In-Place: (\d+)")
    gc_cause_pattern = re.compile(r"\[(\d+\.\d+)s\].*GC\((\d+)\) Garbage Collection \((.+?)\) (\d+)M\((\d+)%\)->(\d+)M\((\d+)%\)")
    jdk_version_pattern = re.compile(r"\[\d+\.\d+s\]\[info\]\[gc,init\] Version: (\d+\.\d+\.\d+\+\d+-LTS(?:-\d+)?) \(release\)")

    jdk_version = None
    lines = log_content.splitlines()

    for line in lines:
        pause_match = gc_pause_pattern.match(line)
        concurrent_match = gc_concurrent_pattern.match(line)
        pgsz_match = gc_pgsz_pattern.match(line)
        cause_match = gc_cause_pattern.match(line)
        version_match = jdk_version_pattern.search(line)

        if pause_match:
            time, gc_cycle, pause_type, duration = pause_match.groups()
            gc_pause_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'PauseType': pause_type,
                'Duration': float(duration)
            })
        elif concurrent_match:
            time, gc_cycle, phase_type, duration = concurrent_match.groups()
            concurrent_phase_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'PhaseType': phase_type,
                'Duration': float(duration)
            })
        elif pgsz_match:
            time, gc_cycle, page_type, used_pages, total_pages, empty_pages, relocated_pages, inplace_pages = pgsz_match.groups()
            gc_pgsz_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'PageType': page_type,
                'UsedPages': int(used_pages),
                'TotalPages': int(total_pages),
                'EmptyPages': int(empty_pages),
                'RelocatedPages': int(relocated_pages),
                'InPlacePages': int(inplace_pages)
            })
        elif cause_match:
            time, gc_cycle, cause, before_usage, before_percent, after_usage, after_percent = cause_match.groups()
            gc_cause_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'Cause': cause,
                'BeforeUsage': int(before_usage),
                'BeforePercent': int(before_percent),
                'AfterUsage': int(after_usage),
                'AfterPercent': int(after_percent)
            })
        elif version_match:
            jdk_version = version_match.group(1)

    # Convert the lists of data to DataFrames
    gc_pause_df = pd.DataFrame(gc_pause_data)
    concurrent_phase_df = pd.DataFrame(concurrent_phase_data)
    gc_pgsz_df = pd.DataFrame(gc_pgsz_data)
    gc_cause_df = pd.DataFrame(gc_cause_data)

    return gc_pause_df, concurrent_phase_df, gc_pgsz_df, gc_cause_df, jdk_version

def generate_plot(gc_pause_df, concurrent_phase_df, gc_pgsz_df, gc_cause_df, selected_value):
    fig = go.Figure()
    if gc_pause_df.empty or concurrent_phase_df.empty or gc_pgsz_df.empty or gc_cause_df.empty:
        return fig  # Return an empty figure

    if selected_value == 'pause':
        # Add traces for each pause type
        for pause_type in gc_pause_df['PauseType'].unique():
            pause_df = gc_pause_df[gc_pause_df['PauseType'] == pause_type]
            fig.add_trace(go.Scatter(
                x=pause_df['Time'],
                y=pause_df['Duration'],
                mode='lines+markers',
                name=f'Pause {pause_type}'
            ))
        fig.update_layout(
            title='GC Pause Duration Over Runtime',
            xaxis_title='Time (s)',
            yaxis_title='Duration (ms)',
            legend_title='Pause Types'
        )
        return fig

    elif selected_value == 'concurrent':
        # Add traces for each concurrent phase type
        for phase_type in concurrent_phase_df['PhaseType'].unique():
            phase_df = concurrent_phase_df[concurrent_phase_df['PhaseType'] == phase_type]
            fig.add_trace(go.Scatter(
                x=phase_df['Time'],
                y=phase_df['Duration'],
                mode='lines+markers',
                name=f'Concurrent {phase_type}'
            ))
        fig.update_layout(
            title='Concurrent Phase Duration Over Runtime',
            xaxis_title='Time (s)',
            yaxis_title='Duration (ms)',
            legend_title='Concurrent Phases'
        )
        return fig

    elif selected_value == 'pgsz':
        # Group the data by 'Time' to get the sum of pages for each type at each time point
        pgsz_grouped = gc_pgsz_df.groupby(['Time', 'PageType']).sum().reset_index()
        # Plot each page type
        for page_type in pgsz_grouped['PageType'].unique():
            page_type_df = pgsz_grouped[pgsz_grouped['PageType'] == page_type]
            fig.add_trace(go.Bar(
                x=page_type_df['Time'],
                y=page_type_df['UsedPages'],
                name=f'{page_type}',
                offsetgroup=page_type,
                # Set the width of the bars for visibilty
                width=3
            ))
        fig.update_layout(
            barmode='group',
            title='Page Sizes Usage Over Time',
            xaxis_title='Time (s)',
            yaxis_title='Pages Used',
            legend_title='Page Types'
        )
        return fig

    # Plot logic for GC causes
    elif selected_value == 'cause':
        fig = make_subplots(
            rows=2, cols=1,
            specs=[[{'type': 'xy'}], [{'type': 'domain'}]],
            subplot_titles=('GC Over Time', 'GC Cause Distribution'),
            vertical_spacing=0.2  # Adjust the space between the subplots
            )
        # Plot the 'BeforeUsage' and 'AfterUsage' for each GC cycle
        fig.add_trace(go.Scatter(
            x=gc_cause_df['Time'],
            y=gc_cause_df['BeforeUsage'],
            mode='lines+markers',
            name='Before GC Usage'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=gc_cause_df['Time'],
            y=gc_cause_df['AfterUsage'],
            mode='lines+markers',
            name='After GC Usage'
        ), row=1, col=1)

        # Create a pie chart for the distribution of GC causes on the second row
        cause_counts = gc_cause_df['Cause'].value_counts()
        fig.add_trace(go.Pie(
            labels=cause_counts.index,
            values=cause_counts.values,
            name='GC Cause Distribution',
            showlegend=False  # Hide legend for the pie chart
        ), row=2, col=1)

        # Update layout for the first row
        fig.update_xaxes(title_text='Time (s)', row=1, col=1)
        fig.update_yaxes(title_text='Memory Usage (MB)', row=1, col=1)
        
        # Update the overall layout
        fig.update_layout(
            title_text='GC Cause Details and Distribution',
            height=800,
            width=800,
        )
        return fig

if __name__ == '__main__':
    app.run_server(debug=True, port=8052)


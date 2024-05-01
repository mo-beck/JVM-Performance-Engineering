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

generation_mapping = {
    'O': 'Old',
    'Y': 'Young'
}

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
    gc_pause_pattern = re.compile(r"\[(\d+\.\d+)s\].*\bGC\((\d+)\) (\w): Pause ((?:\w+\s)+\w+(?: \(\w+\))?)(?:\s+)?(\d+\.\d+)ms")
    gc_concurrent_pattern = re.compile(r"\[(\d+\.\d+)s\].*\bGC\((\d+)\) (\w): Concurrent ([\w\s]+) (\d+\.\d+)ms")
    gc_pgsz_pattern = re.compile(r"\[(\d+\.\d+)s\].*GC\((\d+)\) (\w): (\w+) Pages:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)M\s+(\d+)M\s+(\d+)M")
    gc_cause_pattern = re.compile(r"\[(\d+\.\d+)s\].*GC\((\d+)\) (Minor|Major) Collection \((.+?)\) (\d+)M\((\d+)%\)->(\d+)M\((\d+)%\) (\d+\.\d+)s")
    jdk_version_pattern = re.compile(r"\[\d+\.\d+s\]\[info\]\[gc,init\] Version: (\d+\.\d+\.\d+\+\d+-LTS(?:-\d+)?) \(release\)")

    jdk_version = None
    lines = log_content.splitlines()

    for line in lines:
        pause_match = gc_pause_pattern.search(line)
        concurrent_match = gc_concurrent_pattern.search(line)
        pgsz_match = gc_pgsz_pattern.search(line)
        cause_match = gc_cause_pattern.search(line)
        version_match = jdk_version_pattern.search(line)

        if pause_match:
            time, gc_cycle, gen_type, pause_type, duration = pause_match.groups()
            full_gen_type = generation_mapping.get(gen_type.upper(), "Unknown")  # Default to 'Unknown' if key not found
            gc_pause_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'Generation': full_gen_type,
                'PauseType': pause_type,
                'Duration': float(duration)
            })
        elif concurrent_match:
            time, gc_cycle, gen_type, phase_type, duration = concurrent_match.groups()
            full_gen_type = generation_mapping.get(gen_type.upper(), "Unknown")  # Default to 'Unknown' if key not found
            concurrent_phase_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'Generation': full_gen_type,
                'PhaseType': phase_type,
                'Duration': float(duration)
            })
        elif pgsz_match:
            time, gc_cycle, gen_type, page_type, candidates, selected, in_place, size, empty, relocated = pgsz_match.groups()
            full_gen_type = generation_mapping.get(gen_type.upper(), "Unknown")  # Default to 'Unknown' if key not found
            gc_pgsz_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'Generation': full_gen_type,
                'PageType': page_type,
                'Candidates': int(candidates),
                'Selected': int(selected),
                'In-Place': int(in_place),
                'Sizes': size + 'M',
                'Empty': empty + 'M',
                'Relocated': relocated + 'M'
            })
        elif cause_match:
            time, gc_cycle, collection_type, cause, before_usage, before_percent, after_usage, after_percent, duration = cause_match.groups()
            gc_cause_data.append({
                'Time': float(time),
                'GCCycle': int(gc_cycle),
                'CollectionType': collection_type,
                'Cause': cause,
                'BeforeUsage': before_usage + 'M',
                'BeforePercent': before_percent + '%',
                'AfterUsage': after_usage + 'M',
                'AfterPercent': after_percent + '%',
                'Duration': float(duration)
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
        print("dataframes are empty")
        return fig  # Return an empty figure

    if selected_value == 'pause':
        # Add traces for each pause type and generation
        for pause_type in gc_pause_df['PauseType'].unique():
            for generation in gc_pause_df['Generation'].unique():
                pause_df = gc_pause_df[(gc_pause_df['PauseType'] == pause_type) & (gc_pause_df['Generation'] == generation)]
                fig.add_trace(go.Scatter(
                    x=pause_df['Time'],
                    y=pause_df['Duration'],
                    mode='lines+markers',
                    name=f'{generation} Pause {pause_type}'
                ))
        fig.update_layout(
            title='GC Pause Duration Over Runtime by Generation',
            xaxis_title='Time (s)',
            yaxis_title='Duration (ms)',
            legend_title='Pause Types and Generations'
        )
        return fig

    elif selected_value == 'concurrent':
        # Add traces for each concurrent phase type and generation
        for phase_type in concurrent_phase_df['PhaseType'].unique():
            for generation in concurrent_phase_df['Generation'].unique():
                phase_df = concurrent_phase_df[(concurrent_phase_df['PhaseType'] == phase_type) & (concurrent_phase_df['Generation'] == generation)]
                fig.add_trace(go.Scatter(
                    x=phase_df['Time'],
                    y=phase_df['Duration'],
                    mode='lines+markers',
                    name=f'{generation} Concurrent {phase_type}'
                ))
        fig.update_layout(
            title='Concurrent Phase Duration Over Runtime by Generation',
            xaxis_title='Time (s)',
            yaxis_title='Duration (ms)',
            legend_title='Concurrent Phases and Generations'
        )
        return fig

    elif selected_value == 'pgsz':
        # Group the data by 'Time', 'Generation, and 'PageType' to get the sum of pages for each type at each time point
        pgsz_grouped = gc_pgsz_df.groupby(['Time', 'Generation', 'PageType']).sum().reset_index()

        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Old Generation', 'Young Generation'),
            shared_xaxes=True
        )

        # Plot each page type and generation combination
        for (generation, page_type), group in pgsz_grouped.groupby(['Generation','PageType']):
            trace = go.Scatter(
                x=group['Time'],
                y=group['Sizes'].str.replace('M', '').astype(float),
                name=f'{generation} {page_type}',
                mode='lines+markers',
                marker=dict(symbol='cross', size=10),  # Adjust the size
                line=dict(width=1)
            )
            if generation == 'Old':
                fig.add_trace(trace, row=1, col=1)  # First row for Old
            elif generation == 'Young':
                fig.add_trace(trace, row=2, col=1)  # Second row for Young

        fig.update_layout(
            title='Page Sizes Over Time by Generation',
            height=800
        )
        fig.update_xaxes(title_text='Time (s)', row=1, col=1) 
        fig.update_yaxes(title_text='Page Sizes (MB)',row=1, col=1)

        fig.update_xaxes(title_text='Time (s)', row=2, col=1) 
        fig.update_yaxes(title_text='Page Sizes (MB)',row=2, col=1) 

        return fig

    # Plot logic for GC causes
    elif selected_value == 'cause':
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'xy'}, {'type': 'table'}], 
                   [{'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=('GC Usage Over Time', 'Summary Table', 'GC Cause Distribution', 'GC Duration Categories'),
            vertical_spacing=0.2  # Adjust the space between the subplots
        )
        # Iterate through each collection type for a more detailed breakdown
        for collection_type in gc_cause_df['CollectionType'].unique():
            filtered_df = gc_cause_df[gc_cause_df['CollectionType'] == collection_type]
        
            # Plot the 'BeforeUsage' and 'AfterUsage' for each GC cycle by collection type
            fig.add_trace(go.Scatter(
                x=filtered_df['Time'],
                y=filtered_df['BeforeUsage'].str.replace('M', '').astype(float),
                mode='lines+markers',
                name=f'Before {collection_type} Usage'
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=filtered_df['Time'],
                y=filtered_df['AfterUsage'].str.replace('M', '').astype(float),
                mode='lines+markers',
                name=f'After {collection_type} Usage'
            ), row=1, col=1)

        # Create the summary table
        duration_sum = gc_cause_df.groupby(['CollectionType', 'Cause'])['Duration'].sum().reset_index()
        duration_sum['Label'] = duration_sum['CollectionType'] + ' - ' + duration_sum['Cause']

        fig.add_trace(go.Table(
            header=dict(values=['Collection Type', 'Cause', 'Duration'],
                        align='left', font=dict(size=12, color='white'), fill_color='gray'),
            cells=dict(values=[duration_sum['CollectionType'], duration_sum['Cause'], duration_sum['Duration']],
                        align='left')
        ), row=1, col=2)

        # Create a pie chart for the distribution of GC causes
        cause_counts = gc_cause_df['Cause'].value_counts()
        fig.add_trace(go.Pie(
            labels=cause_counts.index,
            values=cause_counts.values,
            name='GC Cause Distribution',
            showlegend=False  # Hide legend for the pie chart
        ), row=2, col=1)

        # Create a pie chart for GC duration categories
        fig.add_trace(go.Pie(
            labels=duration_sum['Label'],
            values=duration_sum['Duration'],
            name='GC Duration Categories',
            showlegend=False
        ), row=2, col=2)

        # Update layout for the first row
        fig.update_xaxes(title_text='Time (s)', row=1, col=1)
        fig.update_yaxes(title_text='Memory Usage (MB)', row=1, col=1)
        
        # Update the overall layout
        fig.update_layout(
            title_text='GC Cause Details, Distribution, and Duration by Collection Type',
            height=800,
            width=1400,
        )
        return fig

if __name__ == '__main__':
    app.run_server(debug=True, port=8053)


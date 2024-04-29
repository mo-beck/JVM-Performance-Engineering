import re
import sys
import plotly.graph_objs as go

def parse_g1_log(log_content):
    # Regex patterns to match the necessary information
    runtime_pattern = r"\[(\d+\.\d+)s\]"
    region_pattern = r"GC\(\d+\) (\w+) regions: (\d+)->(\d+)"
    region_size_pattern = r"Heap Region Size: (\d+)M"

    # Variables to store the parsed data
    region_data = {'Eden': [], 'Survivor': [], 'Old': [], 'Humongous': []}
    region_size = 0

    lines = log_content.splitlines()
    for line in lines:
        # Check for region size
        size_match = re.search(region_size_pattern, line)
        if size_match:
            region_size = int(size_match.group(1))
            continue

        # Check for runtime and region information
        runtime_match = re.search(runtime_pattern, line)
        region_match = re.search(region_pattern, line)
        if runtime_match and region_match:
            runtime = float(runtime_match.group(1))
            region_type, before, after = region_match.groups()
            before = int(before)
            after = int(after)    
            if region_type in region_data:
                region_data[region_type].append((runtime, before, after))

    return region_data

# Plotting function
def plot_regions(region_data):
    fig = go.Figure()

    for region_type, data_points in region_data.items():
        runtime, before, after = zip(*data_points)

        fig.add_trace(go.Scatter(
            x=runtime,
            y=before,
            mode='lines+markers',
            name=f'{region_type} Before GC',
            line=dict(shape='hv'),
            #connectgaps=True,  # this will connect gaps in the data
        ))
        fig.add_trace(go.Scatter(
            x=runtime,
            y=after,
            mode='lines+markers',
            name=f'{region_type} After GC',
            line=dict(shape='hv'),  # hv makes horizontal-vertical steps
        ))

    fig.update_layout(
        title='GC Region States Over Time',
        xaxis_title='Runtime (s)',
        yaxis_title='Total Count of Regions',
        legend_title='Region States',
        legend=dict(
            itemsizing='constant',
            traceorder='normal',
            font=dict(
                size=12,
            ),
            bgcolor='rgba(255,255,255,0.5)',
            bordercolor='rgba(0,0,0,0)',
            borderwidth=1,
        ),
    )
    return fig

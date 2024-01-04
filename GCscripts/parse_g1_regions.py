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

    # Calculate rates for each region type
    rates = {key: [] for key in region_data}
    for region_type in region_data:
        if region_type == 'Eden':
            # For Eden, use the 'before' value of the current GC event
            # and the 'after' value of the previous GC event
            for i in range(1, len(region_data[region_type])):
                prev_runtime, prev_before, prev_after = region_data[region_type][i-1]
                runtime, before, after = region_data[region_type][i]

                # Calculate the change in memory in MB
                memory_change = (before - prev_after) * region_size

                # Ensure we're not dividing by zero
                time_difference = runtime - prev_runtime
                if time_difference > 0:
                    rate = memory_change / time_difference  # MB/s
                    rates[region_type].append((runtime, rate))
        else:
            # For other regions, use the 'after' values
            for i in range(1, len(region_data[region_type])):
                prev_runtime, prev_before, prev_after = region_data[region_type][i-1]
                runtime, before, after = region_data[region_type][i]

                # Calculate the change in memory in MB
                memory_change = (after - prev_after) * region_size

                # Ensure we're not dividing by zero
                time_difference = runtime - prev_runtime
                if time_difference > 0:
                    rate = memory_change / time_difference  # MB/s
                    rates[region_type].append((runtime, rate))
    return rates

# Plotting function
def plot_rates(rates):
    fig = go.Figure()

    for region_type, data_points in rates.items():
        runtime, rate = zip(*data_points)
        fig.add_trace(go.Scatter(
            x=runtime,
            y=rate,
            mode='lines+markers',
            name=region_type,
            line=dict(shape='linear'),
            connectgaps=True,  # this will connect gaps in the data
        ))

    fig.update_layout(
        title='GC Region Rates Over Time',
        xaxis_title='Runtime (s)',
        yaxis_title='Rate (MB/s)',
        legend_title='Region Types',
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

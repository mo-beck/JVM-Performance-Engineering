# heap_plotter.py

### Overview
`heap_plotter.py` is a Python script for visualizing Java Parallel GC and G1 GC logs, specifically focusing on heap occupancy and GC pause statistics. The script uses the Dash framework for creating an interactive dashboard.

### Features
- **Heap Occupancy Visualization**: View heap occupancy before and after GC events.
- **GC Pause Duration Analysis**: Analyze the duration of different GC pause types over time.
- **GC Scaling Plot**: Visualize the scaling factor and system time over runtime.
- **Pause Summary**: Summarize the pause events, showing their contribution to runtime overhead.
- **G1 GC Region Analysis**: Dedicated visualization for G1 GC regions (requires `parse_g1_regions.py`).

### Dependencies
- Python 3.x
- Dash
- Plotly
- Pandas

You can install these dependencies using pip:
`pip install dash plotly pandas`

### Usage
1. **Run the Script**: Start the server by executing the script:`python3 heap_plotter.py`
2. **Open the Dashboard**: Visit `http://localhost:8051` to access the interactive dashboard.
3. **Upload the GC Log**: Use the file upload option to upload a Java GC log file.
4. **Select Visualization**: Use the sidebar menu to select the type of visualization.

### Visualization Options
- **Heap Occupancy Before GC**: Shows heap occupancy before each GC event.
- **Heap Occupancy After GC**: Shows heap occupancy after each GC event.
- **Pause Duration**: Plots the duration of each GC pause type.
- **GC Scaling Plot**: Displays the scaling factor and system time over runtime.
- **Pause Summary**: Summarizes the pauses with counts, min/max durations, and overhead.
- **G1 GC Region**: If using G1 GC, provides region-specific analysis (requires parse_g1_regions.py).

### Customization
- Colors and Markers: Modify the colors and markers dictionaries to customize the appearance of the plots.
- Port Number: Change the port number in the script (default: 8051).

### Requirements for G1 GC
If analyzing G1 GC logs, ensure parse_g1_regions.py is available for region analysis.

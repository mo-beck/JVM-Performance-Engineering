# zgc_plotter.py

### Overview
`zgc_plotter.py` is a Python script for visualizing Java ZGC (pre-generational) logs, focusing on GC pause duration, concurrent phase duration, page sizes, and GC causes. The script uses the Dash framework for creating an interactive dashboard.

### Features
- **GC Pause Duration Analysis**: Analyze the duration of different GC pause types over time.
- **Concurrent Phase Duration Analysis**: Analyze the duration of ZGC concurrent phases.
- **GC Page Sizes Analysis**: Track page size usage over time.
- **GC Cause Analysis**: Display a distribution of GC causes.

### Dependencies
- Python 3.x
- Dash
- Plotly
- Pandas

You can install these dependencies using pip:
`pip install dash plotly pandas`

### Usage
1. **Run the Script**: Start the server by executing the script: `python3 zgc_plotter.py`
2. **Open the Dashboard**: Visit `http://localhost:8052` to access the interactive dashboard.
3. **Upload the ZGC Log**: Use the file upload option to upload a Java ZGC log file.
4. **Select Visualization**: Use the sidebar menu to select the type of visualization.

### Visualization Options
- **GC Pause Duration**: Visualize the duration of different GC pauses over time.
- **Concurrent Phase Duration**: Analyze the duration of ZGC concurrent phases.
- **GC Page Sizes**: Track page size usage over time.
- **GC Cause Analysis**: Display a distribution of GC causes.

### Customization
- Port Number: Change the port number in the script (default: 8052).

### Notes
- Ensure that the log file being used is correctly formatted and contains ZGC log entries.
- The pie chart for GC causes requires sufficient data to display meaningful results.


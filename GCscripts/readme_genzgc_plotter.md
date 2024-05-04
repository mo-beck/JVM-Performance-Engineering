# genzgc_plotter.py

### Overview
`generational_zgc_plotter.py` is a Python script that offers an interactive dashboard for visualizing Java Generational ZGC logs. It focuses on analyzing GC pauses, concurrent phases, page sizes, and GC causes, with the ability to differentiate between old and young generations.

### Features
- **GC Pause Duration Analysis**: Analyze the duration of different GC pause types, categorized by generation.
- **Concurrent Phase Duration Analysis**: Visualize the duration of concurrent phases in generational ZGC.
- **GC Page Sizes**: Track and compare page size usage in both old and young generations.
- **GC Cause Analysis**: Analyze GC causes and categorize their impact by memory usage and duration.

### Dependencies
- Python 3.x
- Dash
- Plotly
- Pandas

You can install these dependencies using pip: `pip install dash plotly pandas`

### Usage
1. **Run the Script**: Start the server by executing the script: `python3 genzgc_plotter.py`
2. **Open the Dashboard**: Visit `http://localhost:8053` to access the interactive dashboard.
3. **Upload the ZGC Log**: Use the file upload option to upload a generational ZGC log file.
4. **Select Visualization**: Use the sidebar menu to select the type of visualization.

### Visualization Options
- **GC Pause Duration**: Visualize the duration of different GC pauses over time, categorized by generation.
- **Concurrent Phase Duration**: Analyze the duration of ZGC concurrent phases.
- **GC Page Sizes**: Track page size usage across old and young generations.
- **GC Cause Analysis**: Analyze GC causes with pie charts and summary tables.

### Customization
- Port Number: Change the port number in the script (default: 8053).

### Notes
- Make sure the log file is properly formatted and contains generational ZGC log entries.

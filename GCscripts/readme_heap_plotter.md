# heap_plotter.py

### Overview
`heap_plotter.py` is an enhanced Python script for visualizing Java G1 GC logs with comprehensive time-based heap sizing analysis. This enhanced version maintains compatibility with traditional GC log analysis while adding advanced G1 sizing activity visualizations.

### Features
- **Traditional GC Analysis**: Heap occupancy, pause duration, scaling, and summary visualizations
- **G1 Region Transitions**: Interactive visualization of region state changes and uncommit operations
- **Time-based Heap Sizing**: Analysis of G1's uncommit-only mode with evaluation timeline
- **Sizing Activity Summary**: Comprehensive statistics with synchronized timelines and evaluation outcomes
- **Modern Log Format Support**: Handles both traditional `[time]s` and modern `[timestamp][pid][tid]` formats
- **Conditional Display**: Shows sizing visualizations only when G1 Time-Based Heap Sizing is enabled

### Dependencies
- Python 3.x
- Dash
- Plotly
- Pandas
- NumPy
- parse_g1_regions.py (for G1 sizing data)

You can install these dependencies using pip:
`pip install dash plotly pandas numpy`

### Usage
1. **Run the Script**: Start the server by executing the script:
   ```
   python heap_plotter.py
   ```
2. **Open the Dashboard**: Visit `http://localhost:8051` to access the interactive dashboard.
3. **Upload the GC Log**: Use the file upload option to upload a Java GC log file.
4. **Select Visualization**: Use the sidebar menu to select the type of visualization.

### Visualization Options
- **Heap Occupancy Before/After GC**: Traditional heap occupancy analysis
- **Pause Duration**: Duration analysis of different GC pause types
- **GC Scaling Plot**: Scaling factor and system time visualization
- **Pause Summary**: Comprehensive pause statistics and overhead analysis
- **G1 GC Region**: Traditional G1 region analysis
- **Sizing Activity Summary**: Memory uncommit operations and evaluation outcomes (G1 uncommit-only mode)
- **Heap Evaluation Timeline**: Decision-making process and evaluation results over time
- **Region Transitions**: G1 region state transitions with uncommit rate analysis

### Enhanced Features for G1 Time-Based Sizing
- **Uncommit Rate Analysis**: Visualizes G1's conservative uncommit strategy (target: 20-25% of inactive regions)
- **Dual Metric Display**: Shows both uncommit efficiency (%) and memory impact (MB)
- **Synchronized Timelines**: All time-based plots share consistent x-axis scaling with padding
- **G1 Constraints Visualization**: Displays design constraints (25% inactive limit, 10% total committed limit)
- **Evaluation Process**: Shows the relationship between evaluations, decisions, and actual uncommit operations

### Supported Log Formats
- Traditional GC logs (`[time]s` format)
- Modern GC logs (`[timestamp][pid][tid]` format)
- G1 logs with time-based heap sizing data (uncommit-only mode)

### Customization
- **Configuration Constants**: DEFAULT_PORT (8051), CHART_HEIGHT (700), etc.
- **Colors and Markers**: Modify the colors and markers dictionaries for visual customization
- **Plot Heights**: Adjust EVALUATION_TIMELINE_HEIGHT and REGION_TRANSITIONS_HEIGHT

### Requirements for Enhanced G1 Analysis
Ensure `parse_g1_regions.py` is available for full G1 sizing analysis. The plotter will fall back to basic functionality if the enhanced parser is not found.

### Notes
- Enhanced sizing visualizations appear only when G1 Time-Based Heap Sizing is enabled in uncommit-only mode
- All timestamp formats are automatically normalized to relative runtime for consistent visualization
- The tool automatically detects log format and adjusts parsing accordingly

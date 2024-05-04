# parse_g1_regions.py

### Overview
`parse_g1_regions.py` is a Python script specifically designed for parsing and visualizing G1 GC region data from Java GC logs. It provides a clear visualization of GC regions' state changes over time.

### Features
- **Parsing G1 GC Logs**: Extracts region information from G1 GC logs, identifying the runtime, region types, and their state changes before and after GC events.
- **Visualizing Region Data**: Uses Plotly to visualize the parsed region data with interactive graphs showing changes over time.

### Dependencies
- Python 3.x
- Plotly

You can install these dependencies using pip:
`pip install plotly`

### Usage 
1. Import the Functions: Import the functions into your Python project:
```
  from parse_g1_regions import parse_g1_log, plot_regions
```
3. Read the GC Log: Read the GC log file content:
```
  with open('path_to_gc_log.log', 'r') as log_file:
    log_content = log_file.read()
```
4. Parse and Plot the Data:
   - Parse the region data using parse_g1_log:
   ```
     region_data = parse_g1_log(log_content)
   ```
   - Plot the parsed data using plot_regions:
   ```
     fig = plot_regions(region_data)
     fig.show()`
   ```

### Functions
- `parse_g1_log(log_content)`: Parses the provided GC log content to extract region data.
   - Parameters: `log_content` (string): The content of the GC log file.
   - Returns: `region_data` (dict): A dictionary containing the parsed region data.
- `plot_regions(region_data`): Creates a plot based on the parsed region data.
   - Parameters: `region_data` (dict): The dictionary containing the parsed region data.
   - Returns: `fig` (Plotly Figure): The generated plotly figure object.

### Notes
- Ensure the GC log file is in the expected format to guarantee successful parsing.
- Adjust the visualization appearance by modifying the `plot_regions` function.

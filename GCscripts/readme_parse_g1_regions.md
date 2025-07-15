# parse_g1_regions.py

### Overview
`parse_g1_regions.py` is an enhanced Python script for parsing and analyzing G1 GC logs with comprehensive time-based heap sizing support. It extends traditional G1 region parsing with advanced sizing activity analysis and modern log format support.

### Features
- **Enhanced G1 Log Parsing**: Extracts region data, sizing activities, and evaluation processes from G1 GC logs
- **Time-Based Sizing Analysis**: Parses uncommit operations, heap evaluations, and sizing decisions
- **Modern Log Format Support**: Handles both traditional `[time]s` and modern `[timestamp][pid][tid]` log formats
- **Automatic Mode Detection**: Identifies G1 Time-Based Heap Sizing (uncommit-only) configuration
- **Comprehensive Data Export**: Provides structured data for visualization tools
- **Timestamp Normalization**: Converts various timestamp formats to consistent datetime objects

### Dependencies
- Python 3.x
- Plotly

You can install these dependencies using pip:
`pip install plotly`

### Usage 
#### As a Library
1. **Import the Enhanced Parser**: Import the enhanced parser class:
   ```python
   from parse_g1_regions import G1EnhancedParser, plot_regions
   ```

2. **Parse GC Log Content**:
   ```python
   parser = G1EnhancedParser()
   
   # From file
   with open('path_to_gc_log.log', 'r') as log_file:
       log_content = log_file.read()
   parser.parse_log_content(log_content)
   
   # Check for sizing data
   if parser.has_sizing_data and parser.has_uncommit_only_sizing():
       print("G1 Time-Based Heap Sizing detected (uncommit-only mode)")
   ```

3. **Access Parsed Data**:
   ```python
   # Traditional region data
   region_data = parser.get_region_data()
   
   # Sizing activity data
   sizing_entries = parser.sizing_entries
   
   # Export to JSON
   json_data = parser.to_json()
   ```

#### Traditional Usage (Backward Compatible)
1. **Import the Functions**: Import the functions into your Python project:
   ```python
   from parse_g1_regions import parse_g1_log, plot_regions
   ```

2. **Read the GC Log**: Read the GC log file content:
   ```python
   with open('path_to_gc_log.log', 'r') as log_file:
       log_content = log_file.read()
   ```

3. **Parse and Plot the Data**:
   - Parse the region data using parse_g1_log:
     ```python
     region_data = parse_g1_log(log_content)
     ```
   - Plot the parsed data using plot_regions:
     ```python
     fig = plot_regions(region_data)
     fig.show()
     ```

### Key Classes and Methods
- **G1EnhancedParser**: Main parser class with comprehensive G1 log analysis
  - `parse_log_content(content)`: Parse GC log content from string
  - `has_uncommit_only_sizing()`: Check if uncommit-only mode is detected
  - `get_region_data()`: Get traditional region transition data
  - `to_json()`: Export all parsed data as JSON
  
- **SizingEntry**: Data class representing sizing activity events
  - Contains timestamp, sizing type, memory values, and region counts
  - Supports uncommit operations, evaluations, and configuration data

### Functions
- `parse_g1_log(log_content)`: Original function for backward compatibility
   - Parameters: `log_content` (string): The content of the GC log file.
   - Returns: `region_data` (dict): A dictionary containing the parsed region data.
- `plot_regions(region_data)`: Enhanced plotting with improved visualization
   - Parameters: `region_data` (dict): The dictionary containing the parsed region data.
   - Returns: `fig` (Plotly Figure): The generated plotly figure object.

### Supported Log Patterns
- **Traditional Format**: `[time]s` timestamp format
- **Modern Format**: `[timestamp][pid][tid]` with ISO timestamps
- **Sizing Events**: Time-based uncommit operations and evaluations
- **Configuration**: Heap sizing initialization and parameter settings
- **Region Transitions**: Eden, Survivor, Old, and Humongous region changes

### Data Types Extracted
- **Heap Sizing Init**: Initial configuration and mode detection
- **Sizing Parameters**: Evaluation intervals and uncommit delays
- **Time-Based Uncommit**: Actual uncommit operations with memory and region counts
- **Evaluation Events**: Shrink evaluations and no-uncommit decisions
- **Heap Shrink Completed**: Final heap sizes after shrink operations
- **Traditional GC Events**: Standard pause and region transition data

### Notes
- Automatically detects log format and adjusts parsing patterns accordingly
- Maintains backward compatibility with traditional G1 region parsing
- Provides comprehensive error handling for malformed log entries
- Optimized for large log files with efficient pattern matching

# Enhanced G1 GC Analysis Tools

### Overview
This package provides enhanced tools for comprehensive G1 Garbage Collector analysis, with advanced support for time-based heap sizing visualization and modern GC log formats. The tools are designed for Java performance engineers analyzing G1 GC behavior and heap sizing efficiency.

### Package Contents
- **parse_g1_regions.py**: Enhanced G1 log parser with time-based sizing analysis
- **heap_plotter.py**: Interactive web dashboard for G1 GC visualization
- **readme_parse_g1_regions.md**: Parser documentation and usage guide
- **readme_heap_plotter.md**: Plotter documentation and visualization guide

### Key Features
- **Time-Based Heap Sizing Analysis**: Comprehensive analysis of G1's uncommit-only mode
- **Modern Log Format Support**: Handles both traditional and modern GC log formats
- **Interactive Visualizations**: Web-based dashboard with multiple plot types
- **G1 Uncommit Rate Analysis**: Visualizes G1's conservative uncommit strategy
- **Synchronized Timelines**: Consistent time-axis scaling across all visualizations
- **Automatic Mode Detection**: Identifies G1 Time-Based Heap Sizing configuration
- **Backward Compatibility**: Maintains compatibility with existing usage patterns

### Quick Start
1. **Install Dependencies**:
   ```
   pip install dash plotly pandas numpy
   ```

2. **Start the Visualization Dashboard**:
   ```
   python heap_plotter.py
   ```

3. **Access the Dashboard**: Navigate to `http://localhost:8051`

4. **Upload GC Log**: Use the file upload interface to analyze your G1 GC logs

### Supported Analysis Types
- **Traditional GC Analysis**: Heap occupancy, pause duration, scaling analysis
- **G1 Region Transitions**: Region state changes and uncommit operations
- **Sizing Activity Summary**: Evaluation outcomes and memory reclamation statistics
- **Heap Evaluation Timeline**: Decision-making process visualization
- **Uncommit Rate Analysis**: G1 constraint compliance and efficiency metrics

### Log Format Support
- Traditional GC logs (`[time]s` format)
- Modern GC logs (`[timestamp][pid][tid]` format)  
- G1 logs with time-based heap sizing data
- Automatic format detection and parsing

### Enhanced Features for G1 Time-Based Sizing
- **Uncommit Rate Analysis**: Visualizes G1's conservative uncommit strategy (target: 20-25% of inactive regions)
- **Dual Metric Display**: Shows both uncommit efficiency (%) and memory impact (MB)
- **Synchronized Timelines**: All time-based plots share consistent x-axis scaling with padding
- **G1 Constraints Visualization**: Displays design constraints (25% inactive limit, 10% total committed limit)
- **Evaluation Process**: Shows the relationship between evaluations, decisions, and actual uncommit operations

### Use Cases
- **Performance Tuning**: Analyze G1 heap sizing behavior and uncommit efficiency
- **Capacity Planning**: Understand heap utilization patterns and sizing decisions
- **Troubleshooting**: Identify issues with G1 time-based heap sizing configuration
- **Monitoring**: Visualize GC performance trends and memory reclamation patterns

### Dependencies
- Python 3.x
- Dash (web framework)
- Plotly (visualization)
- Pandas (data processing)
- NumPy (numerical operations)

### Architecture
The package uses a modular architecture:
- **Parser Module**: Extracts and structures data from GC logs
- **Plotter Module**: Provides interactive visualization and web interface
- **Clear Separation**: Parse in parser, plot in plotter for maintainability

### Backward Compatibility
The enhanced tools maintain full backward compatibility:
- Original function signatures preserved (`parse_g1_log`, `plot_regions`)
- Existing code will work without modifications
- Enhanced features are additive, not breaking changes

### Version Information
- **Version**: 2.0
- **Enhanced**: July 2025
- **Compatibility**: Python 3.x, G1 GC logs from OpenJDK/Oracle JDK

### Notes
- Enhanced sizing visualizations appear only when G1 Time-Based Heap Sizing is enabled
- Tools automatically detect log format and adjust parsing accordingly
- All timestamp formats are automatically normalized for consistent visualization
- The tools gracefully fall back to basic functionality if enhanced features are not available

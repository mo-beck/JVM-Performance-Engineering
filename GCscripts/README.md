# GC Scripts

### Overview
This directory contains various Python scripts for parsing and visualizing Java GC logs. Each script provides different insights into Java's Garbage Collection (GC) behavior, allowing developers to understand and optimize the performance of their applications.

### Available Scripts

1. **heap_plotter.py** (Enhanced v2.0):  
   Enhanced script for visualizing Java GC logs with comprehensive G1 time-based heap sizing analysis. Supports traditional GC analysis plus advanced G1 sizing activity visualizations. Features modern log format support, interactive dashboards, and backward compatibility.  
   Refer to the detailed [readme_heap_plotter.md](./readme_heap_plotter.md) for more information.

2. **parse_g1_regions.py** (Enhanced v2.0):  
   Enhanced G1 log parser with comprehensive time-based heap sizing support. Handles both traditional `[time]s` and modern `[timestamp][pid][tid]` log formats. Includes automatic mode detection, sizing activity extraction, and JSON export capabilities.  
   Refer to the detailed [readme_parse_g1_regions.md](./readme_parse_g1_regions.md) for more information.

3. **zgc_plotter.py**:  
   Visualizes Java (non-generational) ZGC logs, analyzing GC pauses, concurrent phases, page sizes, and causes.  
   Refer to the detailed [readme_zgc_plotter.md](./readme_zgc_plotter.md) for more information.

4. **genzgc_plotter.py**:  
   Offers visualizations for Generational ZGC logs, focusing on GC pauses, concurrent phases, page sizes, and causes across old and young generations.  
   Refer to the detailed [readme_genzgc_plotter.md](./readme_genzgc_plotter.md) for more information.

### Enhanced G1 Tools Package
For comprehensive G1 GC analysis with time-based heap sizing, refer to [README_G1_TOOLS.md](./README_G1_TOOLS.md) for a complete overview of the enhanced G1 analysis capabilities.

### Recommended GC Logging Configuration

For optimal analysis with the enhanced G1 tools, use the following logging pattern:

```bash
-Xlog:gc*,gc+sizing*:file=gc-sizing.log:time,pid,tid,level,tags:filecount=10,filesize=50M
```

This configuration provides:
- **gc***: Complete GC event logging (pauses, phases, heap transitions)
- **gc+sizing***: Time-based heap sizing events (uncommit evaluations, shrink operations)
- **time,pid,tid,level,tags**: Modern log format with full metadata for accurate parsing
- **Rotation**: 10 files × 50MB = 500MB max log retention

**Note:** The modern format `[timestamp][pid][tid][level][tags]` is required for enhanced features. Traditional `[time]s` format is also supported but with limited sizing analysis capabilities.

### How to Use
Each script has its own specific usage instructions and dependencies outlined in their respective README files. Please consult each README to understand how to use the scripts effectively.

### Requirements
- Python 3.x
- Additional dependencies vary by script; see individual READMEs for details.

### Notes
- Make sure to have Python 3.x installed and set up correctly on your system.
- Follow the individual setup instructions in each README to correctly install dependencies and run the scripts.

### Acknowledgment
These scripts were developed to provide a straightforward and efficient way to analyze Java GC logs using Python. The enhanced G1 tools (v2.0) include comprehensive time-based heap sizing analysis while maintaining full backward compatibility. AI agents were used during development as tools to assist with updating boilerplate code and aligning with modern Python conventions where appropriate. The core logic, design and functionality reflect extensive hands-on experience with Java GC and performance engineering.

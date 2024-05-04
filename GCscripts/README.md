# GC Scripts

### Overview
This directory contains various Python scripts for parsing and visualizing Java GC logs. Each script provides different insights into Java's Garbage Collection (GC) behavior, allowing developers to understand and optimize the performance of their applications.

### Available Scripts

1. **heap_plotter.py**:  
   Focuses on visualizing heap occupancy and GC pause statistics for Java Parallel and G1 GCs.  
   Refer to the detailed [readme_heap_plotter.md](./readme_heap_plotter.md) for more information.

2. **parse_g1_regions.py**:  
   Specializes in parsing and visualizing G1 GC region data to understand heap usage over time.  
   Refer to the detailed [readme_parse_g1_regions.md](./readme_parse_g1_regions.md) for more information.

3. **zgc_plotter.py**:  
   Visualizes Java (non-generational) ZGC logs, analyzing GC pauses, concurrent phases, page sizes, and causes.  
   Refer to the detailed [readme_zgc_plotter.md](./readme_zgc_plotter.md) for more information.

4. **genzgc_plotter.py**:  
   Offers visualizations for Generational ZGC logs, focusing on GC pauses, concurrent phases, page sizes, and causes across old and young generations.  
   Refer to the detailed [readme_genzgc_plotter.md](./readme_genzgc_plotter.md) for more information.

### How to Use
Each script has its own specific usage instructions and dependencies outlined in their respective README files. Please consult each README to understand how to use the scripts effectively.

### Requirements
- Python 3.x
- Additional dependencies vary by script; see individual READMEs for details.

### Notes
- Make sure to have Python 3.x installed and set up correctly on your system.
- Follow the individual setup instructions in each README to correctly install dependencies and run the scripts.

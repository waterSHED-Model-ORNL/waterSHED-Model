# waterSHED_Test
Welcome to the waterSHED Model, an open-source product of Dr. Colin Sasthav and the Standard Modular Hydropower Team at Oak Ridge National Laboratory!

This repository allows user to download the code to the waterSHED model, which stands for the water allocation tool enabling rapid small hydropower environmental design. The model allows users to virtually design, simulate, and evaluate hydropower projects using the Standard Modular Hydropower framework from Oak Ridge National Laboratory. This code base creates a user interface using the Tkinter package in Python that facilitates the input, simulation, and visualization processes.

Please read the waterSHED User Guide before using the code, which can be accessed at the link below. The waterSHED User Guide provides instructions about how to download and run the code, as well as, how to interact with the user interface and related features. 
[Link Here]

The review of literature that informed the methodology is presented in Dr. Sasthav's doctoral dissertation entitled "Environmental Design and Optimization of Modular Hydropower Plants," which can be accessed at the following link. The dissertation also has case studies that provide example applications of the model.
[Link Here]

Steps for using the waterSHED model:
1. Download this repository onto your machine. Make sure the folder names do not overlap with existing folders.
2. Open the "waterSHED_main.py" file in the Python IDE (integrated development environment).
3. Make sure the following list of packages are imported.
4. Run the "waterSHED_main.py" file using the IDE or the command prompt window by navigating to the folder using "cd" commands and the following command "run waterSHED_main.py"

Included files and folders:
- waterSHED_main.py - the main script that must be run to create the user interface and run the model.
- module_classes.py - contains the functions for the static module, simulation, and backend classes needed to run the model.
- dynamic_modules.py - contains the classes for the dynamic module functionality that allows modules to be redesigned automatically during optimization.
- aux_functions.py - contains the additional functionalities needed for the user interface and input process, such as USGS API readers, linear regression functions, and others.
- waterSHED_styles.py - sets the colors and formatting for the user interface.
- case_study_functions.py - contains the functions that create the dynamic modules used in the Deerfield, Housatonic, and Schuylkill case studies
- Images - contains the picture files that are used in the graphical user interface
- Workbooks - contains the waterSHED Workbook files that can be used to interact with the user interface and save input data. 

Packages to be imported using the pip or conda install techniques (python -m pip install package_name)
- tkinter
- webbrowser
- pandas
- queue
- threading
- Pillow 
- matplotlib
- tksheet
- numpy
- os
- openpyxl 
- time
- math
- copy
- random
- statistics
- itertools
- requests
- io
- scipy

Please direct any questions or comments to watershed.model.ornl@gmail.com. Personal assistance may be available for those interested in using waterSHED.

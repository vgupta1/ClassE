ClassE
======

ClassE (pronounced “classy”) is an open-source software tool written in Python for academic timetabling. It was designed in close collaboration with MIT Sloan Educational Services (SES) and has been used as part of the scheduling process at the Sloan School of Management since Fall 2012.

Like other time-tabling software, ClassE takes in a list of classes that need to be taught and allocates them to rooms and times while abiding by natural time constraints ("An instructor can't teach two different classes simultaneously") and capacity constraints ("A class must be allocated a room large enough for its typical enrollment.")  Unlike other time-tabling software, ClassE also focuses on finding **fair** allocations that balance the preferences of faculty members and students.  

ClassE uses binary optimization to identify an optimal timetable, and supports on-the-fly analytics via a simple, graphical interface. Through this interface, users can explore features of the candidate timetable, suggest alterations, and tune the algorithm to balance different, competing objectives.

The integer optimization component leverages either the [CPLEX](https://www-01.ibm.com/software/commerce/optimization/cplex-optimizer/) or [Gurobi](http://www.gurobi.com/) (not included in this distribution).  Both solvers are available via academic or commercial licenses.  
ClassE was custom designed for SES, and, hence, does not fully support general timetabling.  All code is available open-source under the MIT License, without any technical support.  Indeed, many of the libraries originally underlying ClassE (e.g., wxPython) have been deprecated since its creation.  Organizations looking to extend its functionality might want to reimplement these portions or reach out to me directly.  

## Licensing
ClassE is available under the MIT License.  
Copyright (c) 2014 Vishal Gupta 

Also, if you use any portion of the software, I'd appreciate a quick note telling me the application.  As an academic, I like hearing about when my work has impact.  

## Requirements

ClassE requires wxPython, wx, and CPLEX or Gurobi. 


## Overview of Functionality
ClassE can be invoked at terminal.
```
python classE
```

1. **Step 1:  Load in the data**  
This can be done by browsing to the folder "DataFiles."  Any errors parsing the data will be displayed in the bottom status bar and in the log. 

2. **Step 2: Optimize**  
After loading the data, the user can set appropriate weights on each of several objectives.  
  * Score Weights describe the relative importance of an instructor receiving her 1st, 2nd, or 3rd preference for a time-slot for a particular class. 
  * Preferences describe the absolute importance of an instructor receiving one of her desired time-slots.
  * Excess Capacity describes the importance of assigning classes to rooms that fit their enrollment, but are overly large.  
  * Congestion describes the importance of reducing the number of classes that are scheduled simultaneously.
  * Dept. Fairness describes the importance of ensuring that a comparable number of instructors in each department receive their top preferences for time-slots. 
  * Back to Back describes the importance of scheduling requested classes consecutively. 

<img src="https://github.com/vgupta1/ClassE/blob/master/imgs/classEDashboard.png" width="700">

After setting these weights and optimizing, the user can compute on-the-fly analytics for the computed time-table via the accompanying visualizations.  For example, the fairness metrics ensure no department is unfairly penalized in the allocation.

<img src="https://github.com/vgupta1/ClassE/blob/master/imgs/classEFairness.png" width="700">

Similarly, other metrics, such as excess capacity, help ensure that the schedule meets internal targets for room-use efficiency.

<img src="https://github.com/vgupta1/ClassE/blob/master/imgs/classEExcessCapacity.png" width="700">

Finally, a heat map gives a birds-eye-view of congestion and usage:

<img src="https://github.com/vgupta1/ClassE/blob/master/imgs/classEHeatMap.png" width="700">


Once a suitable time-table is found, the user can save the results to a .csv file using the File Menu.  

## Technical Details


### DataFiles

All data defining the optimization is found in this folder in .csv files including the courses that need to be allocated (courseRequests.csv), the available Room Inventory (roomInventory.csv), any sets of classes that cannot be scheduled simultaneously (NoConflict.csv), and any classes that should be scheduled consecutively (back2back.csv) if possible.  These files must be formatted correctly. The.xls spreadsheet "CourseRequests_v5.xls" contains macros that can be used to create such files.  

The file "readData.py" contains all functions to parse these data files.  

### Optimization Problem
The core binary optimization problem that ClassE solves is created either in "optimizer_cplex.py" or "optimzier_gurobi.py" depending on the system.  


### GUI
The file ClassE.py contains the main GUI written in wxPython.  The GUI is the preferred means to run ClassE, in particular to take advantage of its visualizations.  Alternatively, the file "mainSES.py" illustrates how to call the underlying optimization directly in Python, for more programmatic development.  


### Other
Remaining files store either helper functions or test files.  

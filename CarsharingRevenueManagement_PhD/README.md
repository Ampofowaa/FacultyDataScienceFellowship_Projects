## ExperimentalDesign Folder:
  - SAS code that generates the discrete choice experiment experiment to quantify how car sharing customers trade off walking distance and fare discounts when selecting alternative return stations.
  - Stata do file that tranforms the DCE Experimental design into Qualtrics txt file
  
## MNL_Estimation Folder:
  - Python code for cleaning the Qualtrics survey questionnaire data
  - Matlab Code for estimating the MNL parameters

## ADP_Algorithms Folder: 
Contains the python codes for the simulation environment that implements the two approximation algoorithms—a choice‑based deterministic linear program (CDLP) and a decomposition method (DCOMP) for the one-way car-sharing revenue managemment problem. 
  - carsharingProject.py: main python file
  - dpFunctions.py: all functions related to the exact dynamic program (DP) formulations
  - cdlpFunctions.py: all functions related to the CDLP algorithm implementation
  - dcompFunctions: all functions related to the DCOMP algorithm implementation
  - simulationFunctions.py: all functions related to implementing the Monte Carlo Simulation environment

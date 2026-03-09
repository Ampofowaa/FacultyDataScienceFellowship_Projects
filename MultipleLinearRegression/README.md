## Pricing Simulation Codes for Leeds
Note: This requires Python v3.9 to v3.11 to successfully run Google OR Tools.

Ensure that Leeds_ODmatrices, Leeds_pricingsimulation.py, general_functions.py, hindsightpol_functions.py, forecastjourneys_price_29_01.csv, foresight1pol_functions.py, and results_hindsightpol are all downloaded and placed in the same folder.

# Leeds_ODmatrices folder
Contains the seven time periods OD matrices for the 874 internal zones in Leeds. These serve as input data which is read on line 20 in Leeds_pricing simulation.py. They are then used to calculate the various time period probabilities (lines 38-39) as well as the conditional probabilities for the deciding on the origin (line 42) and destination zones when generating the arrivals in the simulation code.

# Leeds_pricingsimulation.py
This is the main python simulation file for implementing our three identified pricing policies (hindsight, foresight1 and foresight2) on the Leeds casestudy data. It is currently supported by three main python module files general_functions.py, hindsightpol_functions.py and foresight1pol_functions.py. 

### The main functions in this python file are as follows:
1. Generating the arrivals for all replications and booking periods (line 135) using the leeds_arrivals function found on lines 127-162 in general_functions.py. The request details of an arrival are also derived by calling the gen_request function (line 141) defined on lines 101-126 in general_functions.py. 

2. The hindsight policy branch of the code can be found on lines 146-201. There are three main functions that are applied over here and they can be found in the hindsightpol_functions.py:
   
   i. hindsight_policy function called on line 155 to run the insertion heuristic and optimization procedure to calculate the optimal prices for the different journy optioons. This function is defined on lines 270-325 in the hindsightpol_functions.py. It comprises of generating the different journey options (line 287) by calling the gen_G_x_t function defined on lines 162-183 in general_functions.py, calling the insertion heuristic function defined on lines 129-242 in hindsight_functions.py and solving the price optimization using the function solve_m defined on lines          247-252 in hindsight_functions.py. The output of this function returns the current optimal m value, the journey options, corresponding request TWs, prices and the best potential insertion positions on the vehicle.
   
   ii. simulate_choice function called on line 159 which randomly selects one of the journey options based on the choice probabilitiies. This is defined on lines 254-268 in hindsightpol_functions.py.
   
   iii. call_optimiser function called on lines 198-199 to run the background routing optimization using google OR Tools. This is defined on lines 466-490 in hindsightpol_functions.py.

4. The foresight policy 1 branch of the code which is currently WIP.


### Code Outputs
For each policy, two csv files are generated - one with the results from the simulation and the other with all the details of the accepted journeys from the simulation.
   

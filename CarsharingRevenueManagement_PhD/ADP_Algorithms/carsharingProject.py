# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 10:31:21 2023

@author: bsraf3

-------------------------------------------------------------------------------------
CODE STRUCTURE:
    
    bool OPT = True - means DP is solved
    Step 1: Load and prepare data 
         1a: Define all other parameters and variables
    Step 2a: Solve CDLP initially to get duals and fractional h(J(k))
          b: Solve single-dimensional DP - vtauxsn
    Step 3a: Solve DP if (opt == True)
          b: Evaluate policies for DP and DCOMP  - both with or without incentives   
    Step 4: Simulation Process
        4.1: for s in range(sim_index)
                Sample Demand for all tau
            Call Simulate(demand, "DLP") #with incentives
            Call Simulate(demand, "DP") #for small problem instances
            Call Simulate(demand, "DLP0") #no incentives
            Call Simulate(demand, "DP0") #for small problem instances
            Call Simulate(demand, "DCOMP") -- Next phase
     Step 5: Write Results to CSV files      
--------------------------------------------------------------------------------- 

        
CODE OUTPUT

    - Results file template:   
        
   Col A: ProbIndex	
   Col B: Initial State index		 
   Col C: Rev DP with choice (at tau=0)	 #for small problem instances
   Col D: DLP obj with choice
   Col E: DP simulation with choice	#for small problem instances
   Col F: DLP simulation with choice
   Col G: Rev DP (at tau=0) no choice #for small problem instances	
   Col H: DLP obj no choice	
   Col I: DP simulation no choice #for small problem instances
   Col J: DLP simulation no choice
   
   - Other CSV files for Analysis
   
   General - StateSpace, Code runtime
   DLP - LP file, solution file, DP decision_matrix
   DP - ValidOfferSet, DP decision_matrix, value function
      
"""



# %% modules and packages
import numpy as np
import pandas as pd
from csv import writer
# import math as m
# import os
import time
import generalFunctions
import cdlpFunctions
import dpFunctions
import simulationFunctions
import dcompFunctions

#%% Step 1: Load data + prep
start_time = time.time()
test_label = input("Please enter test instance number: \n") 
filename = './problemInstance_' + test_label + '.csv' #add the csv file extension
initial_parameters = pd.read_csv(filename, header = None)

N = int(initial_parameters.iloc[0,0])
Tau = int(initial_parameters.iloc[0,1])
S = int(initial_parameters.iloc[0,2])
C = int(initial_parameters.iloc[0,3]) 
_limit = C + 1
park_fee = initial_parameters.iloc[0,4] 
rentalrate = initial_parameters.iloc[0,5]
beta_dist1 = initial_parameters.iloc[0,6]
beta_disc1 = initial_parameters.iloc[0,7]
beta_dist2 = initial_parameters.iloc[0,8]
beta_disc2 = initial_parameters.iloc[0,9]
radius = int(initial_parameters.iloc[0,10])
opt = initial_parameters.iloc[0,11]
n_row = S * S * N * N
product_table = initial_parameters.iloc[0:n_row ,12:18] 
product_table =  product_table.rename(columns={12: "prodIdx", 13: "pickupStn",14: "returnStn",
                                                15: "pickupTime",16: "LOR",17: "arrivalrate"})
routing_matrix = initial_parameters.iloc[0:S , 18:18 + S ] 
routing_matrix.columns = list(range(S))
park_space = initial_parameters.iloc[0:S , 18 + S:18 + S + 1] 
park_space = park_space.rename(columns={18 + S:"parkSpace"})
x_s_n = initial_parameters.iloc[0:S , 18 + S + 1:18 + S + N + 1] 
Q = np.arange(5, 95, 15)
min_q = min(Q)
max_q = max(Q)
x_s_n.columns = list(range(N))
x_s_n = x_s_n.astype(int)
routing_scenario = int(initial_parameters.iloc[0,-1])
M = int(max(product_table['LOR']))
#change datatypes
product_table = product_table.astype({"prodIdx": int, "pickupStn": int, "returnStn": int, "pickupTime": int, "LOR": int, "arrivalrate": float})
park_space = park_space.astype({"parkSpace": int})
routing_matrix = routing_matrix.astype("int")
#other variables needed in results csv file
state_id = None
DP_rev_noalts = None
DP_rev_withalts = None
longSimavgRev_DP_noalts = None
longSimavgRev_DP_withalts = None
states_comptime = None
exactDPnoalts_end = None
exactDPwithalts_end = None
DPnoalts_simend = None
DPwithalts_simend = None

#%% Step 1a: Declare other parameters and variables
max_close_stations = 2
noAlts_scenario = 1
withAlts_scenario = 2
#create all possible distance-discount combinations for each station
possible_offersets =  generalFunctions.all_possible_offers(S, routing_matrix, radius, max_close_stations, Q, min_q, max_q)
#create the set of admissable offer JO(k) - CDLP offersets
CDLPnoAlts_OfferSet = cdlpFunctions.J_k(noAlts_scenario, product_table, possible_offersets)
CDLPwithAlts_OfferSet = cdlpFunctions.J_k(withAlts_scenario, product_table, possible_offersets)
#Function call to create the 3 sets of products for DLP case
K = cdlpFunctions.all_products(S, N, product_table)
K_minus = cdlpFunctions.reduce_inventory_set(S, N, product_table)
K_plus = cdlpFunctions.increase_inventory_set(S, N, product_table)
#create JO(k, xsn) - DCOMP offersets
DCOMPnoAlts_OfferSet = dcompFunctions.decomp_J_k_xsn(S, N, product_table, C, CDLPnoAlts_OfferSet, routing_matrix, K_minus, K_plus)
DCOMPwithAlts_OfferSet = dcompFunctions.decomp_J_k_xsn(S, N, product_table, C, CDLPwithAlts_OfferSet, routing_matrix, K_minus, K_plus)
#Function call for the number of booking periods for each n in N
T_k = cdlpFunctions.no_bookingPeriods(N,Tau) 
#%% Step 2a: Solve CDLP initially to get duals
#computation times is in seconds
decomp_state = x_s_n.to_numpy()
#no alts scenario
noaltstime_duals,noaltscapacity_duals,noaltsparking_duals,noaltsdecisions,noaltssol,cdlp_noaltssoltime =  cdlpFunctions.solve_cdlp(noAlts_scenario, product_table, CDLPnoAlts_OfferSet, S, N, T_k, K, beta_dist1, beta_disc1, routing_matrix, K_minus, decomp_state, K_plus, park_space, rentalrate, park_fee, True)
noalts_policies = cdlpFunctions.decision_matrix(noaltsdecisions, noaltssol, product_table,T_k,Tau,N)
CDLPobj_noalts = noaltssol.objective_value
#with alts scenario
withaltstime_duals,withaltscapacity_duals,withaltsparking_duals,withaltsdecisions,withaltssol,cdlp_withaltssoltime = cdlpFunctions.solve_cdlp(withAlts_scenario, product_table, CDLPwithAlts_OfferSet, S, N, T_k, K, beta_dist1, beta_disc1, routing_matrix, K_minus, decomp_state, K_plus, park_space, rentalrate, park_fee, True)
withalts_policies = cdlpFunctions.decision_matrix(withaltsdecisions, withaltssol, product_table,T_k,Tau,N)    
CDLPobj_withalts = withaltssol.objective_value

# Step 2b: determine the single-dimensional DP value function, vtau(x,s,n) 
# reported average computation time for all (s,n) pairs is in seconds
vtaus_noalts,avgnoalts_decompsoltime = dcompFunctions.decomposition(S, N, Tau, C, product_table, T_k, DCOMPnoAlts_OfferSet, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee, K_minus, K_plus, noaltscapacity_duals)
vtaus_withalts,avgwithalts_decompsoltime = dcompFunctions.decomposition(S, N, Tau, C, product_table, T_k, DCOMPwithAlts_OfferSet, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee, K_minus, K_plus, withaltscapacity_duals)
#%% Step 3a: Solve DP if (opt == True)
if opt:
    #Function call to create valid state space
    states_start = time.time() 
    validStates = dpFunctions.createStateSpace(S, N, C, _limit)
    states_comptime = time.time()
    validStates = np.array(validStates)
    #create J0(k,x) 
    DPnoAlts_OfferSet = dpFunctions.J_k_x(noAlts_scenario, product_table,validStates, N, CDLPnoAlts_OfferSet, "N/A", routing_matrix,radius, Q)
    DPwithAlts_OfferSet = dpFunctions.J_k_x(withAlts_scenario, product_table, validStates, N, "N/A", possible_offersets,routing_matrix, radius, Q)
    #function call to solve DP
    #noalts scenario
    exactDPnoalts_start = time.time() 
    valfunx_DPnoalts,DP_noalts_lookup = dpFunctions.exactDPSol(Tau, N, product_table, validStates, DPnoAlts_OfferSet, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee)
    exactDPnoalts_end = (time.time() - exactDPnoalts_start)
    #with alts scenario
    exactDPwithalts_start = time.time()
    valfunx_DPwithalts,DP_withalts_lookup = dpFunctions.exactDPSol(Tau, N, product_table, validStates, DPwithAlts_OfferSet, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee)
    exactDPwithalts_end = (time.time() - exactDPwithalts_start)
    #get V[0] at the starting state x
    state_id = [x for x in range(len(validStates)) if (validStates[x] == x_s_n.to_numpy()).all()][0] #get index for future state
    DP_rev_noalts = valfunx_DPnoalts[state_id][0]
    DP_rev_withalts = valfunx_DPwithalts[state_id][0]
    
    # Step 3b: Evaluate policies for DP and DCOMP - This is to show that DP >= DCOMP
    DP_policyevalValfuncs_noalts = generalFunctions.policy_evaluation("DP", noAlts_scenario, "N/A", "N/A", DP_noalts_lookup, valfunx_DPnoalts, S, Tau, N, product_table, validStates, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, radius, Q, rentalrate, park_space, park_fee)
    DP_policyeval_Valfuncswithalts = generalFunctions.policy_evaluation("DP", withAlts_scenario, "N/A", "N/A", DP_withalts_lookup, valfunx_DPwithalts, S, Tau, N, product_table, validStates, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, radius, Q, rentalrate, park_space, park_fee)
    DCOMP_policyevalValfuncs_noalts, DCOMP_policies_noalts, DCOMP_validOffersets_noalts = generalFunctions.policy_evaluation("DCOMP", noAlts_scenario, possible_offersets, vtaus_noalts, "N/A", "N/A", S, Tau, N, product_table, validStates, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, radius, Q, rentalrate, park_space, park_fee) 
    DCOMP_policyevalValfuncs_withalts, DCOMP_policies_withalts, DCOMP_validOffersets_withalts = generalFunctions.policy_evaluation("DCOMP", withAlts_scenario, possible_offersets, vtaus_withalts, "N/A", "N/A", S, Tau, N, product_table, validStates, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, radius, Q, rentalrate, park_space, park_fee)
    
    

#%% Simulation process
# add a new role to the product table - for the case of non-arrivals
new_row = {'prodIdx': len(product_table), 'pickupStn': -1, 'returnStn': -1, 'pickupTime':-1, 'LOR':-1, 'arrivalrate': 1 - sum(product_table.iloc[:, 5])}
product_table = product_table.append(new_row, ignore_index=True)    
no_reps = 500
no_cycles = 50
reOpt_window = 7

time_seed = (time.time() - int(time.time())) * np.random.random() * 1000000
demands = simulationFunctions.generate_demands(time_seed,no_reps,no_cycles, Tau,product_table)
# print("simulated demand arrivals: ")
# print(demands)
# function calls for CDLP
# no alts scenario
cdlpnoalts_simbegin = time.time()                 
cdlp_noalts_longsimrev,cdlp_noalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"CDLP",noAlts_scenario,CDLPnoAlts_OfferSet,None,None,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,None,None)                                                                                                                               
cdlpnoalts_simend = time.time() - cdlpnoalts_simbegin
#with alts scenario
cdlpwithalts_simbegin = time.time()                 
cdlp_withalts_longsimrev,cdlp_withalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"CDLP",withAlts_scenario,CDLPwithAlts_OfferSet,None,None,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,None,None)                                                                                                                               
cdlpwithalts_simend = time.time() - cdlpwithalts_simbegin                                                                                                                            
#average revenue
longSimavgRev_cdlp_noalts = np.average(cdlp_noalts_longsimrev)
longSimavgRev_cdlp_withalts = np.average(cdlp_withalts_longsimrev)       
                                                                                                                    
#function calls for DCOMP
#no alts scenario
DCOMPnoalts_simbegin = time.time()
DCOMP_noalts_longsimrev,DCOMP_noalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"DCOMP",noAlts_scenario,None,None,None,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,vtaus_noalts,possible_offersets)
DCOMPnoalts_simend = time.time() - DCOMPnoalts_simbegin
#with alts scenario
DCOMPwithalts_simbegin = time.time()
DCOMP_withalts_longsimrev,DCOMP_withalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"DCOMP",withAlts_scenario,None,None,None,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,vtaus_withalts,possible_offersets)
DCOMPwithalts_simend = time.time() - DCOMPwithalts_simbegin
#average revenue
longSimavgRev_DCOMP_noalts = np.average(DCOMP_noalts_longsimrev)
longSimavgRev_DCOMP_withalts = np.average(DCOMP_withalts_longsimrev)

#function call for DP
if opt:
    #no alts scenario
    DPnoalts_simbegin = time.time()
    dp_noalts_longsimrev, dp_noalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"DP",noAlts_scenario,DPnoAlts_OfferSet,validStates,DP_noalts_lookup,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,None,None)
    DPnoalts_simend = time.time() - DPnoalts_simbegin
    #with alts scenario
    DPwithalts_simbegin = time.time()
    dp_withalts_longsimrev, dp_withalts_simoffers = simulationFunctions.longSim_policies(no_reps,no_cycles,reOpt_window,demands,x_s_n,park_space,S,N,M,Tau,T_k,product_table,"DP",withAlts_scenario,DPwithAlts_OfferSet,validStates,DP_withalts_lookup,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,False,None,None)
    DPwithalts_simend = time.time() - DPwithalts_simbegin
    #average revenue
    longSimavgRev_DP_noalts = np.average(dp_noalts_longsimrev)
    longSimavgRev_DP_withalts = np.average(dp_withalts_longsimrev)
total_computationtime = (time.time() - start_time)/3600

# Pre-requisite - The CSV file should be manually closed before running this code. write results to csv file
list_data = [test_label,routing_scenario,no_reps,no_cycles,reOpt_window,S,N,Tau,C,state_id,DP_rev_noalts,CDLPobj_noalts,DP_rev_withalts,CDLPobj_withalts,
             longSimavgRev_DP_noalts,longSimavgRev_DCOMP_noalts,longSimavgRev_cdlp_noalts,longSimavgRev_DP_withalts,longSimavgRev_DCOMP_withalts,longSimavgRev_cdlp_withalts,
             states_comptime,exactDPnoalts_end,avgnoalts_decompsoltime,cdlp_noaltssoltime,exactDPwithalts_end,avgwithalts_decompsoltime,cdlp_withaltssoltime,
             DPnoalts_simend,DCOMPnoalts_simend,cdlpnoalts_simend,DPwithalts_simend,DCOMPwithalts_simend,cdlpwithalts_simend,total_computationtime]
with open('./results.csv', 'a', newline='') as f_object:  
    writer_object = writer(f_object) # Pass the CSV  file object to the writer() function
    writer_object.writerow(list_data)  # Pass the data in the list as an argument into the writerow() function 
    f_object.close()# Close the file object

#%% write output files
#write admissable offers to csv
df0 = pd.DataFrame.from_dict(CDLPnoAlts_OfferSet, orient='index')
df0.to_csv('./CDLP_solfiles/DLP_noalts_OfferSet_{0}.csv'.format(test_label), index_label="keys")
df1 = pd.DataFrame.from_dict(CDLPwithAlts_OfferSet, orient='index')
df1.to_csv('./CDLP_solfiles/DLP_withalts_OfferSet_{0}.csv'.format(test_label), index_label="keys")
df0 = pd.DataFrame.from_dict(DCOMPnoAlts_OfferSet, orient='index')
df0.to_csv('./DCOMP_solfiles/latestDCOMP_noalts_offersets_{0}.csv'.format(test_label), index_label="keys")
df1 = pd.DataFrame.from_dict(DCOMPwithAlts_OfferSet, orient='index')
df1.to_csv('./DCOMP_solfiles/latestDCOMP_withalts_offersets_{0}.csv'.format(test_label), index_label="keys")

#write duals to csv file
df0 = pd.DataFrame.from_dict(noaltstime_duals, orient='index')
df0.to_csv('./DCOMP_solfiles/noaltstime_duals{0}.csv'.format(test_label), index_label="keys")
df1 = pd.DataFrame.from_dict(withaltstime_duals, orient='index')
df1.to_csv('./DCOMP_solfiles/withaltstime_duals{0}.csv'.format(test_label), index_label="keys")
df2 = pd.DataFrame.from_dict(noaltscapacity_duals, orient='index')
df2.to_csv('./DCOMP_solfiles/noaltscapacity_duals{0}.csv'.format(test_label), index_label="keys")
df3 = pd.DataFrame.from_dict(withaltscapacity_duals, orient='index')
df3.to_csv('./DCOMP_solfiles/withaltscapacity_duals{0}.csv'.format(test_label), index_label="keys")
df4 = pd.DataFrame.from_dict(noaltsparking_duals, orient='index')
df4.to_csv('./DCOMP_solfiles/noaltsparking_duals{0}.csv'.format(test_label), index_label="keys")
df5 = pd.DataFrame.from_dict(withaltsparking_duals, orient='index')
df5.to_csv('./DCOMP_solfiles/withaltsparking_duals{0}.csv'.format(test_label), index_label="keys")

#write CDLP h(J(k)) for the starting state
df0 = pd.DataFrame(noalts_policies)
df0.to_csv('./CDLP_solfiles/CDLPinitialpol_noalts_{0}.csv'.format(test_label), index_label="id")
df0 = pd.DataFrame(withalts_policies)
df0.to_csv('./CDLP_solfiles/CDLPinitialpol_withalts_{0}.csv'.format(test_label), index_label="id")

#write DCOMP vtaus into csv file
df0 = pd.DataFrame.from_dict(vtaus_noalts, orient='index')
df0.to_csv('./DCOMP_solfiles/lateststatesvtaus_noalts_{0}.csv'.format(test_label), index_label="keys")
df1 = pd.DataFrame.from_dict(vtaus_withalts, orient='index')
df1.to_csv('./DCOMP_solfiles/lateststatesvtaus_withalts_{0}.csv'.format(test_label), index_label="keys")

#CDLP selected simulation offers to csv
df1 = pd.DataFrame.from_dict(cdlp_noalts_simoffers, orient='index')
df1.to_csv('./CDLP_solfiles/DLP_noalts_simuloffer_{0}.csv'.format(test_label), index_label="keys")
df2 = pd.DataFrame.from_dict(cdlp_withalts_simoffers, orient='index')
df2.to_csv('./CDLP_solfiles/DLP_withalts_simuloffer_{0}.csv'.format(test_label), index_label="keys")

#DCOMP selected simulation offers to csv
df1 = pd.DataFrame.from_dict(DCOMP_noalts_simoffers, orient='index')
df1.to_csv('./DCOMP_solfiles/DCOMPnoAlts_simuloffers_{0}.csv'.format(test_label), index_label="keys")
df2 = pd.DataFrame.from_dict(DCOMP_withalts_simoffers, orient='index')
df2.to_csv('./DCOMP_solfiles/DCOMPwithAlts_simuloffers_{0}.csv'.format(test_label), index_label="keys")


#write DP results to csv
if opt:
    #admissable offers J(k,x)
    df0 = pd.DataFrame.from_dict(DPnoAlts_OfferSet, orient='index')
    df0.to_csv('./DP_solfiles/latestDP_noalts_offersets_{0}.csv'.format(test_label), index_label="keys")
    df1 = pd.DataFrame.from_dict(DPwithAlts_OfferSet, orient='index')
    df1.to_csv('./DP_solfiles/latestDP_withalts_offersets_{0}.csv'.format(test_label), index_label="keys")
    
    #value functions
    df1 = pd.DataFrame(valfunx_DPnoalts)
    df1.to_csv('./DP_solfiles/latestvalfunx_DPnoalts_{0}.csv'.format(test_label), index_label="state_id")
    df2 = pd.DataFrame(valfunx_DPwithalts)
    df2.to_csv('./DP_solfiles/latestvalfunx_DPwithalts_{0}.csv'.format(test_label), index_label="state_id")
    
    # write policy lookup table to a csv file
    df3 = pd.DataFrame.from_dict(DP_noalts_lookup, orient='index')
    df3.to_csv('./DP_solfiles/latestDP_noalts_lookup_{0}.csv'.format(test_label), index_label="keys")
    df4 = pd.DataFrame.from_dict(DP_withalts_lookup, orient='index')
    df4.to_csv('./DP_solfiles/latestDP_withalts_lookup_{0}.csv'.format(test_label), index_label="keys")
    
    #DP policy evaluation value functions 
    df1 = pd.DataFrame(DP_policyevalValfuncs_noalts)
    df1.to_csv('./DP_solfiles/latestDPpolicyevalfxn_noalts_{0}.csv'.format(test_label), index_label="state_id")
    df2 = pd.DataFrame(DP_policyeval_Valfuncswithalts)
    df2.to_csv('./DP_solfiles/latestDPpolicyevalfxn_withalts_{0}.csv'.format(test_label), index_label="state_id")
    
    #DCOMP policy evaluation value functions
    df3 = pd.DataFrame(DCOMP_policyevalValfuncs_noalts)
    df3.to_csv('./DCOMP_solfiles/latestDCOMPpolicyevalfxn_noalts_{0}.csv'.format(test_label), index_label="state_id")
    df4 = pd.DataFrame(DCOMP_policyevalValfuncs_withalts)
    df4.to_csv('./DCOMP_solfiles/latestDCOMPpolicyevalfxn_withalts_{0}.csv'.format(test_label), index_label="state_id")
    
    #DCOMP policies
    DCOMPpolicies_noalts=dict(sorted(DCOMP_policies_noalts.items()))
    DCOMPpolicies_withalts=dict(sorted(DCOMP_policies_withalts.items()))
    df5 = pd.DataFrame.from_dict(DCOMPpolicies_noalts, orient='index')
    df5.to_csv('./DCOMP_solfiles/latestDCOMPpolicies_noalts_{0}.csv'.format(test_label), index_label="keys")
    df6 = pd.DataFrame.from_dict(DCOMPpolicies_withalts, orient='index')
    df6.to_csv('./DCOMP_solfiles/latestDCOMPpolicies_withalts_{0}.csv'.format(test_label), index_label="keys")
    
    #DCOMP valid offersets
    df1 = pd.DataFrame.from_dict(DCOMP_validOffersets_noalts, orient='index')
    df1.to_csv('./DCOMP_solfiles/latestDCOMPvalidoffersets_noalts_{0}.csv'.format(test_label), index_label="keys")
    df2 = pd.DataFrame.from_dict(DCOMP_validOffersets_withalts, orient='index')
    df2.to_csv('./DCOMP_solfiles/latestDCOMPvalidoffersets_withalts_{0}.csv'.format(test_label), index_label="keys")
    
    #DP selected simulation offers to csv
    df1 = pd.DataFrame.from_dict(dp_noalts_simoffers, orient='index')
    df1.to_csv('./DP_solfiles/DP_noalts_simuloffers_{0}.csv'.format(test_label), index_label="keys")
    df2 = pd.DataFrame.from_dict(dp_withalts_simoffers, orient='index')
    df2.to_csv('./DP_solfiles/DP_withalts_simuloffers_{0}.csv'.format(test_label), index_label="keys")
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 15 06:48:41 2023

@author: bsraf3
"""
#%%
import numpy as np
import math
import generalFunctions
import cdlpFunctions
import dcompFunctions
import time
#%% generate random demand samples for all replications
def generate_demands(time_seed,no_reps,no_cycles, Tau,product_table,):
    demand = {}
    np.random.seed(int(time_seed))
    for r in range(no_reps):
        for c in range(no_cycles):
            demand_list = []
            for tau in range(Tau):
                # print(tau)
                prod_id = product_table["prodIdx"].to_numpy()
                # print(prod_id)
                arrival_rate = product_table["arrivalrate"].to_numpy()
                # print(arrival_rate)
                sample_id = int(np.random.choice(prod_id, size = 1, replace = True, p = arrival_rate)[0])
                # print(sample_id)
                demand_list.append(sample_id)
                # print(demand_list)
            demand[(r,c)] = demand_list
            # print(demand)
    #     # print(demand)
    return demand

#%% find next state
def next_state(S,N, M, augmented_states):
    next_state = np.zeros((S,N),int)
    next_state[:,0:M] = augmented_states[:,N:]
    # print("next_state for M", next_state)
    if N != M:
        final_states = []
        for m in range(N-M):
                final_states.append(augmented_states[:,-1].tolist())
        final_states = np.asarray(final_states).T
        # print("final_states", final_states)
        next_state[:,M:] = final_states
    # print("next_state", next_state)
    return next_state

#%% function to run simulation process
def longSim_policies(no_reps,no_cycles,reOpt_window,demand,start_state,park_space,S,N,M,Tau,T_k,product_table,policy,scenario,offer_set,validStates,dp_lookup_table,beta_dist1, beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,K,K_minus,K_plus,park_fee,checkDCOMP,vtau_xsn,possible_offersets):
    #function to get simulation results for different policies
    decisions = None
    next_state = None
    policy_revenue = np.zeros((no_reps,no_cycles))
    offers = {}
    for r in range(no_reps):
        # print("reps", r + 1)
        for c in range(no_cycles):
            # print("policy_revenue", policy_revenue)
            current_demands = demand[(r,c)]
            # print(current_demands)
            # print("cycles", c + 1)
            # time_seed = (time.time() - int(time.time())) * np.random.random() * 1000000
            if c == 0:
                cycle_state = start_state.to_numpy()
            else:
                cycle_state = next_state
            # print(cycle_state)
            # print("rep", r+1, "cycle", c+1, cycle_state)
            if policy == "CDLP":
                if reOpt_window == 0 and c == 0: #initial solution
                    reoptimise = 1
                else:
                    reoptimise = 0
                if reOpt_window > 0:
                    if c == 0 or c % reOpt_window == 0:
                        reoptimise = 1
                    else:
                        reoptimise = 0
                if reoptimise == 1:
                    #dlp_reoptimise = time.time()
                    #print("reoptimise at cycle", c, "for replication", r, "for state", cycle_state)
                    prodTable = product_table.iloc[0:len(product_table)-1,:]
                    # print(prodTable)
                    data, soln = cdlpFunctions.solve_cdlp(scenario, prodTable, offer_set, S, N, T_k, K, beta_dist1, beta_disc1, routing_matrix, K_minus, cycle_state, K_plus, park_space, rentalrate, park_fee, checkDCOMP)
                    # obj = soln.objective_value
                    # print("objective function for the", policy, "policy", scenario, ":", obj)
                    decisions = cdlpFunctions.decision_matrix(data, soln, prodTable, T_k, Tau, N)
                    #end_reoptimise = time.time() - dlp_reoptimise
                    #print("time taken to reoptimise dlp scenario ",scenario,"is: ", end_reoptimise, "seconds")
                    # decisions.to_csv("decisions.csv")   
                    # if r == 0 and c == 0:
                    #     initial_DLPobj = obj
                    #     initialstate_DLPpolicies = DLPpolicies
            #run simulation
            results = long_Sim(scenario,r,c,cycle_state,current_demands,park_space,S,N,M,Tau,product_table,policy,decisions,offer_set,validStates,dp_lookup_table,beta_dist1,beta_disc1,beta_dist2,beta_disc2,rentalrate,routing_matrix,radius,Q,park_fee,vtau_xsn,possible_offersets, offers)
            # print(results)
            policy_revenue[r][c] += results[0]
            # print("policy revenue",policy_revenue[r][c])
            next_state = results[1]
            # print("next state", next_state)
            offers = results[2]
            # print(dlp_noalts_longsimrev)
            # print("next state", next_state)
    return policy_revenue,offers
  

def long_Sim(scenario,r,c,start_state,demand,park_space,S,N,M,Tau, product_table,policy,dlp_matrix,offer_set,validStates,dp_lookup_table,beta_dist1, beta_disc1,beta_dist2, beta_disc2,rentalrate,routing_matrix,radius, Q,park_fee,vtau_xsn,possible_offersets,Offers):
    park_space = park_space.to_numpy()
    cycle_rev = 0
    
    prob_scenario = "default"
    beta_dist = beta_dist1
    beta_disc = beta_disc1
    # print("vtauxsn", vtau_xsn)
    # print("opt", opt)
    # print("ADP lookuptable", ADP_lookuptable)
    # print("possible_offersets",possible_offersets)
    for n in range(N):  
        # print("n", n)
        if n == 0:
            # print("start_state",start_state)
            state = start_state
            # print("state",state)
            augmented_states = np.zeros((S,N + M),int)
            # print(augmented_states)
            augmented_states[:,0:N] = state
            #update the additional M states
            tracked_states = []
            for m in range(M):
                tracked_states.append(state[:,-1].tolist())
            tracked_states = np.asarray(tracked_states).T
            # print("additonal states", tracked_states)
            augmented_states[:,N:] = tracked_states
        # print(" start state", state)
        # print("augmented state", augmented_states)
        for tau in range(max(0,math.floor((n * Tau)/N)),math.floor((n + 1) * Tau/N)):           
            # print("tau",tau)
            # n_tau = math.floor((tau * N)/Tau)
            # print("n_tau",n_tau)
            # print(demand)
            sample_id = demand[tau]
            product = product_table.iloc[sample_id,:]
            # print("sample_id", sample_id)
            # print("product",product)
            # n_tau = math.floor((tau * N)/Tau)
            if (sample_id == len(product_table)) or (product_table.iloc[sample_id,3] <  n): #if non_arrival or pickup time before n_tau,
                cycle_rev +=0
                augmented_states -= 0
            else:
                if policy == "CDLP":
                    # print(dlp_matrix[dlp_matrix.prodIdx == sample_id])
                    offerid = dlp_matrix.iloc[:,-1][(dlp_matrix.prodIdx == sample_id) & (dlp_matrix.tau == tau)]
                    # print("offer_id", offerid)
                    offers = offer_set[sample_id][offerid.iloc[0]]
                    # print(offers)
                    # print(augmented_states[:,0:N])
                    if offers != [(-1,-1)]:
                        offers = cdlpFunctions.validOffers(product, augmented_states[:,0:N], offers, N)
                    # print(" CDLP offers",offers)
                    Offers[(policy,scenario,r,c,sample_id)] = offers
                elif policy == "DP":
                    state_id = [x for x in range(len(validStates)) if (validStates[x] == augmented_states[:,0:N]).all()][0] #get index for future state
                    # print(state_id)
                    offers = dp_lookup_table[(tau, n,state_id, sample_id)]  
                    # Offers[(policy,scenario,r,c,sample_id)] = offers
                elif policy == "DCOMP":
                    if scenario == 1:
                        pos_offersets = [[(-1, -1)], [(0, 0)]]
                    else:
                        pos_offersets = possible_offersets[product['returnStn']]
                    # print(pos_offersets)
                    valid_offersets = dcompFunctions.decomp_J_k_x(scenario, augmented_states[:,0:N], product, N, pos_offersets, routing_matrix, radius, Q)
                    # print("valid_offersets",valid_offersets)
                    offers = dcompFunctions.onestate_DCOMPpolicy(S, Tau, N, tau, n, augmented_states[:,0:N], product, valid_offersets, vtau_xsn, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee)
                else:
                    print("Please enter a valid policy name")
                    return
                # print("offers", offers)
                # if len(offers) > 1:
                #     print("debug")  
                #check if no purchase - then update probability equations:
                if (offers != [(-1,-1)]) and ((0,0) not in offers):
                    # print("debug")
                    prob_scenario = "no purchase"
                    beta_dist = beta_dist2
                    beta_disc = beta_disc2
                
                if offers == [(-1, -1)]:
                    cycle_rev += 0
                    # print("rev", sim_rev)
                    augmented_states -= 0
                    # print("state", state)
                else: 
                    e_o = np.zeros_like(augmented_states)
                    e_d = np.zeros_like(augmented_states)
                    end_time = int(product['pickupTime']) + int(product['LOR'])
                    # print("end time", end_time)
                    P = generalFunctions.choice_prob(prob_scenario, offers, beta_dist, beta_disc)
                    # print(P)
                    keys_idx = np.asarray(list(range(len(P))))
                    probs =np.asarray(list(P.values()))
                    # print("probs", probs)
                    time_seed = (time.time() - int(time.time())) * np.random.random() * 1000000
                    np.random.seed(int(time_seed))
                    sel_idx = np.random.choice(keys_idx, size = 1, replace = True, p = probs)[0]  
                    # print(sel_idx)
                    selected_offer = list(P.keys())[sel_idx]
                    Offers[(policy,scenario,r,c,sample_id)] = selected_offer
                    # print(selected_offer)
                    # print("current rev", (rentalrate * product['LOR'] * (1 - selected_offer[1]/100)))
                    if selected_offer == (-2,-2):#if customer rejects the booking - no revenue
                        # print("debug")
                        cycle_rev += 0
                        augmented_states -= 0
                    else:   
                        cycle_rev += (rentalrate * product['LOR'] * (1 - selected_offer[1]/100))   
                        # print(cycle_rev)
                        #update state here
                        e_o[int(product['pickupStn']), int(product['pickupTime']):] = 1 #for n onwards for o
                        # print(e_o)
                        route = routing_matrix.iloc[int(product['returnStn'])]
                        # print("route",route)
                        rtnStn = route[route == selected_offer[0]].index.to_list()[0]
                        # print(rtnStn)
                        e_d[rtnStn,end_time:] = 1
                        # print(e_d)
                        augmented_states += - e_o + e_d
                        # print(augmented_states)
                        # print("cycle_rev without park_fees", cycle_rev)
        cycle_rev -= generalFunctions.parking_charges(Tau, N, park_space, park_fee, augmented_states[:,n], tau)
    # print("end augmented state", augmented_states)
    nextcycle_state = next_state(S,N, M, augmented_states)
    # print("end_state", nextcycle_state)
    return cycle_rev, nextcycle_state,Offers



  
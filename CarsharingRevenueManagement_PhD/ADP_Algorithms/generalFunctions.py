# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 11:27:15 2023

@author: bsraf3
"""
#%% import modules
import numpy as np
import math as m
#import dcompFunctions
#%%
def all_possible_offers(S, routing_matrix, radius, max_close_stations, q, min_q, max_q):
    """
    Creates a dictionary containing all the different distance-discount combinations
    for each stations based on the 2 alt closest stations within the selected radius
    """
    alt_stns = {}
    possible_offersets = {}
    for i in range(S):
        initial_combination = [[(-1, -1)], [(0, 0)]] #rejection, initial booking
        # station in close proximity, distance
        alt_stns[i] = [routing_matrix[i][(routing_matrix[i] > 0) & (routing_matrix[i] < radius + 1)].nsmallest(max_close_stations).index.to_list(
        ), list(routing_matrix[i][(routing_matrix[i] > 0) & (routing_matrix[i] < radius + 1)].nsmallest(max_close_stations).values)]
        # print(alt_stns)
        # alt_stns[i] = [routing_matrix[i][(routing_matrix[i] > 0) & (routing_matrix[i] < radius + 1)].nsmallest(max_close_stations).index.to_list(),list(routing_matrix[i][(routing_matrix[i] > 0) & (routing_matrix[i] < radius + 1)].values)]
        if len(alt_stns[i][0]) < max_close_stations:
            initial_combination.extend(
                [(0, 0), (alt_stns[i][1][0], x)] for x in q)
            possible_offersets[i] = initial_combination
        else:
            min_distance = min(alt_stns[i][1])
            max_distance = max(alt_stns[i][1])
            initial_combination.extend(
                [(0, 0), (alt_stns[i][1][0], x)] for x in q)
            initial_combination.extend(
                [(0, 0), (alt_stns[i][1][1], x)] for x in q)
            initial_combination.extend([[(0, 0), (min_distance, j), (max_distance, i)]
                                        for j in q if j != max_q for i in q if i != min_q if i > j])
            possible_offersets[i] = initial_combination
    return possible_offersets
#%% parking charges calculations
def parking_charges(Tau, N, park_space, park_fee, idlecars_ntau, tau):
    # print(Tau, N, park_space, park_fee, idlecars_ntau, tau)
    total_parkcost = 0
    if (tau + 1) % (Tau/N) == 0:
        additional_parking = idlecars_ntau.reshape(park_space.shape) - park_space
        # print("additional_parking", additional_parking)
        total_parkcost = sum(additional_parking[additional_parking > 0]) * park_fee
    # print("total_parkcost", total_parkcost)
    return total_parkcost
#%% choice probability calculations
def choice_prob(prob_scenario,choiceset, beta_dist, beta_disc):
    # print(numerator)
    if prob_scenario == "no purchase":
        # print(prob_scenario,choiceset, beta_dist, beta_disc)
        numerator = {x:(np.exp(beta_dist * x[0] + beta_disc * x[1]) if x!= (-2,-2) else 1)for x in choiceset}
        # print("numerator",numerator)
    else:
        numerator = {x:np.exp(beta_dist * x[0] + beta_disc * x[1]) for x in choiceset}
    denom = sum(numerator.values())
    prob = {k: v/denom for (k,v) in numerator.items()}
    return prob
#%% parking charges for a (s,n) pair
def parkingcost_sn(s,tau_n,tau,x,parkspace_s, park_fee):
    total_parkcost = 0
    if tau == tau_n:
        additional_parking = x - parkspace_s
        # print("additional_parking", additional_parking)
        if additional_parking > 0:
            total_parkcost = additional_parking * park_fee
            # print("total_parkcost", total_parkcost)
    return total_parkcost
#%% function to evaluate DP and DCOMP generated policies
# def policy_evaluation(policy,scenario,possible_offersets,ADPvtauxsn,DPlookup_table,value_function,S,Tau,N,product_table,validStates,beta_dist1,beta_disc1,beta_dist2,beta_disc2,routing_matrix,radius,Q,rentalrate,park_space,park_fee):
#     park_space = park_space.to_numpy()
#     value_function = np.zeros((len(validStates), Tau + 1))
#     prob_scenario = "default"
#     beta_dist = beta_dist1
#     beta_disc = beta_disc1
#     ADP_lookuptable = {}
#     validoffersets = {}
#     for tau in reversed(range(Tau)):
#         n_tau = m.floor((tau * N)/Tau)
#         # print("tau,n_tau",tau, n_tau)
#         K = product_table[product_table["pickupTime"] >= n_tau]
#         # K = K.astype({"prodIdx": int, "pickupStn": int, "returnStn": int, "pickupTime": int, "LOR": int, "arrivalrate": float})
#         # print(K)
#         for x in range(len(validStates)):
#             state = validStates[x]
#             v_allpdts = 0 #v_k = sum (lambda * max(v_k))
#             for k in range(len(K)):
#                 # print("state", state)
#                 # print("k", K.iloc[k, [0, 1, 2, 3, 4]])
#                 product = K.iloc[k]
#                 # print(product)
#                 if policy == 'DP':
#                     choiceset = DPlookup_table[(tau, n_tau, x, K.iloc[k, 0])]
#                     # print("DP choiceset", choiceset)
#                 elif policy == 'DCOMP':
#                     if scenario == 1:
#                         pos_offersets = [[(-1, -1)], [(0, 0)]]
#                     else:
#                         pos_offersets = possible_offersets[K.iloc[k,2]]
#                     #get all J_0(k,\mathbf(x))
#                     valid_offersets = dcompFunctions_v5.decomp_J_k_x(scenario, state, product, N, pos_offersets, routing_matrix, radius, Q)
#                     # print(valid_offersets)
#                     validoffersets[(k,x)] = valid_offersets
#                     # print("valid offersets",valid_offersets)
#                     choiceset = dcompFunctions_v5.onestate_DCOMPpolicy(S, Tau, N, tau, n_tau, state, product, valid_offersets, ADPvtauxsn, beta_dist1, beta_disc1, beta_dist2, beta_disc2, routing_matrix, rentalrate, park_space, park_fee)
#                     ADP_lookuptable[(tau, n_tau, x, K.iloc[k, 0])] = choiceset
#                     # print("ADP choiceset", choiceset)
#                 if choiceset == [(-1,-1)]:
#                     v_j = -parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau) + value_function[x][tau + 1]
#                     # print("v_j", v_j)
#                 else:
#                     # print("debug")
#                     e_o = np.zeros_like(state)
#                     e_o[K.iloc[k,1], K.iloc[k,3]:] = 1 #for n onwards for o
#                     # print("e_o",e_o)
#                     end_time = K.iloc[k, 3] + K.iloc[k, 4]
#                     # print("choiceset", choiceset)
#                     v_j = 0
#                     if (0,0) not in choiceset:#check if original booking is not included in offersets
#                         # print("debug")
#                         prob_scenario = "no purchase"
#                         beta_dist = beta_dist2
#                         beta_disc = beta_disc2
#                     P = choice_prob(prob_scenario, choiceset, beta_dist, beta_disc)
#                     # print(P)
#                     for choice in choiceset:
#                         # print(choice)
#                         if choice == (-2,-2):
#                             v_j += P[choice] * (-parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau) + value_function[x][tau + 1]) #get cummulative sum for choice_set
#                             # print("v_j", v_j)
#                         else:
#                             e_d = np.zeros_like(state)
#                             if choice == (0,0):
#                                 return_stn = K.iloc[k,2]
#                             else:
#                                 # print("k", K.iloc[k, [0, 1, 2, 3, 4]])
#                                 route = routing_matrix.iloc[K.iloc[k,2]]
#                                 # print(route)
#                                 return_stn = route[route == choice[0]].index.to_list()[0]
#                             # print("d", return_stn)
#                             e_d[return_stn,end_time:] = 1
#                             # print("e_d", e_d)
#                             future_state = state - e_o + e_d
#                             # print("future state",future_state)
#                             total_parkcost = parking_charges(Tau, N, park_space, park_fee, future_state[:,n_tau], tau)
#                             # print("total_park_cost", total_parkcost)
#                             idx = [x for x in range(len(validStates)) if (validStates[x] == future_state).all()][0] #get index for future state
#                             # print("future index",idx)
#                             # print("future value function", value_function[idx][tau + 1])
#                             v_j += P[choice] * ((rentalrate * (1-choice[1]/100) * K.iloc[k, 4]) - total_parkcost + value_function[idx][tau + 1]) #get cummulative sum for choice_set
#                             # print("total choice value", v_j)
#                 # print("total choice value", v_j)     
#                 # print("v_allpdts",v_allpdts)
#                 v_allpdts += K.iloc[k, 5] * v_j
#                 # print("v_allpdts",v_allpdts)
#             nonarrival_parkcost = parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau)
#             # print("nonarrival_parkcost",nonarrival_parkcost)
#             # print("future value function", value_function[x][tau + 1])
#             value_function[x][tau] = v_allpdts + ((1 - sum(K.iloc[:, 5])) * (value_function[x][tau + 1] - nonarrival_parkcost))
#             # print("value_function at state =", x, "for tau =", tau, "is", value_function[x][tau])
#     if policy == 'DP':
#         return value_function
#     else:
#         return value_function, ADP_lookuptable, validoffersets
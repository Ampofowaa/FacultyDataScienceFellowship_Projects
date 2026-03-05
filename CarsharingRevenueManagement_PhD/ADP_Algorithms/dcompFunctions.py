# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 13:51:36 2023

@author: bsraf3
"""
# %%
import numpy as np
import math as m
import generalFunctions
import time
# %% setting the boundary condition to the number of cars * capacity dual for the (s,n) pair
def boundary_conditions(S, N, C, Tau,T_k,capacity_duals,vtau_xsn):
    for s in range(S):
        for n in range(N):
            boundary_taus = [i for i in range(int(T_k[n]),Tau + 1)]
            for tau in boundary_taus:
                for x in range(C+1):
                    vtau_xsn[(s, n, x, tau)] = x * capacity_duals[(s,n)]
    return vtau_xsn
# %% Function to determine offer set
"""
Pseudocode for J_k_xsn
for all s=1,S
 for all n=1,N
  for all x=0,C
    if 0<x<C
	for all k in K
	  J(k,x)=J(k) //in such a case x does not matter
    else if x=0
	for all k in K
	 for all J in J(k) // for all choice sets
	  for all j in J //for all alternatives in each choice set
	    if l_j in K^-_(s,n), continue // ignore this option if it reduces x from 0 to -1
	    else, add j into J(k,x)
    else // x=C
	for all k in K
	 for all J in J(k)
           for all j in J //for all alternatives in each choice set
	    if l_j in K^+_(s,n), continue // ignore this option if it increases x from C to C+1
	    else if l_j in K^-_(s',n) for any other station s', continue // ignore if it reduces one car from any s' in period n. They have no cars.
	    else, add j into J(k,x)

"""
def decomp_J_k_xsn(S, N, product_table, C, dlp_offersets, routing_matrix, K_minus, K_plus):
    # print(valid_offer_sets)
    valid_offer_sets = {}
    for s in range(S):
        for n in range(N):
            for x in range(C + 1):
                # print("s,n,x",s,n,x)
                for k in range(len(product_table)):
                    # print("prod",product_table.iloc[k])
                    stop1 = False
                    stop2 = False
                    stop3 = False
                    if (x > 0) and (x < C):
                        valid_offer_sets[(s, n, x, product_table.iloc[k, 0])] = dlp_offersets[k]
                    elif x == 0:
                        get_offersets = []
                        for J in dlp_offersets[k]:
                            # print("J", J)
                            get_offers = []
                            for j in J:
                                # print("j",j)
                                if j == (-1, -1):
                                    get_offers.append(j) # print(get_offers)
                                else:
                                    if j == (0, 0):
                                        return_stn = product_table.iloc[k, 2]
                                    else:
                                        # print("j",j)
                                        route = routing_matrix.iloc[product_table.iloc[k, 2]]
                                        return_stn = route[route == j[0]].index.to_list()[0]
                                    # print("return stn", return_stn)
                                    alt_book = (product_table.iloc[k, 1], return_stn, product_table.iloc[k, 3], product_table.iloc[k, 4])
                                    # print("alt_book",alt_book)
                                    # print("K_minus",K_minus[s,n])
                                    if alt_book in K_minus[s, n]:
                                        # print("In K_minus so should not appear in offer set")
                                        # if j == (0, 0):
                                            # stop1 = True
                                            # break  # go to next product
                                        # else:
                                            # print("Move to next offer: next j")
                                        continue  # go to next offer
                                    else:
                                        # print("Add to get offers"
                                        get_offers.append(j)
                                        # print("get_offers",get_offers)
                                    if ((-1,-1) not in get_offers) and ((0,0) not in get_offers):
                                        get_offers.insert(0, (-2,-2))
                            if stop1 == True:
                                # print("move to the next product")
                                break
                            if len(get_offers) > 0:
                                if get_offers not in get_offersets:
                                    get_offersets.append(get_offers)
                                    # print("get_offersets",get_offersets)
                        valid_offer_sets[(s, n, x, product_table.iloc[k, 0])] = get_offersets
                        # print("valid offerset for ", s,n,x,product_table.iloc[k,0], ":",valid_offer_sets[(s,n,x,product_table.iloc[k, 0])])
                    else:  # x=C
                        # print("s,n,x,product", s,n,x,product_table.iloc[k,0])
                        get_offersets2 = []
                        for J in dlp_offersets[k]:
                            # print("J", J)
                            get_offers2 = []
                            for j in J:
                                # print("j",j)
                                stop4 = False
                                if j == (-1, -1):
                                    get_offers2.append(j)
                                else:
                                    if j == (0, 0):
                                        return_stn = product_table.iloc[k, 2]
                                    else:
                                        route = routing_matrix.iloc[product_table.iloc[k, 2]]
                                        return_stn = route[route == j[0]].index.to_list()[
                                            0]
                                    # print("j", j)
                                    # print("return stn", return_stn)
                                    alt_book = (
                                        product_table.iloc[k, 1], return_stn, product_table.iloc[k, 3], product_table.iloc[k, 4])
                                    # print("alt_book",alt_book)
                                    # print("K_plus", K_plus[s,n])
                                    if alt_book in K_plus[s, n]:
                                        # print("In K_plus so should not appear in offer set")
                                        if j == (0, 0):
                                            # print("Move to next product : next k")
                                            stop2 = True  # go to next product
                                            break
                                        else:
                                            # print("Move to next offer: next j")
                                            continue  # go to next offer
                                    else:
                                        sprimes_n = [(s_prime, n) for s_prime in range(S) if s_prime != s]
                                        # print(sprimes_n)
                                        for items in sprimes_n:
                                            # print('(sprime,n)',items)
                                            # print(K_minus[items])
                                            if alt_book in K_minus[items]:
                                                # print("In K_plus so should not appear in offer set")
                                                if j == (0, 0):
                                                    stop3 = True
                                                    # print("Move to next product : next k")
                                                    # break
                                                stop4 = True
                                                # print("Stop iterating through (s_prime,n")
                                                # print("Move to next offer : next j")
                                                break
                                        # print("get_offers",get_offers2)
                                        if stop4 == False:
                                            if j not in get_offers2:
                                                get_offers2.append(j)
                                                # print("get_offers",get_offers2)
                            if (stop2 == True) or (stop3 == True):
                                # print("move to the next product")
                                break
                            if len(get_offers2) > 0:
                                # print("initial offer sets", get_offers2)
                                if get_offers2 not in get_offersets2:
                                    get_offersets2.append(get_offers2)
                                    # print("get_offersets",get_offersets2)
                        valid_offer_sets[(s, n, x, product_table.iloc[k, 0])] = get_offersets2
                        # print("valid offerset for ", s,n,x,product_table.iloc[k,0], ":",valid_offer_sets[(s,n,x,product_table.[k, 0])])
    return valid_offer_sets
# %% function to determine next state of single DP
def nextstate(s, n, x_s_n, alt_book, K_minus, K_plus):
    x_tilde = 0
    if alt_book in K_minus[s, n]:
        # print("booking is in K_minus")
        x_tilde = x_s_n - 1
    elif alt_book in K_plus[s, n]:
        # print("booking is in K_plus")
        x_tilde = x_s_n + 1
    else:
        x_tilde = x_s_n
        # print("booking is in neither")
    # print("next x_tilde", x_tilde)
    return x_tilde

# %% function to determine total marginal cost for single DP
def totalmarginal_costs(sn_primes, alt_book, K_minus, K_plus, pi):
    marg_costs = 0
    # print("pis", pi)
    for item in sn_primes:
        if alt_book in K_minus[item]:
            # print("in K_minus")
            marg_costs += pi[item]
            # print("marg_costs", marg_costs)
        if alt_book in K_plus[item]:
            # print("in K_plus")
            marg_costs -= pi[item]
            # print("marg_costs",marg_costs)
    # print("ending_margcosts", marg_costs)
    return marg_costs

# %% Decomposition Process
def decomposition(S, N, Tau, C, product_table, T_k, decomp_valOfferset, beta_dist1, beta_disc1, beta_dist2,beta_disc2, routing_matrix, rentalrate, park_space, park_fee, K_minus, K_plus, capacity_duals):
    vtau_xsn = {(s, n, x, tau): 0 for s in range(S) for n in range(N)
                 for x in range(C+1) for tau in range(Tau+1)} #s,n,x_s_n,tau
    prob_scenario = "default"
    beta_dist = beta_dist1
    beta_disc = beta_disc1
    compute_times = np.zeros((S, N))
    for s in range(S):
        for n in range(N):
            tau_n = int(T_k[n]) - 1  # last booking period in n
            # print("tau_n", tau_n)
            decompstart = time.time()
            # get bookable products for that n
            for tau in reversed(range(tau_n + 1)):
                n_tau = m.floor((tau * N)/Tau)
                # print("s,n,tau,n_tau",s,n,tau, n_tau)
                K = product_table[(product_table["pickupTime"] >= n_tau) & (product_table["pickupTime"] <= n)]
                # print("K",K)
                for x in range(C + 1):
                    if s == 1 and n == 1 and x == 0:
                        print("debug")
                    # print("x", x)
                    v_allpdts = 0
                    for k in range(len(K)):
                        # print("s,n,tau,x,k", s,n,tau,x,K.iloc[k,0])
                        # prod = (K.iloc[k,1], K.iloc[k,2], K.iloc[k,3], K.iloc[k,4])
                        # print("prod", prod)
                        if decomp_valOfferset[s, n, x, K.iloc[k, 0]] == [[(-1, -1)]]:
                            # print("s,tau_n,tau,x,parkspace,parkfee", s,tau_n,tau,x,park_space, park_fee)
                            max_vJ = -generalFunctions.parkingcost_sn(s, tau_n, tau, x, park_space.iloc[s, 0], park_fee) + vtau_xsn[(s, n, x, tau + 1)]
                            # print('cost',max_vJ)
                        else:
                            max_vJ = -100000
                            all_choicesets = decomp_valOfferset[s,n, x, K.iloc[k, 0]]
                            # print("all choice sets", all_choicesets)
                            if [(0,0)] not in all_choicesets:
                                # print("debug")
                                prob_scenario = "no purchase"
                                beta_dist = beta_dist2
                                beta_disc = beta_disc2
                            for choiceset in all_choicesets:
                                # print(choiceset)
                                v_j = 0
                                P = generalFunctions.choice_prob(prob_scenario, choiceset, beta_dist, beta_disc)
                                # print("prob",P)
                                for choice in choiceset:
                                    # print(choice)
                                    if choice == (-1, -1):
                                        v_j += -generalFunctions.parkingcost_sn(s, tau_n, tau, x, park_space.iloc[s, 0], park_fee) + vtau_xsn[(s, n, x, tau + 1)]
                                        # print("v_j",v_j)
                                    else:
                                        if choice == (-2,-2):
                                            # print("debug")
                                            v_j += P[choice] * (-generalFunctions.parkingcost_sn(s, tau_n, tau, x, park_space.iloc[s, 0], park_fee) + vtau_xsn[(s, n, x, tau + 1)])
                                            # print("v_j",v_j)
                                        else:
                                            # get the alternative product
                                            if choice == (0, 0):
                                                return_stn = K.iloc[k, 2]
                                            else:
                                                route = routing_matrix.iloc[K.iloc[k, 2]]
                                                return_stn = route[route == choice[0]].index.to_list()[0]
                                            # print("return stn", return_stn)
                                            alt_book = (K.iloc[k, 1], return_stn, K.iloc[k, 3], K.iloc[k, 4])
                                            # print("alt book", alt_book)
                                            # print("K_minus[s,n]",K_minus[s, n])
                                            # print("K_plus[s,n]",K_plus[s, n])
                                            if (alt_book not in K_minus[s, n]) and (alt_book not in K_plus[s, n]):
                                                v_j += P[choice] * (-generalFunctions.parkingcost_sn(s, tau_n, tau, x, park_space.iloc[s, 0], park_fee) + vtau_xsn[(s, n, x, tau + 1)])
                                                # print("v_j",v_j)
                                            else:
                                                # print("debug")
                                                # calculate the future state based on the alternative product
                                                x_tilde = nextstate(s, n, x, alt_book, K_minus, K_plus)
                                                # print("x_tilde", x_tilde)
                                                sn_primes = [(s_prime, n_prime) for s_prime in range(S) for n_prime in range(N) if (s_prime, n_prime) != (s, n)]
                                                # print("sn_primes", sn_primes)
                                                marginal_costs = totalmarginal_costs(sn_primes, alt_book, K_minus, K_plus, capacity_duals)
                                                # print("marg_costs", marginal_costs)
                                                total_parkcost = generalFunctions.parkingcost_sn(s, tau_n, tau, x_tilde, park_space.iloc[s, 0], park_fee)
                                                # print("totalparkcost", total_parkcost)
                                                v_j += P[choice] * ((rentalrate * (1-choice[1]/100) * K.iloc[k, 4]) - marginal_costs - total_parkcost + vtau_xsn[(s, n, x_tilde, tau + 1)])  # get cummulative sum for choice_set
                                                # print("v_j", v_j)
                                # print("total choice value", v_j)
                                if v_j > max_vJ:
                                    max_vJ = v_j
                                # print("max_vj", max_vJ)
                        # print("arrivalrate", K.iloc[k, 5])
                        # print("v_allpdt",K.iloc[k, 5] * max_vJ)
                        v_allpdts += K.iloc[k, 5] * max_vJ
                        # print("v_allpdts", v_allpdts)
                    nonarrival_parkcost = generalFunctions.parkingcost_sn(s, tau_n, tau, x, park_space.iloc[s, 0], park_fee)
                    vtau_xsn[(s, n, x, tau)] = v_allpdts + ((1 - sum(K.iloc[:, 5]))* (vtau_xsn[(s, n, x, tau + 1)] - nonarrival_parkcost))
                    # print("vtau_xsn", vtau_xsn[(s,n,x,tau)])
            decompend = time.time() - decompstart
            compute_times[s,n] = decompend
    return vtau_xsn, np.average(compute_times)
# %% define a new function for the set of all possible offer sets for a particular state
def decomp_J_k_x(scenario,x, product,N,possible_offersets,routing_matrix,radius,Q):
    all_offers = None
    # print("state", x)
    # print("product",product)
    # print("all offersets",possible_offersets)
    # print(product)
    if int(product['pickupStn'])== int(product['returnStn']):
        # check if one way rental is possible, cars must be available from n to N
        boolean = x[int(product['pickupStn']), int(product['pickupTime']):N] >= 1
        # print(boolean)
        if boolean.all() == True:
            all_offers = possible_offersets
        else: # check if return trip is possible, cars must be available from n to n + m - 1
            boolean = x[int(product['pickupStn']),int(product['pickupTime']):min(N,int(product['pickupTime']) + int(product['LOR']))] >= 1
            if boolean.all() == True:
                all_offers = [[(-1, -1)], [(0, 0)]]
            else:
                all_offers = [[(-1, -1)]]
    else:#case of one-way rentals
        boolean = x[int(product['pickupStn']), int(product['pickupTime']):N]>= 1
        if boolean.all() == True:
            all_offers = possible_offersets
        else:
            boolean = x[int(product['pickupStn']), int(product['pickupTime']):min(N,int(product['pickupTime']) + int(product['LOR']))]
            if boolean.all() == True:
                if scenario == 1: #noalts scenario
                    all_offers = [[(-1, -1)]]
                else:#withalts scenario
                    #propose a return trip with different discount combinations
                    initial_combination = [[(-1, -1)]]
                    distance = routing_matrix.iloc[int(product['returnStn']),int(product['pickupStn'])]
                    if distance <= radius:
                        initial_combination.extend([(-2,-2),(distance, q)] for q in Q)
                        all_offers = initial_combination #corresponding return trip
                    else:
                        all_offers = [[(-1, -1)]]
            else:
                all_offers = [[(-1, -1)]]
    return all_offers
# %% Function to calculate vhat for a single state
def onestate_vhat(S, N, vtau_xsn, x, tau):
    v_hat = 0
    indexes = [(i, j, x[i][j], tau) for i in range(x.shape[0])
               for j in range(x.shape[1])]
    for idx in indexes:
        v_hat += vtau_xsn[idx]
    return v_hat

#function to determine DCOMP policy for a particular state
def onestate_DCOMPpolicy(S, Tau, N, tau, n, x, product, all_offersets, vtau_xsn, beta_dist1, beta_disc1,beta_dist2,beta_disc2,routing_matrix, rentalrate, parkspace, park_fee):
    # print("state, tau, n",x, tau, n)
    # print("product", product)
    # print("all_offersets", all_offersets)
    # print("vtau_xsn", vtau_xsn)
    offers = None
    prob_scenario = "default"
    beta_dist = beta_dist1
    beta_disc = beta_disc1
    # parkspace = park_space.to_numpy()
    if all_offersets == [[(-1, -1)]]:
        max_vJ = - generalFunctions.parking_charges(Tau, N, parkspace, park_fee, x[:, n], tau) + onestate_vhat(S, N, vtau_xsn, x, tau + 1)  # vhat[x][tau + 1]
        offers = [(-1, -1)]
    else:
        e_o = np.zeros_like(x)
        # for n onwards for o
        e_o[int(product['pickupStn']), int(product['pickupTime']):] = 1
        # print("e_o",e_o)
        end_time = int(product['pickupTime']) + int(product['LOR'])
        max_vJ = -100000
        for offerset in all_offersets:
            # print("offerset", offerset)
            v_j = 0
            if [(0,0)] not in all_offersets:
                # print("debug")
                prob_scenario = "no purchase"
                beta_dist = beta_dist2
                beta_disc = beta_disc2
            P = generalFunctions.choice_prob(prob_scenario, offerset, beta_dist, beta_disc)
            # print(P)
            for offer in offerset:
                # print("offer", offer)
                if offer == (-1, -1):
                    v_j += - generalFunctions.parking_charges(Tau, N, parkspace, park_fee, x[:, n], tau) + onestate_vhat(S, N, vtau_xsn, x, tau + 1)
                    # print("v_j",v_j)
                else:
                    if offer == (-2,-2):
                        v_j += P[offer] * (-generalFunctions.parking_charges(Tau, N, parkspace, park_fee, x[:, n], tau) + onestate_vhat(S, N, vtau_xsn, x, tau + 1))  # get cummulative sum for choice_set
                    else:
                        e_d = np.zeros_like(x)
                        if offer == (0, 0):
                            return_stn = int(product['returnStn'])
                        else:
                            # print("k", K.iloc[k, [0, 1, 2, 3, 4]])
                            route = routing_matrix.iloc[int(product['returnStn'])]
                            # print(route)
                            return_stn = route[route == offer[0]].index.to_list()[0]
                            # print(return_stn)
                            # print("d", return_stn)
                        e_d[return_stn, end_time:] = 1
                        # print("e_d", e_d)
                        future_x = x - e_o + e_d
                        # print("future state",future_x)
                        total_parkcost = generalFunctions.parking_charges(Tau, N, parkspace, park_fee, future_x[:, n], tau)
                        # print("total_parkcost", total_parkcost)
                        v_j += P[offer] * ((rentalrate * (1-offer[1]/100) * product['LOR']) - total_parkcost + onestate_vhat(S, N, vtau_xsn, future_x, tau + 1))  # get cummulative sum for choice_set
            # print(max_vJ)
            # print("total choice value", v_j)
            if v_j > max_vJ:
                max_vJ = v_j
                offers = offerset
            # print("offers",offers)
    return offers

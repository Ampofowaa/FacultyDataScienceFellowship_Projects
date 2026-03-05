# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 15:35:05 2023

@author: bsraf3
"""
#%% import modules
import numpy as np
import math as m
import generalFunctions
#%% Functions to create state space
def createAllElements(numCol, numRow, _limit):
    '''
    Create a two dimensional array of all the possible states using the functions:
    increaseValueByOne and elementIncrements 

   '''
    twoDimArray = np.zeros((numRow, numCol), dtype='i')

    for i in range(numRow):
        if i == 0:
            elementList = np.zeros(numCol, dtype="i")
            _hasvalueBeenReset = [False] * numCol
        else:
            lastElement = elementList[numCol - 1]
            elementList[numCol - 1], _hasvalueBeenReset[numCol -
                                                        1] = increaseValueByOne(lastElement, _limit)
            elementList, _hasvalueBeenReset = elementIncrements(
                elementList, _hasvalueBeenReset, _limit)
        for j in range(numCol):
            twoDimArray[i][j] = elementList[j]
    return twoDimArray

def increaseValueByOne(elementIncrementer, _limit):
    ''' 
    Increases the argument by 1, if this addition is equal to the capacity limit, reset value to 0, and
    resetValue to True: otherwise, reset value as False after increment.
    '''
    if elementIncrementer + 1 == _limit:
        resetValue = True
    else:
        resetValue = False
    elementIncrementer = (elementIncrementer + 1) % _limit
    return elementIncrementer, resetValue

def elementIncrements(elementList, _hasvalueBeenReset, _limit):
    ''' 
    Increases the previous element in the element list by 1, if the current element = 0, and
   _hasvalueBeenReset is True. After this, change _hasvalueBeenReset for the current element as False.    
    '''
    for i in reversed(range(len(elementList))):
        # increase the previous element by 1
        if elementList[i] == 0 and _hasvalueBeenReset[i] == True:
            prevElement = elementList[i - 1]
            elementList[i - 1], _hasvalueBeenReset[i -
                                                   1] = increaseValueByOne(prevElement, _limit )
            _hasvalueBeenReset[i] = False
    return elementList, _hasvalueBeenReset

def isStateValid(N, S, C, state):
    isValidState = True
    # The total number of cars in the network must not exceed the fleet size
    for n in range(N):
        temp = 0
        for s in range(S):
            temp += state[s][n]
        if temp > C:
            isValidState = False
    return isValidState

def createStateSpace(S, N, C, _limit):  # create the valid state space
    numCol = S * N
    numRow = 1
    valid_state = []
    rollOverLimits = np.zeros(numCol, dtype="i")
    for n in range(numCol):
        rollOverLimits[n] = C + 1
        numRow *= rollOverLimits[n]
    #print("numcol: ", numCol,"numrow: ", numRow, "rolloverlimit: ", rollOverLimits)
    allElements = createAllElements(numCol, numRow, _limit)
    for i in range(len(allElements)):  # create a state for each element
        numCars = []
        for s in range(S):
            numCarsThisCategory = []
            for t in range(N):
                numCarsThisCategory.append(allElements[i][s * N + t])
            numCars.append(numCarsThisCategory)
        # check validity of the state
        if isStateValid(N, S, C, numCars):
            valid_state.append(numCars)  # store that state
    return valid_state
# %%
def J_k_x(scenario,product_table,validStates,N,noaltsOffersets,withaltsOffersets,routing_matrix,radius,Q):
    """
    Returns the valid offersets for product based on the state as a dictionary(pdtid,stateid) based on 
    """
    valid_offer_sets = {}
    for k in range(len(product_table)):
        # print("k", "k", product_table.iloc[k,[0,1,2,3,4]])
        for x in range(len(validStates)):
            state = validStates[x]
            # print("state",state)
            if product_table.iloc[k, 1] == product_table.iloc[k, 2]:
                # check if one way rental is possible, cars must be available from n to N
                boolean = state[product_table.iloc[k, 1],
                                product_table.iloc[k, 3]:N] >= 1
                if boolean.all() == True:  # offer set
                    if scenario == 1:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = noaltsOffersets[product_table.iloc[k, 0]]
                    else:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = withaltsOffersets[product_table.iloc[k, 2]]
                else:
                    # check if return trip is possible, cars must be available from n to n + m - 1
                    boolean = state[product_table.iloc[k, 1], product_table.iloc[k, 3]:min(
                        N, product_table.iloc[k, 3] + product_table.iloc[k, 4])] >= 1
                    if boolean.all() == True:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = [[(-1, -1)], [(0, 0)]]  # original booking
                    else:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = [[(-1, -1)]]
            else:
                # check if one way rental is possible, cars must be available from n to N
                boolean = state[product_table.iloc[k, 1],product_table.iloc[k, 3]:N] >= 1
                if boolean.all() == True:  # offer set
                    if scenario == 1:
                       valid_offer_sets[(product_table.iloc[k, 0], x)] = noaltsOffersets[product_table.iloc[k, 0]]
                    else:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = withaltsOffersets[product_table.iloc[k, 2]]  # offer set
                else:
                    boolean = state[product_table.iloc[k, 1], product_table.iloc[k, 3]:min(
                        N, product_table.iloc[k, 3] + product_table.iloc[k, 4])] >= 1
                    if boolean.all() == True:
                        if scenario == 1:
                            valid_offer_sets[(product_table.iloc[k, 0], x)] = [[(-1, -1)]]
                        else:
                            #propose a return trip with different discount combinations
                            initial_combination = [[(-1, -1)]]
                            distance = routing_matrix.iloc[product_table.iloc[k, 2],product_table.iloc[k, 1]]
                            if distance <= radius: #set customer rejection as (-2,-2)
                                initial_combination.extend([(-2,-2),(distance, q)] for q in Q)
                                valid_offer_sets[(product_table.iloc[k, 0], x)] = initial_combination #corresponding return trip
                            else:
                                valid_offer_sets[(product_table.iloc[k, 0], x)] = [[(-1, -1)]]
                    else:
                        valid_offer_sets[(product_table.iloc[k, 0], x)] = [[(-1, -1)]]
    return valid_offer_sets

#%%
def exactDPSol(Tau,N,product_table,validStates,valid_offer_sets,beta_dist1, beta_disc1,beta_dist2, beta_disc2,routing_matrix,rentalrate,park_space,park_fee):
    park_space = park_space.to_numpy()
    value_function = np.zeros((len(validStates), Tau + 1))
    lookup_table = {}
    prob_scenario = "default"
    beta_dist = beta_dist1
    beta_disc = beta_disc1
    for tau in reversed(range(Tau)):
        # print
        n_tau = m.floor((tau * N)/Tau)
        # print(tau, n_tau)
        K = product_table[product_table["pickupTime"] >= n_tau]
        # K = K.astype({"prodIdx": int, "pickupStn": int, "returnStn": int, "pickupTime": int, "LOR": int, "arrivalrate": float})
        # print(K)
        for x in range(len(validStates)):
            state = validStates[x]
            v_allpdts = 0 #v_k = sum (lambda * max(v_k))
            for k in range(len(K)):
                # print("state", state)
                # print("state id", x)
                # print("k", K.iloc[k, [0, 1, 2, 3, 4]])
                # if (k,x) == (32,4):
                #     print("debug")
                if valid_offer_sets[K.iloc[k,0], x] == [[(-1,-1)]]:
                    max_vJ = - generalFunctions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau) + value_function[x][tau + 1]
                    lookup_table[(tau, n_tau, x, K.iloc[k, 0])] = [(-1, -1)]
                    # print(max_vJ)
                else:
                    e_o = np.zeros_like(state)
                    e_o[K.iloc[k,1], K.iloc[k,3]:] = 1 #for n onwards for o
                    # print("e_o",e_o)
                    end_time = K.iloc[k, 3] + K.iloc[k, 4]
                    max_vJ = -100000
                    all_choicesets = valid_offer_sets[K.iloc[k,0], x]
                    # print("all choicesets", all_choicesets)
                    # print("debug")
                    if [(0,0)] not in all_choicesets:
                        # print("debug")
                        prob_scenario = "no purchase"
                        beta_dist = beta_dist2
                        beta_disc = beta_disc2
                    for choiceset in all_choicesets:
                        # print(choiceset)
                        v_j = 0
                        P = generalFunctions.choice_prob(prob_scenario, choiceset, beta_dist, beta_disc)
                        # print(P)
                        for choice in choiceset:
                            #print(choice)
                            if choice == (-1,-1):
                                # print("parking_charges", - general_functions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau))
                                # print("val func", value_function[x][tau + 1])
                                v_j += - generalFunctions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau) + value_function[x][tau + 1]
                                # print("v_j",v_j)
                            else:
                                if choice == (-2,-2):
                                    # print("debug")
                                    # print("total_park_cost", -generalFunctions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau))
                                    # print("future value function", value_function[x][tau + 1])
                                    v_j += P[choice] * (-generalFunctions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau)  + value_function[x][tau + 1])
                                    # print("v_j",v_j) #get cummulative sum for choice_set
                                else:
                                    # print("debug")
                                    e_d = np.zeros_like(state)
                                    if choice == (0,0):
                                        return_stn = K.iloc[k,2]
                                    else:
                                        # print("k", K.iloc[k, [0, 1, 2, 3, 4]])
                                        route = routing_matrix.iloc[K.iloc[k,2]]
                                        # print(route)
                                        return_stn = route[route == choice[0]].index.to_list()[0]
                                    # print("d", return_stn)
                                    e_d[return_stn,end_time:] = 1
                                    # print("e_d", e_d)
                                    future_state = state - e_o + e_d
                                    # print("future state",future_state)
                                    total_parkcost = generalFunctions.parking_charges(Tau, N, park_space, park_fee, future_state[:,n_tau], tau)
                                    # print("total_park_cost", total_parkcost)
                                    idx = [x for x in range(len(validStates)) if (validStates[x] == future_state).all()][0] #get index for future state
                                    # print("future index",idx)
                                    # print("future value function", value_function[idx][tau + 1])
                                    v_j += P[choice] * ((rentalrate * (1-choice[1]/100) * K.iloc[k, 4]) - total_parkcost + value_function[idx][tau + 1]) #get cummulative sum for choice_set
                        # print("total choice value", v_j)
                        if v_j > max_vJ:
                            max_vJ = v_j
                            lookup_table[(tau, n_tau, x, K.iloc[k, 0])] = choiceset
                # print("max_vj", max_vJ)                          
                # print("max_choice", lookup_table[(tau, n_tau, x, K.iloc[k, 0])])                           
                v_allpdts += K.iloc[k, 5] * max_vJ
                # print("v_allpdts",v_allpdts)
            nonarrival_parkcost = generalFunctions.parking_charges(Tau, N, park_space, park_fee, state[:,n_tau], tau)
            # print("nonarrival_parkcost",nonarrival_parkcost)
            # print("future value function", value_function[x][tau + 1])
            value_function[x][tau] = v_allpdts + ((1 - sum(K.iloc[:, 5])) * (value_function[x][tau + 1] - nonarrival_parkcost))
            # print("value_function at state =", x, "for tau =", tau, "is", value_function[x][tau])
    return value_function, lookup_table
#%%
def dp_boundarycond(N,Tau,validStates,capacity_duals,value_func):
    for x in validStates:
        state_idx = [i for i in range(len(validStates)) if (validStates[i] == x).all()][0]
        indexes = [(s,N-1) for s in range(x.shape[0])]
        for idx in indexes:
            value_func[state_idx,Tau] += (capacity_duals[idx] * x[idx])
    return value_func
                    

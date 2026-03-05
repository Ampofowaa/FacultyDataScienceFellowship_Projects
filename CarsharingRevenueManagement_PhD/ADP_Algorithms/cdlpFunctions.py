# -*- coding: utf-8 -*-
"""
Created on Thu Jun  8 11:35:18 2023

@author: bsraf3
"""
#%% import modules
import generalFunctions
from docplex.mp.model import Model
import pandas as pd
import numpy as np
import time
perturbation = 0.5 #used for rounding up h(J(k))
#%% defining J0(k)
def J_k(scenario, product_table, possible_offersets): #no states involved
    valid_Offersets = {}
    for k in range(len(product_table)):
        if scenario == 1:# no alternatives
            valid_Offersets[product_table.iloc[k,0]] = [[(-1, -1)], [(0, 0)]]
        elif scenario == 2: #with alternatives
            valid_Offersets[product_table.iloc[k,0]] = possible_offersets[product_table.iloc[k,2]]
        else:
            print("Scenario must be either 1 (no alternatives) or 2 (with alternatives)")
    return valid_Offersets

#%% main functions
#defining the three sets for products
def all_products(S,N,product_table):
    """
    Creates a dictionary containing all products for a specific pick-up station s and pick-up time n
    """
    K = {}
    for s in range(S):
        for n in range(N):
              filtered_data = product_table.iloc[:, [1,2,3,4]][(product_table['pickupStn'] == s) & (product_table['pickupTime'] == n)]
              filtered_data = filtered_data.values.tolist() 
              K[(s,n)] = filtered_data
    return K

def reduce_inventory_set(S,N,product_table):
    """
    Creates a combination of products that reduces the inventory for a specific pick-up station s and a pick-up time n
    """
    K_minus = {}
    for s in range(S):
        for n in range(N):
            filtered_data = product_table.iloc[:, [1,2,3,4]][(product_table['pickupStn'] == s) & (product_table['pickupTime'] <= n)]
            acceptable_booking = []
            for k in range(len(filtered_data)):
                #for n_prime in range(filtered_data.iloc[k,2] + 1):
                if filtered_data.iloc[k,0] == filtered_data.iloc[k,1]: #return trip
                    if filtered_data.iloc[k,2] >=  n -filtered_data.iloc[k,3] + 1:
                        acceptable_booking.extend([(filtered_data.iloc[k,0],filtered_data.iloc[k,1],filtered_data.iloc[k,2],filtered_data.iloc[k,3])])
                else: 
                    acceptable_booking.extend([(filtered_data.iloc[k,0],filtered_data.iloc[k,1],filtered_data.iloc[k,2],filtered_data.iloc[k,3])])
                K_minus[(s,n)] = acceptable_booking
    return K_minus
                    
def increase_inventory_set(S,N,product_table):
    """
    Creates a combination of products that increases the inventory for a specific pick-up station s and a pick-up time n
    """
    K_plus = {}
    for s in range(S):
        for n in range(N):
            filtered_data = product_table.iloc[:, [1,2,3,4]][(product_table['pickupStn'] != s) & (product_table['returnStn'] == s)& (product_table['pickupTime'] <= n)]
            acceptable_booking = []
            for k in range(len(filtered_data)):              
                if filtered_data.iloc[k,2] + filtered_data.iloc[k,3] <= n  :
                    acceptable_booking.extend([(filtered_data.iloc[k,0],filtered_data.iloc[k,1],filtered_data.iloc[k,2],filtered_data.iloc[k,3])])
                K_plus[(s,n)] = acceptable_booking
    return K_plus

#function to calculate T(k)
def no_bookingPeriods(N,Tau):
    T_k = {}
    """
    Creates a dictionary that maps the no of booking periods for each rental period n in N 
    """
    for n in range(N):
        T_k[n] = ((n + 1) * Tau)/N 
    return T_k

#functions to help calculate inventory loss or gain in constraint 5c
def reduce_inventory(s,n,K,product_table,offerset,beta_dist,beta_disc,routing_matrix,K_minus,h): # check the return station in the case of noAlts and withAlts
    # print(product_table)
    cars_consumed = 0
    for n_prime in range(n + 1):
        K_s_n = K[(s,n_prime)]
        for k in K_s_n:
            # print(k)
            mask = (product_table['pickupStn'] == k[0]) & (product_table['returnStn'] == k[1]) & (product_table['pickupTime'] == k[2]) & (product_table['LOR'] == k[3])            
            # print(mask)
            idx = product_table[mask].index[0]
            # print(idx)
            counter = -1
            choicesets = offerset[idx]
            for choiceset in choicesets:
                counter += 1
                P = generalFunctions.choice_prob("default", choiceset, beta_dist, beta_disc)
                for choice in choiceset:
                    if choice == (-1,-1):
                        binary_indicator = 0
                    else:
                        if choice == (0,0):
                            return_stn = k[1]
                        else:
                            route = routing_matrix.iloc[k[1]]
                            return_stn = route[route == choice[0]].index.to_list()[0]
                        alt_book = (k[0], return_stn, k[2], k[3])
                        if alt_book in K_minus[(s,n)]:
                            binary_indicator = 1
                        else:
                            binary_indicator = 0
                    cars_consumed += binary_indicator * product_table.iloc[idx,-1] * P[choice] * h[idx,counter]
    return cars_consumed

def increase_inventory(s,n,S,K,product_table,offer_set,beta_dist,beta_disc,routing_matrix,K_plus,h):
    # print(product_table)
    cars_added = 0
    for s_prime in [x for x in range(S) if x != s ]:
        if n == 0:
            cars_added = 0
        else:
            for n_prime in range(n):
                K_s_n = K[(s_prime,n_prime)]
                for k in K_s_n:
                    mask = (product_table['pickupStn'] == k[0]) & (product_table['returnStn'] == k[1]) & (product_table['pickupTime'] == k[2]) & (product_table['LOR'] == k[3])
                    # print(mask)
                    idx = product_table[mask].index[0]
                    # print(idx)
                    counter = -1
                    choicesets = offer_set[idx]
                    for choiceset in choicesets:
                        counter += 1
                        P = generalFunctions.choice_prob("default", choiceset, beta_dist, beta_disc) 
                        for choice in choiceset:
                            if choice == (-1,-1):
                                binary_indicator = 0
                            else:
                                if choice == (0,0):
                                    return_stn = k[1]
                                else:
                                    route = routing_matrix.iloc[k[1]]
                                    return_stn = route[route == choice[0]].index.to_list()[0]
                                alt_book = (k[0], return_stn, k[2], k[3])
                                if alt_book in K_plus[(s,n)]:
                                    binary_indicator = 1
                                else:
                                    binary_indicator = 0
                            cars_added += binary_indicator * product_table.iloc[idx,-1] * P[choice] * h[idx,counter]                    
    return cars_added

#function to calculate revenue in the objective function equation 5a
def total_revenue(product_table,offer_set,beta_dist, beta_disc,rentalrate,h):
    # print(product_table)
    total_revenue = 0
    for k in range(len(product_table)):  
        choicesets = offer_set[k]
        counter = -1
        for choiceset in choicesets: 
            counter += 1
            sum_choices = 0
            if (len(choiceset) == 1) and (choiceset == [(-1, -1)]):
                total_revenue += 0                                                                                                           
            else:
                P = generalFunctions.choice_prob("default", choiceset, beta_dist, beta_disc)
                for choice in choiceset:
                    sum_choices += (1-choice[1]/100) * P[choice] 
                total_revenue += product_table.iloc[k,5] * (rentalrate * product_table.iloc[k,4] * sum_choices) * h[k,counter]
            # print(total_revenue)
    return total_revenue        

#function to calculate parking costs in the objective function equation 5a
def total_park_fees(S,N, park_fee, z):
    total_park_fees = 0 
    for s in range(S):
        for n in range(N):
            total_park_fees += park_fee *  z[s,n]
    return total_park_fees

#function to help correct rounding errors in h(J(k))
def check_cdlpmatrix(cdlp_matrix, product_table, Tau,N):
    # print("initial size of matrix", len(dlp_matrix))
    df = pd.DataFrame(columns=['prodIdx','n','tau'])
    df['prodIdx'] = product_table['prodIdx']
    df['n'] = product_table['pickupTime']
    df['tau'] = ((product_table['pickupTime'] + 1) * Tau)/N 
    df = df.astype("int")
    # df = df.iloc[0:len(product_table)-1,:]
    # print(df)
    df1 = cdlp_matrix.groupby("prodIdx")['tau'].count().reset_index()
    df1['tau_diff'] = (df1['tau'] - df['tau'])
    del_rows = list(df1[df1['tau_diff'] > 0].index)
    increase_rows = list(df1[df1['tau_diff'] < 0].index)
    # print("delete_rows", del_rows)
    # print("increase_rows",increase_rows)
    if increase_rows:
        for i in increase_rows:
            # print("increase_rows")
            no_rows = abs(int(df1['tau_diff'][df1['prodIdx']==i].iloc[0])) 
            # print("no_rows",no_rows)
            idx = list(cdlp_matrix[cdlp_matrix.prodIdx == i].index)[-1]
            # print(idx)
            # print(row_list)
            cdlp_matrix = cdlp_matrix.append(cdlp_matrix.iloc[[idx]*no_rows])
            # print(dlp_matrix)
            cdlp_matrix = cdlp_matrix.sort_index()
            cdlp_matrix.iloc[idx + 1,1] += 1
            # print(dlp_matrix)
    if del_rows:
        # print("delete_rows")
        for i in del_rows:
            # no_rows = int(df1['tau_diff'][df1['prodIdx']==i].iloc[0])
            # print(no_rows)
            idx = list(cdlp_matrix[cdlp_matrix.prodIdx == i].index)[-1]
            # print(idx)
            cdlp_matrix.drop(index=idx, inplace = True)
    cdlp_matrix = cdlp_matrix.reset_index()
    cdlp_matrix.drop(cdlp_matrix.columns[[0]], axis=1, inplace=True)
     # print(dlp_matrix)
    return cdlp_matrix

#function to sort h(J(k)) decisions based on heuristics
def sort_matrix(sol_matrix, T_k):
    new_list = []
    for i in range(len(sol_matrix)):
        if sol_matrix.iloc[i,2] not in list(T_k.values()):
            prod = sol_matrix[sol_matrix.prodIdx == sol_matrix.iloc[i,0]]
            if 0 in list(prod.offerIdx.unique()):
                sorted_prod = prod.sort_values('offerIdx', ascending = False)
                prod_list = sorted_prod.values.tolist()
                for i in range(len(prod_list)):
                    if prod_list[i] not in new_list:
                        new_list.append(prod_list[i])
            else:
                new_list.append([sol_matrix.iloc[i,0],sol_matrix.iloc[i,1], sol_matrix.iloc[i,2]])
        else:
            new_list.append([sol_matrix.iloc[i,0],sol_matrix.iloc[i,1], sol_matrix.iloc[i,2]])
    sorted_solmatrix = pd.DataFrame(new_list,columns=sol_matrix.columns)
    sorted_solmatrix = sorted_solmatrix.astype("int")
    return sorted_solmatrix

#function to get CDLP admissable policy
def decision_matrix(data, sol,product_table, T_k,Tau,N):
    sol_matrix = pd.DataFrame(data, columns = [ 'var', 'prodIdx','offerIdx', 'offerPeriods'])
    sol_matrix = sol_matrix.iloc[:,1:][(sol_matrix["var"] == "h") & (sol_matrix["offerPeriods"] > 0)].reset_index(drop = True)
    sol_matrix = sol_matrix.astype({"prodIdx": int, "offerIdx": int,  "offerPeriods": float})
    sol_matrix.offerPeriods = np.floor(sol_matrix.offerPeriods + perturbation)
    sorted_solmatrix = sort_matrix(sol_matrix, T_k)
    sorted_solmatrix['index'] = list(range(len(sorted_solmatrix)))
    # dlp_matrix = sorted_solmatrix.loc[sorted_solmatrix.index.repeat(np.floor(sorted_solmatrix.offerPeriods + perturbation))]
    cdlp_matrix = sorted_solmatrix.loc[sorted_solmatrix.index.repeat(sorted_solmatrix.offerPeriods)]
    tau_list = []
    for i in range(len(product_table)):
        filtered = cdlp_matrix[cdlp_matrix.prodIdx == i]
        counter = -1
        for j in range(len(filtered)):
            counter += 1
            tau_list.append(counter)
    cdlp_matrix['tau'] = tau_list
    cdlp_matrix = cdlp_matrix[['prodIdx', 'tau', 'offerIdx']].reset_index(drop = True)
    checked_matrix = check_cdlpmatrix(cdlp_matrix, product_table, Tau,N)
    return checked_matrix 

#functions to get duals
def get_timeduals(model,name,index):
    duals = {}
    for i in range(index):
        cons_name = name + str(i + 1)
        duals[i] = model.get_constraint_by_name(cons_name).dual_value    
    return duals 

def get_otherduals(model,name,S,N):
    duals = {}
    index = 0
    for n in range(N):
        for s in range(S):
            index += 1
            cons_name = name + str(index)
            duals[(s,n)] = model.get_constraint_by_name(cons_name).dual_value    
    return duals 

#function to solve CDLP model
def solve_cdlp(scenario,product_table,offer_set, S,N,T_k, K, beta_dist, beta_disc,routing_matrix, K_minus, x_s_n,K_plus, park_space, rentalrate, park_fee,checkDCOMP):
    if scenario == 1:
        cdlp = Model('DLP model without alternatives') #instance of model with name
    else:
        cdlp = Model('DLP model with alternatives') #instance of model with name
    #decision variables
    keys = [(k,j) for k in range(len(product_table)) for j in range(len(offer_set[k]))]
    keys2 = [(s,n) for s in range(S) for n in range(N)]
    h = cdlp.continuous_var_dict(keys, name = 'h', lb = 0)
    # h = dlp.integer_var_dict(keys, name = 'h', lb = 0)
    y = cdlp.continuous_var_dict(keys2, name = 'y', lb = 0)
    # y = dlp.integer_var_dict(keys2, name = 'y', lb = 0)
    z = cdlp.continuous_var_dict(keys2, name = 'z', lb = 0)
    #time constraint (5b)
    cdlp.add_constraints([cdlp.sum(h[k,j] for j in range(len(offer_set[k])))== T_k[product_table.iloc[k,3]] for k in range(len(product_table))], "time_cons")
    #capacity constraint (5c)
    cdlp.add_constraints([y[s,n] + reduce_inventory(s, n, K, product_table, offer_set, beta_dist, beta_disc, routing_matrix, K_minus, h) 
                          - increase_inventory(s, n, S, K, product_table, offer_set, beta_dist, beta_disc, routing_matrix, K_plus, h) == x_s_n[s,n] for n in range(N) for s in range(S)]
                        , "capacity_cons")
    #parking space constraint (5d) 
    cdlp.add_constraints([y[s,n] - park_space.iloc[s,0] <= z[s,n] for n in range(N) for s in range(S)], names="parking_cons")       
    #objective function (5a)
    obj_fxn = total_revenue(product_table,offer_set,beta_dist,beta_disc,rentalrate,h) - total_park_fees(S,N, park_fee, z) #- total_park_fees #calculating objective function
    #set objective function
    cdlp.set_objective("max", obj_fxn) 
    #print model info
    # dlp.print_information()
    #write lp file
    cdlp.export_as_lp("{0}_dlpfile.lp".format(scenario))
    #solve the model
    if checkDCOMP:
        primal_starttime = time.time()
        sol = cdlp.solve(log_output = True)
        sol.display()
        primal_endtime = time.time() - primal_starttime
    else:
        sol = cdlp.solve(log_output = False)
    
    
    #export solution as json file
    # dlp.solution.export("C:/Users/bsraf3/OneDrive - Loughborough University/PhD/DLP/{0}_dlpsoln_{1}.csv".format(scenario,filename.rstrip(".csv")))
    #get solution results
    data = [v.name.split('_') + [sol.get_value(v)] for v in cdlp.iter_variables()]
    if checkDCOMP:
        time_duals = get_timeduals(cdlp,"time_cons",len(product_table))
        capacity_duals = get_otherduals(cdlp,"capacity_cons",S,N)
        parking_duals = get_otherduals(cdlp,"parking_cons",S, N)
        return time_duals,capacity_duals,parking_duals,data,sol,primal_endtime
    else:
        return data, sol
    # print model solution
    # dlp.print_solution()   
    
#%%
def validOffers(product, state, offer,N):
    # print("state", state)
    # print("product", product)
    # print("offer", offer)
    if product['pickupStn'] == product['returnStn']:
        # check if one way rental is possible, cars must be available from n to N
        boolean = state[int(product['pickupStn']),int(product['pickupTime']):N] >= 1
        # print(boolean)
        if boolean.all() == True:
            valid_offers = offer
        else:
            # check if return trip is possible, cars must be available from n to n + m - 1
            boolean = state[int(product['pickupStn']),int(product['pickupTime']):min
                            (N, int(product['pickupTime']) + int(product['LOR']))] >= 1
            # print(boolean)
            if boolean.all() == True:
                valid_offers = [(0, 0)]
            else:
                valid_offers = [(-1, -1)]
    else:
        # check if one way rental is possible, cars must be available from n to N
        boolean = state[int(product['pickupStn']), int(product['pickupTime']):N] >= 1
        # print(boolean)
        if boolean.all() == True:  # offer set
            valid_offers = offer
        else:
            valid_offers = [(-1, -1)]
    # print(valid_offers)
    return valid_offers

  
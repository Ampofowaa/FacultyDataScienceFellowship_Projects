# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 10:16:05 2025

@author: k2370694
"""

#%% import modules
import time
import numpy as np
import pandas as pd
import random as r
import math as m
import general_functions as gf
from copy import deepcopy
from scipy.optimize import fsolve
#%%function to generate journeys
def gen_journeyTWs(request,earth_radius, vehicle_speed, departafter_indicator, noG_max, Delta, service_duration):
    # calculate travel time
    travel_time = gf.haversine_distance(request[2], request[3], earth_radius) /vehicle_speed * 60
    #generate journey options
    if request[2] == departafter_indicator: #depart after so pickup request time provided
        pickup_reqtime = request[5]
        dropoff_reqtime = request[6]
    else: #arrive by so dropoff request time provided
        dropoff_reqtime = request[6]
        pickup_reqtime = request[5]
    G_x_t = gf.gen_G_xt(pickup_reqtime, dropoff_reqtime, travel_time, noG_max, Delta, service_duration)
    requestTWs = gf.gen_requestTWs(pickup_reqtime, dropoff_reqtime,noG_max, Delta)
   
    #randomly select one of the journey options
    sel_idx = r.choice(list(G_x_t.keys()))
    
    #assign TWs
    if request[4] == departafter_indicator: #pickup time is given, so options generated on drop-off
        TWs_dropoff = G_x_t[sel_idx]
        TWs_pickup = requestTWs[sel_idx] 
    else:
        TWs_pickup =  G_x_t[sel_idx]
        TWs_dropoff = requestTWs[sel_idx]
    # print("selected_journey", sel_idx)
    # print("initial request", request)
    journeyTWs = [TWs_pickup, TWs_dropoff]
    # print("updated request", request)
    return journeyTWs

#%% function to simulate historical journeys
def simulate_histactualjourneys(no_weeks,no_days,lambda_,probs_timeperiod,allprobs_origins,
                                od_matrices,departafter_indicator,latlongs,earth_radius, vehicle_speed, noG_max, Delta, service_duration):
    tot_demandsper_day = []
    requests = []
    journeys = []
    
    for week_no in range(1, no_weeks+1):
        for day in range(1,no_days+1):
            tot_norequests = np.random.poisson(lam=lambda_) #use of a poisson distribution with mean 80
            tot_demandsper_day.append(tot_norequests)
            # print("total number of requests", tot_norequests)
            for request_id in range(1,tot_norequests+1):
                #first generate request
                request = gf.gen_request(probs_timeperiod,allprobs_origins,od_matrices,departafter_indicator,latlongs)
                requests.append({
                    'week_no': week_no,
                    'day': day,
                    'cus_id': request_id,
                    'o_zone': request[0],
                    'd_zone': request[1],
                    'o_coords': request[2],
                    'd_coords': request[3],
                    'req_type': request[4],
                    'reqpickup_time': request[5],
                    'reqdropoff_time':request[6]})

                #now generate the journeys - i.e. requests with TWs
                journeyTWs = gen_journeyTWs(request,earth_radius, vehicle_speed, departafter_indicator, 
                                            noG_max, Delta, service_duration)
                journeys.append({
                    'week_no': week_no,
                    'day': day,
                    'cus_id': request_id,
                    'o_zone': request[0],
                    'd_zone': request[1],
                    'o_xcoords': request[2][0],
                    'o_ycoords': request[2][1],
                    'd_xcoords': request[3][0],
                    'd_ycoords': request[3][1],
                    'req_type': request[4],
                    'reqpickup_time': request[5],
                    'reqdropoff_time': request[6],
                    'pickupTWs_lb':journeyTWs[0][0],
                    'pickupTWs_ub':journeyTWs[0][1],
                    'dropoffTWs_lb':journeyTWs[1][0],
                    'dropoffTWs_ub':journeyTWs[1][1]
                    })
                
    #convert to a pandas dataframe 
    requests_df = pd.DataFrame(requests)
    journeys_df = pd.DataFrame(journeys)
    return requests_df, journeys_df
#%% functions for google or tools capacitated pickup and delivery problem with time windows data prep and implementation 
#get time matrix for routing data model
def get_timematrix(journeys,allzones_travelmat):
    time_mat = np.zeros((len(journeys)*2+1, len(journeys)*2+1), dtype=int) #to store the traveltimes
    #get all pickup zones
    pickup_zones = journeys['o_zone'].tolist()
    #get all dropoff zones
    dropoff_zones = journeys['d_zone'].tolist()
    #combine depot, pickup and dropoff zones together
    allzones = [0] + pickup_zones + dropoff_zones
    
    for node1 in range(len(journeys)*2+1):
        for node2 in range(len(journeys)*2+1):
            time_mat[node1][node2] = round(allzones_travelmat[allzones[node1],allzones[node2]],0)
    return time_mat

#get TWs for routing data model
def get_TWs(journeys, depotTWs):
    depotTWs = [tuple(depotTWs)]
    pickupTWs = list(zip(journeys['pickupTWs_lb'], journeys['pickupTWs_ub']))
    dropoffTWs = list(zip(journeys['dropoffTWs_lb'], journeys['dropoffTWs_ub']))
    allTWs = [*depotTWs, *pickupTWs, *dropoffTWs]
    return allTWs


def create_data_model(journeys, allzones_travelmat, no_vehicles, no_pax, max_capacity,
                      depotTWs):
    journeys = journeys.astype({'pickupTWs_lb': 'int', 'pickupTWs_ub': 'int',
                                'dropoffTWs_lb': 'int', 'dropoffTWs_ub': 'int'})

    data = {}
    data['time_matrix'] = get_timematrix(journeys,allzones_travelmat)
    data['pickups_dropoffs'] = [[i,i+len(journeys)] for i in range(1,len(journeys)+1)]
    data['time_windows'] = get_TWs(journeys,depotTWs)
    data['num_vehicles'] = no_vehicles
    data['depot'] = 0 
    data["demands"] = [0 if node == 0 else no_pax if (node > 0 and node <= len(journeys)) else
                       -no_pax for node in range(2*len(journeys)+1)]
    data["vehicle_capacities"] = [max_capacity] * no_vehicles
    # data['max_ridetimes'] = get_maxridetimes(len(journeys),data['time_matrix'],scaler)
    # print(data)
    return data

def get_routes(solution, routing, manager):
    """Get vehicle routes from a solution and store them in an array."""
    # Get vehicle routes and store them in a two dimensional array whose
    # i,j entry is the jth location visited by vehicle i along its route.
    routes = []
    for route_nbr in range(routing.vehicles()):
        index = routing.Start(route_nbr)
        route = [manager.IndexToNode(index)]
        while not routing.IsEnd(index):
            index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))
        routes.append(route)
    return routes

def solve_DARP(journeys, allzones_travelmat,no_vehicles, no_pax, max_capacity, depotTWs):
    while True:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        # Instantiate the data problem.
        data = create_data_model(journeys,allzones_travelmat,no_vehicles, no_pax, max_capacity,
                                 depotTWs)
        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(
            len(data['time_matrix']), data["num_vehicles"], data["depot"])
        # print(manager)
        # Create Routing Model.
        routing = pywrapcp.RoutingModel(manager)
        # Create and register a transit callback.
        def time_callback(from_index, to_index):
            """Returns the travel time between the two nodes."""
            # Convert from routing variable Index to time matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["time_matrix"][from_node][to_node]
           
        transit_callback_index = routing.RegisterTransitCallback(time_callback)
            
        # Define cost of each arc.
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
        # Add Time Windows constraint.
        time = "Time"
        routing.AddDimension(
            transit_callback_index,
            30,  # allow waiting time
            data["time_windows"][0][1],  # maximum time per vehicle 
            False,  # Don't force start cumul to zero.
            time,
        )
        time_dimension = routing.GetDimensionOrDie(time)
        # print(time_dimension)
        # Add time window constraints for each location except depot.
        # print("time windows",data['time_windows'])
        for location_idx, time_window in enumerate(data["time_windows"]):
            if location_idx == data["depot"]:
                continue
            index = manager.NodeToIndex(location_idx)
            # print("index", index)
            # print("time window", time_window)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        # Add time window constraints for each vehicle start node.
        depot_idx = data["depot"]
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(
                data["time_windows"][depot_idx][0], data["time_windows"][depot_idx][1]
            )
        
        # Instantiate route start and end times to produce feasible times.
        for i in range(data["num_vehicles"]):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(i))
            )
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))
                
        # Add Capacity constraint.
        def demand_callback(from_index):
            """Returns the demand of the node."""
            # Convert from routing variable Index to demands NodeIndex.
            from_node = manager.IndexToNode(from_index)
            return data["demands"][from_node]
    
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            data["vehicle_capacities"],  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity",
        )
            
        # Define Transportation Requests.
        for request in data["pickups_dropoffs"]:
            # max_ridetime = data['max_ridetimes'][request[0]]
            # print("max ride time", max_ridetime)
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
            )
            routing.solver().Add(
                time_dimension.CumulVar(pickup_index)
                < time_dimension.CumulVar(delivery_index)
            )
            # routing.solver().Add(
            #     time_dimension.CumulVar(delivery_index) - time_dimension.CumulVar(pickup_index) 
            #     <= max_ridetime
            #     )
            
        # Setting first solution heuristic.
       #  search_parameters = pywrapcp.DefaultRoutingSearchParameters()
       #  search_parameters.first_solution_strategy = (
       # routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION)
        
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.seconds = 60
        # search_parameters.log_search = True
    
        # Solve the problem.
        solution = routing.SolveWithParameters(search_parameters)
    
        # Print solution on console.
        if solution:
            # print("Feasible solution found")
            # print_solution(data, manager, routing, solution)
            soln_aftersearch = get_routes(solution, routing, manager)
            # print("soln after search",soln_aftersearch)
            return journeys, soln_aftersearch
        else:
            # print("Feasible solution not found")
            # print(journeys)
            #randomly delete one of the journeys
            journeys = journeys[~journeys.index.isin([r.choice(journeys.index)])]
            if len(journeys) > 0:
                # print(journeys)
                #reset request_id column
                journeys.loc[:,'cus_id'] = range(1,len(journeys)+1)
                #reset index
                journeys.reset_index(drop=True, inplace=True)
                # print(journeys)
                #resolve the problem
                continue
            else:
                # print(journeys)
                return journeys, None
#%% function to check feasibility of journeys
def check_feasible_journeys(journeys, allzones_travelmat,num_weeks, num_days, no_vehicles, no_pax, max_capacity,
                            depotTWs):
    
    feasible_journeys = pd.DataFrame()
    for week in range(1,num_weeks+1):
        for day in range(1,num_days+1):
            weekday_journeys = journeys[(journeys['week_no']==week) & (journeys['day']==day)]
            soln,routes = solve_DARP(weekday_journeys,allzones_travelmat, no_vehicles, no_pax, max_capacity,
                                     depotTWs)
            feasible_journeys = pd.concat([feasible_journeys,soln])
            # print(feasible_journeys)
    feasible_journeys.reset_index(drop=True, inplace=True)
    return feasible_journeys
#%% functions for forecasting journey samples
def forecast_norequests(npriorweeks_requests):
    forecast_noreqs = round(npriorweeks_requests.groupby('day')['total_requests'].mean().reset_index().set_index('day'))
    #weekday_demand['forecast_SMA'] =  round(weekday_demand['total_requests'].rolling(window=window).mean(),0)    
    return forecast_noreqs

def forecast_requestinfo(no_samples,journeys,ndaily_forecasts,num_days, no_priorweeks, num_weeks,maxroutedur):
    allforecast_requests = pd.DataFrame()
    for sample_id in range(1,no_samples+1):
        for n in range(1,num_days+1):
            #get journeys for no for that same day
            n_prevjourneys = journeys[(journeys['day'] == n) & (journeys['week_no'].isin(list(
            range(num_weeks-no_priorweeks+1, num_weeks + 1))))].reset_index(drop=True)
            #randomly sample forecast requests from previous journeys
            n_forecastreqsinfo = n_prevjourneys[['day','o_zone','d_zone','o_xcoords','o_ycoords','d_xcoords','d_ycoords', 'reqpickup_time',
                                                 'reqdropoff_time','pickupTWs_lb','pickupTWs_ub', 'dropoffTWs_lb', 'dropoffTWs_ub']].sample(n=ndaily_forecasts.loc[n, 'total_requests']).reset_index(drop=True)      
            n_forecastreqsinfo['sample_id'] = sample_id
            allforecast_requests = pd.concat([allforecast_requests, n_forecastreqsinfo], ignore_index=True)
    return allforecast_requests

def get_forecastTWs(row, noG_max, Delta, allzones_travelmat, service_dur, max_dur):
    #TODO: Improve this code by factoring the travel time and the service duration
    dir_traveltime = allzones_travelmat[row['o_zone'], row['d_zone']]
    if row['reqpickup_time'] == row['pickupTWs_lb']: #generate wide time windows on the pickup and no TWs on the drop-off
        row['pickupTWs_ub'] = row['pickupTWs_lb'] + (noG_max * Delta)
        row['dropoffTWs_lb'] = row['pickupTWs_lb'] + service_dur + dir_traveltime #earliest time to arrive at the drop-off
        row['dropoffTWs_ub'] = max_dur
    elif row['reqdropoff_time'] == row['dropoffTWs_ub']:
        row['dropoffTWs_lb'] = row['dropoffTWs_ub'] - (noG_max * Delta)  
        row['pickupTWs_lb'] = row['dropoffTWs_lb'] - service_dur - dir_traveltime
        row['pickupTWs_ub'] = max_dur
    return row

def initial_routes(forecast_sample,allzones_travelmat,no_forecastsample,numdays,no_vehicles, no_pax, max_capacity,
        depotTWs):
    feasible_routes = {}
    feasible_journeys = pd.DataFrame()
    for sample_id in range(1,no_forecastsample+1):
        for day in range(1,numdays+1):
            forecast_journeys = forecast_sample[(forecast_sample['sample_id'] == sample_id) & (forecast_sample['day']==day)]
            # print(forecast_journeys)
            soln,routes = solve_DARP(forecast_journeys, allzones_travelmat,no_vehicles, no_pax, max_capacity, depotTWs)
            feasible_journeys = pd.concat([feasible_journeys,soln])
            feasible_routes[(sample_id,day)] = routes
    feasible_journeys.reset_index(drop=True, inplace=True)
    return feasible_journeys, feasible_routes

def gen_prices(row,allzones_distmat,bus_fare,cost_perkm):
    dist_km = allzones_distmat[row['o_zone'], row['d_zone']]
    row['price'] = round(r.uniform(bus_fare, cost_perkm*dist_km),2)
    return row

def gen_forecastjourneys(feasible_journeys,num_weeks,num_days,no_priorweeks,no_sampleforecasts,allzones_travelmat,
                         allzones_distmat,num_veh,no_passengers, Q, depotTWs,noG_max, Delta,service_duration,max_T,
                         bus_fare,cost_perkm):
    #---forecasting samples
    #get number of feasible journeys received no_priorweeks for a particular day
    weekly_demand = feasible_journeys.groupby(['week_no','day']).size().reset_index(name='total_requests')
    npriorweeks_norequests = weekly_demand[weekly_demand['week_no'].isin(list
            (range(num_weeks-no_priorweeks+1,num_weeks+1)))].reset_index(drop=True)
    #set forecast for each day via a simple moving average (SMA) based on the no of prior weeks for that same day
    forecast_nodailyrequests = forecast_norequests(npriorweeks_norequests)
    # Change the dtype of 'total_requests' to int
    forecast_nodailyrequests["total_requests"] = forecast_nodailyrequests["total_requests"].astype(int)
    # forecast_nodailyrequests.to_csv('no_forecastrequests.csv')
    #forecast sample 
    forecast_sample = forecast_requestinfo(no_sampleforecasts,feasible_journeys,forecast_nodailyrequests,num_days, no_priorweeks, num_weeks, max_T)
    # forecast_sample.to_csv('forecastsample.csv', index=None)
    #update TWs - give widest TWs at one end and no TWs at the other end
    forecast_sample = forecast_sample.apply(get_forecastTWs, args=(noG_max, Delta, allzones_travelmat, service_duration,max_T), axis=1)
    # forecast_sample.to_csv('updatedforecast_TWs.csv', index=None)
    #set datatyes --> might need to include reqdropoff_time as int in other simulation runs
    forecast_sample = forecast_sample.astype({"day": int, "o_zone":int,"d_zone":int, "reqpickup_time": int,
                                              "pickupTWs_lb":int,"pickupTWs_ub":int, "dropoffTWs_lb":int,"dropoffTWs_ub":int,"sample_id": int})
    #check feasibility of forecast sample and create initial routes
    feasible_forecastjourneys, routes =  initial_routes(forecast_sample, allzones_travelmat,no_sampleforecasts,num_days,num_veh,
                                                        no_passengers, Q, depotTWs)
    #generate prices 
    feasible_forecastjourneys = feasible_forecastjourneys.apply(gen_prices, args=(allzones_distmat,bus_fare,cost_perkm),axis=1)
    #rearrange columns, set dtypes
    feasible_forecastjourneys = feasible_forecastjourneys.astype({"day": int, "o_zone":int,"d_zone":int, "reqpickup_time": int,
                                              "pickupTWs_lb":int,"pickupTWs_ub":int, "dropoffTWs_lb":int,"dropoffTWs_ub":int,"sample_id": int})
    feasible_forecastjourneys = feasible_forecastjourneys[['sample_id', 'day','o_zone','d_zone','o_xcoords','o_ycoords','d_xcoords','d_ycoords', 'reqpickup_time',
                                         'reqdropoff_time','pickupTWs_lb','pickupTWs_ub', 'dropoffTWs_lb', 'dropoffTWs_ub','price']]
    feasible_forecastjourneys.to_csv('forecastjourneys_price.csv', index=None)
    # print("Feasible routes", routes)
    return feasible_forecastjourneys, routes

#%% main function to generate set of feasible forecast journeys
def gen_setofforecastorders(gen_forecastdata,num_weeks, num_days, no_potbookings, probs_timeperiod, allprobs_origins, od_matrices,
                          departafter_indicator, allzones_latlongs, earth_radius, vehicle_speed, noG_max, Delta, service_duration,
                          allzones_traveltimes,num_vehicles, no_passengers,veh_cap,depotTWs,no_priorweeks,no_sampleforecasts,
                          allzones_distmat,max_routedur,bus_fare,fuelcost_perkm):
    if gen_forecastdata:
        #Step 1: Run simulation to generate set of forecast journeys
        fp_requests, fp_journeys = simulate_histactualjourneys(num_weeks, num_days, no_potbookings, probs_timeperiod, allprobs_origins, od_matrices,
                                  departafter_indicator, allzones_latlongs, earth_radius, vehicle_speed, noG_max, Delta, service_duration)
        # print(fp_requests, fp_journeys)
        
        #Step 2: Check feasibility of forecast journeys, if infeasible delete one of the journeys at random 
        #and repeat feasibility check until feasible
        fp_feasiblejourneys = check_feasible_journeys(fp_journeys,allzones_traveltimes,num_weeks,num_days,num_vehicles, no_passengers,veh_cap,depotTWs)
        #Step 3: Generate forecast samples
        fp_feasforecastjourneys, fp_initialroutes = gen_forecastjourneys(fp_feasiblejourneys,num_weeks,num_days,no_priorweeks,no_sampleforecasts,allzones_traveltimes,
                                 allzones_distmat,num_vehicles,no_passengers, veh_cap, depotTWs,noG_max, Delta,service_duration,max_routedur,bus_fare,fuelcost_perkm)
    else:
        fp_feasforecastjourneys = pd.read_csv('./forecastjourneys_price29_01.csv')
        fp_initialroutes = {(1, 1): [[0, 5, 10, 4, 3, 8, 9, 0], [0, 2, 7, 1, 6, 0]], (1, 2): [[0, 2, 4, 0], [0, 1, 3, 0]], (1, 3): [[0, 2, 3, 1, 6, 5, 4, 0], [0, 0]], 
         (2, 1): [[0, 2, 4, 0], [0, 1, 3, 0]], (2, 2): [[0, 2, 4, 0], [0, 1, 3, 0]], (2, 3): [[0, 2, 5, 1, 4, 0], [0, 3, 6, 0]], (3, 1): [[0, 3, 2, 4, 7, 9, 8, 0], 
         [0, 5, 10, 1, 6, 0]], (3, 2): [[0, 1, 3, 0], [0, 2, 4, 0]], (3, 3): [[0, 3, 6, 0], [0, 1, 2, 4, 5, 0]]}
    return fp_feasforecastjourneys, fp_initialroutes

#%%functions for steps needed in opportunity cost estimation procedure
def get_corrveh(route, forecast_reqs_indices):
    for index, sublist in enumerate(route):
        if forecast_reqs_indices.issubset(sublist):
            return index, sublist
    return None, None  # Return None if the set is not found in any sublist

def get_corrzones(route,sample_forecast,request,reqpickup_idx,reqdropoff_idx,prev_sampidx,accepted_reqs):
    corr_zones = {}
    # print(route)
    # print(sample_forecast)
    for node in route:
        # print("node index in route", node)
        if node == 0: #depot
            corr_zones[node] = 0
        elif node == reqpickup_idx: #request pickup:
            corr_zones[node] = request['o_zone']
        elif node == reqdropoff_idx: #request dropoff
            corr_zones[node] = request['d_zone']
        elif node <= (reqpickup_idx -1)//2:
            #node refers to the pickup of that forecast request
            if prev_sampidx == 0:
                corr_zones[node] = sample_forecast.loc[node-1,'o_zone']
            else:
                corr_zones[node] = sample_forecast.loc[prev_sampidx+node,'o_zone']
        elif node >  (reqpickup_idx -1)//2 and node < reqpickup_idx:
            #node refers to the dropoff of that forecast request
            if prev_sampidx == 0:
                corr_zones[node] = sample_forecast.loc[node-len(sample_forecast)-1,'d_zone']
            else:
                corr_zones[node] = sample_forecast.loc[prev_sampidx+(node-len(sample_forecast)),'d_zone']
        else: #case where the node is an actual accepted request
            if len(accepted_reqs) != 0:
                print(accepted_reqs)
    return corr_zones

def get_corrtimematrix(corr_zones,allzones_traveltimes):
    # print(corr_zones)
    time_matrix = {}
    for idx1,node1 in corr_zones.items():
        for idx2,node2 in corr_zones.items():
            time_matrix[idx1,idx2] = round(allzones_traveltimes[node1,node2],4)
    return time_matrix
    
def get_corrdistmatrix(corr_zones,allzones_distmat):
    # print(corr_zones)
    distance_matrix = {}
    for idx1,node1 in corr_zones.items():
        for idx2,node2 in corr_zones.items():
            distance_matrix[idx1,idx2] = round(allzones_distmat[node1,node2],4)
    return distance_matrix    

#function to compute total route duration
def tot_routedur(route,route_timemat):
    # print(route)
    # print(route_timemat)
    route_dur = 0
    for node_posn in range(len(route)-1):
        route_dur += route_timemat[route[node_posn], route[node_posn+1]]
    return route_dur

#function to compute total route distance in km
def tot_routedist(route,route_distmat):
    # print(route)
    # print(route_distmat)
    route_dist = 0
    for node_posn in range(len(route)-1):
        route_dist += route_distmat[route[node_posn], route[node_posn+1]]
    return route_dist

#function to get TWs
def get_timewindows(route,sample_forecast,request,reqpickup_idx,reqdropoff_idx,depotTWs,journey_option,requestTW,prev_sampidx):
    # print(route)
    # print(sample_forecast)
    # print(request)
    TWs = {}
    for node in route:
        # print("node index in route", node)
        if node == 0: #depot
            TWs[node] = depotTWs
        elif node == reqpickup_idx and request['reqpickup_time']!= None: #request pickup time given 
            TWs[node] = [requestTW[0],requestTW[1]]
        elif node == reqpickup_idx and request['reqpickup_time']== None: #request pickup time not given; journey options used 
            TWs[node] = [journey_option[0],journey_option[1]]
        elif node == reqdropoff_idx and request['reqdropoff_time']!= None: #request dropoff time given 
            TWs[node] = [requestTW[0],requestTW[1]]
        elif node == reqdropoff_idx and request['reqdropoff_time'] == None: #request dropoff time not given; journey  options used 
            TWs[node] = [journey_option[0],journey_option[1]]
        elif node <= (reqpickup_idx -1)//2:
            #node refers to the pickup of that forecast request
            if prev_sampidx == 0:
                TWs[node] = [sample_forecast.loc[node-1,'pickupTWs_lb'],sample_forecast.loc[node-1,'pickupTWs_ub']]
            else:
                TWs[node] = [sample_forecast.loc[prev_sampidx+node,'pickupTWs_lb'],
                             sample_forecast.loc[prev_sampidx+node,'pickupTWs_ub']]
        elif node >  (reqpickup_idx -1)//2 and node < reqpickup_idx:
            #node refers to the dropoff of that forecast request
            if prev_sampidx == 0:
                TWs[node] = [sample_forecast.loc[node-len(sample_forecast)-1,'dropoffTWs_lb'],
                             sample_forecast.loc[node-len(sample_forecast)-1,'dropoffTWs_ub']]
            else:
                TWs[node] = [sample_forecast.loc[prev_sampidx+(node-len(sample_forecast)),'dropoffTWs_lb'],
                             sample_forecast.loc[prev_sampidx+(node-len(sample_forecast)),'dropoffTWs_ub']]
        else: #case where the node is an actual accepted request
            ...
    return TWs
   


def fp_isfeasible(route,zones_route,no_pax,time_matrix,service_dur,TWs,veh_cap,max_routedur, 
                  len_sampleforecasts,newreq_dropoffnode,accepted_reqs,multiplier):
    # print("temp_route", route)
    # print("zones in route", zones_route)
    # print("TWs", TWs)
    # print(time_matrix)
    #track the time that the bus arrives at the node, the time service starts(pickup or dropoffs) the time the bus leaves the node
    # print("max route dur", max_routedur)
    forecast_dropoffnodes = [i + len_sampleforecasts for i in range(1,len_sampleforecasts+1)]
    all_dropoffnodes = [newreq_dropoffnode,*forecast_dropoffnodes] #TODO: add dropoff nodes of accepted requests
    # print("all_dropoffnodes", all_dropoffnodes)
    corr_pickupnodes = {node: node - len_sampleforecasts for node in all_dropoffnodes} #TODO: ensure accepted request nodes are included
    # print("corr_pickupnodes", corr_pickupnodes)
    no_onboardpass = 0
    depot_depart = max(TWs[route[0]][0],TWs[route[1]][0] - time_matrix[route[0],route[1]])
    arrival_times = {route[0]: depot_depart}#start from the depot at deport_depart

    for i in range(1,len(route)):
        # print("node",route[i])
        if route[i] == 0:
            no_pass = 0
        elif route[i] in all_dropoffnodes: #handle no of passengers as negative for drop-offs
            no_pass = no_pax * -1
        else:
            no_pass = no_pax
        if no_onboardpass + no_pass <= veh_cap:
            #find the arrival time at that node, inherently captures waiting times
            arrival_time = max(arrival_times[route[i-1]] + service_dur \
                               + time_matrix[route[i-1],route[i]], TWs[route[i]][0])
            # print("arrival time at node", route[i], arrival_time)
            #check TWs violations
            if arrival_time > TWs[route[i]][1]:
                # print("TWs violated")
                return False
            #check passenger ride time violations
            if route[i] in all_dropoffnodes: 
                pass_ridetime = arrival_time - (arrival_times[corr_pickupnodes[route[i]]] + service_dur)
                # print("pass_ridetime", pass_ridetime)
                if pass_ridetime > multiplier * time_matrix[corr_pickupnodes[route[i]], route[i]]:
                    # print("Ride time violated")
                    return False
            #update no of onboard pass and arr times
            no_onboardpass += no_pass
            if i != len(route)-1: #this is to prevent the overwriting of the start depot results since both depots are repesented by 0
                arrival_times[route[i]] = arrival_time 
            else:
                arrival_times[-1] = arrival_time #change the key for the end depot to -1
            # print("No of onboard passengers", no_onboardpass)
            # print("arrrival times", arrival_times)
        else: #capacity is violated
            # print("capacity violated")
            return False
    #check maximum route duration    
    # print("arr times", arrival_times)
   
    if arrival_times[-1] - arrival_times[route[0]] > max_routedur:
        # print("max route duration violated")
        return False
    return True

def calc_revenueloss():
    return 0

#%% function for opportunity cost estimation
def calc_opportunitycost(request,journey_options,requestTWs,no_samples,cand_forecastjourneys,routes,day,accepted_reqs,no_forecastsamp_perday,
                         allzones_traveltimes,allzones_distmat,no_pax,service_dur,veh_capacity,max_T,multiplier,driverpay,fuelcost,depotTWs):
    """
    1. Sort journey options in descending order
    2. If there are any forecast journeys in current route:
    3.     For each journey option:
                For each candidate forecast journey:
                    temporarily 
                    Find the best forecast to be removed
        Else:
            Find the incremental delivery cost 
    """
    print("request",request)
    print("no forecast samp per day",no_forecastsamp_perday)
    print("states under consideration", accepted_reqs)
    opportunity_costs = {}
    sample_bestinsertcost = {}
    sample_bestvehicleposns = {}
    sample_bestcandforecast = {}
    request_idxs = {}
    starting_insertcost = 500
    #sort journey options in descending order of flexibility
    sorted_Gs = dict(sorted(journey_options.items(), key=lambda item: abs(item[1][1] - 
                          item[1][0]), reverse=True))

    for idx1,journey_option in sorted_Gs.items():
        print(idx1, journey_option)
        
        #loop through each sample
        for sample_id in range(1,no_samples+1):
            print("sample id", sample_id)
            best_insertcost = starting_insertcost #float('inf') #initialise best insertion cost
            best_vehicleidx = None #initialise best route
            best_forecastreq = None
            best_posns = None
            #get sample candidate forecasts for that day
            sample_candforecasts = cand_forecastjourneys[cand_forecastjourneys['sample_id']
                                  ==sample_id]
            print(sample_candforecasts)
            #get routes for that sample
            sample_route = routes[sample_id, day]
            print("route", sample_route)
            # print("accepted reqs to date", accepted_reqs)
            prev_sampidx = max(0,sample_candforecasts.index[0] - 1) #if sample_id == 1,0
            print("prev_sampidx", prev_sampidx)
            #derive pickup and dropoff index for the request in the route
            reqpickup_idx = max(2 * no_forecastsamp_perday[day,sample_id]+1,
                            max([request['route_reqpickupidx'] for request in accepted_reqs], 
                                default=-1)+1)
            #TODO: build in right logic to get the right reqdrop_off idx
            # reqdropoff_idx = reqpickup_idx + no_forecastsamp_perday[day,sample_id]
            reqdropoff_idx = max(reqpickup_idx + no_forecastsamp_perday[day,sample_id], 
                     max([request['route_reqdropoffidx'] for request in accepted_reqs], 
                         default=-1) + 1)
            print("request idxs", reqpickup_idx, reqdropoff_idx)
            request_idxs[sample_id] = (reqpickup_idx, reqdropoff_idx)
            
            #TODO: Think about the case where the route has no forecasts
            #loop through each candidate forecast
            for forecast_id in sample_candforecasts.index.to_list(): 
                print("cand forecast id", forecast_id)
                if sample_id == 1:
                    forecast_pickupidx = forecast_id + 1
                else:
                    forecast_pickupidx =  forecast_id -  prev_sampidx
                forecast_routeidx = (forecast_pickupidx, forecast_pickupidx + no_forecastsamp_perday[day,sample_id])
                print("forecast_idx", forecast_routeidx)
                # generate a temp route 
                copy_sampleroute = deepcopy(sample_route)
                # find vehicle route where the forecast request has been placed
                idx2, vehroute = get_corrveh(copy_sampleroute, set(forecast_routeidx))
                print("forecast route under consideration", idx2, vehroute)
                # get time_matrix, distancematrix for this vehroute
                zones_invehroute = get_corrzones(vehroute,sample_candforecasts,request,reqpickup_idx,reqdropoff_idx,prev_sampidx,accepted_reqs)
                print("zones in route", zones_invehroute)
                vehroute_timematrix = get_corrtimematrix(zones_invehroute,allzones_traveltimes)
                print("initial route time matrix", vehroute_timematrix)
                vehroute_distmatrix = get_corrdistmatrix(zones_invehroute,allzones_distmat)
                print("initial route distance matrix", vehroute_distmatrix)
                # remove forecast request
                routes_without_forecast = [node for node in vehroute if node not in forecast_routeidx] 
                print("routes with forecast removed", routes_without_forecast)
   
                #-------start insertion heuristics process: consider only the vehicle route in which the forecast order is temporarily removed from--------
                if len(routes_without_forecast) == 2: #empty route
                    temproute= [routes_without_forecast[0]] + [reqpickup_idx] + [reqdropoff_idx] + [routes_without_forecast[-1]]
                    print("temproute", temproute)
                    # get time_matrix, distancematrix for temp route + new request
                    zones_intemproute = get_corrzones(temproute,sample_candforecasts,request,reqpickup_idx,reqdropoff_idx,prev_sampidx,accepted_reqs)
                    print("zones in route", zones_intemproute)
                    temproute_timematrix = get_corrtimematrix(zones_intemproute,allzones_traveltimes)
                    print("initial route time matrix", temproute_timematrix)
                    temproute_distmatrix = get_corrdistmatrix(zones_intemproute,allzones_distmat)
                    print("initial route dist matrix", temproute_distmatrix)
                    extra_time = tot_routedur(temproute,temproute_timematrix) + 2*service_dur #service duration at both pick-up and drop-off
                    extra_dist = tot_routedist(temproute,temproute_distmatrix)
                    #use the  extra time of travel +service time * driver pay + distance * fuel cost
                    insertion_cost = (extra_time * driverpay)  + (extra_dist * fuelcost)
                    best_insertcost = insertion_cost #initialise best insertion cost
                    best_vehicleidx = idx2 #initialise best route
                    best_forecastreq = (forecast_id, forecast_routeidx) #forecast route_idx
                    best_posns = (1,2)
                    break  #continue to next journey option if we find bestposn
                else:
                    for pickuposn in range(1,len(routes_without_forecast)):
                        pickupseq = deepcopy(routes_without_forecast)
                        pickupseq.insert(pickuposn, reqpickup_idx)
                        # print("pickuposn", pickuposn)
                        # print("pickupseq", pickupseq)

                        for dropoffposn in range(pickuposn+1,len(pickupseq)):
                            copy_route = deepcopy(pickupseq)
                            copy_route.insert(dropoffposn,reqdropoff_idx)
                            # print("dropoffposn", dropoffposn)
                            # print("copyroute", copy_route)
                            # get time_matrix, distancematrix for the copy route
                            zones_incopyroute = get_corrzones(copy_route,sample_candforecasts,request,reqpickup_idx,reqdropoff_idx,prev_sampidx,accepted_reqs)
                            print("zones in route", zones_incopyroute)
                            copyroute_timematrix = get_corrtimematrix(zones_incopyroute,allzones_traveltimes)
                            print("initial route time matrix", copyroute_timematrix)
                            copyroute_distmatrix = get_corrdistmatrix(zones_incopyroute,allzones_distmat)
                            print("initial route dist matrix", copyroute_distmatrix)

                            # get TWs
                            copyroute_timewindows = get_timewindows(copy_route,sample_candforecasts,request,reqpickup_idx,reqdropoff_idx,
                                                                    depotTWs,journey_option,requestTWs[idx1],prev_sampidx)
                            print("time_windows",copyroute_timewindows)
                            
                            #----------compute insertion cost to see the best forecast request to remove for this sample
                            if fp_isfeasible(copy_route,zones_incopyroute,no_pax,copyroute_timematrix,service_dur,
                                              copyroute_timewindows,veh_capacity,max_T,no_forecastsamp_perday[day,sample_id],
                                              reqdropoff_idx,accepted_reqs,multiplier):
                                # print("Feaible route found")
                                #calculate the insertion cost as the extra travel time
                                extra_time = (tot_routedur(copy_route,copyroute_timematrix) + 2*service_dur) - \
                                (tot_routedur(vehroute,vehroute_timematrix) + 2*service_dur)
                                extra_dist = tot_routedist(copy_route,copyroute_distmatrix) - \
                                tot_routedist(vehroute,vehroute_distmatrix) 
                                # print("extra traveltime", extra_traveltime)
                                #TW_factor = 5 * (journey_option[1] - journey_option[0])
                                insertion_cost = (extra_time * driverpay)  + (extra_dist * fuelcost)
                                # print("insertion cost", insertion_cost)
                                
                                if insertion_cost < best_insertcost:
                                    best_insertcost = insertion_cost #initialise best insertion cost
                                    best_vehicleidx = idx2 #initialise best route
                                    best_forecastreq = (forecast_id, forecast_routeidx) #forecast route_idx
                                    best_posns = (pickuposn,dropoffposn)
                                    # print(best_vehicleidx, best_forecastreq)
                                
            # print("----------sample results----------")
            # print(f" journey option: {idx1}, sample id: {sample_id}, insertion cost : {best_insertcost}, best vehicle idx: {best_vehicleidx}, best posn: {best_posns}, best forecast: {best_forecastreq}")
            sample_bestinsertcost[sample_id, idx1] = best_insertcost
            sample_bestvehicleposns[sample_id, idx1] = (best_vehicleidx, best_posns)
            sample_bestcandforecast[sample_id, idx1] = best_forecastreq
               
                                
        #find the average of the best sample insertion costs for that journey option
        #TODO: what do we do if we do not find a feasible forecast journey to remove, that insertion cost is currently set to 500
        insertion_cost = sum(sample_bestinsertcost.values()) / len(sample_bestinsertcost)
        # #TODO: call potential revenue loss function to calculate that
        revenue_loss = calc_revenueloss()
        # #TODO: Calculate opportunity cost 
        opportunity_costs[idx1] = insertion_cost + revenue_loss
    return opportunity_costs, sample_bestcandforecast, sample_bestvehicleposns,request_idxs

#%% price optimization functions
def func_m(root_m,rhs): #constructing the root finding equation
    return (root_m-1) * np.exp(root_m) - rhs

def solve_m(function, guess,other_params): #solving the root finding equation
    sol = fsolve(func_m,guess,args=(other_params), full_output=1)
    while sol[2] != 1: #solution does not converge
        guess = guess + r.random() #update initial guess - try and solve again
        sol = fsolve(func_m,guess,args=(other_params), full_output=1)
    return sol[0]

def simulate_choice(b0,b_TWs,b_price,G,P): #simulating customer choice
    num = {k:np.exp(b0 + b_TWs*(v[1] - v[0])+ b_price * P[k]) 
           for k,v in G.items()} #for journey options
    denom = 1 + sum(num.values())
    num[0] = 1 #for no purchase option
    # print("num", num)
    # print("denom", denom)
    probs = {k: v/denom for k,v in num.items()} #calculate the probabilities
    # print("prob",probs)
    #select offer based on probabilities
    time_seed= (time.time() - int(time.time())) * np.random.random() * 100000000
    np.random.seed(int(time_seed))
    sel_idx = np.random.choice(np.asarray(list(probs.keys())), size = 1, replace = True, 
                               p = np.asarray(list(probs.values())).flatten())[0]  
    print("sel idx", sel_idx)
    return sel_idx

                     
#%% main function for foresight policy 1
def foresightpolicy1(arrival_info,no_cus,feasible_forecastjourneys,routes,day,accepted_requestsTD,no_sampleforecasts,allzones_traveltimes,
                    allzones_distmat,multiplier,noG_max, Delta,no_pax,service_dur,veh_capacity,max_T,driverpay,fuelcost,depotTWs,
                    beta_0,beta_TWs,beta_price,initial_guess,opt_m):
    #copy initial set of feasible forecast journeys and routes
    copy_feasibleforecastjourneys = feasible_forecastjourneys.copy()
    #get all forecast journeys for that particular day under consideration
    copy_feasibleforecastjourneys = copy_feasibleforecastjourneys[copy_feasibleforecastjourneys['day']
                          ==day].reset_index(drop=True)
    print(copy_feasibleforecastjourneys)
    feasible_routes = deepcopy(routes)
    print(feasible_routes)
    print("accepted requests till date", accepted_requestsTD)
    #get number of forecasts candidates per day and sample_id and store in a dictionary
    forecasts_sampday = feasible_forecastjourneys.groupby(['day','sample_id']).size().to_dict()
    # calculate travel time in minutes
    travel_time = allzones_traveltimes[arrival_info['o_zone'],arrival_info['d_zone']]
    # print("tt",travel_time)
    # calculate max ride time as m * travel time
    L_max = round(multiplier * travel_time,4)
    # print("max ride time", L_max)
    #Find the candidate forecast journeys to consider. Currently using all the feasible forecast journeys for that day 
    #but could consider within a certain radius and time? 
    candidateforecast_journeys = copy_feasibleforecastjourneys.copy()
    candidateforecast_journeys = candidateforecast_journeys.reset_index(drop=True)#.rename(columns={'index': 'initial_index'})
    print(candidateforecast_journeys)
    
    #Generate journey options for the request
    G_x_t = gf.gen_G_xt(arrival_info['reqpickup_time'], arrival_info['reqdropoff_time'], 
                        travel_time, noG_max, Delta, service_dur)
    # print("G_X_t", G_x_t)
    
    #Tighten TWs for the request using the generated journey options
    requestTWs = gf.gen_requestTWs(arrival_info['reqpickup_time'], arrival_info['reqdropoff_time'], 
                noG_max, Delta)
    # print("requestTWs", requestTWs)
    # Implement Opportunity cost estimation algorithm
    OC, bestcandforecast_sample, bestvehicleposns_sample, request_idxs = \
        calc_opportunitycost(arrival_info,G_x_t,requestTWs,no_sampleforecasts,candidateforecast_journeys,feasible_routes,day,
                             accepted_requestsTD,forecasts_sampday,allzones_traveltimes,allzones_distmat,
                             no_pax,service_dur,veh_capacity,max_T,multiplier,driverpay,fuelcost,depotTWs)
    # print(f"opportunity cost: {OC}")
    # print(f"best cand forecast:{bestcandforecast_sample}")
    # print(f" best vehicle and posn: {bestvehicleposns_sample}")
    #Price optimization procedure
    #compute rhs of equation for m
    rhs = sum(np.exp(beta_0 + beta_TWs*(v[1] - v[0])+ 
                     beta_price* OC[k]) 
              for k,v in G_x_t.items())
    # print("rhs", rhs)
    #set initial guess of the root of m - see if i can use  a lambda expression to do this
    m_guess = (lambda opt_m: opt_m if opt_m is not None else 
               initial_guess)(opt_m)
    #print("m_guess", m_guess)
    #solve for m
    opt_m = solve_m(func_m, m_guess,rhs)
    #find optimal prices 
    opt_prices = {k:v - (opt_m[0]/beta_price) for k,v in OC.items()}
    return opt_m, G_x_t, requestTWs, opt_prices, bestcandforecast_sample, bestvehicleposns_sample, request_idxs,\
        candidateforecast_journeys,feasible_routes
    
#%% function to remove best candidate forecasrt
def remove_selcandforecast(day,accepted_option, routes, request, bestcandforecast, allcandforecasts):
    # print("-------------checking forecast removal code -----------------")
    #get best canforecast requests for that accepted journey request
    #keys for best candforecast--> sample_idx, journey_option idx
    #values for best candforecast --> 
    #forecast_idx (starting from 0 for the first sample), (pickup and dropoff index in route)
    #index for routes --> sample_idx, day
    
    #make a copy of current candidate forecast journeys
    print(allcandforecasts)
    prev_sampidx = max(0,allcandforecasts.index[0] - 1)
    print(prev_sampidx)
    #get the best sample forecasts for the accepted option
    sample_bestcandforecasts = {key: value for key, value in bestcandforecast.items() 
                            if key[1] == accepted_option}
    print(sample_bestcandforecasts)
    # print("current routes", routes) #sample_id, day
    #loop through each of the sample forecasts:
    for k,v in sample_bestcandforecasts.items(): #sample_id, option_index
        print("key",k)    
        print("value",v)
        allcandforecasts = allcandforecasts.drop(v[0])
        print(allcandforecasts)
        
        #remove these forecasts from the routes?
        ammended_routes = [[node for node in sublist if node not in v[1]] 
                                  for sublist in routes[k[0],day]]
        # print("ammended route", ammended_routes)
        routes[k[0],day] = ammended_routes.copy()
        print(ammended_routes,routes)
    allcandforecasts = allcandforecasts.reset_index(drop=True)
    return allcandforecasts, routes       

def temp_routeupdate(day,accepted_option, current_route, route_vehposns, request_idxs):
    # print("-------------checking temporary route update code -----------------")
    print("current route",current_route)
    print("route_vehposns", route_vehposns)
    #get corresponding vehicle route positions for that accepted journey request
    sample_route_vehposns = {key: value for key, value in route_vehposns.items() 
                            if key[1] == accepted_option}
    print(sample_route_vehposns)
    for k,v in sample_route_vehposns.items(): #keys: sample_id, selected_option
        print("key", k)
        print("values", v)
        #temporary copy of route for that sample id on that day
        print("temp_route", current_route[k[0],day][v[0]])
        #insert pickup
        current_route[k[0],day][v[0]].insert(v[1][0],request_idxs[k[0]][0])
        #insert dropoff
        current_route[k[0],day][v[0]].insert(v[1][1],request_idxs[k[0]][1])
        print("ammended route", current_route)
    return current_route

def reindex_route(day,accepted_option, current_route,route_vehposns):
    print("current route",current_route)
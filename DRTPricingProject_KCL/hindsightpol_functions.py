#%% import modules
import numpy as np
from copy import deepcopy
import general_functions as gf
import time 
from scipy.optimize import fsolve
import random as r

#%% function to convert nodes in routes to the corresponding zones
def convertroute_tozones(route,no_cus,all_arrivals):
    corr_zones = deepcopy(route)
    corr_zones[-1] = 0 #change the ending depot index to 0
    for node in range(1,len(route) - 1):
        # print('node', node)
        if route[node] > no_cus: #node id indicates a drop-off
            cus_id = route[node] - no_cus
            # print('cus_id',cus_id)
            arrival_info = next((item for item in all_arrivals if item.get('cus_id')==cus_id),None)
            # print('arrival info', arrival_info)
            #get the corresponding drop-off zone
            corr_zones[node] = arrival_info.get('d_zone')
        else: #node id indicates a pickup 
            cus_id = route[node]
            # print('cus_id',cus_id)
            arrival_info = next((item for item in all_arrivals if item.get('cus_id')==cus_id),None)
            # print('arrival info', arrival_info)
            #get the corresponding origin-off zone
            corr_zones[node] = arrival_info.get('o_zone')
    return corr_zones

#%% function to compute total route duration
def tot_routedur(zones_routes,allzones_traveltimes):
    # print("veh route", veh_route)
    route_dur = 0
    # print("zones in route", zones_routes)
    for zone_idx in range(len(zones_routes) - 1):
       route_dur += allzones_traveltimes[zones_routes[zone_idx], zones_routes[zone_idx+1]]
    # print("route duration in minutes", route_duration)
    return route_dur

#function to compute total route distance in km
def tot_routedist(zones_routes,allzones_distmat):
    # print("veh route", veh_route)
    route_dist = 0
    # print("zones in route", zones_routes)
    for zone_idx in range(len(zones_routes) - 1):
       route_dist += allzones_distmat[zones_routes[zone_idx], zones_routes[zone_idx+1]]
    # print("route duration in minutes", route_duration)
    return route_dist
#%%function to get the TWs for the temporary routes
def getTWs_nodes(nodes,pickup_time,X_t,G,requestTWs,depotTWs,pickup_nodes,dropoff_nodes):
    req_ids = {i: i-len(pickup_nodes) for i in  nodes[1:-1] 
               if i in dropoff_nodes}
    # print("request ids", req_ids)
    accepted_cusid = [item['cus_id'] for item in X_t]
    # print("accepted cus", accepted_cusid)
    TWs = {}
    for i in range(len(nodes)):
        if nodes[i] ==0 or nodes[i] == dropoff_nodes[-1]+1:
            TWs[nodes[i]] = depotTWs
        else:
            if nodes[i] in pickup_nodes: #pickup node
                if nodes[i] in accepted_cusid:
                    TWs[nodes[i]] = [item['TW_o'][j] for item in X_t 
                                     for j in range(2) if item['cus_id'] == nodes[i]]
                else:
                    if pickup_time != None: #req TWs on pickup node; G_xt on dropoff node
                        TWs[nodes[i]] = [requestTWs[0], requestTWs[1]]
                    else: # req TWs on dropoff node, G_xt on pickup
                        TWs[nodes[i]] = [G[0], G[1]]
            else:
                if req_ids[nodes[i]] in accepted_cusid: #if customer request has already been accepted
                    TWs[nodes[i]] = [item['TW_d'][j] for item in X_t 
                                     for j in range(2) if item['cus_id'] == req_ids[nodes[i]]]
                else:
                    if pickup_time != None: #req TWs on pickup node; G_xt on dropoff node
                        TWs[nodes[i]] = [G[0], G[1]]
                    else: # req TWs on dropoff node, G_xt on pickup
                        TWs[nodes[i]] = [requestTWs[0], requestTWs[1]]
    return TWs

#%% function to check feasibility of the route
def isfeasible(route,zones_routes,no_pax,allzones_traveltimes,service_dur,TWs,dropoffnodes,veh_cap,
               max_routedur,multiplier):

    no_onboardpass = 0
    depot_depart = max(TWs[route[0]][0],TWs[route[1]][0] - allzones_traveltimes[zones_routes[0],zones_routes[1]])
    arrival_times = {route[0]: depot_depart}#start from the depot at deport_depart
    # print("arr times", arrival_times)
    for i in range(1,len(route)):
        # print(route[i])
        if route[i] == route[-1]:
            no_pass = 0
        elif route[i] in dropoffnodes: #handle no of passengers as negative for drop-offs
            no_pass = no_pax * -1
        else:
            no_pass = no_pax
        if no_onboardpass + no_pass <= veh_cap:
            #find the arrival time at that node, inherently captures waiting times
            arrival_time = max(arrival_times[route[i-1]] + service_dur + \
                allzones_traveltimes[zones_routes[i-1],zones_routes[i]], TWs[route[i]][0])
            # print("arrival time at node",route[i],"is", arrival_time)
            #check TWs violations
            if arrival_time > TWs[route[i]][1]:
                # print("TWs violated")
                return False
            #check passenger ride time violations
            if route[i] in dropoffnodes:
                pass_ridetime = arrival_time - (arrival_times[route[i] - len(dropoffnodes)] + service_dur)
                if pass_ridetime > multiplier * allzones_traveltimes[zones_routes[route.index(route[i]-len(dropoffnodes))],zones_routes[i]]:
                    # print("Ride time violated")
                    return False

            #update no of onboard pass and arr times
            no_onboardpass += no_pass
            # print("no of onboard passengers after node",route[i],no_onboardpass)
            arrival_times[route[i]] = arrival_time 
            # print("arrival time at node",route[i] , arrival_time)
        else: #capacity is violated
            # print("capacity violated")
            return False
    #check maximum route duration    
    # print("arr times", arrival_times)
    if arrival_times[route[-1]] - arrival_times[route[0]] > max_routedur: 
        # print("max route duration violated")
        return False
    return True
#%% function for insertion heuristics
def insertion_heur(routes,all_arrivals,no_cus,pickup_idx,dropoff_idx,pickupreq_time,journey_options,
                   reqTWs,accepted_ordersTD, nopass,servicedur,vehicle_capacity,depotTWs,P_nodes,D_nodes,
                   allzones_traveltimes,allzones_distmat,max_routedur,multiplier,fuelcost,driverpay):
    """
    First, sort journey options in descending order of flexibility. 
    Insert each journey option to the first feasible route in the best position
    Whenever an available vehicle route is checked, find feasible position with the least insertion cost 
    as the best insertion
    If there is no feasible insertion position on the vehicle being checked, other vehicles will be continuously
    checked until a feasible insertion position is found.
    However, if it is infeasible to insert the journey option with the most flexible time window (e.g., $3 * \Delta$),
    then all the other options will also be considered as infeasible.
    If all vehicles routes cannot satisfy the user's insertion, return infinity as best insertion cost,
    and set best vehicle and positions to None.
    """

    insertion_costs = {} #dictionary to store insertion cost for each journey option
    best_insertposns = {} #dictionary to store the best veh, insertion posns for the journey option
    
    #sort journey options in descending order of flexibility
    sorted_Gs = dict(sorted(journey_options.items(), key=lambda item: abs(item[1][1] - 
                          item[1][0]), reverse=True))
   
    for idx1,journey_option in sorted_Gs.items():
        # print("idx", idx1,"G", journey_option)
        best_insertcost = float('inf') #initialise best insertion cost
        best_vehicle = None #initialise best route
        best_posns = None
        #initialise insertion costs and best_insertposns dictionary
        insertion_costs[idx1] = best_insertcost
        best_insertposns[idx1] = (best_vehicle,best_posns)
        
        for idx2, route in routes.items(): #loop through each vehicle route
            # print("idx", idx2, "route", route)
            #convert nodes in routes to zones
            route_tozones = convertroute_tozones(route,no_cus,all_arrivals) 
            # print("zones in route", route_tozones)
            if len(route) == 2: #empty route
                temp_route= [route[0]] + [pickup_idx] + [dropoff_idx] + [route[-1]]
                temproute_tozones = convertroute_tozones(temp_route,no_cus,all_arrivals)
                # print("zones in temp route",temproute_tozones)
                extra_time = tot_routedur(temproute_tozones,allzones_traveltimes) + 2*servicedur #service duration at both pick-up and drop-off
                extra_dist = tot_routedist(temproute_tozones,allzones_distmat)
                #use the  extra time of travel +service time * driver pay + distance * fuel cost
                insertion_cost = (extra_time * driverpay)  + (extra_dist * fuelcost)
                # print("extra time", extra_time)
                # print("extra dist", extra_dist)
                # print("insertion_cost in £", insertion_cost)
                best_insertcost = insertion_cost
                best_vehicle = idx2
                best_posns = (1,2)
                insertion_costs[idx1] = best_insertcost
                best_insertposns[idx1] = (best_vehicle,best_posns)
                break  #continue to next journey option if we find bestposn
            else:
                # print("There are already customers in the vehicle")
                
                for pickuposn in range(1,len(route)):
                    # print("pickuposn",pickuposn)
                    pickupseq = deepcopy(route)
                    pickupseq.insert(pickuposn,pickup_idx)
                    for dropoffposn in range(pickuposn+1,len(pickupseq)):
                        # print("dropoffposn",dropoffposn)
                        temp_route = deepcopy(pickupseq)
                        temp_route.insert(dropoffposn,dropoff_idx)
                        # print("temp_route",temp_route)
                        #convert nodes in temp routes to zones
                        temproute_tozones = convertroute_tozones(temp_route,no_cus,all_arrivals)
                        # print("zones in temp route",temproute_tozones)
                        #get TWs for the nodes in this temporary routes
                        time_windows = getTWs_nodes(temp_route,pickupreq_time,accepted_ordersTD,
                                                    journey_option,reqTWs[idx1],
                                                    depotTWs,P_nodes,D_nodes)
                        # print("time windows",time_windows)
                        #check feasibility of temp route
                        if isfeasible(temp_route,temproute_tozones,nopass,allzones_traveltimes,servicedur,
                                      time_windows,D_nodes,vehicle_capacity,max_routedur,multiplier):
                            extra_time = (tot_routedur(temproute_tozones,allzones_traveltimes) + 2*servicedur) - \
                            (tot_routedur(route_tozones,allzones_traveltimes) + 2*servicedur)
                            extra_dist = tot_routedist(temproute_tozones,allzones_distmat) - \
                            tot_routedist(route_tozones,allzones_distmat) 
                            # print("extra traveltime", extra_traveltime)
                            #TW_factor = 5 * (journey_option[1] - journey_option[0])
                            insertion_cost = (extra_time * driverpay)  + (extra_dist * fuelcost)
                            # print("extra traveltime in mins", extra_traveltime)
                            # print("insertion_cost in £", insertion_cost)
                            # print("best insertcost",best_insertcost)
                            if insertion_cost < best_insertcost:
                                best_insertcost = insertion_cost
                                best_vehicle = idx2
                                best_posns = (pickuposn,dropoffposn)
                                # print("best insertcost",best_insertcost)
                                # print("best vehicle", best_vehicle)
                                # print("best_route",best_posns)
                        # print("go to next dropoffpson")
                    # print("go to next pickup")
                if best_vehicle is not None:
                    # print("best insertcost",best_insertcost)
                    # print("best vehicle", best_vehicle)
                    # print("best_route",best_posns)
                    insertion_costs[idx1] = best_insertcost
                    best_insertposns[idx1] = (best_vehicle,best_posns)
                    break  #continue to next journey option if we find bestposn 

        #if the most flexible TW is not flexible, then all other TWs are not flexible 
        #so exit this function
        if idx1 == next(iter(sorted_Gs)) and best_insertcost == float('inf'):
            #set the insertion costs and best insertposns
            insertion_costs = {k:best_insertcost for k in sorted_Gs.keys()}
            best_insertposns = {k:(best_vehicle,best_posns) for k in sorted_Gs.keys()}
            # print("insertion_costs", insertion_costs)
            # print("best_insertposns",best_insertposns) 
            return insertion_costs, best_insertposns         
    return insertion_costs, best_insertposns
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
    return sel_idx

#%% function for hindsight policy
def hindsight_policy(arrival_info,all_arrivals,no_cus,routes,pickups,dropoffs,accepted_ordersTD,no_pass,service_dur,
                     veh_cap, depotTWs,allzones_traveltimes,allzones_distmat,max_routedur,multiplier,fuelcost,driverpay,opt_m,
                     noG_max,Delta,beta_0,beta_TWs,beta_price,initial_guess):
    # print("request", arrival_info)
    #generate corr pickup idx and pickup information
    pickup_idx = arrival_info['cus_id']
    dropoff_idx = pickup_idx + no_cus
    # print("indexes", pickup_idx, dropoff_idx)
    
    # calculate travel time in minutes
    travel_time = allzones_traveltimes[arrival_info['o_zone'],arrival_info['d_zone']]
    # print("tt",travel_time)
    # calculate max ride time as m * travel time
    L_max = round(multiplier * travel_time,4)
    # print("max ride time", L_max)
    #generate journey options 
    G_x_t = gf.gen_G_xt(arrival_info['reqpickup_time'], arrival_info['reqdropoff_time'], 
                        travel_time, noG_max, Delta, service_dur)
    # print("G_X_t", G_x_t)
    
    #Tighten TWs for the request using the generated journey options
    requestTWs = gf.gen_requestTWs(arrival_info['reqpickup_time'], arrival_info['reqdropoff_time'], 
                noG_max, Delta)
    # print("requestTWs", requestTWs)

    #call insertion heuristics to calculate check feasibility the insertion cost
    insert_costs, insert_posns = insertion_heur(routes,all_arrivals,no_cus,pickup_idx,dropoff_idx,arrival_info['reqpickup_time'], 
                   G_x_t, requestTWs,accepted_ordersTD,no_pass,service_dur,veh_cap, depotTWs, pickups, 
                   dropoffs,allzones_traveltimes,allzones_distmat,max_routedur,multiplier,fuelcost,driverpay)
    

    #re-sort the options in ascending order
    C_x_t = dict(sorted(insert_costs.items()))
    pot_insertions = dict(sorted(insert_posns.items()))
    # print("insertion costs",C_x_t)
    # print("route update params",pot_insertions)
    
    #----price optimization procedure----------#
    #compute rhs of equation for m
    rhs = sum(np.exp(beta_0 + beta_TWs*(v[1] - v[0])+ 
                     beta_price* C_x_t[k]) 
              for k,v in G_x_t.items())
    # print("rhs", rhs)
    #set initial guess of the root of m - see if i can use  a lambda expression to do this
    m_guess = (lambda opt_m: opt_m if opt_m is not None else 
               initial_guess)(opt_m)
    #print("m_guess", m_guess)
    #solve for m
    opt_m = solve_m(func_m, m_guess,rhs)
    # print("root m", opt_m)
    #find optimal prices 
    opt_prices = {k:v - (opt_m[0]/beta_price) for k,v in C_x_t.items()}
    # print("opt_prices", opt_prices)

    return opt_m, G_x_t, requestTWs, opt_prices, pot_insertions


#%% GOOOGLE OR TOOLS OPTIMISATION PROCESS
#function to get unique nodes in route
def get_uniquenodes(veh_routes,no_requests):
    #get all unique pickup and dropoff nodes currently in the routes
    all_nodes =[value for values in veh_routes.values() for value in values if value != 2*no_requests+1]
    unique_nodes = sorted(list(set(all_nodes)))
    corr_index_list = list(range(len(unique_nodes)))
    corr_index_dict = {node:corr_index_list[unique_nodes.index(node)] 
                       for node in unique_nodes}
    return unique_nodes, corr_index_list, corr_index_dict  

#function to get corresponding zones for the nodes in the route
def nodes_to_zones(unique_nodes,tot_requests,all_arrivals):
    zones_inroute = {}
    for node in unique_nodes:
        if node == 0:
            zones_inroute[node] = 0
        elif node > tot_requests:
            cus_id = node - tot_requests
            arrival_info = next((item for item in all_arrivals if item.get('cus_id')==cus_id),None)
            zones_inroute[node] = arrival_info.get('d_zone')
        else:
            cus_id = node
            arrival_info = next((item for item in all_arrivals if item.get('cus_id')==cus_id),None)
            zones_inroute[node] = arrival_info.get('o_zone')
    return zones_inroute

#function to derive travel time matrix for zones in route
def get_routetimemat(unique_nodes,corr_index_keys,nodes_tozones, allzones_timemat):
    route_timemat = np.zeros((len(unique_nodes), len(unique_nodes)), dtype=int)
    for node1 in unique_nodes:
        for node2 in unique_nodes:
            route_timemat[corr_index_keys[node1]][corr_index_keys[node2]] = \
                int(round(allzones_timemat[nodes_tozones[node1], nodes_tozones[node2]]))
    return route_timemat

#function to get list of pickup and dropoff nodes in route
def get_pickups_dropoffs(dict_nodes_idx,accepted_requests,tot_requests):
    pickup_dropoffs = [[dict_nodes_idx[node],
                        dict_nodes_idx[node-1+tot_requests+1]]
                       for node in sorted(accepted_requests)]
    return pickup_dropoffs    

#function to get TWs of nodes in route
def get_TWs(accepted_requests,corr_index_keys,states,tot_requests):
    TWs = {}
    for idx, cus_id in enumerate(accepted_requests):
        pickup = states[idx]['cus_id']
        dropoff = pickup - 1 + tot_requests + 1
        TWs[corr_index_keys[pickup]] = (round(states[idx]['TW_o'][0]), 
                                        round(states[idx]['TW_o'][1]))
        TWs[corr_index_keys[dropoff]] = (round(states[idx]['TW_d'][0]), 
                                         round(states[idx]['TW_d'][1]))
    return TWs

#function to get demands for nodes in route
def get_nopass(unique_nodes, corr_index_keys, no_pass, tot_requests):
    nopax_dict = {corr_index_keys[node]: (0 if node == 0 else (-1 * no_pass if node > tot_requests + 1 else no_pass)) 
              for node in unique_nodes}
    return nopax_dict

#create corresponding google or tools index for routing
def reindex_initialroutes(routes,corr_index_keys, tot_requests):
    initial_routes = [[corr_index_keys[node] for node in route 
                       if node not in (0,2*tot_requests+1)]
                      for route in routes.values()]
    return initial_routes

def create_data_model(routes,nodes,dict_nodes_idx,zones,allzones_timemat,accepted_requests,tot_requests,states,
                      no_vehicles, no_pass, max_capacity, depotTWs):
    data = {}
    data['time_matrix'] = get_routetimemat(nodes,dict_nodes_idx,zones,allzones_timemat)
    data['pickups_dropoffs'] = get_pickups_dropoffs(dict_nodes_idx,accepted_requests,tot_requests)
    data['time_windows'] = get_TWs(accepted_requests,dict_nodes_idx,states,tot_requests)
    data['num_vehicles'] = no_vehicles
    data['depot'] = 0 
    data['end_depot'] = [2*tot_requests+1] * no_vehicles
    data["demands"] = get_nopass(nodes, dict_nodes_idx, no_pass, tot_requests)
    #do not include starting and ending depotsin the route
    data['initial_routes'] = reindex_initialroutes(routes, dict_nodes_idx,tot_requests)
    data["vehicle_capacities"] = [max_capacity] * no_vehicles
    data['depotTWs'] = depotTWs
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

def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    # print(f"Objective: {solution.ObjectiveValue()}")
    time_dimension = routing.GetDimensionOrDie("Time")
    total_time = 0
    route_load = 0
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        plan_output = f"Route for vehicle {vehicle_id}:\n"
        while not routing.IsEnd(index):
            route_load += data["demands"].get(index,0)
            plan_output += f"{manager.IndexToNode(index)} Load({route_load});"
            time_var = time_dimension.CumulVar(index)
            plan_output += (
                #f"{manager.IndexToNode(index)}"
                f" Time({solution.Min(time_var)},{solution.Max(time_var)})"
                " -> "
            )
            index = solution.Value(routing.NextVar(index))
        plan_output += f" {manager.IndexToNode(index)} Load({route_load})\n"
        time_var = time_dimension.CumulVar(index)
        plan_output += (
            #f"{manager.IndexToNode(index)}"
            f" Time({solution.Min(time_var)},{solution.Max(time_var)})\n"
        )
        plan_output += f"Time of the route: {solution.Min(time_var)}min\n"
        # print(plan_output)
        total_time += solution.Min(time_var)
    # print(f"Total time of all routes: {total_time}min")
    
def convert_routeidx(routes, corr_index_keys, tot_requests):
    # print("initial routes", routes)
    # print("corr", corr_index_keys)
    new_routeidx = [
        [(2 * tot_requests + 1 if i == len(route) - 1 
          else next(k for k, v in corr_index_keys.items() 
          if v == node)) for i, node in enumerate(route)]
        for route in routes]
    return new_routeidx    

def call_optimiser(routes,tot_requests,all_arrivals,allzones_timemat, states,
                   no_vehicles,no_pass, max_capacity, max_routeduration, depotTWs):
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    
    """Entry point of the program."""
    # Instantiate the data problem.
    nodes, list_nodes_idx, dict_nodes_idx = get_uniquenodes(routes,tot_requests)
    # print("unique nodes", nodes, len(nodes))
    # print("corr_index_list", list_nodes_idx)
    # print("corr_index_keys",dict_nodes_idx)
    zones_inroutes = nodes_to_zones(nodes,tot_requests,all_arrivals)
    # print("zones in routes", zones_inroutes)
    accepted_customers = [request['cus_id'] for request in states]
    # print(accepted_customers)
    data = create_data_model(routes,nodes,dict_nodes_idx,zones_inroutes,allzones_timemat,accepted_customers,tot_requests,
                             states, no_vehicles, no_pass, max_capacity, depotTWs)
    # print(data)
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(
        len(data['time_matrix']), data["num_vehicles"], data["depot"]
    )
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
        data['depotTWs'][1],  # maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time,
    )
    time_dimension = routing.GetDimensionOrDie(time)
    # Add time window constraints for each location except depot.
    # print("time")
    for location_idx, time_window in data["time_windows"].items():
        # print(location_idx,time_window)
        if location_idx == data["depot"]:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['depotTWs'][0], data['depotTWs'][1])

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
        pickup_index = manager.NodeToIndex(request[0])
        delivery_index = manager.NodeToIndex(request[1])
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(
            routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index)
        )
        routing.solver().Add(
            time_dimension.CumulVar(pickup_index)
            <= time_dimension.CumulVar(delivery_index)
        )
    # Close model with the custom search parameters.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(15)
    #search_parameters.log_search = True
    # When an initial solution is given for search, the model will be closed with
    # the default search parameters unless it is explicitly closed with the custom
    # search parameters.
    routing.CloseModelWithParameters(search_parameters)

    # Get initial solution from routes after closing the model.
    # print("initial routes", data["initial_routes"])
    initial_solution = routing.ReadAssignmentFromRoutes(data["initial_routes"], True)
    #solve the problem
    solution = routing.SolveFromAssignmentWithParameters(
            initial_solution, search_parameters)
    # Print solution on console.
    if solution:
        # print("Solution found with google OR TOOLS")
        # print("Solution after search:")
        soln_aftersearch = get_routes(solution, routing, manager)
        # print("soln after search",soln_aftersearch)
        print_solution(data, manager, routing, solution)
        revised_soln_aftersearch = convert_routeidx(soln_aftersearch, dict_nodes_idx, tot_requests)
        # print("revised_soln_aftersearch",revised_soln_aftersearch)
        final_routes = {i + 1: sublist for i, sublist in enumerate(revised_soln_aftersearch)}
        return final_routes
    else:
        return routes




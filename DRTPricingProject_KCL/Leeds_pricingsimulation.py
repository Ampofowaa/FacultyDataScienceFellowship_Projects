# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 13:50:28 2025

@author: k2370694
"""

#%% modules to 
import numpy as np
import pandas as pd
import random as r
from copy import deepcopy
import os
import time
import general_functions as gf
import hindsightpol_functions as hpf
import foresight1pol_functions as fp1f
#%% read leeds od matrices
# Specify the folder containing CSV files
folder_path = "./Leeds_ODmatrices"  # Replace with your folder path

# List all files in the folder
files = os.listdir(folder_path)

# Filter out only CSV files
csv_files = [file for file in files if file.endswith('.csv')]

# Dictionary to store DataFrames with the filename as key
od_matrices = {}

# Loop through each CSV file and read it into a DataFrame
for file in csv_files:
    file_path = os.path.join(folder_path, file)
    df_name = os.path.splitext(file)[0]  # Use the filename (without extension) as the key
    od_matrices[df_name] = pd.read_csv(file_path, index_col=0)

#get time period probabilities
numerators = {k: v.sum().sum() for k,v in od_matrices.items()}
probs_timeperiod = {k: v/sum(numerators.values()) for k,v in numerators.items()}

#generate probabilities for all origin zones for all time periods
allprobs_origins = gf.allperiodsprobs_origins(od_matrices)

#%% variables and parameters
#------ for simulation runs
replications = 5 #number of replications
policies = ['hindsight','foresight_1', 'foresight_2']  #, list of policies to try in simulation run 
operating_hours = 12
num_vehicles = 2
veh_cap = 8
veh_speed = 25 #km/hr
no_potbookings = 200 #over the whole booking period
booking_horizon = 1000 #time intervals
lambda_rate = no_potbookings/booking_horizon 


departafter_indicator = 0 #given pickup time
arriveby_indicator = 1 #given dropoff time

no_passengers = 1
service_duration = 3
scaler = 1.5 #max ride time multiplier
noG_max = 3 #max no of potential options
Delta = 5 #delays used to derive journey options
max_routedur = operating_hours * 60

#--depots info
depot_coords = [53.7833, -1.5489] # First Bus Hunslet Park Depot
depotTWs = [0,24*60]

#----------- for generating lat longs ----------
zone_dim = 10 #square of zone_dim x zone_dim in kim
# Assuming a reference point (e.g., center of the zone)
reference_lat = 53.801277
reference_lon = -1.548567 
degrees_per_km = 0.009009  # Convert zone size to degrees (approximate, assuming a spherical Earth)
earth_radius = 6371 #in km

#generate lat-longs for all internal zones
allzones_latlongs = gf.gen_allzoneslatlongs(depot_coords,od_matrices['am1'].index.tolist(),degrees_per_km, 
                    zone_dim, reference_lat, reference_lon)
#generate distance matrix between internal zones
allzones_distmat = gf.gen_distancematrix(allzones_latlongs,earth_radius)
#generate travel time matrix between all internal zones
allzones_traveltimes = gf.gen_traveltimes(allzones_latlongs,earth_radius,veh_speed)

#beta parameters

beta_0 = -0.567072
beta_traveltime = -0.097079 
#travel times used in Shobhit's work --> [2mins-2hours], avg: 27mins, std: 20mins
beta_TWs = -0.010071 #measured in minutes [5,10,15,30]
#price of DRT hinged on taxi cost: 2.8 + 0.85*distance(km)+0.17*duration(mins) --> [.2,.3,.4] 
#price ranges[min:1,max:24,avg:5.50,std:3.50]#total price
#£15 per hour --> national average for the value of time 
beta_price = -0.097079 

#---travel cost for insertion heuristic
fuelcost_permile = 0.17 #https://www.gov.uk/guidance/advisory-fuel-rates
fuelcost_perkm = fuelcost_permile/1.60934
driverpay_perhour = 12.50 #https://www.cfirst.org.uk/job/demand-responsive-transport-minibus-driver/
driverpay_permin = driverpay_perhour/60 

#---simulate/ forecast demands
num_weeks = 3
num_days = 3
specific_weekday = 1 #for forecasting
no_priorweeks = 3 #use the last n for forecasting
no_sampleforecasts = 3

#---gen prices for forecast journeys in foresight policy
bus_fare = 3

#----foresight policy 1 parameters
gen_forecastdata = False
#%% generating set of sample forecast orders for foresight policy 1
if 'foresight_1' in policies:
    fp1_feasforecastjourneys, fp1_initialroutes = fp1f.gen_setofforecastorders(gen_forecastdata,num_weeks, num_days, no_potbookings, probs_timeperiod, 
                                   allprobs_origins, od_matrices,departafter_indicator, allzones_latlongs, earth_radius, veh_speed,noG_max, Delta, service_duration, 
                                  allzones_traveltimes,num_vehicles, no_passengers,veh_cap,depotTWs,no_priorweeks,no_sampleforecasts,
                                  allzones_distmat,max_routedur,bus_fare,fuelcost_perkm)
#%% main function
def main():
    #---- hindsight policies----
    hp_acceptedordersTD = []
    hp_results = []
    hp_optroutes = []
    
    #foresight policies
    fp1_results = []
    fp1_acceptedordersTD = []
    
    fp1_forecastjourneys = deepcopy(fp1_feasforecastjourneys)
    fp1_startroutes = deepcopy(fp1_initialroutes)
    fp1_consideredstates = deepcopy(fp1_acceptedordersTD)
    
    for rep in range(1,replications+1):
        #generate all arrivals and request information for that replication
        all_arrivals, tot_customers = gf.leeds_arrivals(booking_horizon,lambda_rate,od_matrices, 
                     allzones_latlongs,probs_timeperiod,allprobs_origins,departafter_indicator)
        # print(all_arrivals)
        #initialise vehicle routes
        hp_vehroutes = {i:[0,2*tot_customers+1] for i in range(1,num_vehicles+1)} 
        hp_pickupnodes = list(range(1,tot_customers+ 1)) #list of pickup nodes
        hp_dropoffnodes= list(range(tot_customers+1,tot_customers*2+1)) #list of dropoff nodes
        opt_m = None #root search parameter
        initial_guess = 0.5 #for price optimization
        for policy in policies:
            for idx, arrival in enumerate(all_arrivals):
                if policy == 'hindsight':
                    hp_results.append([rep,arrival.get('t'),arrival.get('cus_id'),arrival.get('o_zone'),arrival.get('d_zone'),arrival.get('o_coords'),
                               arrival.get('d_coords'), arrival.get('req_type'), arrival.get('reqpickup_time'), arrival.get('reqdropoff_time')])
                    if arrival['cus_id'] != 'Non-arrival':
                        #Step 1: run insertion heuristic and price optimization procedureto calculate optimal prices for feasible journey options
                        opt_m, journey_options, requestTWs, opt_prices, pot_insertions = hpf.hindsight_policy(arrival,all_arrivals,tot_customers,hp_vehroutes,hp_pickupnodes,
                                         hp_dropoffnodes,hp_acceptedordersTD,no_passengers,service_duration,veh_cap,depotTWs,allzones_traveltimes,allzones_distmat,
                                         max_routedur,scaler,fuelcost_perkm,driverpay_permin,opt_m,noG_max,Delta,beta_0,beta_TWs,beta_price,initial_guess)
                        #Step 2: simulate customer choice using MNL choice model
                        selected_option = hpf.simulate_choice(beta_0,beta_TWs,beta_price,journey_options,opt_prices)
                        
                        #writing results
                        hp_results[-1].extend([*journey_options.values(),selected_option,*opt_prices.values()])
                        #Step 3: Update states with accepted order details if one of the journey options is selected 
                        if selected_option != 0: #not no purchase
                             if arrival['reqpickup_time'] != None:
                                 TWs_dropoff = journey_options[selected_option]
                                 TWs_pickup = requestTWs[selected_option] 
                             else:
                                 TWs_pickup =  journey_options[selected_option]
                                 TWs_dropoff = requestTWs[selected_option]
                             hp_acceptedordersTD.append({
                                     'r': rep,
                                     't': arrival['t'],
                                     'cus_id': arrival['cus_id'], 
                                     'o_zone': arrival['o_zone'],
                                     'd_zone': arrival['d_zone'],
                                     'TW_o': TWs_pickup,
                                     'TW_d': TWs_dropoff,
                                     'P': opt_prices[selected_option]            
                             }) 
                             # print("accepted orders TD", hp_acceptedordersTD)
                             #Step 4: temporarily update route with insertion heuristics solutions
                             # print("routes before temporary insertion", hp_vehroutes)
                             sel_veh, sel_posns = pot_insertions[selected_option]
                             # print(sel_veh, sel_posns)
                             #insert pickup
                             hp_vehroutes[sel_veh].insert(sel_posns[0],arrival['cus_id'])
                             #insert dropoff
                             hp_vehroutes[sel_veh].insert(sel_posns[1],arrival['cus_id']+tot_customers)
                             # print("routes after temporary insertion", hp_vehroutes)
                             
                             ##################################################
                             #Step 5: Run Google OR Tools Background Optimisation 
                             #state under consideration for the current replication
                             filtered_states = [state for state in hp_acceptedordersTD if state['r'] == rep]
                             # print("current state for replication",rep, "is", filtered_states)
                             #if any(len(route) > 4 for route in vehicle_routes.values()):
                             opt_vehroutes = hpf.call_optimiser(hp_vehroutes, tot_customers, all_arrivals, allzones_traveltimes,
                                             filtered_states, num_vehicles,no_passengers,veh_cap, max_routedur,depotTWs)
                             
                             #call_optimiser(routes,zones_inroute,tot_customers)
                             # print("optimised routes", opt_vehroutes)
                             #set vehicle routes to the optimised routes
                             hp_vehroutes = deepcopy(opt_vehroutes)
                             ##################################################  
                    
                elif policy == 'foresight_1':
                    fp1_results.append([rep,arrival.get('t'),arrival.get('cus_id'),arrival.get('o_zone'),arrival.get('d_zone'),arrival.get('o_coords'),
                               arrival.get('d_coords'), arrival.get('req_type'), arrival.get('reqpickup_time'), arrival.get('reqdropoff_time')])
                    if arrival['cus_id'] != 'Non-arrival':
                        #Step 1: run opportunity cost and price optimization procedure to calculate optimal prices for feasible journey options
                        opt_m, journey_options, requestTWs, opt_prices, best_forecasts, best_vehposns, request_idxs,\
                            candforecastjourneys,feasible_routes = fp1f.foresightpolicy1(arrival,tot_customers,fp1_forecastjourneys,fp1_startroutes,\
                                specific_weekday,fp1_consideredstates,no_sampleforecasts,allzones_traveltimes,allzones_distmat,scaler,noG_max, Delta,no_passengers,\
                                service_duration,veh_cap,max_routedur,driverpay_permin,fuelcost_perkm,depotTWs,beta_0,beta_TWs,beta_price,initial_guess,opt_m)
                        
                        #Step 2: simulate customer choice using MNL choice model
                        selected_option = fp1f.simulate_choice(beta_0,beta_TWs,beta_price,journey_options,opt_prices)
                        print("journey_options", journey_options)
                        #writing results
                        fp1_results[-1].extend([*journey_options.values(),int(selected_option),
                                                *[float(value) for value in opt_prices.values()]])
                        print(fp1_results)
                        #Step 3: Updates if one of the options is selected are as follows
                        if selected_option != 0:
                            #a. Remove forecast order from route and future candidate forecasts
                            print("arrival", arrival)
                            print("all feasible forecast journeys")
                            print(candforecastjourneys)
                            print("initial routes", feasible_routes)
                            print(f"best cand forecast:  {best_forecasts}, best vehicle: {best_vehposns}")
                            print("request idx", request_idxs)
                            updated_candforecasts, ammended_routes = fp1f.remove_selcandforecast(specific_weekday,selected_option, 
                            feasible_routes, arrival, best_forecasts, candforecastjourneys)
                            #updated previous candidate forecasts with updated 
                            fp1_forecastjourneys = deepcopy(updated_candforecasts)
                            print("ammended all feasible forecast journeys")
                            print(fp1_forecastjourneys)
                            #TODO: b. Temporarily update routes with vehicle and best positions from the opportunity cost calculation
                            print("routes before update", ammended_routes)
                            updated_routes = fp1f.temp_routeupdate(specific_weekday,selected_option, ammended_routes, 
                            best_vehposns,request_idxs)
                            print("routes after update", updated_routes)
                            #TODO: reindex nodes in routes for background optimization and next simulation run
                            #TODO: reqpickups and dropoffidxs for previous states
                           
                            #TODO c. Update accepted orders to date
                            #update states with accepted order details if one of the journey options is selected 
                            #state: origin,destination, TWs on pickup, TWs on dropoffs, price, pickup and drop-off index for routing
                            #set reqpickupidx and reqdropoffidx by subtracting 1 from them
                            if arrival['reqpickup_time'] != None:
                                TWs_dropoff = journey_options[selected_option]
                                TWs_pickup = requestTWs[selected_option] 
                            else:
                                TWs_pickup =  journey_options[selected_option]
                                TWs_dropoff = requestTWs[selected_option]
                            # fp1_acceptedordersTD.append({
                            #         'r': rep,
                            #         't': arrival['t'],
                            #         'cus_id': arrival['cus_id'], 
                            #         'o_zone': arrival['o_zone'],
                            #         'd_zone': arrival['d_zone'],
                            #         'TW_o': TWs_pickup,
                            #         'TW_d': TWs_dropoff,
                            #         'P': opt_prices[selected_option],
                            #         'route_reqpickupidx': reqpickup_routeidx, 
                            #         'route_reqdropoffidx': reqdropoff_routeidx
                            # }) 
                            
                            # print("accepted orders to date", fp1_acceptedordersTD)
                            
                            
                            #TODO: replace this routes after running background optimization
                            # fp1_startroutes = deepcopy(updated_routes)
                            # fp1_consideredstates =  [state for state in fp1_acceptedordersTD if state['r'] == rep]
                            # print("states for replication", rep, fp1_consideredstates)
                            
                            ##################################################
                            # #TODO: d. Run Google OR Tools Background Optimisation 
                            # #state under consideration for the current replication
                            # filtered_states = [state for state in hp_acceptedordersTD if state['r'] == rep]
                            # # print("current state for replication",rep, "is", filtered_states)
                            # #if any(len(route) > 4 for route in vehicle_routes.values()):
                            # opt_vehroutes = hpf.call_optimiser(hp_vehroutes, tot_customers, all_arrivals, allzones_traveltimes,
                            #                 filtered_states, num_vehicles,no_passengers,veh_cap, max_routedur,depotTWs)
                            
                            # #call_optimiser(routes,zones_inroute,tot_customers)
                            # # print("optimised routes", opt_vehroutes)
                            # #set vehicle routes to the optimised routes
                            # hp_vehroutes = deepcopy(opt_vehroutes)
                            ################################################## 
                    
        #present routes with pickups and dropoffs
        hpconv_routes = gf.print_routes(hp_vehroutes)
        hp_optroutes.append(hpconv_routes)
    return hp_results,hp_acceptedordersTD,hp_optroutes
 
#%% function call
if __name__ =="__main__":
    hp_results,hp_acceptedordersTD,hp_optroutes, = main()
   
    #write solutions into pandas and csv file
    colnames = ['r','t','cus_id','o_zone','d_zone', 'o_coords','d_coords','req_type','reqpickup_time','reqdropoff_time', 
               'journey_opt1','journey_opt2','journey_opt3','accepted_journey','price1','price2','price3']
    hpresults_df = pd.DataFrame(hp_results, columns=colnames)
    hpresults_df.to_csv("./results_hindsightpol/outputs.csv", index=None)
    hpacceptedreqs_df = pd.DataFrame(hp_acceptedordersTD) 
    hpacceptedreqs_df.to_csv("./results_hindsightpol/acceptedjourneys.csv", index=None)
    
    #-----------------print routes---------------------------
    print("-------------------------------------------------------------------------------------------------------------")
    print("optimised routes for hindsight policy")
    print(hp_optroutes)
    print("-------------------------------------------------------------------------------------------------------------")

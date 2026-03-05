# -*- coding: utf-8 -*-
"""
Created on Tue Jan 14 13:56:36 2025

@author: k2370694
"""

#%% modules 
import numpy as np
import random as r
import math as m
#%% function to calculate conditional probabilities for all time periods
def allperiodsprobs_origins(od_matrix):
    allprobs_origins = {}
    for k,v in od_matrix.items():
        totals = v.sum().sum()
        row_sums = v.sum(axis=1).to_dict()
        allprobs_origins[k] = {k: v/totals for k,v in row_sums.items()}
    return allprobs_origins

#function to generate zone latitudes and longitudes
def gen_latlongs(degrees_per_km, zone_dim, reference_lat, reference_lon): 
    #Generates a random pair of coordinates within a square zone in km.
    zone_size_degrees = zone_dim * degrees_per_km
    
    # Generate random offsets in latitude and longitude
    lat_offset = r.uniform(-zone_size_degrees/2, zone_size_degrees/2)
    lon_offset = r.uniform(-zone_size_degrees/2, zone_size_degrees/2)
    
    # Calculate the random coordinates
    lat = round(reference_lat + lat_offset,4)
    lon = round(reference_lon + lon_offset,4)
    return [lat, lon]

def gen_allzoneslatlongs(depot_coords, allzones,degrees_per_km, zone_dim, reference_lat, reference_lon):
    allzones_latlongs = {}
    #include depot latlongs
    allzones_latlongs[0] = depot_coords
    for zone in allzones:
        zone_coords = gen_latlongs(degrees_per_km, zone_dim, reference_lat, reference_lon)
        allzones_latlongs[zone] = zone_coords
    return allzones_latlongs

def haversine_distance(pickup_coordinates,dropoff_coordinates,earth_radius):
    """
    The Haversine distance is a formula used to calculate the shortest distance between two points on the surface of a sphere, given their longitudes 
    and latitudes. It's especially useful for calculating distances between points on Earth, which is approximately a sphere.
    The formula accounts for the curvature of the Earth, making it more accurate than using simple Euclidean distance for geographic coordinates.
    Units: km
    """
    lat_diff = m.radians(dropoff_coordinates[0]) - m.radians(pickup_coordinates[0])
    long_diff = m.radians(dropoff_coordinates[1]) - m.radians(pickup_coordinates[1])
    
    a = m.sin(lat_diff / 2)**2 + m.cos(pickup_coordinates[0]) * m.cos(dropoff_coordinates[0]) * m.sin(long_diff / 2)**2
    c = 2 * m.atan2(m.sqrt(a), m.sqrt(1 - a))
    return c * earth_radius

#function to generate distance matrix across all zones
def gen_distancematrix(latlongs,earth_radius):
    distances = {}
    for zone1 in latlongs.keys():
        for zone2 in latlongs.keys():
            if zone1 == zone2:
                distances[zone1, zone2] = 0
            else:
                distances[zone1, zone2] = haversine_distance(latlongs[zone1], latlongs[zone2], earth_radius) 
    return distances

#function to generate travel time matrix across all zones
def gen_traveltimes(latlongs,earth_radius,veh_speed):
    traveltimes = {}
    for zone1 in latlongs.keys():
        for zone2 in latlongs.keys():
            if zone1 == zone2:
                traveltimes[zone1, zone2] = 0
            else:
                traveltimes[zone1, zone2] = haversine_distance(latlongs[zone1], latlongs[zone2], earth_radius) /veh_speed * 60
    return traveltimes

#function to generate pickup or dropoff time
def gen_requesttime(time_period):
    #generated based on time periods given in Leeds dataset
    if time_period == 'am1':
        req_time =  np.random.randint(0,60)
    elif time_period == 'am2':
        req_time =  np.random.randint(60,120)
    elif time_period == 'am3':
        req_time =  np.random.randint(120,180)
    elif time_period == 'ip1':
        req_time =  np.random.randint(180,540)
    elif time_period == 'pm1':
        req_time =  np.random.randint(540,600)
    elif time_period == 'pm2':
        req_time =  np.random.randint(600,660)
    else:
        req_time =  np.random.randint(660,720)
    return req_time


def gen_request(probs_timeperiod,allprobs_origins,od_matrices,departafter_indicator,latlongs):
    #Step 1: select time of day based on probabilities
    timeperiod_q = np.random.choice(np.asarray(list(probs_timeperiod.keys())), size = 1, replace = True, 
                               p = np.asarray(list(probs_timeperiod.values())).flatten())[0]
    #Step 3: select an origin zone for the selected time period 
    probs_allorigins = allprobs_origins[timeperiod_q]
    sel_originzone = np.random.choice(np.asarray(list(probs_allorigins.keys())), size = 1, replace = True, 
                               p = np.asarray(list(probs_allorigins.values())).flatten())[0]
    #Step 4: select a destination zone for the selected origin zone
    all_destinations = od_matrices[timeperiod_q].loc[sel_originzone]
    probs_destinations = (all_destinations/all_destinations.sum()).to_dict()
    #select destination zone ensuring that it is not the same as the origin zone
    sel_destzone = sel_originzone
    while sel_destzone == sel_originzone:
        sel_destzone = int(np.random.choice(np.asarray(list(probs_destinations.keys())), size = 1, replace = True, 
                                 p = np.asarray(list(probs_destinations.values())).flatten())[0])
    #Step 5: generate request type: for now set it to depart after always
    req_type = departafter_indicator
    #Step 6: generate request time - i.e. time for pickup or dropoff
    reqpickup_time = gen_requesttime(timeperiod_q)
    reqdropoff_time = None
    #Step 7: generate latitudes and longitudes for zones
    o_coords = latlongs[sel_originzone]
    d_coords = latlongs[sel_destzone]
    req_details = [int(sel_originzone),int(sel_destzone),o_coords,d_coords,req_type,reqpickup_time,reqdropoff_time]
    return req_details
#%% function to generate arrivals and requests
def leeds_arrivals(booking_horizon, lambda_rate, od_matrices, latlongs, probs_timeperiod,
                   allprobs_origins, departafter_indicator):
    arrivals = []
    cus_id = 0 # counter to track customer ids
    arrivals_counter = 0
    non_arrivals_counter = 0
    for period in range(1,booking_horizon+1):
       if np.random.random() < lambda_rate:
           #there is an arrival
           arrivals_counter += 1
           #Step 1: Generate a unique customer id
           cus_id += 1
           #Generate request details
           req_details = gen_request(probs_timeperiod,allprobs_origins,od_matrices,
                          departafter_indicator,latlongs)
           request = {"t": period,
                    "cus_id":cus_id, 
                    "o_zone": req_details[0],
                    "d_zone": req_details[1],
                    "o_coords": req_details[2], 
                    "d_coords":req_details[3], 
                    "req_type": req_details[4],
                    "reqpickup_time": req_details[5],
                    "reqdropoff_time": req_details[6]
                    }
           arrivals.append(request)
       else:
            non_arrivals_counter += 1
            request = {"t": period,
                    "cus_id":"Non-arrival"
                    }
            arrivals.append(request)
    print("Total number of arrivals", arrivals_counter)
    print("Total number of non-arrivals", non_arrivals_counter)
    return arrivals, arrivals_counter
#%%other functions
#function to generate journey options
def gen_G_xt(pickup_reqtime,dropoff_reqtime,tt,
               nG_max,delta,service_dur):
        #case 1: cus provides their earliest pickup time, TWs gen at dropoff
        if pickup_reqtime != None:
             #earliest arr time at dropoff
             earliest_arr = pickup_reqtime + service_dur + tt
             G_x_t = {i: [round(earliest_arr), round(earliest_arr + i *
                                                     delta)] 
                    for i in range(1,nG_max+1) 
                 }
        #case 2:  cus provides their latest drop-off time, TWs gen at pickup
        else:
             #latest pickup time at the pickup
             latest_depart = dropoff_reqtime - tt - service_dur
             G_x_t = {i: [round(latest_depart - i * delta), 
                          round(latest_depart)] 
                        for i in range(1,nG_max+1) 
                    }
        
        return G_x_t

#function to generate potential request time windows
def gen_requestTWs(pickup_reqtime,dropoff_reqtime,nG_max,delta):
    #getting TWs for the request based on the generated journey options
    if pickup_reqtime != None:
        req_TWs = {i: [pickup_reqtime, pickup_reqtime + i * delta] 
                for i in range(1,nG_max+1)}
    else:
        req_TWs = {i: [dropoff_reqtime - i * delta, dropoff_reqtime] 
                   for i in range(1,nG_max+1) 
               }
   
    return req_TWs

def print_routes(routes):
    conv_routes = {}
    for veh_id, route in routes.items():
        store_routes = []
        for node in route:
            if node == 0: 
                store_routes.append("0+")
            elif node == route[-1]:
                store_routes.append("0-")
            elif node <= (route[-1] - 1)//2:
                store_routes.append(str(node)+"+")
            else:
                store_routes.append(str(node - ((route[-1]-1)//2))+"-")
        conv_routes[veh_id] = store_routes
    return conv_routes    

import os
from dotenv import load_dotenv
import openrouteservice
import numpy as np
from historic.config.settings import ENV_VARS

API_NAME = 'ORS'

OPENROUTESERVICE_TOKEN = ENV_VARS.get('OPENROUTESERVICE_TOKEN')
ors_client = openrouteservice.Client(key=OPENROUTESERVICE_TOKEN)

PROFILE_FOOT_WALKING = 'foot-walking'
PROFILE_CYCLING_REGULAR = 'cycling-regular'

PROFILES = [
    PROFILE_FOOT_WALKING,
    PROFILE_CYCLING_REGULAR
]

# matrix api works for at most 50x50 table
MAX_SRC_DST = 50

def run_matrix_api(locations, sources_idx, destinations_idx, profile):
    """get matrix of durations/distances via openrouteservice

    Args:
        locations (list): (a single location, or a list of locations, where a location is a list or tuple of lng,lat values)
        sources_idx (list): A list of indices that refer to the list of locations (starting with 0). 
        destinations_idx (list): A list of indices that refer to the list of locations (starting with 0). 
        profile (str): Specifies the mode of transport to use when calculating directions. 
            One of [“driving-car”, “driving-hgv”, “foot-walking”, “foot-hiking”, “cycling-regular”, 
            “cycling-road”, “cycling-safe”, “cycling-mountain”, “cycling-tour”, “cycling-electric”,]
    """
    
    # Specifies a list of returned metrics. One or more of [“distance”, “duration”].
    metrics = ['distance', 'duration']

    # Specifies whether given locations are resolved or not. If set ‘true’, 
    # every element in destinations and sources will contain the name element that 
    # identifies the name of the closest street.
    resolve_locations = False

    # Specifies the unit system to use when displaying results. 
    # One of [“m”, “km”, “mi”].
    units = 'm'

    # Specifies whether Dijkstra algorithm (‘false’) or any available technique to speed up 
    # shortest-path routing (‘true’) is used. For normal Dijkstra the number of visited nodes 
    # is limited to 100000. 
    optimized = False # todo: understand this better
    
    # Specifies whether parameters should be validated before sending the request
    validata = True

    # Print URL and parameters without sending the request.
    dry_run = False

    json_data  = openrouteservice.distance_matrix.distance_matrix(
        ors_client, 
        locations, 
        profile=profile, 
        sources=sources_idx, 
        destinations=destinations_idx, 
        metrics=metrics, 
        resolve_locations=resolve_locations, 
        units=units, 
        optimized=optimized, 
        validate=validata, 
        dry_run=dry_run
    )

    return json_data    

def build_matrices(locations, profile):
    """To build duration and direction matrices for arbitrarily big tables

    Args:
        locations (list of list): [long,lat]
        profile ([type]): foot/cycling

    Returns:
        tuple: durations_matrix, distances_matrix
    """
    num_points = len(locations)

    distances_matrix = np.zeros((num_points,num_points))
    durations_matrix = np.zeros((num_points,num_points))    

    print(f'Building matrix for {profile}')

    for src_start in range(0, num_points, MAX_SRC_DST):
        for dst_start in range(0, num_points, MAX_SRC_DST):
            src_stop = min(src_start + MAX_SRC_DST, num_points)
            dst_stop = min(dst_start + MAX_SRC_DST, num_points)
            sources_idx = list(range(src_start, src_stop))
            destinations_idx = list(range(dst_start, dst_stop))

            json_data = run_matrix_api (
                locations = locations,
                sources_idx=sources_idx,
                destinations_idx=destinations_idx,
                profile=profile
            )

            distances_sub_matrix = np.array(json_data['distances'])
            durations_sub_matrix = np.array(json_data['durations'])
            distances_matrix[src_start:src_stop, dst_start:dst_stop] = distances_sub_matrix
            durations_matrix[src_start:src_stop, dst_start:dst_stop] = durations_sub_matrix            

    return distances_matrix.tolist(), durations_matrix.tolist()

def run_directions_api(coordinates, profile, format='json'):
    """[summary]

    Args:
        coordinates (list of pairs): The coordinates tuple the route should be calculated from. In order of visit.
        profile (str): One of [“driving-car”, “driving-hgv”, “foot-walking”, “foot-hiking”, “cycling-regular”, 
            “cycling-road”, “cycling-safe”, “cycling-mountain”, “cycling-tour”, “cycling-electric”,]
        format (str):" Specifies the response format. One of [‘json’, ‘geojson’, ‘gpx’]
            gpx has a bug: https://github.com/GIScience/openrouteservice-py/issues/43
    
    Returs: json_data from openrouteservice.directions.directions
        if format is json the relevant info is in
        json_data["routes"]["geometry"]: string with encoded polyline
    """

    result = openrouteservice.directions.directions(
        client=ors_client, 
        coordinates=coordinates, 
        profile=profile, 
        format_out=None, 
        format=format, 
        preference=None, 
        units=None, 
        language=None, 
        geometry=None, 
        geometry_simplify=None, 
        instructions=None, 
        instructions_format=None, 
        alternative_routes=None, 
        roundabout_exits=None, 
        attributes=None, 
        maneuvers=None, 
        radiuses=None, 
        bearings=None, 
        skip_segments=None, 
        continue_straight=None, 
        elevation=None, 
        extra_info=None, 
        suppress_warnings=None, 
        optimized=None, 
        optimize_waypoints=None, 
        options=None, 
        validate=True, 
        dry_run=None
    )    
    return result

def get_direction_polyline(coordinates, profile):
    try:
        json_data = run_directions_api(coordinates, profile, format='json')
        poly_entry = json_data["routes"][0]["geometry"]
        return poly_entry
    except openrouteservice.exceptions.ApiError:
        print('Reached daily quota')                     
        return None

def test_directions():    
    import json
    from historic.hunt_route import render_map
    coordinates = [
        [11.1022361, 46.060613], 
        [11.1188586, 46.0627946] 
    ]
    json_data = run_directions_api(coordinates, profile = 'cycling-regular', format='json')
    with open('data/test_directions.json', 'w') as f:
        json.dump(json_data, f, indent=3, ensure_ascii=False)
    render_map.render_map_from_ors_json(json_data)

if __name__ == "__main__":
    test_directions()
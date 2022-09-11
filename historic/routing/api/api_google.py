# see doc https://googlemaps.github.io/google-maps-services-python/docs/index.html
# github https://github.com/googlemaps/google-maps-services-python

import os
import googlemaps
import numpy as np
import polyline
from historic.config.settings import ENV_VARS


API_NAME = 'GOOGLE'

gmaps = googlemaps.Client(key=ENV_VARS.get('GOOGLE_API_KEY'))

PROFILE_FOOT_WALKING = 'walking'
PROFILE_CYCLING_REGULAR = 'bicycling'

PROFILES = [
    PROFILE_FOOT_WALKING, 
    PROFILE_CYCLING_REGULAR
]

# matrix api works for at most 25x25 table
# Maximum of 25 origins or 25 destinations per request.
# Maximum 100 elements per request (origins x destinations)
# see https://developers.google.com/maps/documentation/distance-matrix/usage-and-billing
MAX_SRC_DST = 10
MAX_SINGLE_ROW = 25

def get_direction_polyline(origin, destination, mode='walking', debug=False):
    """[summary]

    Args:
        origin (tuple):  latitude/longitud tuple
        destination (tuple):  latitude/longitud tuple
        mode (str, optional): driving, walking, bicycling or transit

    Returns:
        [type]: [description]
    """
    directions_result = gmaps.directions(
        origin=origin,
        destination=destination,
        mode=mode,
        units='metric'
    )
    result = directions_result[0]
    polyline = result['overview_polyline']['points']
    legs = result['legs']
    if debug:
        total_distance = sum(l['distance']['value'] for l in legs)
        total_duration = sum(l['duration']['value'] for l in legs)
        print('total_distance', total_distance)
        print('total_duration', total_duration)
    return polyline

def build_distance_matrix_simple(origins, destinations, mode='walking'):
        
    matrix_result = gmaps.distance_matrix(
        origins=origins,
        destinations=destinations,
        mode=mode,
        units='metric'
    )

    # Results are returned in rows, each row containing one origin paired with each destination.
    rows = matrix_result['rows']

    num_rows = len(origins)
    num_cols = len(destinations)
    distance_mtx = np.zeros((num_rows, num_cols))
    duration_mtx = np.zeros((num_rows, num_cols))

    for r in range(num_rows):
        row_elements = rows[r]['elements']
        for c in range(num_cols):
            rc_cell = row_elements[c]
            distance_mtx[r,c] = rc_cell['distance']['value']
            duration_mtx[r,c] = rc_cell['duration']['value']
        
    return distance_mtx.tolist(), duration_mtx.tolist()

def build_distance_matrices(locations, mode='walking'):

    num_points = len(locations)

    distances_matrix = np.zeros((num_points,num_points))
    durations_matrix = np.zeros((num_points,num_points))    

    print(f'Building dst matrix for {mode}')

    for src_start in range(0, num_points, MAX_SRC_DST):
        for dst_start in range(0, num_points, MAX_SRC_DST):
            src_stop = min(src_start + MAX_SRC_DST, num_points)
            dst_stop = min(dst_start + MAX_SRC_DST, num_points)
            origins = locations[src_start:src_stop]
            destinations = locations[dst_start:dst_stop]

            distances_sub_matrix, durations_sub_matrix = \
                build_distance_matrix_simple(origins, destinations, mode)
        
            distances_matrix[src_start:src_stop, dst_start:dst_stop] = distances_sub_matrix
            durations_matrix[src_start:src_stop, dst_start:dst_stop] = durations_sub_matrix            

    return distances_matrix.tolist(), durations_matrix.tolist()

def build_distance_row(locations, source_idx, destinations_idx, mode='walking'):

    origin = locations[source_idx]
    destinations = [locations[i] for i in destinations_idx]

    num_points = len(destinations)

    distances_row = np.zeros(num_points)
    durations_row = np.zeros(num_points)   

    for dst_start in range(0, num_points, MAX_SINGLE_ROW):
        dst_stop = min(dst_start + MAX_SINGLE_ROW, num_points)
        sub_destinations = destinations[dst_start:dst_stop]

        distances_sub_row, durations_sub_row = \
            build_distance_matrix_simple([origin], sub_destinations, mode)
            # single row (2-dim matrix)
        
        distances_row[dst_start:dst_stop] = distances_sub_row[0]
        durations_row[dst_start:dst_stop] = durations_sub_row[0]         
    
    return distances_row.tolist(), durations_row.tolist()

def snap_to_roads(path):
    result = gmaps.snap_to_roads(path)
    new_coord = [[d['location']['latitude'],d['location']['longitude']] for d in result]
    new_poly = polyline.encode(new_coord, geojson=False)
    return new_poly

def test_polyline():
    porteghet = (46.071298, 11.124574)
    poste = (46.06683, 11.124260)
    polyline = get_direction_polyline(porteghet, poste, debug=True)
    print('polyline', polyline)

def test_distance_matrix():
    porteghet = (46.071298, 11.124574)
    poste = (46.06683, 11.124260)
    distance_mtx, duration_mtx = build_distance_matrix_simple([porteghet], [poste])
    print('distance_mtx', distance_mtx)
    print('duration_mtx', duration_mtx)

def test_snap_to_roads():
    polyline_path = "o`exGmiybAsB`AQmAUgAMoAAc@Ju@b@iAj@}@HAHGDKA[FeA|@wFDBNGDG@MEUCECCSg@y@aBCQA]NeAR_A@o@cAyFAs@D[`@AZBC[IsAYoGm@oCCI}@eD_AeCWg@gAgAfAm@`@KN["
    latlong_list = polyline.decode(polyline_path, geojson=False) # lat,lon
    coord_path = '|'.join([f'{lat},{long}' for lat,long in latlong_list])
    snap_to_roads(coord_path)

if __name__ == "__main__":
    # test_polyline()
    # test_distance_matrix()
    test_snap_to_roads()
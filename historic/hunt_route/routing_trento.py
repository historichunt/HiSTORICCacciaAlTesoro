import os
from re import A
import pandas as pd
from historic.hunt_route.data_matrices import DataMatrices
from historic.hunt_route import api_ors
from historic.hunt_route import api_google
from historic.hunt_route.render_map import render_map_with_coordinates
from historic.hunt_route.routing import RoutePlanner
from historic.hunt_route import hunt_params
from historic.config.settings import ENV_VARS

def read_data_from_spreadsheet(max_points=None):
    trento_key = ENV_VARS.get('TRENTO_SPREADSHEET_KEY')
    trento_gid = ENV_VARS.get('TRENTO_SPREADSHEET_GID')
    url = f'https://docs.google.com/spreadsheets/d/{trento_key}/export?gid={trento_gid}&format=csv'
    df = pd.read_csv(url)
    
    # each row becomes a dictionary where key is column name and value is the data in the cell
    records = df.to_dict('records') 
    if max_points is not None:
        records = records[:max_points]
    name_coordinates = {
        r['storia']: [r['long'],r['lat']]
        for r in records
        if not any(pd.isnull(r[c]) for c in ['storia','lat','long'])
    }
    return name_coordinates

def build_trento_dm(api, max_points=None):    
    coordinates = read_data_from_spreadsheet(max_points)
    return DataMatrices(
        dataset_name = 'Trento',
        points_name_coordinate = coordinates,
        api = api
    )        

def get_trento_dm(api):
    return DataMatrices(
        dataset_name = 'Trento',
        api = api
    )        

def get_routes(api, profile, plot_dm_stats=False):
    
    trento_dm = get_trento_dm(api)
    metric = hunt_params.METRIC_DURATION

    if plot_dm_stats:
        trento_dm.plot(profile, metric)

    route_planner = RoutePlanner(
        dm = trento_dm,
        profile = profile,
        metric = metric,
        start_num = 1, # fontana netturno
        min_dst = 60, # 2 min
        max_dst = 600, # 10 min
        goal_tot_dst = 3600, # 1 h
        tot_dst_tolerance = 600, # ± 10 min
        min_route_size = None,
        max_route_size = None,
        check_convexity = False,
        overlapping_criteria = 'GRID',
        max_overalapping = 20, # 300, # in meters/grids, None to ignore this constraint
        stop_duration = 300, # da cambiare in 300 per 5 min
        num_attempts = 1000, # set to None for exaustive search
        random_seed = None, # only relevan if num_attempts is not None (non exhaustive serach)
        exclude_neighbor_dst = 60,    
        circular_route = True,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = None
    )

    route_planner.get_routes_and_plots(
        show_map=True,
        log=True
    )      

    trento_dm.save_data()

def test_trento_map():
    import numpy as np
    names_longlat = read_data_from_spreadsheet()
    coordinates = np.array(list(names_longlat.values()))
    render_map_with_coordinates(coordinates)

if __name__ == "__main__":
    # build_trento_dm(api=api_google)
    # build_trento_dm(api=api_ors)
    # test_trento_map()
    # dm = get_trento_dm(api=api_google)
    # dm = get_trento_dm(api=api_ors)

    get_routes(api=api_ors, profile = api_ors.PROFILE_FOOT_WALKING)
    # get_routes(api=api_ors, profile = api_ors.PROFILE_CYCLING_REGULAR)
    # get_routes(api=api_google, profile = api_google.PROFILE_FOOT_WALKING)
    # get_routes(api=api_google, profile = api_google.PROFILE_CYCLING_REGULAR)
    
    
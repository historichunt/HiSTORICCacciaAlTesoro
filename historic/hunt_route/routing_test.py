from historic.hunt_route import api_google
from historic.hunt_route.routing import RoutePlanner
from historic.hunt_route import routing

def get_routes(api, profile, plot_dm_stats=False):
    
    from historic.hunt_route.data_matrices import DataMatrices
    
    trento_dm = DataMatrices(
        dataset_name = 'apph7gGu4AAOgcbdA',
        api = api
    )  

    metric = routing.METRIC_DURATION

    if plot_dm_stats:
        trento_dm.plot(profile, metric)

    profile = api_google.PROFILE_CYCLING_REGULAR

    start_idx = 9

    duration_min = 60
    duration_sec = duration_min * 60

    route_planner = RoutePlanner(
        dm = trento_dm,
        profile = profile,
        metric = metric,
        start_idx = start_idx, 
        min_dst = 60, # 1 min
        max_dst = 600, # 10 min
        goal_tot_dst = duration_sec,
        tot_dst_tolerance = 600, # ± 10 min
        min_route_size = None,
        max_route_size = None,
        skip_points_idx = [39],
        check_convexity = False,
        overlapping_criteria = 'GRID',
        max_overalapping = 20, # 300, # in meters/grids, None to ignore this constraint
        stop_duration = 300, # da cambiare in 300 per 5 min
        num_attempts = 1000000, # set to None for exaustive search
        random_seed = 1, # only relevan if num_attempts is not None (non exhaustive serach)
        exclude_neighbor_dst = 60,    
        circular_route = False,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = None,
        show_progress_bar = True
    )

    route_planner.build_routes()

    route_planner.get_routes(
        show_map=True,
        log=True
    )

if __name__ == "__main__":
    # get_routes(api=api_ors, profile = api_ors.PROFILE_FOOT_WALKING)
    # get_routes(api=api_ors, profile = api_ors.PROFILE_CYCLING_REGULAR)
    get_routes(api=api_google, profile = api_google.PROFILE_FOOT_WALKING)
    # get_routes(api=api_google, profile = api_google.PROFILE_CYCLING_REGULAR)
    
    

from tqdm import tqdm
from historic.hunt_route import api_google
from historic.hunt_route.routing import RoutePlanner
from historic.hunt_route import routing
from historic.hunt_route.data_matrices import DataMatrices
from historic.hunt_route.trento_open_params import fine_tuning_trento_open
from collections import Counter

def get_route_planner(datamatrix, profile, metric, start_idx, duration_sec, tot_dst_tolerance,
    max_grid_overalapping, circular_route, show_progress_bar):

    return RoutePlanner(
        dm = datamatrix,
        profile = profile,
        metric = metric,
        start_idx = start_idx, 
        min_dst = 60, # 1 min
        max_dst = 720, # 12 min
        goal_tot_dst = duration_sec,
        tot_dst_tolerance = tot_dst_tolerance, # ± 10 min
        min_route_size = None,
        max_route_size = None,
        skip_points_idx = [],
        check_convexity = False,
        overlapping_criteria = 'GRID', 
        max_overalapping = max_grid_overalapping, # 20, # in meters/grids, None to ignore this constraint
        stop_duration = 300, # 5 min
        num_attempts = 10000, # set to None for exaustive search
        random_seed = 1, # only relevan if num_attempts is not None (non exhaustive serach)
        exclude_neighbor_dst = 60,    
        circular_route = circular_route,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = 1,
        show_progress_bar = show_progress_bar
    )

def test_single_route():

    api = api_google
    metric = routing.METRIC_DURATION
    # profile = api_google.PROFILE_FOOT_WALKING
    profile = api_google.PROFILE_CYCLING_REGULAR    
    start_idx = 24
    duration_min = 30
    circular_route = True
    plot_dm_stats = False
    
    trento_dm = DataMatrices(
        dataset_name = 'apph7gGu4AAOgcbdA',
        api = api
    )  

    if plot_dm_stats:
        trento_dm.plot(profile, metric)    

    duration_sec = duration_min * 60

    route_planner = get_route_planner(
        trento_dm, profile, metric, start_idx, duration_sec, 
        tot_dst_tolerance=10*60,
        max_grid_overalapping=100,
        circular_route=circular_route, 
        show_progress_bar=True)

    route_planner.build_routes()

    route_planner.get_routes(
        show_map=True,
        log=True
    )

    if len(route_planner.solutions) == 0:
        print(f'Missing route for start_idx {start_idx}')
        route_planner.get_routes(
            show_map=False,
            log=True
        )            

def test_multi_routes():

    api = api_google
    metric = routing.METRIC_DURATION
    max_attempts = 10

    trento_dm = DataMatrices(
        dataset_name = 'apph7gGu4AAOgcbdA', # trento open
        api = api
    )  

    for profile in [api_google.PROFILE_FOOT_WALKING, api_google.PROFILE_CYCLING_REGULAR]:        

        for duration_min in [45, 60, 90, 120]:

            duration_sec = duration_min * 60

            for circular_route in [False]: #                 

                print(f'Using profile {profile}, duration {duration_min}, circular {circular_route}')

                # max_grid_overalapping, duration_tolerance_min = \
                #     fine_tuning_trento_open(profile, circular_route, duration_min)

                # print('max_grid_overalapping', max_grid_overalapping)
                # print('duration_tolerance_min', duration_tolerance_min)

                # route_errors_idx = []                
                solution_counter = Counter()

                for start_idx in tqdm(range(trento_dm.num_points)):

                    max_grid_overalapping = 20
                    duration_tolerance_min = 10                    
                    found_solution = False                    
                    
                    for attempt in range(1,max_attempts+1):

                        duration_tolerance_sec = duration_tolerance_min * 60

                        route_planner = get_route_planner(
                            trento_dm, profile, metric, start_idx, duration_sec, 
                            tot_dst_tolerance=duration_tolerance_sec,
                            max_grid_overalapping=max_grid_overalapping,
                            circular_route=circular_route, 
                            show_progress_bar=False)

                        route_planner.build_routes()

                        if len(route_planner.solutions) > 0:
                            found_solution = True
                            solution_counter[attempt]+=1
                            break
                        
                        max_grid_overalapping += 20
                        duration_tolerance_min += 10

                        # if len(route_planner.solutions) == 0:
                        

                    if not found_solution:
                        # route_errors_idx.append(start_idx)
                        print(f'Missing route for start_idx {start_idx}')
                        # route_planner.get_routes(
                        #     show_map=False,
                        #     log=True
                        # )            
                        return

                    # if route_errors_idx:
                    #     print('route_errors_idx', route_errors_idx)

                print(sorted(solution_counter.items(), key=lambda x: x[0]))

if __name__ == "__main__":
    # test_single_route()
    test_multi_routes()
    
    

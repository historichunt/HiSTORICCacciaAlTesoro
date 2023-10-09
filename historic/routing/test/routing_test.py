from tqdm import tqdm
from historic.routing.api import api_google
from historic.routing.route_planner import RoutePlanner
from historic.routing.data_matrices import DataMatrices
# from historic.hunt_route.trento_open_params import fine_tuning_trento_open
from collections import Counter
from historic.routing.metrics import METRIC_DISTANCE, METRIC_DURATION, METRICS
from historic.routing.datasets.trento_hunt_params import TRENTO_BASE_KEY

def get_route_planner(datamatrix, profile, metric, start_idx, duration_sec, tot_dst_tolerance,
    max_grid_overalapping, exclude_neighbor_dst, circular_route, show_progress_bar):

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
        exclude_neighbor_dst = exclude_neighbor_dst,    
        circular_route = circular_route,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = None, # for debugging purpose
        show_progress_bar = show_progress_bar
    )

def test_single_route():

    api = api_google
    metric = METRIC_DURATION
    profile = api_google.PROFILE_FOOT_WALKING
    # profile = api_google.PROFILE_CYCLING_REGULAR    

    start_point_name = 'CRISTO RE La SLOI'    
    duration_min = 45
    exclude_neighbor_dst = 60
    circular_route = False
    plot_dm_stats = False
    
    trento_dm = DataMatrices(
        dataset_name = TRENTO_BASE_KEY,
        api = api
    )  
    
    start_idx = trento_dm.get_stop_name_index(start_point_name)

    if start_idx == None:
        print(f'Start point ({start_point_name}) not found' )
        return
        
    print(f'Start: {{start_point_name}}, idx:{start_idx}')

    if plot_dm_stats:
        trento_dm.plot(profile, metric)    

    duration_sec = duration_min * 60

    route_planner = get_route_planner(
        trento_dm, profile, metric, start_idx, duration_sec, 
        tot_dst_tolerance=10*60,
        max_grid_overalapping=20,        
        exclude_neighbor_dst=exclude_neighbor_dst,
        circular_route=circular_route,         
        show_progress_bar=True
    )

    route_planner.build_routes()

    route_planner.get_routes(
        show_map=True,
        log=True
    )


def test_multi_routes():

    api = api_google
    metric = METRIC_DURATION
    max_attempts = 10

    trento_dm = DataMatrices(
        dataset_name = TRENTO_BASE_KEY,
        api = api
    )  

    for profile in [api_google.PROFILE_FOOT_WALKING, api_google.PROFILE_CYCLING_REGULAR]:        

        for duration_min in [45, 60, 90, 120]:

            duration_sec = duration_min * 60

            for circular_route in [False]: #                 

                print(f'\nUsing profile {profile}, duration {duration_min}, circular {circular_route}')

                # max_grid_overalapping, duration_tolerance_min = \
                #     fine_tuning_trento_open(profile, circular_route, duration_min)

                # print('max_grid_overalapping', max_grid_overalapping)
                # print('duration_tolerance_min', duration_tolerance_min)

                solution_counter = Counter() # attempt -> counter
                missing_route_start = []

                for start_idx in tqdm(range(trento_dm.num_points)):

                    max_grid_overalapping = 20
                    duration_tolerance_min = 10                    
                    found_solution = False          
                    start_point_name = trento_dm.point_names[start_idx]          
                    
                    for attempt in range(1,max_attempts+1):

                        duration_tolerance_sec = duration_tolerance_min * 60

                        route_planner = get_route_planner(
                            trento_dm, profile, metric, start_idx, duration_sec, 
                            tot_dst_tolerance=duration_tolerance_sec,
                            max_grid_overalapping=max_grid_overalapping,
                            exclude_neighbor_dst=None,
                            circular_route=circular_route, 
                            show_progress_bar=False)

                        route_planner.build_routes()

                        if len(route_planner.solutions) > 0:
                            found_solution = True
                            solution_counter[attempt]+=1
                            break
                        
                        # max_grid_overalapping += 20
                        # duration_tolerance_min += 10                        

                    if not found_solution:
                        missing_route_start.append(start_point_name)                        


                if missing_route_start:
                    for spn in missing_route_start:
                        print(f'Missing route for start: {spn}')                          
                else:
                    print('No missing routes!')   
                
                print("Attempts, count:", sorted(solution_counter.items(), key=lambda x: x[0]))


if __name__ == "__main__":
    # test_single_route()
    test_multi_routes()
    
    

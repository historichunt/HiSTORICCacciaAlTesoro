from tqdm import tqdm
from historic.routing.api import api_google
from historic.routing.route_planner import RoutePlanner
from historic.routing.data_matrices import DataMatrices
from collections import Counter
from historic.routing.metrics import METRIC_DURATION
from historic.routing.datasets.trento_hunt_params import TRENTO_BASE_KEY
from historic.routing.datasets.trento_hunt_params import get_trento_route_planner, NUM_PLANNER_ATTEMPTS

# def get_route_planner(datamatrix, profile, metric, start_idx, duration_sec, tot_dst_tolerance,
#     max_grid_overalapping, exclude_neighbor_dst, circular_route, show_progress_bar):

#     return RoutePlanner(
#         dm = datamatrix,
#         profile = profile,
#         metric = metric,
#         start_idx = start_idx, 
#         min_dst = 0, # 1 min
#         max_dst = 900, # 35 min
#         goal_tot_dst = duration_sec,
#         tot_dst_tolerance = tot_dst_tolerance, # ± 10 min
#         min_route_size = None,
#         max_route_size = None,
#         skip_points_idx = [],
#         check_convexity = False,
#         overlapping_criteria = 'GRID', 
#         max_overalapping = max_grid_overalapping, # 20, # in meters/grids, None to ignore this constraint
#         stop_duration = 300, # 5 min
#         num_attempts = 10000, # set to None for exaustive search
#         random_seed = 1, # only relevan if num_attempts is not None (non exhaustive serach)
#         exclude_neighbor_dst = exclude_neighbor_dst,    
#         circular_route = circular_route,
#         num_best = 1,
#         stop_when_num_best_reached = True,
#         num_discarded = None, # for debugging purpose
#         show_progress_bar = show_progress_bar
#     )

def test_single_route(random_seed):

    planner_attempt = 2

    api = api_google
    metric = METRIC_DURATION
    # profile = api_google.PROFILE_FOOT_WALKING
    profile = api_google.PROFILE_CYCLING_REGULAR    

    start_point_name = 'Biblioteca pubblica comunale di Trento'    
    duration_min = 120
    circular_route = False
    
    plot_dm_stats = False
    
    trento_dm = DataMatrices(
        dataset_name = TRENTO_BASE_KEY,
        api = api
    )  
    
    start_idx = trento_dm.get_stop_name_index(start_point_name)
    skip_points_idx = []

    if start_idx == None:
        print(f'Start point ({start_point_name}) not found' )
        return
        
    print(f'Start: {{start_point_name}}, idx:{start_idx}')

    if plot_dm_stats:
        trento_dm.plot(profile, metric)    

    route_planner = get_trento_route_planner(
        trento_dm, profile, start_idx, duration_min, skip_points_idx, circular_route,
        planner_attempt,
        random_seed=random_seed
    )

    route_planner.build_routes()

    best_route_idx, best_stop_names, info, best_route_img, duration_min = route_planner.get_routes(
        show_map=False,
        log=True
    )
    
    if best_route_idx:
        print(f'{best_route_idx}: {len(best_route_idx)}')
        print(f'{set(best_route_idx)}: {len(set(best_route_idx))}')
        if(len(best_route_idx)!=len(set(best_route_idx))):
            return False    
    else:
        print('No solutions?')
        return True
    
    return True


def test_multi_routes():

    api = api_google
    skip_points_idx = []

    trento_dm = DataMatrices(
        dataset_name = TRENTO_BASE_KEY,
        api = api
    )  

    for profile in [api_google.PROFILE_FOOT_WALKING, api_google.PROFILE_CYCLING_REGULAR]:        

        for duration_min in [45, 60, 90, 120]:

            for circular_route in [False]: #                 

                print(f'\nUsing profile {profile}, duration {duration_min}, circular {circular_route}')

                solution_counter = Counter() # attempt -> counter
                missing_route_start = []

                for start_idx in tqdm(range(trento_dm.num_points)):

                    found_solution = False          
                    start_point_name = trento_dm.point_names[start_idx]          
                    
                    for planner_attempt in range(NUM_PLANNER_ATTEMPTS):

                        route_planner = get_trento_route_planner(
                            trento_dm, profile, start_idx, duration_min, skip_points_idx, circular_route,
                            planner_attempt
                        )

                        route_planner.build_routes()

                        if len(route_planner.solutions) > 0:
                            found_solution = True
                            solution_counter[planner_attempt]+=1
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
    seed_no_solution = 3
    seed_duplicate_mission = 15
    
    print(test_single_route(seed_no_solution))
    # test_multi_routes()
    
    

from historic.routing.route_planner import RoutePlanner
from historic.routing.metrics import METRIC_DURATION

TRENTO_BASE_KEY = 'apph7gGu4AAOgcbdA'

DURATION_TOLERANCE_MIN_ATTEMPTS = [10,15,20,30]
MIN_DST_SEC_ATTEMPTS = [60, 30, 5, 5]
MAX_DST_MIN_ATTEMPTS = [12, 20, 25, 35]
EXCLUDE_NEIGHBOR_DST_SEC_ATTEMPTS = [60, 30, 5,5]
MAX_GRID_OVERALAPPING_ATTEMPTS = [20,30,40,60]

NUM_PLANNER_ATTEMPTS = len(DURATION_TOLERANCE_MIN_ATTEMPTS)

def get_trento_route_planner(game_dm, profile, start_idx, duration_min, skip_points_idx, circular_route, attempt, random_seed=None):

    assert attempt < NUM_PLANNER_ATTEMPTS # 0, 1, 2
    
    duration_tolerance_sec = DURATION_TOLERANCE_MIN_ATTEMPTS[attempt] * 60
    min_dst = MIN_DST_SEC_ATTEMPTS[attempt]
    max_dst = MAX_DST_MIN_ATTEMPTS[attempt] * 60
    tot_duration_sec = duration_min * 60    
    max_grid_overalapping = MAX_GRID_OVERALAPPING_ATTEMPTS[attempt]
    exclude_neighbor_dst = EXCLUDE_NEIGHBOR_DST_SEC_ATTEMPTS[attempt]
    
    
    route_planner = RoutePlanner(
        dm = game_dm,
        profile = profile,
        metric = METRIC_DURATION,
        start_idx = start_idx, 
        min_dst = min_dst, 
        max_dst = max_dst, 
        goal_tot_dst = tot_duration_sec,
        tot_dst_tolerance = duration_tolerance_sec,
        min_route_size = None,
        max_route_size = None,
        skip_points_idx = skip_points_idx,
        check_convexity = False,
        overlapping_criteria = 'GRID',
        max_overalapping = max_grid_overalapping, # in grids, None to ignore this constraint
        stop_duration = 300, # da cambiare in 300 per 5 min
        num_attempts = 10000, # set to None for exaustive search
        random_seed = random_seed, # only relevan if num_attempts is not None (non exhaustive serach)
        exclude_neighbor_dst = exclude_neighbor_dst, # exclude neighbour stop within 1 min    
        circular_route = circular_route,
        num_best = 1,
        stop_when_num_best_reached = True,
        num_discarded = None,
        show_progress_bar = False
    )

    return route_planner

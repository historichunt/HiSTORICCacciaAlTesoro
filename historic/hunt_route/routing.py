import numpy as np
from numpy.random import RandomState
from dataclasses import dataclass, field
from typing import List
from tqdm import tqdm
from historic.hunt_route.data_matrices import DataMatrices
from historic.hunt_route.limited_size_sorted_dict import LimitedSizeSortedDict
from historic.hunt_route import locations_utils
from historic.hunt_route.render_map import render_map
from collections import Counter

METRIC_DISTANCE = 'distance'
METRIC_DURATION = 'duration'

METRICS = [
    METRIC_DISTANCE,
    METRIC_DURATION
]

@dataclass
class RoutePlanner:    
    """This is the class responsible for the route planning

    Attributes:
        dm (DataMatrices): object with data
        profile (str): one of api.PROFILES ('walking', 'cycling') / differs for ORS/GOOGLE 
        metric (str): one of routing.METRICS ('duration', 'distance')
        start_idx (int): start point index (0-based in list of points)        
        max_attempts (int): max number of attempts (upper bound on the number of correct routes being returned)        
        min_dst (int): min distance (or duration) between consecutive points in the route
        max_dst (int): max distance (or duration) between consecutive points in the route
        goal_tot_dst (int): total max distance (or duration) of the entire path
        tot_dst_tolerance (int): tolerance on total max distance (or duration) of the entire path    
        min_route_size (int): min number of stops in a route
        max_route_size (int): max number of stops in a route        
        check_convexity (bool): ensure that the route must form a convex shape
        overlapping_criteria (str): type of overlapping method (None, SEGMENT or GRID)
        max_overalapping (int): max distance (in meters/grids) of overlapping routes (defaultd to None: no max)
        stop_duration (int): time being spent in each stop (only relevant if dst is in duration)
        num_attempts (int): number of possible routes to be explored (defaults to None: exaustive search)
        random_seed (int): random seed for reproducibility (set to None if you always want different results)
            Only used if num_attempts is not None        
        exclude_neighbor_dst (int): exclude points in proximity of chosen stop by the given distance (or duration)
            Defautls to None if no neighbor constraints is to be set.
        exclude_suboptimal_solutions (bool): exclude solution routes for which longer solution route exists (with same prefix)
        circular_route (bool): ensure the route to be circular (going back to first point)
        num_best (int): num of best solutions to keep (defaults to None for all)
        stop_when_num_best_reached (bool): stop when the given number of solutions is reached (not optimized)
        num_discarded (int): num of discarded solutions to keep (for debugging purpose)
    """

    dm: DataMatrices
    profile: str
    metric: str
    start_idx: int     
    goal_tot_dst: int
    tot_dst_tolerance: int
    min_dst: int = 0
    max_dst: int = float('inf')
    min_route_size: int = 1
    max_route_size: int = float('inf')
    skip_points_idx: List = field(default_factory=lambda: [])
    check_convexity: bool = False
    overlapping_criteria: str = None # 'SEGMENT', 'GRID'
    max_overalapping: int = None
    stop_duration: int = 0
    num_attempts: int = None    
    random_seed: int = None        
    exclude_neighbor_dst: int = None    
    exclude_suboptimal_solutions: bool = True
    circular_route: bool = False
    num_best: int = 1
    stop_when_num_best_reached: bool = False
    num_discarded: int = None    
    show_progress_bar: bool = True

    def __post_init__(self):
        self.__check_params()        
        self.check_overlapping = self.overlapping_criteria is not None
        self.rs = RandomState(self.random_seed)
        self.dst_matrix = np.array(self.dm.dst_matrices[self.profile][self.metric])
        self.num_points = len(self.dst_matrix)
        self.point_names = self.dm.point_names
        self.points = np.array(self.dm.coordinates)      
    
    def __check_params(self):
        assert self.num_attempts is None or self.num_attempts > 0, \
            f'num_attempts ({self.num_attempts}) must be None or > 0'            
        assert self.overlapping_criteria in [None, 'SEGMENT', 'GRID'], \
            f'overlapping_criteria ({self.overlapping_criteria}) must be one of ' \
            f"{[None, 'SEGMENT', 'GRID']}"
        assert (self.overlapping_criteria==None) == (self.max_overalapping==None), \
            f'overlapping_criteria ({self.overlapping_criteria}) ' \
            f'and max_overalapping ({self.max_overalapping}) ' \
            'must be both None or both different from None'

    def get_routes(self, show_map=True, log=False):
        """Display best routes

        Args:
            plot (bool): show plots
            show_map (bool): show map
            log (bool): log to std out
        """

        info = [
            'PARAMETERS:',
            f'dataset name = {self.dm.dataset_name}',
            f'start num = {self.start_idx + 1}',
            f'duration min = {self.goal_tot_dst / 60}',
            f'profile = {self.profile}',
            f'circular route = {self.circular_route}',
            ''
        ]

        def print_info(s):
            info.append(s)
            if log:
                print(s)

        def print_info_list(s_list):
            info.append('')
            info.extend(s_list)
            if log:
                print('')
                for s in s_list:
                    print(s)

        print_info(f'Routes found/total: {self.total_solutions}/{self.total_attempts}')

        best_route_idx = None
        best_stop_names = None
        best_route_img = None    
        duration_min = None    

        if len(self.solutions) == 0:                  
            print_info('No solution found!')            
            if self.save_discarded and len(self.discarded_solutions)>0:
                print_info('!!!!!!!!!!')
                print_info('Showing discarded solutions.')
                print_info('!!!!!!!!!!')
                displayed_solutions = self.discarded_solutions
            else:
                return best_route_idx, best_stop_names, info, best_route_img, duration_min
        else:
            displayed_solutions = self.solutions
        
        # plot at most first x results
        first = True
        for (error, _), route_idx in displayed_solutions.items():    
            if first:
                best_route_idx = route_idx
                best_stop_names = [self.point_names[i] for i in route_idx]
            route_points = np.take(self.points, route_idx, axis=0)            
            route_info, duration_min = self.get_route_info(
                route_points, route_idx, self.dst_matrix, error, self.point_names)
            print_info_list(route_info)
            if show_map or first:      
                overlapping_dst, path_points, unique_segments, segments_counts = \
                    locations_utils.compute_overlapping_path_segments(
                        self.dm, route_points, self.profile
                    )  
            if show_map:              
                overlapping_dst_int = int(round(overlapping_dst,0))
                print_info(f'Overlapping dst: {overlapping_dst_int} m')
                
                grid_counter = locations_utils.compute_grid_counter(self.dm, route_idx, self.profile)
                overlapping_grids = np.sum(x-1 for x in grid_counter.values() if x>1)
                print_info(f'Overlapping grids: {overlapping_grids}')
                
                locations_utils.plot_route_points(route_points)
                locations_utils.plot_route_graph(
                    self.points, route_points, path_points, unique_segments, segments_counts,
                    grid_counter=grid_counter,
                    print_dots=False, 
                    print_path_numbers=False
                )             
            if show_map or first:         
                map_img = render_map(route_points, path_points, unique_segments, segments_counts, self.points, show=show_map)
                if first:
                    best_route_img = map_img
            
            first = False

        return best_route_idx, best_stop_names, info, best_route_img, duration_min

    def build_routes(self):
        """Get all routes satisfying specific constraints

        Args:
            dst_matrix (np.ndarray): matrix with distances (or durations) between any pair of points
        
        Returns:
            list(tuple(int)): list of routes (0-based indexed) sorted by how close they are to the given goal_tot_dst
        """        
        
        self.solutions = LimitedSizeSortedDict(size_limit=self.num_best) # (error, counter) -> route_idx
        self.discarded_solutions = \
            None if self.num_discarded is None \
            else LimitedSizeSortedDict(size_limit=self.num_discarded) # (error, counter) -> route_idx
        self.save_discarded = self.num_discarded is not None

        self.total_attempts = 0
        self.total_solutions = 0
        self.total_discarded_solutions = 0

        self.goal_tot_dst_min = self.goal_tot_dst - self.tot_dst_tolerance
        self.goal_tot_dst_max = self.goal_tot_dst + self.tot_dst_tolerance        
        self.all_points_idx = list(range(self.num_points))
        
        self.remove_neighbor = self.exclude_neighbor_dst is not None
        if self.remove_neighbor:
            self.p_idx_neighbor_idx = {
                p: [n for n in self.all_points_idx if self.dst_matrix[p][n] < self.exclude_neighbor_dst]
                for p in self.all_points_idx
            }

        remaining_idx = [
            i for i in range(self.num_points)
            if i not in self.skip_points_idx
        ]

        route_idx = [self.start_idx]
        
        if self.show_progress_bar:
            self.pbar = tqdm(total=self.num_attempts)

        grid_counter = Counter() if self.overlapping_criteria == 'GRID' else None
        
        self.__search_route_recursive(
            route_idx, route_size=1, prev_idx=self.start_idx,
            tot_dst=self.stop_duration, remaining_idx=remaining_idx,
            grid_counter=grid_counter)
        
        if self.show_progress_bar:
            self.pbar.close()

    def get_pair_dst(self, idx_a, idx_b, add_stop_duration):
    
        pair_dst = self.dst_matrix[idx_a][idx_b]
        
        if pair_dst < self.min_dst:
            # pairwise distance too small
            return None            
        
        if pair_dst > self.max_dst:
            # pairwise distance too big
            return None  

        if add_stop_duration:
            pair_dst += self.stop_duration

        return pair_dst          

    def check_route_overlapping(self, route_idx, grid_counter):
        if not self.check_overlapping:
            return True        
        if self.overlapping_criteria == 'GRID':
            overlapping_grids = np.sum(x-1 for x in grid_counter.values() if x>1)
            return overlapping_grids <= self.max_overalapping
        else:
            # 'SEGMNET'
            route_points = np.take(self.points, route_idx, axis=0)
            overlapping_dst, _, _, _ = locations_utils.compute_overlapping_path_segments(
                self.dm, route_points, self.profile
            )
            return overlapping_dst <= self.max_overalapping

    def check_route_convexity(self, route_idx):
        if not self.check_convexity:
            return True   
        if len(route_idx) < 3:
            return True # too few sides to be a polygon     
        route_points = np.take(self.points, route_idx, axis=0)
        return locations_utils.is_convex_polygon(route_points)

    def check_and_add_solution(self, tot_dst, route_size, route_idx):
        valid = \
            ( # reached minimal goal distance (goal distance - tolerance)
            tot_dst > self.goal_tot_dst_min
            ) and \
            ( # satisfies min_route_size
                self.min_route_size == None or \
                route_size >= self.min_route_size
            )
        if valid or self.save_discarded:
            error = np.abs(tot_dst-self.goal_tot_dst)
            if valid:
                self.total_solutions += 1
                self.solutions[(error, self.total_solutions)] = route_idx
            else:
                self.total_discarded_solutions += 1
                self.discarded_solutions[(error, self.total_discarded_solutions)] = route_idx
            
        return valid

    def is_time_to_stop(self):
        return self.total_attempts == self.num_attempts or \
            self.stop_when_num_best_reached and len(self.solutions)==self.num_best

    def __search_route_recursive(self, route_idx, route_size, prev_idx, 
        tot_dst, remaining_idx, grid_counter):   
        """[summary]

        Args:
            route_idx ([type]): [description]
            route_size ([type]): [description]
            prev_idx ([type]): [description]
            tot_dst ([type]): [description]
            remaining_idx ([type]): [description]
            grid_counter ([type]): [description]

        Returns:
            [type]: [description]
        """

        remaining_idx = remaining_idx.copy()
        if grid_counter is not None:
            grid_counter = grid_counter.copy()
        
        if self.remove_neighbor:
            for n_idx in self.p_idx_neighbor_idx[prev_idx]:
                if n_idx in remaining_idx:
                    remaining_idx.remove(n_idx)
        else:
            remaining_idx.remove(prev_idx)

        if len(remaining_idx)==0:                     
            self.total_attempts += 1  
            if self.show_progress_bar:
                self.pbar.update(1)  
            return False # no more options

        self.rs.shuffle(remaining_idx)

        found_solution = False

        for next_idx in remaining_idx:        

            self.total_attempts += 1
            
            if self.is_time_to_stop():
                break
            
            if self.show_progress_bar:
                self.pbar.update(1)            
            
            pair_dst = self.get_pair_dst(prev_idx, next_idx, add_stop_duration=True)

            if pair_dst is None:
                continue

            new_tot_dst = tot_dst + pair_dst
            if new_tot_dst > self.goal_tot_dst_max:
                # total distance too big (bigger than goal distance + tolerance)
                continue

            new_route_idx = route_idx + [next_idx] # this creates a copy with additional element
            new_route_size = route_size + 1

            new_grid_counter = None if grid_counter is None else grid_counter.copy()
            if self.check_overlapping:
                new_grid_counter.update(
                    self.dm.get_direction_path_grid_set(route_idx[-1], next_idx, self.profile)
                )

            if not self.check_route_convexity(new_route_idx):
                continue

            if self.circular_route:
                first_idx = new_route_idx[0]
                pair_dst = self.get_pair_dst(next_idx, first_idx, add_stop_duration=False)
                if pair_dst is None:
                    continue
                circle_route_idx = new_route_idx + [first_idx]
                circle_grid_counter = None if grid_counter is None else new_grid_counter.copy()
                if self.check_overlapping:
                    circle_grid_counter.update(
                        self.dm.get_direction_path_grid_set(new_route_idx[-1], first_idx, self.profile)
                    )

                if not self.check_route_overlapping(circle_route_idx, circle_grid_counter):
                    continue
                cicle_route_size = new_route_size + 1                
                cicle_tot_dst = new_tot_dst + pair_dst
                found_solution = self.check_and_add_solution(
                    cicle_tot_dst, cicle_route_size, circle_route_idx)
            else:                
                if not self.check_route_overlapping(new_route_idx, new_grid_counter):
                    continue


            # after this point current route is valid 
            # (or can turn into a valid route with additional points)  

            found_extended_solution = False                          

            if self.max_route_size == None or new_route_size < self.max_route_size:
                # can still add more points

                found_extended_solution = self.__search_route_recursive( 
                    new_route_idx, new_route_size, next_idx,
                    new_tot_dst, remaining_idx,
                    new_grid_counter
                )

                found_solution = found_solution or found_extended_solution

                if self.is_time_to_stop():
                    break # reached number of attempts

            if not self.circular_route and \
                ( not self.exclude_suboptimal_solutions or \
                  not found_extended_solution
                ):
                # add current solution even if suboptimal            

                found_solution = self.check_and_add_solution(
                    new_tot_dst, new_route_size, new_route_idx)

        return found_solution

    def get_route_info(self, route_points, route_idx, dst_matrix, error, point_names):
        """[summary]

        Args:
            route_points ([type]): [description]
            route_idx ([type]): [description]
            dst_matrix ([type]): [description]
            error ([type]): [description]
            point_names ([type]): [description]
        """
        info = []
        route_size = len(route_points)
        # route_points_num = [i+1 for i in route_idx]
        dist = [dst_matrix[route_idx[i],route_idx[i+1]] for i in range(route_size-1)]
        stop_duration_factor = route_size
        if self.circular_route:
            stop_duration_factor -= 1
        tot_dst = np.sum(dist) + stop_duration_factor * self.stop_duration
        check_error = np.abs(tot_dst-self.goal_tot_dst)
        assert np.abs(check_error - error) < 1E-5
        # route_num = [i+1 for i in route_idx]
        # info.append(f'route_num: {route_num}')        
        if point_names is not None:
            route_names_stop = '\n'.join(
                [
                    f'  - {n} ({str(i+1).rjust(3)}): {point_names[i]}' 
                    for n,i in enumerate(route_idx,1)
                ]
            )
            info.append(f'route names stop:\n{route_names_stop}')
        # info.append(f'route points: {route_points_num}')
        if self.metric == METRIC_DURATION:
            # show distances in minutes (instead of seconds)
            dist = [d/60 for d in dist]
            tot_dst /= 60
            error /= 60
        legs_str = ', '.join(["{:.1f}".format(d) for d in dist])
        info.append(f'legs duration: {legs_str}')
        info.append(f'total duration: {"{:.1f}".format(tot_dst)}')
        info.append(f'duration error: {"{:.1f}".format(error)}')
        duration_min = int(np.ceil(tot_dst))
        return info, duration_min
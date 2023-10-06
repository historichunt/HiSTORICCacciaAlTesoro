from dataclasses import dataclass
import sys
from typing import Callable
import polyline
import os
import json
from tqdm import tqdm
import numpy as np
from numpy.random import RandomState
from historic.routing.api import api_ors
from historic.routing.api import api_google
from historic.routing.utils.mgrs_utils import get_grid_id_set_from_route
from historic.routing.utils import plot_utils
from historic.config.params import ROOT_DIR
from historic.routing.metrics import METRIC_DISTANCE, METRIC_DURATION, METRICS
from geopy import distance
from collections import defaultdict

from historic.routing.utils.utils import fill_double_list

ROUTING_DIR = os.path.join(ROOT_DIR, 'routing_data')

@dataclass
class DataMatrices:  
    """This is the class responsible for keeping the 
    matrices with the directions (encoded polylines)

    Attributes:
        dataset_name (str): name of the dataset (airtable base key)
        api: if to use module api_google or api_ors        
        json_file (str): the auto-coded file `data/<dataset_name>.json` contianing all the data
        max_linear_dst_km: max linear distance between two points to be considered connected (otherwise don't retrieve distance)
    
    Matrixes:
        Saved in data:
            - self.dst_matrices[profile][metric][i][j]: distance/duration (based on metrics) from i to j
            - self.poly_matrices[profile][i][j]: string representing polyline with points connecting i to j
            - self.grid_matrices[profile][i][j]: list of mgrs ids to connect i to j 
        
        Used in building data:
            - self.coord_matrices[profile][i][j]: array of long,lat coordinates of path connecting i with j
                used for building grid_matrix
                used in get_direction_path_coordinates
            - self.grid_matrices_set[profile][i][j]: set of mgrs ids to connect i to j 
                used in get_direction_path_grid_set

    Important:
        - It is possible for two location names to map to the same coordinates 

    """
    dataset_name:str     
    api:Callable # module api_google or api_ors
    json_file:str = None
    max_linear_dst_km: float = None # by default do not discriminate pairs by linear distance

    def __post_init__(self):
        self.__check_params()        
        self.restrict_connections_by_linear_dst = self.max_linear_dst_km != None        
        if self.json_file is None:
            # use default file path
            self.json_file = os.path.join(
                ROUTING_DIR, 
                f'{self.dataset_name}_DM_{self.api.API_NAME}.json'
            )                 
        if os.path.exists(self.json_file):
            self.modified = False
            self.data = json.load(open(self.json_file)) # might still be incomplete
            self.read_data() # read matrices from data
            self.num_points = len(self.point_names)
            if self.completed:
                self.__build_direction_coord_matrices()
                self.__convert_grid_matrices_to_set() # builds grid_matrices_set
            else:
                self.update_matrices()
        else:
            self.modified = True
            self.completed: False
            self.coordinates_longlat = []
            self.point_names = []                        
            self.num_points = 0            
            self.__init_matrices()                                                                       
            self.save_data()        

    def __check_params(self):
        assert self.api in [api_google, api_ors], \
            f"api param ({self.api}) must be 'api_google' or 'api_ors'"        

    def __init_matrices(self):
        self.dst_matrices = {
            profile: {
                metric: fill_double_list(None, self.num_points)
                for metric in METRICS
            }
            for profile in self.api.PROFILES                        
        }
        self.poly_matrices = {
            profile: fill_double_list('', self.num_points)
            for profile in self.api.PROFILES
        }
        self.grid_matrices = {
            profile: fill_double_list(None, self.num_points)
            for profile in self.api.PROFILES
        }                     

    def __copy_sub_matrix(self, src_matrix, dst_matrix):
        # src_matrix smaller than dst_matrix
        num_points = len(src_matrix)
        for i in range(num_points):
            for j in range(num_points):
                dst_matrix[i][j] = src_matrix[i][j]

    def __enlarge_matrices(self):
        self.old_dst_matrices = self.dst_matrices
        self.old_poly_matrices = self.poly_matrices
        self.old_grid_matrices = self.grid_matrices
        
        # reinitialize matrix with new number of points
        self.__init_matrices() 
        
        for profile in self.api.PROFILES:
            for metric in METRICS:
                src_matrix = self.old_dst_matrices[profile][metric]
                dst_matrix = self.dst_matrices[profile][metric]
                self.__copy_sub_matrix(src_matrix,dst_matrix)
            
            self.__copy_sub_matrix(self.old_poly_matrices[profile],self.poly_matrices[profile])
            self.__copy_sub_matrix(self.old_grid_matrices[profile],self.grid_matrices[profile])

    def __build_coordinates_for_api(self):        
        if self.api == api_google:
            self.coordinates_for_api = np.flip(self.coordinates_longlat, axis=1)
        else:
            self.coordinates_for_api = self.coordinates_longlat

    def __convert_grid_matrices_to_set(self):
        self.grid_matrices_set = {}
        for profile in self.api.PROFILES:
            grid_matrix_list_profile = self.grid_matrices[profile]
            grid_matrix_set_profile = fill_double_list(None, self.num_points)
            self.grid_matrices_set[profile] = grid_matrix_set_profile
            for i in range(self.num_points):
                for j in range(self.num_points):
                    if i==j:
                        continue
                    value = grid_matrix_list_profile[i][j]
                    if value is None:
                        continue
                    grid_matrix_set_profile[i][j] = set(value)                        

    def update_matrices(self, name_longlat=None, allow_change_gps=False):
        """update dst_matrices, poly_matrices and grid_matrices

        Args:
            name_longlat (dict): dictionary mapping new points names (str) to long,lat coordinates            
        """

        if name_longlat is not None:
            # set self.completed to False and self.modified to True if more data found
            self.__update_locations(name_longlat, allow_change_gps) 
        
        if self.completed:
            print("No new points found and DataMatrices already completed")
            return

        self.__build_coordinates_for_api()
        self.name_longlat = {p:c for p,c in zip(self.point_names, self.coordinates_longlat)}
        # self.longlat_name = { c:p for p,c in zip(self.point_names, self.coordinates_longlat)}

        self.__update_dst_matrices() # setting modified to true
        
        if self.__update_direction_matrices():
            self.completed = True
            self.save_data()

    def __update_locations(self, name_longlat, allow_change_gps):
        new_points = []
        new_coordinates = []
        self.updated_gps_idx = set()
        num_gps_conflicts = 0
        for p,c in name_longlat.items():
            if p in self.point_names:
                # already present: skip but make sure it's maps to same coordiante
                idx = self.point_names.index(p)
                p_gps = self.coordinates_longlat[idx]
                if c != p_gps:
                    num_gps_conflicts += 1
                    print(f"Point name {p} already present but associated to new GPS: old -> {p_gps}, new ->{c}")                    
                    if allow_change_gps:
                        self.updated_gps_idx.add(idx)
                        self.coordinates_longlat[idx] = c
            else:
                new_points.append(p)
                new_coordinates.append(c)     

        if num_gps_conflicts > 0:            
            if allow_change_gps:
                print('Updated GPS coordinates:', num_gps_conflicts)
            else:
                print(f'{num_gps_conflicts} GPS conflict(s) - set allow_change_gps to True to allow changes.')
                sys.exit(1)

        if len(new_points) == 0:
            print(f'No new point names found')
            if num_gps_conflicts > 0:
                self.modified = True
                self.completed = False
            return            
                
        old_num_points = self.num_points        
        
        self.point_names.extend(new_points)
        self.coordinates_longlat.extend(new_coordinates)        
        self.num_points = len(self.point_names)
        self.__enlarge_matrices()
        self.modified = True
        self.completed = False 

        print(f'Num new points found {len(new_points)}: {", ".join(new_points)}')
        print(f'Total points increased from {old_num_points} to {self.num_points}')

    def __update_dst_matrices(self):
        
        all_connected = True
        connected_point_names = None
        if self.restrict_connections_by_linear_dst:
            connected_point_names, all_connected = self.__compute_connected_point_names()

        if all_connected:
            empty_dst_matrices = self.__check_matrix_empty(
                matrix = self.dst_matrices[self.api.PROFILES[0]][METRIC_DISTANCE],
                empty_value=None
            )
            if empty_dst_matrices:
                # build entire matrix without checking linear distance
                self.__build_full_dst_matrices() # saving data
                return

        # dst matrixes could be 
        # - empty (but only connected points should be considered)
        # - incomplete (e.g., new points added)            
        self.__complete_dst_matrices(connected_point_names) # saving data

    def __check_matrix_empty(self, matrix, empty_value):
        """Check if dst matrices are simply initialized with None        
        Returns:
            _type_: _description_
        """
                
        for row in matrix:
            for dst in row:
                if dst != empty_value:
                    return False
        return True


    def __compute_connected_point_names(self):
        """Compute set of connected points

        Returns:
            connected_point_names: set of pairs tuple of connected coordinates (sorted by long/lat)
            all_connected: bool stating if all points are connected (less than max_linear_dst_km)
        """
        
        # dictionary from point names to set of connected point names
        connected_point_names = defaultdict(set) 

        # sort coordinate by 1st element (long) and 2nd element (lat)
        sorted_point_names = sorted(self.point_names) 
        
        all_connected = True
        connected_pairs = 0
        for i in range(self.num_points):
            for j in range(i+1, self.num_points):
                pA = sorted_point_names[i]
                pB = sorted_point_names[j]
                cA_latlong = reversed(self.name_longlat[pA]) # convert to lat, long
                cB_latlong = reversed(self.name_longlat[pB]) # convert to lat, long
                # distance requires lat, long coordinates
                linear_dst_km = distance.distance(cA_latlong, cB_latlong).km
                if linear_dst_km <= self.max_linear_dst_km:                    
                    connected_point_names[pA].add(pB)
                    connected_point_names[pB].add(pA)
                    connected_pairs += 1
                else:
                    all_connected = False
        total_num_pairs = int((self.num_points ** 2 - self.num_points) / 2) # excluding self
        non_connected_num_pairs = total_num_pairs - connected_pairs
        connected_percentage = connected_pairs / total_num_pairs * 100
        print(f'Total pairs: {total_num_pairs}')
        print(f'Non connected pairs: {non_connected_num_pairs}')
        print(f'Connected pairs: {connected_pairs} ({connected_percentage:.2f}%)')
        
        print(f'All connected: {all_connected}')
        return connected_point_names, all_connected
                
    def __build_full_dst_matrices(self):            

        for profile in self.api.PROFILES: # foot, cycling
            distances_matrix, durations_matrix = \
                    self.api.build_distance_matrices(self.coordinates_for_api, profile)
            self.dst_matrices[profile][METRIC_DURATION] = durations_matrix
            self.dst_matrices[profile][METRIC_DISTANCE] = distances_matrix                            
        self.save_data()

    def __complete_dst_matrices(self, connected_point_names):

        print('Completing dst matrices...')
        num_elements_changed = 0

        for profile in self.api.PROFILES:

            profile_distance_metric = self.dst_matrices[profile][METRIC_DISTANCE]
            profile_duration_metric = self.dst_matrices[profile][METRIC_DURATION]
            
            for origin_idx in range(self.num_points):
                p_origin = self.point_names[origin_idx]
                connected_point_names_origin = connected_point_names[p_origin]
                # find all the destinations connected to origin
                destinations_idx = []
                for dst_idx, dst_name in enumerate(self.point_names):
                    if dst_name not in connected_point_names_origin:
                        # not connected points, including self connection
                        # reset it just in case
                        profile_distance_metric[origin_idx][dst_idx] = None
                        profile_duration_metric[origin_idx][dst_idx] = None
                        continue
                    if ( 
                        profile_distance_metric[origin_idx][dst_idx] == None or                            
                        origin_idx in self.updated_gps_idx or
                        dst_idx in self.updated_gps_idx
                        # recalculate dst if GPS of origin or dst changed
                    ):
                        destinations_idx.append(dst_idx) 

                if len(destinations_idx) == 0:
                    continue

                num_elements_changed += len(destinations_idx)
                
                distances_row, durations_row = self.api.build_distance_row(
                        self.coordinates_for_api, origin_idx, destinations_idx, profile)

                for dst_idx, distance, duration in zip(destinations_idx, distances_row, durations_row):
                    profile_distance_metric[origin_idx][dst_idx] = distance
                    profile_duration_metric[origin_idx][dst_idx] = duration                    

                self.modified = True

        print('Total number of elements changed:', num_elements_changed)
        
        if num_elements_changed > 0:
            self.save_data()


    def __update_direction_matrices(self):
        save_every = 1 if self.api == api_ors else 100
        
        finished, added = self.__build_direction_poly_matrix(save_every) 
        
        self.__build_direction_coord_matrices()

        if finished and added > 0:            
            self.__build_direction_grid_matrices()                

        return finished

            
    def __build_direction_poly_matrix(self, save_every=1):
        import warnings
        warnings.simplefilter("ignore") # avoid getting warnings from openrouteservice/client.py:214
        
        for profile in self.api.PROFILES:

            dst_matrix_profile = self.dst_matrices[profile][METRIC_DISTANCE] # distance
            poly_matrices_profile = self.poly_matrices[profile]

            added = 0
            total = int(self.num_points * (self.num_points-1))
            
            missing_idx_pairs = []
            for i in range(self.num_points):
                for j in range(self.num_points):
                    if dst_matrix_profile[i][j] == None: 
                        # not connected (including self)
                        # resetting just in case
                        poly_matrices_profile[i][j] = ''
                        continue
                    if (
                        # GPS for i or j have changed
                        i in self.updated_gps_idx or        
                        j in self.updated_gps_idx or
                        poly_matrices_profile[i][j] == ''
                    ):
                        pair = (i,j)
                        missing_idx_pairs.append(pair)                

            missing = len(missing_idx_pairs)      
            if missing == 0:
                print('Direction Matrix already filled')
                return True, added
            print(f'Direction Matrix {profile} (missing/tot): {missing}/{total}')
            pbar = tqdm(total=missing)
            for i,j in missing_idx_pairs:
                c1 = self.coordinates_for_api[i]
                c2 = self.coordinates_for_api[j]
                pbar.update(1)
                poly_entry = self.api.get_direction_polyline(c1, c2, profile)
                if poly_entry is None:
                    pbar.close()
                    self.save_data()
                    print('Added polylines:', added)  
                    print('Interruption in retrieving polylines: data saved, pleease run it again.')                    
                    return False, added
                poly_matrices_profile[i][j] = poly_entry 
                added += 1        
                self.modified = True            
                if added % save_every == 0:
                    self.save_data()        
            pbar.close()        
            self.save_data()
            print('Added polylines:', added)
        return True, added

    def __build_direction_coord_matrices(self):

        self.coord_matrices = {
            profile: fill_double_list(None, self.num_points)
            for profile in self.api.PROFILES
        }    

        for profile in self.api.PROFILES:        
            coord_matrix_profile = self.coord_matrices[profile]
            poly_matrices_profile = self.poly_matrices[profile]
            for i in range(self.num_points):
                for j in range(self.num_points):
                    if i==j:
                        continue                
                    poly_entry = poly_matrices_profile[i][j]
                    if poly_entry == '':
                        # non connected
                        # if poly_entry is '' path_coordinates will be None
                        continue                                 
                    path_coordinates = np.array(polyline.decode(poly_entry, geojson=True)) # long, lat                    
                    coord_matrix_profile[i][j] = path_coordinates        

    def __build_direction_grid_matrices(self):

        for profile in self.api.PROFILES:
        
            profile_grid_matrix = self.grid_matrices[profile]

            bar = tqdm(total=self.num_points**2, desc=f'Build grid matrix ({profile})')
            for i in range(self.num_points):
                for j in range(self.num_points):
                    bar.update()
                    if i==j:
                        continue                
                    path_coordinates = self.coord_matrices[profile][i][j]
                    if path_coordinates is None:
                        # if path_coordinates is None (e.g., not connected) 
                        # grid_list will be set to None
                        grid_list = None
                    else:                        
                        grid_list = list(get_grid_id_set_from_route(path_coordinates))
                    profile_grid_matrix[i][j] = grid_list
            bar.close()            
        
        self.modified = True

    def get_stop_name_index(self, point_name):
        if point_name in self.point_names:
            return self.point_names.index(point_name)
        return None

    def get_coordinate_index(self, lat, long):        
        target = [long, lat]
        if target in self.coordinates_longlat:
            return self.coordinates_longlat.index(target)
        return None


    def get_direction_path_coordinates(self, c1, c2, profile):
        i = self.coordinates_longlat.index(c1)
        j = self.coordinates_longlat.index(c2)
        path_coordinates = self.coord_matrices[profile][i][j] # long, lat
        assert path_coordinates is not None
        return path_coordinates

    def get_direction_path_grid_set(self, i, j, profile):
        path_grid_set = self.grid_matrices_set[profile][i][j] # long, lat
        assert path_grid_set is not None
        return path_grid_set

    def plot(self, profile, metric):
        rs = RandomState(123)
        colors = rs.rand(self.num_points)   
        points = np.array(self.coordinates_longlat)      
        x = points[:,0]
        y = points[:,1]
        xlim = [np.min(x)-0.001, np.max(x)+0.001]
        ylim = [np.min(y)-0.001, np.max(y)+0.001]

        dst_matrix = np.array(self.dst_matrices[profile][metric])

        plot_utils.plot_points(x, y, colors, xlim, ylim)
        plot_utils.plot_distance_matrix(dst_matrix)
        plot_utils.plot_distance_distribution(dst_matrix)        

    def read_data(self):
        self.completed = self.data.get('completed', False)
        self.coordinates_longlat = self.data['coordinates'] # long-lat format
        self.point_names = self.data['point_names'] 
        self.dst_matrices = self.data['dst_matrices'] # profile -> metric -> dst_matrix
        self.poly_matrices = self.data['poly_matrices']   # profile -> poly_matrix
        self.grid_matrices = self.data.get('grid_matrices') # profile -> grid_matrix

    def save_data(self):
        if not self.modified:
            return

        self.data = {
            'completed': self.completed,
            'coordinates': self.coordinates_longlat,
            'point_names': self.point_names,
            'dst_matrices': self.dst_matrices,
            'poly_matrices': self.poly_matrices,
            'grid_matrices': self.grid_matrices
        }

        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False) # indent=3, 
from dataclasses import dataclass
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

ROUTING_DIR = os.path.join(ROOT_DIR, 'routing_data')

@dataclass
class DataMatrices:  
    """This is the class responsible for keeping the 
    matrices with the directions (encoded polylines)

    Attributes:
        dataset_name (str): name of the dataset (airtable base key)
        api: if to use module api_google or api_ors        
        json_file (str): the auto-coded file `data/<dataset_name>.json` contianing all the data
        matrix (dict): profile (str) -> polylines_matrix (list(list(str))) where polylines are stored 
        max_linear_dst_km: max linear distance between two points to be considered connected (otherwise don't retrieve distance)
    """
    dataset_name:str     
    api:Callable # module api_google or api_ors
    json_file:str = None
    max_linear_dst_km: float = None # by default do not discriminate pairs by linear distance

    def __post_init__(self):
        self.__check_params()        
        self.restrict_connections_by_linear_dst = self.max_linear_dst_km != None
        self.modified = False
        if self.json_file is None:
            # use default file path
            self.json_file = os.path.join(
                ROUTING_DIR, 
                f'{self.dataset_name}_DM_{self.api.API_NAME}.json'
            )                 
        if os.path.exists(self.json_file):
            self.data = json.load(open(self.json_file)) # might still be incomplete
            self.completed = self.data.get['completed', False]
            self.coordinates = [tuple(c) for c in self.data['coordinates']]
            self.point_names = self.data['point_names'] 
            self.dst_matrices = self.data['dst_matrices'] # profile -> metric -> dst_matrix
            self.poly_matrices = self.data['poly_matrices']   # profile -> poly_matrix
            self.grid_matrices = self.data.get('grid_matrices', None) # profile -> grid_matrix
            self.num_points = len(self.point_names)
        else:
            self.completed: False
            self.coordinates = []
            self.point_names = []                        
            self.num_points = 0

            self.__init_matrices()                                   
                        
            self.data = {
                'completed': self.completed,
                'coordinates': self.coordinates,
                'point_names': self.point_names,
                'dst_matrices': self.dst_matrices,
                'poly_matrices': self.poly_matrices,
                'grid_matrices': self.grid_matrices_list
            }
            self.save_data()        

    def __check_params(self):
        assert self.api in [api_google, api_ors], \
            f"api param ({self.api}) must be 'api_google' or 'api_ors'"        

    def __build_empty_matrix(self, fill_value):
        return [ 
            [fill_value] * self.num_points 
            for _ in range(self.num_points)
        ]

    def __init_matrices(self):
        self.dst_matrices = {
            profile: {
                metric: self.__build_empty_matrix(0)
                for metric in METRICS
            }
            for profile in self.api.PROFILES                        
        }
        self.poly_matrices = {
                profile: self.__build_empty_matrix('')
                for profile in self.api.PROFILES
            }
        self.grid_matrices = {
            profile: self.__build_empty_matrix(None)
            for profile in self.api.PROFILES
        }                            
        self.grid_matrices_list = {
            profile: self.__build_empty_matrix(None)
            for profile in self.api.PROFILES
        }     


    def update_matrices(self, name_longlat):
        """update dst_matrices, poly_matrices and grid_matrices

        Args:
            name_longlat (dict): dictionary mapping new points names (str) to long,lat coordinates            
        """

        if self.completed:
            print("DataMatrices already completed")
            return

        new_points = []
        new_coordinates = []
        for p,c in name_longlat.items():
            if p not in self.point_names:
                new_points.append(p)
                new_coordinates.append(tuple(c))
        
        self.point_names.extend(new_points)
        self.coordinates.extend(new_coordinates)
        self.num_points = len(self.point_names)
        
        # initialize dict 
        # - name -> longlat
        # - longlat -> name
        # self.name_longlat = { p:c for p,c in zip(self.point_names, self.coordinates)}
        # self.longlat_name = {c:p  for p,c in zip(self.point_names, self.coordinates)}

        # assert len(self.name_longlat) == len(self.longlat_name), \
        #     "Error: two locations have same name and/or coordinates"

        if len(new_points) > 0:
            print(f'Num new points found: {len(new_points)}')
        print(f'Total points: {self.num_points}')

        self.__update_dst_matrices() # setting modified to true
        self.__build_direction_matrices()


    def __update_dst_matrices(self):
        empty_dst_matrices = self.__check_dst_matrices_empty()

        all_connected = True
        connected_coordinates = None
        if self.restrict_connections_by_linear_dst:
            connected_coordinates, all_connected = self.__compute_connected_point_names()

        if empty_dst_matrices and all_connected:
                # build entire matrix without checking linear distance
                self.__build_full_dst_matrices() # saving data
        else:
            # dst matrixes could be 
            # - empty (but only connected points should be considered)
            # - incomplete (e.g., new points added)            
            self.__complete_dst_matrices(connected_coordinates) # saving data

    def __get_default_dst_matrix(self):
        # All profiles/metrics are updated all or none, 
        # so we need to check only one combination
        profile = self.api.PROFILES[0] # foot, cycling
        metric = METRICS[0]
        return self.dst_matrices[profile][metric]


    def __check_dst_matrices_empty(self):
        """Check if dst matrices are simply initialized with None        
        Returns:
            _type_: _description_
        """
        
        matrix = self.__get_default_dst_matrix()
        for row in matrix:
            for dst in row:
                if dst != 0:
                    return False
        return True


    def __compute_connected_point_names(self):
        """Compute set of connected points

        Returns:
            connected_coordinates: set of pairs tuple of connected coordinates (sorted by long/lat)
            all_connected: bool stating if all points are connected (less than max_linear_dst_km)
        """
        # sorting names by lexicographic order
        connected_coordinates = set() # set of lex-order pairs of coordinates
        sorted_coordinates = sorted(self.coordinates) # sort coordinate by 1st element (long) and 2nd element (lat)
        all_connected = True
        for i in range(self.num_points):
            for j in range(i+1, self.num_points):
                cA = np.flip(sorted_coordinates[i]) # convert into lat, long
                cB = np.flip(sorted_coordinates[j]) # convert into lat, long
                # distance requires lat, long coordinates
                linear_dst_km = distance.distance(cA, cB).km
                if linear_dst_km <= self.max_linear_dst_km:
                    coordinates_pair = (cA, cB)
                    connected_coordinates.add(coordinates_pair)
                else:
                    all_connected = False
        total_num_pairs = int((self.num_points ** 2 - self.num_points) / 2)
        connected_num_pairs = len(connected_coordinates)
        connected_percentage = connected_num_pairs / total_num_pairs * 100
        print(f'Total num pairs: {total_num_pairs}')
        print(f'Connected num pairs: {connected_num_pairs} ({connected_percentage:.0f}%)')
        print(f'All connected: {all_connected}')
        return connected_coordinates, all_connected

    @staticmethod
    def flip_coordinates(coordinates):        
        coordinates = np.flip(coordinates, axis=1)
        # make sure they remain tuples
        coordinates = list(map(tuple, coordinates)) 
        return coordinates
                
    def __build_full_dst_matrices(self):    

        coordinates = self.coordinates
        if self.api == api_google:
            # GOOGLE (need to give coordinates in lat long order)
            coordinates = self.flip_coordinates(coordinates)

        for profile in self.api.PROFILES: # foot, cycling
            distances_matrix, durations_matrix = \
                    self.api.build_distance_matrices(coordinates, profile)
            self.dst_matrices[profile][METRIC_DURATION] = durations_matrix
            self.dst_matrices[profile][METRIC_DISTANCE] = distances_matrix                            
        self.save_data()

    def __complete_dst_matrices(self, connected_coordinates):
        # do not consider connected_coordinates if all_connected
        # self.name_longlat
        # self.longlat_name

        # get one profile/metric matrix (to check for zero values)
        check_matrix = self.__get_default_dst_matrix()

        coordinates = self.coordinates
        if self.api == api_google:
            # GOOGLE (need to give coordinates in lat long order)
            coordinates = self.flip_coordinates(coordinates)

        for origin_idx in range(self.num_points):
            origin = self.coordinates[origin_idx]
            destinations_idx = [
                dst_idx for dst_idx,c in enumerate(self.coordinates)
                if (
                    sorted(origin,c) not in connected_coordinates and 
                    origin_idx != dst_idx and 
                    check_matrix[origin_idx][dst_idx] == 0
                )
            ]
            
            for profile in self.api.PROFILES:
                distances_row, durations_row = \
                    self.api.build_distance_row(
                        coordinates, origin_idx, destinations_idx, profile)
                profile_distance_metric = self.dst_matrices[profile][METRIC_DISTANCE]
                profile_duration_metric = self.dst_matrices[profile][METRIC_DURATION]
                for dst_idx, distance, duration in zip(destinations_idx, distances_row, durations_row):
                    profile_distance_metric[origin_idx][dst_idx] = distance
                    profile_duration_metric[origin_idx][dst_idx] = duration                    

        self.save_data()


    def __build_direction_matrices(self):
        save_every = 1 if self.api == api_ors else 100

        for profile in self.api.PROFILES:
            self.__build_direction_poly_matrix(profile, save_every)
            self.__build_direction_coord_matrix(profile)
            self.__build_direction_grid_matrix(profile)                

        self.save_data()
            

    def __get_poly_entry(self, c1, c2, profile):
        if self.api == api_ors:
            poly_entry = api_ors.get_direction_polyline([c1, c2], profile)                        
        else:
            c1_lat_long = np.flip(c1).tolist()
            c2_lat_long = np.flip(c2).tolist()
            poly_entry, _, _ = api_google.get_directions(c1_lat_long, c2_lat_long, profile)        
        return poly_entry

    def __build_direction_poly_matrix(self, profile, save_every=1):
        import warnings
        warnings.simplefilter("ignore") # avoid getting warnings from openrouteservice/client.py:214
        
        added = 0
        total = int(self.num_points * (self.num_points-1))
        missing = np.sum([
            self.poly_matrices[profile][i][j] == ''
            for i in range(self.num_points)
            for j in range(self.num_points)
            if i!=j
        ])
        if missing==0:
            # print('Direction Matrix already filled')
            return
        print(f'Direction Matrix {profile} (missing/tot): {missing}/{total}')
        pbar = tqdm(total=total)
        for i, c1 in enumerate(self.coordinates):
            for j, c2 in enumerate(self.coordinates):
                if i==j:
                    continue                
                pbar.update(1)
                poly_entry = self.poly_matrices[profile][i][j]
                if poly_entry == '':
                    poly_entry = self.__get_poly_entry(c1, c2, profile)
                    if poly_entry is None:
                        pbar.close()
                        self.save_data()
                        print('Added: ', added)                        
                        return
                    self.poly_matrices[profile][i][j] = poly_entry 
                    added += 1        
                    self.modified = True            
                    if added % save_every == 0:
                        self.save_data()        
        pbar.close()
        self.save_data()
        print('Added: ', added)

    def __build_direction_coord_matrix(self, profile):
        
        # init coord matrices
        self.coord_matrices = {
            profile: self.__build_empty_matrix(fill_value=None)
            for profile in self.api.PROFILES
        }    

        profile_coord_matrix = self.coord_matrices[profile]
        for i in range(self.num_points):
            for j in range(self.num_points):
                if i==j:
                    continue                
                poly_entry = self.poly_matrices[profile][i][j]
                assert poly_entry != '', 'poly_entry must be filled'
                path_coordinates = np.array(polyline.decode(poly_entry, geojson=True)) # lon, lat
                profile_coord_matrix[i][j] = path_coordinates        

    def __build_direction_grid_matrix(self, profile):
        profile_grid_matrix = self.grid_matrices[profile]

        if profile_grid_matrix[0][1] is not None:
            # already initialized, just need to convert lists to sets
            for i in range(self.num_points):
                for j in range(self.num_points):
                    if i==j:
                        continue                
                    profile_grid_matrix[i][j] = set(profile_grid_matrix[i][j])

        else:
            # need to initialize it
            profile_grid_matrix_list = self.grid_matrices_list[profile]
            bar = tqdm(total=self.num_points**2, desc=f'Build grid matrix ({profile})')
            for i in range(self.num_points):
                for j in range(self.num_points):
                    bar.update()
                    if i==j:
                        continue                
                    path_coordinates = self.coord_matrices[profile][i][j]
                    grid_set = get_grid_id_set_from_route(path_coordinates)
                    profile_grid_matrix[i][j] = grid_set
                    profile_grid_matrix_list[i][j] = list(grid_set)
            bar.close()            
            self.modified = True

    def get_stop_name_index(self, point_name):
        assert point_name in self.data['point_names']
        return self.data['point_names'].index(point_name)

    def get_coordinate_index(self, lat, lon):        
        target = [lon, lat]
        assert target in self.data['coordinates']
        return self.data['coordinates'].index(target)

    def get_direction_path_coordinates(self, c1, c2, profile):
        i = self.coordinates.index(c1)
        j = self.coordinates.index(c2)
        path_coordinates = self.coord_matrices[profile][i][j] # lon, lat
        assert path_coordinates is not None
        return path_coordinates

    def get_direction_path_grid_set(self, i, j, profile):
        path_grid_set = self.grid_matrices[profile][i][j] # lon, lat
        assert path_grid_set is not None
        return path_grid_set

    def plot(self, profile, metric):
        rs = RandomState(123)
        colors = rs.rand(self.num_points)   
        points = np.array(self.coordinates)      
        x = points[:,0]
        y = points[:,1]
        xlim = [np.min(x)-0.001, np.max(x)+0.001]
        ylim = [np.min(y)-0.001, np.max(y)+0.001]

        dst_matrix = np.array(self.dst_matrices[profile][metric])

        plot_utils.plot_points(x, y, colors, xlim, ylim)
        plot_utils.plot_distance_matrix(dst_matrix)
        plot_utils.plot_distance_distribution(dst_matrix)        


    def save_data(self):
        if not self.modified:
            return
        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False) # indent=3, 
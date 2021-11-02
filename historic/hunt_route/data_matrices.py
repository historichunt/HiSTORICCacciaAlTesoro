from dataclasses import dataclass
import polyline
import os
import json
from tqdm import tqdm
import numpy as np
from numpy.random import RandomState
from historic.hunt_route import api_ors
from historic.hunt_route import api_google
from historic.hunt_route.mgrs_utils import get_grid_id_set_from_route
from historic.hunt_route import hunt_params
from historic.hunt_route import plot_utils
from historic.config.params import ROOT_DIR

ROUTING_DIR = os.path.join(ROOT_DIR, 'routing_data')

@dataclass
class DataMatrices:  
    """This is the class responsible for keeping the 
    matrices with the directions (encoded polylines)

    Attributes:
        dataset_name (str): name of the dataset 
        points_name_coordinate (dict): dictionary mapping points names (str) to long,lat coordinates            
        json_file (str): the auto-coded file `data/<dataset_name>.json` contianing all the data
        matrix (dict): profile (str) -> polylines_matrix (list(list(str))) where polylines are stored 
    """

    def __init__(self, dataset_name, api, points_name_coordinate=None):
        self.dataset_name = dataset_name
        self.api = api
        self.__check_params()        
        self.modified = False
        self.json_file = os.path.join(ROUTING_DIR, f'{self.dataset_name}_DM_{self.api.API_NAME}.json') 
        if points_name_coordinate is None:
            assert os.path.exists(self.json_file), \
                f'File {self.json_file} does not exist, so you should pass points_name_coordinate in args'
            self.data = json.load(open(self.json_file))
            self.coordinates = self.data['coordinates'] 
            self.point_names = self.data['point_names'] 
            self.dst_matrices = self.data['dst_matrices'] # profile -> metric -> dst_matrix
            self.poly_matrices = self.data['poly_matrices']   # profile -> poly_matrix
            self.grid_matrices = self.data.get('grid_matrices', None) # profile -> grid_matrix

        else:
            self.point_names = list(points_name_coordinate.keys())
            self.coordinates = list(points_name_coordinate.values())
            self.__build_dst_matrices() # setting modified to true
            self.poly_matrices = {
                profile: self.__get_empty_matrix(fill_value='')
                for profile in self.api.PROFILES
            }
            self.grid_matrices = {
                profile: self.__get_empty_matrix(fill_value=None)
                for profile in self.api.PROFILES
            }                            
            self.grid_matrices_list = {
                profile: self.__get_empty_matrix(fill_value=None)
                for profile in self.api.PROFILES
            }                            
                        
            self.data = {
                'coordinates': self.coordinates,
                'point_names': self.point_names,
                'dst_matrices': self.dst_matrices,
                'poly_matrices': self.poly_matrices,
                'grid_matrices': self.grid_matrices_list
            }
            self.save_data()

        self.num_points = len(self.point_names)
        self.__build_direction_matrices()

    def __check_params(self):
        assert self.api in [api_google, api_ors], \
            f"api param ({self.api}) must be 'api_google' or 'api_ors'"        

    def __get_empty_matrix(self, fill_value):
        return [ 
            [fill_value] * self.num_points 
            for _ in range(self.num_points)
        ]

    def __build_dst_matrices(self):
        self.dst_matrices = {
            profile: {
                metric: {}
                for metric in hunt_params.METRICS
            }
            for profile in self.api.PROFILES                        
        }
        for profile in self.api.PROFILES: # foot, cycling
            if self.api == api_ors:
                distances_matrix, durations_matrix = \
                    api_ors.build_matrices(self.coordinates, profile)                
            else:
                # GOOGLE (need to give coordinates in lat long order)
                coordinates_lat_long = np.flip(self.coordinates, axis=1).tolist()
                distances_matrix, durations_matrix = \
                    api_google.get_distance_matrix(coordinates_lat_long, profile)
            self.dst_matrices[profile][hunt_params.METRIC_DURATION] = durations_matrix
            self.dst_matrices[profile][hunt_params.METRIC_DISTANCE] = distances_matrix
            
        self.modified = True

    def __build_direction_matrices(self):
        save_every = 1 if self.api == api_ors else 100

        # init coord matrices
        self.coord_matrices = {
            profile: self.__get_empty_matrix(fill_value=None)
            for profile in self.api.PROFILES
        }    

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
            json.dump(self.data, f, indent=3, ensure_ascii=False)
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import mgrs
from collections import Counter

# see https://www.maptools.com/tutorials/mgrs/quick_guide

# 1m      (precision 5) - default
# 10m     (precision 4)
# 100m    (precision 3)
# 1,000m  (precision 2)
# 10,000m (precision 1)

MGRS_PRECISION = 4

mgrs_object = mgrs.MGRS()

def get_mgrs_id(lat, lon):
    mgrs_id = mgrs_object.toMGRS(lat, lon, MGRSPrecision=MGRS_PRECISION)
    return mgrs_id

def get_mgrs_id_coordinates(mgrs_id):
    prefix = mgrs_id[:5]
    numeric_part = mgrs_id[5:]
    split_point = int(len(numeric_part)/2)
    x_plus = str(int(numeric_part[:split_point]) + 1).zfill(split_point)
    y_plus = str(int(numeric_part[split_point:]) + 1).zfill(split_point)
    next_grid_id = f'{prefix}{x_plus}{y_plus}'
    lat_min, lon_min = mgrs_object.toLatLon(mgrs_id)
    lat_max, lon_max = mgrs_object.toLatLon(next_grid_id)
    bottom_left = (lon_min, lat_min)
    # top_right = (lat_max, lon_max)
    width = lon_max - lon_min
    height = lat_max - lat_min
    return bottom_left, width, height

def interpolate(seg, num_interp_points):
    (x1,y1), (x2,y2) = seg
    points = []
    if x1==x2:
        for y in np.linspace(y1,y2, num_interp_points):
            points.append((x1,y))
    else:
        m = (y2-y1)/(x2-x1)    
        for x in np.linspace(x1,x2, num_interp_points):
            y = m * (x - x1) + y1
            points.append((x,y))
    return points

def get_grid_id_set_from_route(route_points, num_interp_points=100):
    from historic.hunt_route.locations_utils import convert_path_to_segments
    segments_route1 = convert_path_to_segments(route_points)
    route_grid_set = set()
    for seg in segments_route1:
        points = interpolate(seg, num_interp_points)
        grid_points = [get_mgrs_id(lonlat[1], lonlat[0]) for lonlat in points]
        route_grid_set.update(grid_points)
    return route_grid_set

def add_grid_to_plot(ax, grid_counter):
    for grid_id, count in grid_counter.items():
        bottom_left, width, height = get_mgrs_id_coordinates(grid_id)
        c = 'green' if count==1 else 'red'
        rect = patches.Rectangle(bottom_left, width, height, linewidth=1, edgecolor='none', facecolor=c)
        ax.add_patch(rect)


def test_route_overlap():
    from historic.hunt_route.data_matrices import DataMatrices
    from historic.hunt_route import api_google
    from historic.hunt_route.locations_utils import plot_route_points

    dm = DataMatrices(
        dataset_name = 'Trento',
        api = api_google
    )   
    p1 = dm.coordinates[0]
    p2 = dm.coordinates[1]
    route1_points = dm.get_direction_path_coordinates(p1, p2, profile=api_google.PROFILE_FOOT_WALKING)
    route2_points = dm.get_direction_path_coordinates(p2, p1, profile=api_google.PROFILE_FOOT_WALKING)
    all_points = np.concatenate([route1_points, route2_points])
    # plot_route_points(route1_points, markersize=2)

    route1_grid_set = get_grid_id_set_from_route(route1_points)
    route2_grid_set = get_grid_id_set_from_route(route2_points)

    grid_counter = Counter()
    for s in [route1_grid_set, route2_grid_set]:
        grid_counter.update(s)
    
    plot_route_points(all_points, grid_counter, markersize=1, annotate_numbers=False)


def test_mgrs():
    # a readaptation of https://dida.do/blog/understanding-mgrs-coordinates
    import pyproj

    mgrs_id = mgrs_object.toMGRS(12.40, 53.51, MGRSPrecision=4) # 10m precision
    # returns '39PYP72907206'    

    prefix = mgrs_id[:5]
    numeric_part = mgrs_id[5:]
    split_point = int(len(numeric_part)/2)
    x,y = int(numeric_part[:split_point]), int(numeric_part[split_point:])

    next_grid_id = f'{prefix}{x+1}{y+1}'

    geod = pyproj.Geod(ellps='WGS84')

    lat_min, lon_min = mgrs_object.toLatLon(mgrs_id)
    lat_max, lon_max = mgrs_object.toLatLon(next_grid_id)

    geod.line_length([lon_min, lon_min], [lat_min, lat_max])

    delta_x = geod.line_length([lon_min, lon_min], [lat_min, lat_max]) # 9.900266971657954
    delta_y = geod.line_length([lon_min, lon_max], [lat_min, lat_min]) # 10.088424614158024


if __name__ == "__main__":
    # test_mgrs()
    test_route_overlap()
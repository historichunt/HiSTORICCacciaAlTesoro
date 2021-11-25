import numpy as np
from numpy.random import RandomState
import matplotlib.pyplot as plt
from geopy import distance
from math import pi, atan2
from collections import Counter
from historic.hunt_route import mgrs_utils


TWO_PI = 2 * pi

def is_convex_polygon(polygon):
    """Return True if the polynomial defined by the sequence of 2D
    points is 'strictly convex': points are valid, side lengths non-
    zero, interior angles are strictly between zero and a straight
    angle, and the polygon does not intersect itself.

    NOTES:  1.  Algorithm: the signed changes of the direction angles
                from one side to the next side must be all positive or
                all negative, and their sum must equal plus-or-minus
                one full turn (2 pi radians). Also check for too few,
                invalid, or repeated points.
            2.  No check is explicitly done for zero internal angles
                (180 degree direction-change angle) as this is covered
                in other ways, including the `n < 3` check.
    """
    try:  # needed for any bad points or direction changes
        # Check for too few points
        if len(polygon) < 3:
            return False
        # Get starting information
        old_x, old_y = polygon[-2]
        new_x, new_y = polygon[-1]
        new_direction = atan2(new_y - old_y, new_x - old_x)
        angle_sum = 0.0
        # Check each point (the side ending there, its angle) and accum. angles
        for ndx, newpoint in enumerate(polygon):
            # Update point coordinates and side directions, check side length
            old_x, old_y, old_direction = new_x, new_y, new_direction
            new_x, new_y = newpoint
            new_direction = atan2(new_y - old_y, new_x - old_x)
            if old_x == new_x and old_y == new_y:
                return False  # repeated consecutive points
            # Calculate & check the normalized direction-change angle
            angle = new_direction - old_direction
            if angle <= -pi:
                angle += TWO_PI  # make it in half-open interval (-Pi, Pi]
            elif angle > pi:
                angle -= TWO_PI
            if ndx == 0:  # if first time through loop, initialize orientation
                if angle == 0.0:
                    return False
                orientation = 1.0 if angle > 0.0 else -1.0
            else:  # if other time through loop, check orientation is stable
                if orientation * angle <= 0.0:  # not both pos. or both neg.
                    return False
            # Accumulate the direction-change angle
            angle_sum += angle
        # Check that the total number of full turns is plus-or-minus 1
        return abs(round(angle_sum / TWO_PI)) == 1
    except (ArithmeticError, TypeError, ValueError):
        return False  # any exception means not a proper convex polygon

def convert_path_to_segments(path_coordinates):
    """Given an array of coordinates representing points (e.g., A, B, C, D)
    returns an array of segments for each subsequent point in the input array
    (e.g, [(A,B), (B,C), (C,D)] )

    Args:
        path_coordinates ([type]): [description]

    Returns:
        [type]: [description]
    """
    if not isinstance(path_coordinates, np.ndarray):
        path_coordinates = np.array(path_coordinates)
    path_coordinates_start = path_coordinates[:-1]
    path_coordinates_end = path_coordinates[1:]
    segments = np.stack([path_coordinates_start, path_coordinates_end], axis=1)
    return segments

def compute_grid_counter(dm, routed_idx, profile):
    grid_counter = Counter()
    for i in range(0, len(routed_idx)-1):
        grid_path = dm.get_direction_path_grid_set(routed_idx[i], routed_idx[i+1], profile)
        grid_counter.update(grid_path)
    return grid_counter

def compute_overlapping_path_segments(dm, route_points, profile):
    """[summary]

    Args:
        dm ([type]): [description]
        route_points ([type]): [description]
        profile ([type]): [description]
        extra_info (bool, optional): [description]. Defaults to False.

    Returns:
        [type]: [description]
    """
    route_segments = convert_path_to_segments(route_points)
    
    path_points = np.concatenate([
        dm.get_direction_path_coordinates(segment[0].tolist(), segment[1].tolist(), profile)
        for segment in route_segments
    ])
    path_segments = convert_path_to_segments(path_points) # shape: num_segments, 2, 2

    # sorting the two coordinates in each segment in lexicographic order (by x and y)
    # todo: check if there is a more efficient way (e.g., with np.lexsort)
    path_segments_sorted = [sorted(pair.tolist()) for pair in path_segments]

    unique_segments_sorted, segments_counts = \
        np.unique(path_segments_sorted, axis=0, return_counts=True)
    
    overlapping_dst = 0
    for segment, count in zip(unique_segments_sorted, segments_counts):
        if count > 1:
            segment = np.flip(segment, axis=1) # geopy distance expect lat, long
            dst = distance.distance(segment[0], segment[1]).m
            overlapping_dst += dst * (count-1) # count only repeted path
    
    return overlapping_dst, path_points, unique_segments_sorted, segments_counts

def plot_route_points(route_points, grid_counter=None, markersize=15, annotate_numbers=True):    
    segments = convert_path_to_segments(route_points)
    circular = np.all(route_points[0] == route_points[-1])
    _, ax = plt.subplots()    
    for seg in segments:
        ax.plot(seg[:,0], seg[:,1], 'o-',  markersize=markersize) # fillstyle='none'
    points = route_points[:-1] if circular else route_points
    if annotate_numbers:
        for n,p in enumerate(points,1):        
            ax.annotate(str(n), (p[0], p[1]), ha='center', va='center')        
    if grid_counter is not None:
        mgrs_utils.add_grid_to_plot(ax, grid_counter)

    plt.show()


def plot_route_graph(points, route_points, path_points, unique_segments, segments_counts,
    grid_counter=None, print_dots=False, print_path_numbers=False):
    """[summary]

    Args:
        points ([type]): [description]
        route_points ([type]): [description]
        path_points ([type]): [description]
        unique_segments:
        segments_counts:
        colors ([type]): [description]
        xlim ([type]): [description]
        ylim ([type]): [description]
        print_dots (bool): 
        print_path_numbers (bool): 
    """
    num_points = len(points)
    route_size = len(route_points)
    x, y = points[:,0], points[:,1]

    rs = RandomState(123)
    colors = rs.rand(num_points)   
    xlim = [np.min(x)-0.001, np.max(x)+0.001]
    ylim = [np.min(y)-0.001, np.max(y)+0.001]

    selected_x, selected_y = route_points[:,0], route_points[:,1]

    _, ax = plt.subplots()    
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect('equal')
    
    ax.scatter(x, y, s=200, c=colors, alpha=0.5)        
    
    # ax.plot(selected_x, selected_y, c='orange')
    # ax.plot(path_points[:,0], path_points[:,1], '-', c='red')

    if grid_counter is not None:
        mgrs_utils.add_grid_to_plot(ax, grid_counter)

    for segment, count in zip(unique_segments, segments_counts):
        color = 'green' if count == 1 else 'red'
        ax.plot(segment[:,0], segment[:,1], '-', c=color)

    # unique coordinates in path
    if print_dots:
        rout_path_unique, counts = np.unique(path_points, axis=0, return_counts=True)
        unique_p = np.array([p for p,c in zip(rout_path_unique, counts) if c==1])
        repeated_p = np.array([p for p,c in zip(rout_path_unique, counts) if c>1])
        ax.plot(unique_p[:,0], unique_p[:,1], '.', c='green')
        ax.plot(repeated_p[:,0], repeated_p[:,1], '.', c='red')

        # print path step numbers
        if print_path_numbers:
            for p in rout_path_unique:
                idx = np.where(np.all(path_points==p,axis=1))[0]
                nums = ', '.join([str(i+1) for i in idx])
                ax.annotate(nums, (p[0], p[1]), ha='center', va='center')        
    
    # if cyclic route, do not plot last number
    skip_last_number = np.all(route_points[0] == route_points[-1])
    last_number = route_size-1 if skip_last_number else route_size

    for i in range(last_number):
        ax.annotate(str(i+1), (selected_x[i], selected_y[i]), ha='center', va='center')

    plt.title('Route Solution')
    plt.show()

def test_convert_path_to_segments():
    coordinates = [
        [11.1022361, 46.060613], 
        [11.1188586, 46.0627946], 
        [11.13785, 46.05821], 
        [11.1061717, 46.0700165], 
        [11.107944444, 46.061277777]
    ]
    a = convert_path_to_segments(coordinates)
    print(a.tolist())

def test_convexity():
    polygon = [
        [0,0],
        [1,0],
        [1,1],
        [0,1],
        [0,0]
    ]
    print(is_convex_polygon(polygon))

if __name__ == "__main__":
    # test_convert_path_to_segments()
    test_convexity()

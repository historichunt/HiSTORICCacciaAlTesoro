import matplotlib.pyplot as plt
import numpy as np

def plot_points(x,y, colors, xlim, ylim):
    num_points = len(x)
    _, ax = plt.subplots()
    
    ax.scatter(x, y, s=200, c=colors, alpha=0.5)     
    ax.set_title('Initial Configuration')
    ax.set_aspect('equal')   
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    for i in range(num_points):
        ax.annotate(str(i+1), (x[i], y[i]), ha='center', va='center')        
    plt.show()

def plot_distance_matrix(dst_matrix):
    cmap_inv = plt.cm.get_cmap('viridis_r')        
    plt.title('Pairwise distance matrix')
    plt.imshow(dst_matrix, cmap=cmap_inv)       
    plt.colorbar()
    plt.show()

def plot_distance_distribution(dst_matrix):
    num_points = len(dst_matrix)
    all_dst = dst_matrix[np.triu_indices(num_points, k=1)] # elements in the upper triang (no diagonal)
    assert len(all_dst) == num_points*(num_points-1)/2
    _, ax = plt.subplots()
    ax.set_title('Pairwise distance distribution')
    ax.hist(all_dst, bins=50)
    plt.show()

def plot_route_graph(path_coordinates, print_dots=False, print_path_numbers=False):
    """[summary]

    Args:
        polylines ([type]): [description]
        print_dots (bool): 
        print_path_numbers (bool): 
    """
    import matplotlib.cm as cm
    import itertools

    _, ax = plt.subplots()    

    # colors = cm.rainbow(np.linspace(0, 1, len(polylines)))
    colors = itertools.cycle(["r", "b", "g"])
    markers = itertools.cycle(["*", "+"])
    for coordinates in path_coordinates:        
        x = coordinates[:,0]
        y = coordinates[:,1]
        ax.plot(x, y, linestyle='-', marker=next(markers), color=next(colors))
        # ax.scatter(x, y, linestyle='-', marker='o', s=20, color=next(colors), alpha=0.5)

    # ax.set_xlim(xlim)
    # ax.set_ylim(ylim)
    ax.set_aspect('equal')
    
    
    plt.title('Route Solution')
    plt.show()
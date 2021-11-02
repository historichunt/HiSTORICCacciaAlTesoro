import os
import io

from PIL import Image
import requests
import numpy as np
import polyline
import urllib
from historic.config.settings import ENV_VARS

# for showing larger images 
import matplotlib as mpl
mpl.rcParams['figure.figsize'] = [12.0, 8.0]



MAPBOX_STYLE_ID = ENV_VARS.get('MAPBOX_STYLE_ID')
MAPBOX_USER_NAME = ENV_VARS.get('MAPBOX_USER_NAME')
MAPBOX_ACCESS_TOKEN = ENV_VARS.get('MAPBOX_ACCESS_TOKEN')

PATH_COLOR_REPEATED = 'c82d2d'
PATH_COLOR_UNIQUE = '006600'
STOP_PINS_COLOR = '6470C1'
OTHER_PINS_COLOR = '222222'
PADDING = 100

def show_image(img_content):
    import matplotlib.pyplot as plt
    img = Image.open(io.BytesIO(img_content), 'r') 
    plt.imshow(img)
    plt.show()    

def render_map_from_ors_json(json_data, all_coordinates=None,
    width=1200, height=800, path_width=4, path_color='c82d2d', 
    stop_pins_color='6470C1', other_pins_color='222222', padding=100):    
    """[summary]

    Args:
        json_data ([type]): [description]
        width (int, optional): [description]. Defaults to 600.
        height (int, optional): [description]. Defaults to 400.
        path_width (int, optional): [description]. Defaults to 4.
        path_color (str, optional): [description]. Defaults to 'c82d2d'.
        stop_pins_color (str, optional): [description]. Defaults to '6470C1'.
        other_pins_color (str, optional): [description]. Defaults to '222222'.
        padding (int, optional): [description]. Defaults to 10.
    """
    stop_coordinates = json_data['metadata']['query']['coordinates']
    bbox = json_data['routes'][0]['bbox']
    encoded_path = urllib.parse.quote(json_data['routes'][0]['geometry'], safe='')
    url = 'https://api.mapbox.com/styles/v1/mapbox/streets-v11/static'
    url += f'/path-{path_width}+{path_color}({encoded_path})'
    for n, c in enumerate(stop_coordinates,1):
        url += f',pin-l-{n}+{stop_pins_color}({c[0]},{c[1]})'
    if all_coordinates is not None:
        for n, c in enumerate(all_coordinates):
            if c in stop_coordinates:
                continue
            url += f',pin-s-{n}+{other_pins_color}({c[0]},{c[1]})'
    url += f'/[{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}]'
    url += f'/{width}x{height}'
    url += f'?padding={padding},{padding},{padding},{padding}'
    url += f'&access_token={MAPBOX_ACCESS_TOKEN}'
    r = requests.get(url)
    assert r.status_code == 200, r.content
    show_image(r.content)
    
def render_map_with_coordinates(coordinates, width=1200, height=800):    
    """[summary]

    Args:
        coordinates long,lat tuples
        width (int, optional): [description]. Defaults to 1200.
        height (int, optional): [description]. Defaults to 800.
        padding (int, optional): [description]. Defaults to 10.
    """
    # bbox = json_data['routes'][0]['bbox']    
    long_min = np.min(coordinates[:,0])
    long_max = np.max(coordinates[:,0])
    lat_min = np.min(coordinates[:,1])
    lat_max = np.max(coordinates[:,1])

    # encoded_path = urllib.parse.quote(json_data['routes'][0]['geometry'], safe='')
    url = 'https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/'
    url_overlays = []
        
    for n, c in enumerate(coordinates,1):
        url_overlays.append(f'pin-l-{n}+{STOP_PINS_COLOR}({c[0]},{c[1]})')

    url += ','.join(url_overlays)
    url += f'/[{long_min},{lat_min},{long_max},{lat_max}]'
    url += f'/{width}x{height}'
    url += f'?padding={PADDING},{PADDING},{PADDING},{PADDING}'
    url += f'&access_token={MAPBOX_ACCESS_TOKEN}'
    assert len(url) < 8192, 'URL TOO LONG'
    r = requests.get(url)
    assert r.status_code == 200, r.content
    show_image(r.content)

def render_map(route_points, path_points, unique_segments, segments_counts, all_coordinates,
    width=1200, height=800, path_width=4, show=True):    
    """[summary]

    Args:
        route_points long,lat tuples
        path_points
        unique_segments
        segments_counts
        width (int, optional): [description]. Defaults to 1200.
        height (int, optional): [description]. Defaults to 800.
        path_width (int, optional): [description]. Defaults to 4.        
    """

    num_route_points = len(route_points)
    # bbox = json_data['routes'][0]['bbox']    
    long_min = np.min(route_points[:,0])
    long_max = np.max(route_points[:,0])
    lat_min = np.min(route_points[:,1])
    lat_max = np.max(route_points[:,1])

    # encoded_path = urllib.parse.quote(json_data['routes'][0]['geometry'], safe='')
    url = 'https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/'
    url_overlays = []
        
    tuple_seg = lambda seg: tuple(tuple(t) for t in seg)

    # route segment
    unique_segments_count = {
        tuple_seg(s):c 
        for s,c in zip(unique_segments, segments_counts)
    }

    prev_path_point = path_points[0]
    seg_stretch = [prev_path_point]
    stretch_count = None

    def add_path_overlay():
        path_color = PATH_COLOR_UNIQUE if stretch_count==1 else PATH_COLOR_REPEATED
        encoded_path = urllib.parse.quote(polyline.encode(seg_stretch,geojson=True), safe='')
        url_overlays.append(f'path-{path_width}+{path_color}({encoded_path})')

    for current_path_point in path_points[1:]:
        segment = tuple(sorted(tuple_seg([prev_path_point, current_path_point])))
        seg_count = unique_segments_count[segment]
        if stretch_count is None:
            # only for first time in first stretch
            stretch_count = seg_count
        if seg_count == stretch_count:
            seg_stretch.append(current_path_point)
        else:
            add_path_overlay()
            stretch_count = seg_count
            seg_stretch = [prev_path_point, current_path_point]
        prev_path_point = current_path_point
    if stretch_count is not None:
        add_path_overlay()

    # all points (small)
    if all_coordinates is not None:
        for n, c in enumerate(all_coordinates):
            if c in route_points:
                continue
            url_overlays.append(f'pin-s-{n}+{OTHER_PINS_COLOR}({c[0]},{c[1]})')
    
    # route stops (big) - skip last if cyclic route
    skip_last = np.all(route_points[0]==route_points[-1])
    for n, c in enumerate(route_points,1):
        if skip_last and n==num_route_points:
            break
        url_overlays.append(f'pin-l-{n}+{STOP_PINS_COLOR}({c[0]},{c[1]})')

    url += ','.join(url_overlays)
    url += f'/[{long_min},{lat_min},{long_max},{lat_max}]'
    url += f'/{width}x{height}'
    url += f'?padding={PADDING},{PADDING},{PADDING},{PADDING}'
    url += f'&access_token={MAPBOX_ACCESS_TOKEN}'
    assert len(url) < 8192, 'URL TOO LONG'
    r = requests.get(url)
    assert r.status_code == 200, r.content
    if show:
        show_image(r.content)
    return r.content

def test_render_map():    
    from historic.hunt_route.routing_wikidata import read_wikidata_locations
    from historic.hunt_route import api_ors
    coordinates = [
        [11.1022361, 46.060613], 
        [11.1188586, 46.0627946], 
        [11.13785, 46.05821], 
        [11.1061717, 46.0700165], 
        [11.107944444, 46.061277777]
    ]
    wikidata_locations = read_wikidata_locations()
    all_coordinates = list([list(t) for t in wikidata_locations.values()])
    json_data = api_ors.run_directions_api(coordinates, profile = 'cycling-regular', format='json')
    render_map_from_ors_json(json_data, all_coordinates)

if __name__ == "__main__":
    # test_map()
    test_render_map()
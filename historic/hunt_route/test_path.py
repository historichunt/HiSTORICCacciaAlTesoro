from historic.hunt_route import plot_utils
import numpy as np
import polyline

def test_snapped_road():
    original_poly = 'o`exGmiybAsB`AQmAUgAMoAAc@Ju@b@iAj@}@HAHGDKA[FeA|@wFDBNGDG@MEUCECCSg@y@aBCQA]NeAR_A@o@cAyFAs@D[`@AZBC[IsAYoGm@oCCI}@eD_AeCWg@gAgAfAm@`@KN['
    snapped_poly =  'o`exGmiybAsB`AQmAUgAMoAAc@Ju@b@iAj@}@HAHGDKA[FeA|@wFDBNGDG@MEUCECASi@y@aBCQA]NeAR_A@o@cAyFAs@D[`@AZBC[IsAYoGm@oCCI}@eD_AeCWg@gAgAfAm@`@MNY'
    path_coordinates = [
        np.array(polyline.decode(original_poly, geojson=False)),
        np.array(polyline.decode(snapped_poly, geojson=False)),
    ]
    plot_utils.plot_route_graph(path_coordinates)

def test_road_inverse():
    from historic.hunt_route import routing_trento
    from historic.hunt_route import api_google
    trento_dm = routing_trento.get_trento_dm('GOOGLE')
    
    i=1
    j=5
    c1 = trento_dm.coordinates[i]
    c2 = trento_dm.coordinates[j]
    forward_path = trento_dm.get_direction_path_coordinates(c1, c2, api_google.PROFILE_FOOT_WALKING)
    back_path = trento_dm.get_direction_path_coordinates(c2, c1, api_google.PROFILE_FOOT_WALKING)
    path_coordinates = [
        np.array(forward_path),
        np.array(back_path),
    ]
    plot_utils.plot_route_graph(path_coordinates)


if __name__ == "__main__":
    # test_snapped_road()
    test_road_inverse()
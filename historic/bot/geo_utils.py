from geopy.distance import distance

#point1 = (41.49008, -71.312796)
#point2 = (41.499498, -81.695391)
def distance_meters(point1, point2):
    return int(distance(point1, point2).meters)

def distance_km(point1, point2):
    return int(distance(point1, point2).kilometers)


# lat, lon, poly is a list of lat lon coords
def point_inside_polygon(x,y,poly):
    n = len(poly)
    inside =False
    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y
    return inside

def test_distance():
    point1 = (41.49008, -71.312796)
    point2 = (41.499498, -81.695391)
    d = distance_meters(point1, point2)
    assert d == 866455

if __name__ == "__main__":
    test_distance()
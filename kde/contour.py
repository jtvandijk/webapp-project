#grid reconstruction
import numpy as np
from shapely.geometry import Point,Polygon,LineString,MultiPolygon

def to_concave_points(df, coord):

    groups = np.unique(df['group'].tolist())
    contours = []

    def create_lookup(coord):
        record = dict()
        sorted_data = sorted(coord)
        for x, y in sorted_data:
            if x in record.keys():
                record[x][y] = None
            else:
                record[x] = dict()
                record[x][y] = None

        return record

    for g in groups:
        boundary = []
        gdf = df.loc[df['group'] == g]

        X = np.unique(gdf['x'].tolist())
        coordx = [[int(x[0]), int(x[1])] for x in (list(zip(gdf.x, gdf.y)))]
        Xlook = create_lookup(coordx)

        for x in X:
            if x in Xlook.keys():
                min_y = min(Xlook[x].keys())
                max_y = max(Xlook[x].keys())
                if not min_y == max_y:
                    boundary.append((int(x), min_y))

        for x in np.flipud(X):
            if x in Xlook.keys():
                max_y = max(Xlook[x].keys())
                min_y = min(Xlook[x].keys())
                if not max_y == min_y:
                    boundary.append((int(x), max_y))
        contours.append(boundary)
    return contours

def points_to_polygon(plist):
    points = [Point(p) for p in plist]
    polcoords = [p.coords[:][0] for p in points]
    line = LineString(polcoords)
    contour = Polygon(line).buffer(100)
    return contour

def polygon_to_multipolygon(pols):
    multi = []
    for p in pols:
        multi.append(points_to_polygon(p))
    full_cont = MultiPolygon(multi)
    return full_cont

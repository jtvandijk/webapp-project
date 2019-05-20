#django
from django.conf import settings
from .models import *
from .contour import to_concave_points

#libraries
from shapely.geometry import Polygon
from sklearn.cluster import dbscan
from fiona.crs import from_epsg
import pandas as pd
import geopandas as gpd
import sys,os

#grid -- keep in memory
xy = kdegridxy.objects.values('gid','x','y','bool')
gridc = pd.DataFrame.from_records(xy)
gridc = gridc[(gridc['bool'] == 1)]

#uk -- keep in memory
path = os.path.join(settings.STATIC_ROOT,'js/uk.geojson')
uk = gpd.read_file(path).to_crs(epsg=27700)
uk.drop(uk.columns[[0,1,2,3,4]],axis=1,inplace=True)

#param
level = 25

#class
def str_to_class(classname):
    return getattr(sys.modules[__name__],classname)

#kde
def calculate_kde(clean_sur,years):
    contour_collection=[]
    for year in years:

        #get year data
        kdev = str_to_class("kdeclus"+(str(year)))
        year_data = str(kdev.objects.filter(surname=clean_sur).values('kde'))

        #prepare data
        idx = [int(x) for x in year_data.split(';')[0][21:].split(',')]
        kdx = [int(x) for x in year_data.split(';')[1][:-5].split(',')]

        #pd dataframe
        kdf = pd.DataFrame({'gid':idx,'val':kdx})
        kdf = kdf[(kdf['val'] <= level)]

        #add values to grid
        kde = pd.merge(gridc,kdf,on='gid',how='inner')
        coord = [[int(x[1]),int(x[0])] for x in (list(zip(kde.x,kde.y)))]
        cs,lbls = dbscan(coord,eps=2000)
        kde = kde.copy()
        kde['group'] = lbls
        kde = kde[(kde['group'] >= 0)]

        #group to concave points
        contourp = to_concave_points(kde,coord)

        #clip
        contours = gpd.GeoSeries([Polygon(contour) for contour in contourp if len(contour) >= 3])
        contours = gpd.GeoDataFrame({'geometry': contours})
        contours.crs = from_epsg(27700)
        clp_prj = gpd.overlay(uk,contours,how='intersection')

        #smooth and project
        clp_prj['geometry'] = clp_prj.geometry.buffer(10000,join_style=1).buffer(-10000,join_style=1)
        clp_prj['geometry'] = clp_prj['geometry'].to_crs(epsg=4326)

        #to json
        contourprj = clp_prj.to_json()

        #add to collection
        data = []
        data.append(year)
        data.append(contourprj)
        contour_collection.append(data)

    #return
    return(contour_collection)

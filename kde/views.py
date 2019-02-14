#JTVD - 2018

#libraries
from django.contrib.gis.geos import fromstr
from django.http import HttpResponse
from django.conf import settings
from .models import KdeLookup, KdeGridxy, KdevClus1851, KdevClus1861, KdevClus1881, KdevClus1891, KdevClus1901, KdevClus1911, KdevClus1997, KdevClus1998, KdevClus1999, KdevClus2000, KdevClus2001, KdevClus2002, KdevClus2003, KdevClus2004, KdevClus2005, KdevClus2006, KdevClus2007, KdevClus2008, KdevClus2009, KdevClus2010, KdevClus2011, KdevClus2012, KdevClus2013, KdevClus2014, KdevClus2015, KdevClus2016, LsoaTopnames, GeoTopnames, RenderedNames
from .contour import to_concave_points
from pyproj import Proj, transform
from sklearn.cluster import dbscan
from shapely.geometry import Polygon,MultiPolygon
from fiona.crs import from_epsg
import json
import pandas as pd
import geopandas as gpd
import sys
import re
import ast
import os

#reconstruct grid -- keep in memory
xy = KdeGridxy.objects.values('gid','x','y','bool')
gridc = pd.DataFrame.from_records(xy)
gridc = gridc[(gridc['bool'] == 1)]

#uk outline -- keep in memory
path = os.path.join(settings.STATIC_ROOT,'js/uk.geojson')
uk = gpd.read_file(path).to_crs(epsg=27700)
uk.drop(uk.columns[[0,1,2,3,4]],axis=1,inplace=True)

#param
level = 50

#class
def str_to_class(classname):
    return getattr(sys.modules[__name__],classname)

#search view
def search(request):

    #query db
    search_sur = (request.POST['q']).lower()
    clean_sur = re.sub(r'[\W^0-9^\s]+','',search_sur)
    db_sur = KdeLookup.objects.filter(surname=clean_sur)
    ren_sur = RenderedNames.objects.filter(surname=clean_sur)

    #empty search
    if len(search_sur) == 0:
        search = {
                 'source':'empty',
                 }

        #return empty
        return HttpResponse(json.dumps(search),content_type="application/json")

    #if not in db
    elif not db_sur:
        search = {
                  'source':'none',
                  'surname': search_sur,
                 }

        #return none
        return HttpResponse(json.dumps(search),content_type="application/json")

    #if pre-rendered
    # elif ren_sur:
    #
    #     #pre-rendered data
    #     data = RenderedNames.objects.filter(surname=clean_sur).values()[0]
    #     count = data.get('count')
    #     RenderedNames.objects.filter(surname=clean_sur).update(count=count+1)
    #
    #     #combine data
    #     search = {
    #             'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
    #             'source': data.get('source'),
    #             'years': ast.literal_eval(data.get('years')),
    #             'hr_freq': ast.literal_eval(data.get('hr_freq')),
    #             'cr_freq': ast.literal_eval(data.get('cr_freq')),
    #             'contours': ast.literal_eval(data.get('contours'))
    #             }
    #
    #     #return data
    #     return HttpResponse(json.dumps(search),content_type="application/json")

    #calculate
    else:

        #contours
        contours = []

        #surname attributes
        data = KdeLookup.objects.filter(surname=clean_sur).values()[0]
        source = 'found'
        available = {key: value for key, value in data.items() if value != None}
        years = [str(year[4:]) for year in list(available.keys()) if year.startswith('freq')]

        #frequencies
        freq_chart = {key: value for key, value in data.items() if key.startswith('freq')}
        freqs = [str(value) for value in freq_chart.values()]
        freqs = [0 if x=='None' else int(x) for x in freqs]
        hr_freq = freqs[:6]
        cr_freq = freqs[6:]

        #get kdes
        for year in years:

            #get year data
            kdev = str_to_class("KdevClus" + (str(year)))
            year_data = str(kdev.objects.filter(surname=clean_sur).values('kde'))

            #prepare data
            val = [int(x) for x in year_data[21:-5].split(',')]
            spx = int((len(val)/2)+.5)
            idx = val[:spx]
            kdx = val[spx:]

            #temp data fix // population weighted kde
            #idx[spx-1] = int(str(val[spx-1])[:-1])
            #kdx.insert(0,1)

            #pd dataframe
            kdf = pd.DataFrame({'gid':idx,'val':kdx})
            kdf = kdf[(kdf['val'] >= level)]

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
            contours = gpd.GeoSeries([Polygon(contour) for contour in contourp])
            contours = gpd.GeoDataFrame({'geometry': contours})
            contours.crs = from_epsg(27700)

            clp_prj = gpd.overlay(uk,contours,how='intersection')
            clp_prj['geometry'] = clp_prj['geometry'].to_crs(epsg=4326)

            print(clp_prj)

            #contour data
            contourprj = []
            for contour in contourp:

                #clip
                polygon = gpd.GeoDataFrame()
                polygon.loc[0,'geometry'] = Polygon(contour)
                polygon.crs = from_epsg(27700)
                clp_prj = gpd.overlay(uk,polygon,how='intersection')

                #reproject
                clp_prj['geometry'] = clp_prj['geometry'].to_crs(epsg=4326)

            #add
            data = []
            data.append(year)
            data.append(contourprj)
            contours.append(data)

        #combine data
        search = {
                'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
                'source': source,
                'years': years,
                'hr_freq': hr_freq,
                'cr_freq': cr_freq,
                'contours': contours
                }

        #save to db
        if not ren_sur:
            rendered = RenderedNames(clean_sur,source,years,hr_freq,cr_freq,contours,1)
            rendered.save()

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

def location(request):

    #user location
    lon = request.POST['longitude']
    lat = request.POST['latitude']

    #reproject
    inProj = Proj(init='epsg:4326')
    outProj = Proj(init='epsg:27700')
    locprj = list(transform(inProj,outProj,lon,lat))
    pnt = fromstr('POINT(' +str(locprj[0]) + ' ' +str(locprj[1]) + ')',srid=27700)

    #spatial query for topnames
    lsoa = LsoaTopnames.objects.filter(shape__contains=pnt)

    #if spatial query successful
    if lsoa:
        div = {key: value for key, value in lsoa.values()[0].items()}
        tnlist = [str(x).title() for x in div['topnames'][1:-1].split(',')]
        unique = div['unique_n']
        total = div['total_n']
        alpha = div['diversity_a']

        #combine data
        loclist = {'topnames': tnlist,
                   'unique': unique,
                   'total': total,
                   'alpha': alpha
                   }

    #if spatial query unsuccesful
    else:
        loclist = None

    #return data
    return HttpResponse(json.dumps(loclist),content_type='application/json')

def geography(request):

    #selected geography
    geo = request.POST['geography']

    #query for topnames
    sel_geo = GeoTopnames.objects.filter(agg_geo=geo)
    div = {key: value for key, value in sel_geo.values()[0].items()}
    tnlist = [str(x).title() for x in div['topnames'][1:-1].split(',')]
    unique = div['unique_n']
    total = div['total_n']
    alpha = div['diversity_a']

    #combine data
    loclist = {'topnames': tnlist,
               'unique': unique,
               'total': total,
               'alpha': alpha
               }

    #return data
    return HttpResponse(json.dumps(loclist),content_type='application/json')

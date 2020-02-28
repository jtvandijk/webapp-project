#django
from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from .statistics import *

#libraries
from shapely import wkt
from fiona.crs import from_epsg
import pandas as pd
import geopandas as gpd
import json,re,os
from itertools import chain

#index view
def index(request):

    #return
    return render(request,'index.html')

#search view
def search(request):

    #query
    name_search = (request.POST['surname']).lower()
    name_clean = re.sub(r'[\W^0-9^\s]+','',name_search)
    name_meta = names_kde.objects.filter(surname=name_clean)

    #search: emtpy
    if len(name_search) == 0:
        search = {'surname':'empty'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #search: not found
    elif not name_meta:
        search = {'surname':'none'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #search found
    elif name_meta:

        #available years
        years = [1851,1861,1881,1891,1901,1911,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016]
        avbls = name_meta.values('year','freq')
        freqs = [0 for f in range(0,26)]
        for a in avbls:
            idx = years.index(a.get('year'))
            freqs[idx] = a.get('freq')
        years = [y.get('year') for y in avbls]
        
        #statistics
        stats = surname_statistics(name_clean)

        #update count
        #name_meta.objects.filter(surname=name_clean).update(count=count+1)

        #combine data
        search = {'surname': name_clean.title(),'freqs': freqs, 'years': years, 'stats': stats,}

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

#location view
def location(request):

    #query
    sel = request.POST['id']
    all = request.POST.getlist('all[]')
    sr = request.POST['sr']

    #geom
    if sr == 'hr':
        admin1 = conpar51.objects.filter(conparid__in=all).values('conparid','centroid')
        admin2 = conpar01.objects.filter(conparid__in=all).values('conparid','centroid')
        admin = list(chain(admin1,admin2))
    elif sr == 'cr':
        admin = census_msoa.objects.filter(msoa11nm__in=all).values('msoa11nm','centroid')

    #prepare all
    allgeom = []
    for aa in admin:

        #name
        if sr == 'hr':
            if lookup_parish.objects.filter(conparid=aa['conparid']).values():
                name = lookup_parish.objects.filter(conparid=aa['conparid']).values()[0]
                geom = gpd.GeoSeries(wkt.loads(aa['centroid'].wkt))
                geom = gpd.GeoDataFrame({'id': name['conparid'],'geometry': geom,'parish': name['parish'],'regcnty': name['regcnty'],'cnty': name['country']})
        elif sr == 'cr':
                name = lookup_oa.objects.filter(msoa11nm=aa['msoa11nm']).values('ladnm','msoa11cd','msoa11nm')[0]
                geom = gpd.GeoSeries(wkt.loads(aa['centroid'].wkt))
                geom = gpd.GeoDataFrame({'id': name['msoa11nm'],'geometry': geom,'ladnm': name['ladnm'],'msoa11cd': name['msoa11cd'],'msoa11nm': name['msoa11nm']})

        #prepare
        geom.crs = from_epsg(27700)
        geom['geometry'] = geom['geometry'].to_crs(epsg=4326)
        allgeom.append(geom)

    #concat
    location = {'sel': sel,'all': pd.concat(allgeom).to_json(),'sr':  sr}

    #return
    return HttpResponse(json.dumps(location),content_type="application/json")

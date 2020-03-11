#libraries
from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from .statistics import *
from re import sub
import json

from shapely import wkt
from fiona.crs import from_epsg
import pandas as pd
import geopandas as gpd
from itertools import chain

#index views
def index(request):

    #return
    return render(request,'index.html')

#search view
def search(request):

    #query
    name_input = (request.POST['surname']).lower()
    name_search = sub(r'[\W^0-9^\s]+','',name_input)
    name_found = names_kde.objects.filter(surname=name_search)

    #search: emtpy
    if len(name_input) == 0:
        search = {'surname':'empty'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #search: not found
    elif not name_found:
        search = {'surname':'none'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #search: found
    elif name_found:

        #surname data
        search_data = names_kde.objects.filter(surname=name_search).order_by('year').values()
        #search_count = search_data.get('count')
        #names_kde.objects.filter(surname=name_search).update(count=count+1)

        #available years
        years = [1851,1861,*range(1881,1911,10),*range(1997,2016,1)]
        avbls = search_data.values('year','freq')
        freqs = [0 for f in range(0,26)]
        for a in avbls:
            freqs[years.index(a.get('year'))] = a.get('freq')
        years = [y.get('year') for y in avbls]

        #surname statistics
        name_stats = surname_statistics(name_search)
        name_kde = [kde for kde in search_data.values('kde')]

        #output
        search = {'surname': name_search.title(),'years': years,'freqs': freqs,'kdes': name_kde,'stats': name_stats}

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

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
    admin = {'sel': sel,'all': pd.concat(allgeom).to_json(),'sr':  sr}

    #return
    return HttpResponse(json.dumps(admin),content_type="application/json")

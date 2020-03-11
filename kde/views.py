#django
from django.http import HttpResponse
from .models import *
from .statistics import *
from .kde import *

#libraries
from shapely import wkt
from fiona.crs import from_epsg
import pandas as pd
import geopandas as gpd
import json,re,ast,os
from itertools import chain

#search view
def search(request):

    #query db
    search_sur = (request.POST['q']).lower()
    clean_sur = re.sub(r'[\W^0-9^\s]+','',search_sur)
    db_sur = kdelookup.objects.filter(surname=clean_sur)
    ren_sur = names_rendered.objects.filter(surname=clean_sur)
    nireland = names_rendered.objects.filter(surname='nireland')

    #empty search
    if len(search_sur) == 0:
        search = {'source':'empty'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #if not in db
    elif not db_sur:
        search = {'source':'none','surname': search_sur}
        return HttpResponse(json.dumps(search),content_type="application/json")

    elif ren_sur:

        #pre-rendered data
        data = names_rendered.objects.filter(surname=clean_sur).values()[0]
        count = data.get('count')
        names_rendered.objects.filter(surname=clean_sur).update(count=count+1)

        #statistics
        fore_female_hist,fore_male_hist,fore_female_cont,fore_male_cont,par_top,oa_top,oac_mod,oah_mod,imd_mod,bband_mod,iuc_mod,crvul_mod = all_statistics(clean_sur)

        #combine data
        search = {'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
                'source': data.get('source'),
                'years': ast.literal_eval(data.get('years')),
                'hr_freq': ast.literal_eval(data.get('hr_freq')),
                'cr_freq': ast.literal_eval(data.get('cr_freq')),
                'contours': ast.literal_eval(data.get('contours')),
                'foremh': fore_male_hist,'forefh': fore_female_hist,
                'foremc': fore_male_cont,'forefc': fore_female_cont,
                'partop': par_top,'oatop': oa_top,'oacat': oac_mod,
                'oahlth': oah_mod,'oaimd': imd_mod,'bband': bband_mod,
                'iuc': iuc_mod,'crvul': crvul_mod,'nireland': nireland.values()[0].get('contours'),}

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

    #calculate
    else:

        #contour collection
        contour_collection = []

        #surname attributes
        data = kdelookup.objects.filter(surname=clean_sur).values()[0]
        source = 'found'
        available = {key: value for key, value in data.items() if value != None}
        years = [int(str(year[4:])) for year in list(available.keys()) if year.startswith('freq')]

        #frequencies
        freq_chart = {key: value for key, value in data.items() if key.startswith('freq')}
        freqs = [str(value) for value in freq_chart.values()]
        freqs = [0 if x=='None' else int(x) for x in freqs]
        hr_freq = freqs[:6]
        cr_freq = freqs[6:]

        #get kdes
        contour_collection = calculate_kde(clean_sur,years)

        #statistics
        fore_female_hist,fore_male_hist,fore_female_cont,fore_male_cont,par_top,oa_top,oac_mod,oah_mod,imd_mod,bband_mod,iuc_mod,crvul_mod = all_statistics(clean_sur)

        #combine data
        search = {'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
                'source': source,'years': years,'hr_freq': hr_freq,
                'cr_freq': cr_freq,'contours': contour_collection,
                'foremh': fore_male_hist,'forefh': fore_female_hist,
                'foremc': fore_male_cont,'forefc': fore_female_cont,
                'partop': par_top,'oatop': oa_top,'oacat': oac_mod,
                'oahlth': oah_mod,'oaimd': imd_mod,'bband': bband_mod,
                'iuc': iuc_mod,'crvul': crvul_mod,'nireland': nireland.values()[0].get('contours'),}

        #save to db
        if not ren_sur:
           rendered = names_rendered(clean_sur,source,years,hr_freq,cr_freq,contour_collection,1)
           rendered.save()

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

def locate_admin(request):

    #query db
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

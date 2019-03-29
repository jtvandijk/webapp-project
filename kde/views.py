#JTVD - 2019

#libraries
from django.contrib.gis.geos import fromstr
from django.http import HttpResponse
from django.conf import settings
from .models import KdeLookup, KdeGridxy, KdevClus1851, KdevClus1861, KdevClus1881, KdevClus1891, KdevClus1901, KdevClus1911, KdevClus1997, KdevClus1998, KdevClus1999, KdevClus2000, KdevClus2001, KdevClus2002, KdevClus2003, KdevClus2004, KdevClus2005, KdevClus2006, KdevClus2007, KdevClus2008, KdevClus2009, KdevClus2010, KdevClus2011, KdevClus2012, KdevClus2013, KdevClus2014, KdevClus2015, KdevClus2016, ForeNamesHist, ForeNamesCont, ParishNames, ParishLookup, OaNames, OaLookup, OaNamesCat, OaNamesAHAH, OaNamesIMD, OaNamesIUC, OaNamesBBAND, OaNamesCRVUL, CatLookup, RenderedNames
from .contour import to_concave_points
from pyproj import Proj, transform
from sklearn.cluster import dbscan
from shapely.geometry import Polygon,MultiPolygon
from fiona.crs import from_epsg
import json
import pandas as pd
import numpy as np
import geopandas as gpd
import random
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
        search = {'source':'empty',}

        #return empty
        return HttpResponse(json.dumps(search),content_type="application/json")

    #if not in db
    elif not db_sur:
        search = {'source':'none',
                  'surname': search_sur,}

        #return none
        return HttpResponse(json.dumps(search),content_type="application/json")

    #if pre-rendered
    elif ren_sur:

        #pre-rendered data
        data = RenderedNames.objects.filter(surname=clean_sur).values()[0]
        count = data.get('count')
        RenderedNames.objects.filter(surname=clean_sur).update(count=count+1)

        #statistics -- forename
        forenames_hist = ForeNamesHist.objects.filter(surname=clean_sur).values('surname','forename','sex')
        forenames_cont = ForeNamesCont.objects.filter(surname=clean_sur).values('surname','forename','sex')
        fore_female_hist, fore_male_hist = forenames_stats(forenames_hist)
        fore_female_cont, fore_male_cont = forenames_stats(forenames_cont)

        #statistics -- parish
        parishes = ParishNames.objects.filter(surname=clean_sur).values('regcnty','parish')
        par_top = parish_stats(parishes)

        #statistics -- oa
        oas = OaNames.objects.filter(surname=clean_sur).values('oa')
        oa_top = oa_stats(oas)

        #statistics -- oac
        oac = OaNamesCat.objects.filter(surname=clean_sur).values('oagroupcd','oagroupnm')
        oac_mod = oac_stats(oac)

        #statistics -- oah
        oah = OaNamesAHAH.objects.filter(surname=clean_sur).values('surname','ahah_dec_rev')
        oah_mod = oah_stats(oah)

        #statistics -- imd
        imd = OaNamesIMD.objects.filter(surname=clean_sur).values('surname','imd_dec')
        imd_mod = imd_stats(imd)

        #statistics -- bband
        bband = OaNamesBBAND.objects.filter(surname=clean_sur).values('surname','bbandcd')
        bband_mod = bband_stats(bband)

        #statistics -- iuc
        iuc = OaNamesIUC.objects.filter(surname=clean_sur).values('surname','iuccd','iucnm')
        iuc_mod = iuc_stats(iuc)

        #statistics -- crvul
        crvul = OaNamesCRVUL.objects.filter(surname=clean_sur).values('surname','crvulcd','crvulnm')
        crvul_mod = crvul_stats(crvul)

        #combine data
        search = {'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
                'source': data.get('source'),
                'years': ast.literal_eval(data.get('years')),
                'hr_freq': ast.literal_eval(data.get('hr_freq')),
                'cr_freq': ast.literal_eval(data.get('cr_freq')),
                'contours': ast.literal_eval(data.get('contours')),
                'foremh': fore_male_hist,
                'forefh': fore_female_hist,
                'foremc': fore_male_cont,
                'forefc': fore_female_cont,
                'partop': par_top[:10].tolist(),
                'oatop': oa_top[:10].tolist(),
                'oacat': list(oac_mod),
                'oahlth': oah_mod,
                'oaimd': imd_mod,
                'bband': bband_mod,
                'iuc': iuc_mod,
                'crvul': crvul_mod,}

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

    #calculate
    else:

        #contour collection
        contour_collection = []

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

        #statistics -- forename
        forenames_hist = ForeNamesHist.objects.filter(surname=clean_sur).values('surname','forename','sex')
        forenames_cont = ForeNamesCont.objects.filter(surname=clean_sur).values('surname','forename','sex')
        fore_female_hist, fore_male_hist = forenames_stats(forenames_hist)
        fore_female_cont, fore_male_cont = forenames_stats(forenames_cont)

        #statistics -- parish
        parishes = ParishNames.objects.filter(surname=clean_sur).values('regcnty','parish')
        par_top = parish_stats(parishes)

        #statistics -- oa
        oas = OaNames.objects.filter(surname=clean_sur).values('oa')
        oa_top = oa_stats(oas)

        #statistics -- oac
        oac = OaNamesCat.objects.filter(surname=clean_sur).values('oagroupcd','oagroupnm')
        oac_mod = oac_stats(oac)

        #statistics -- oah
        oah = OaNamesAHAH.objects.filter(surname=clean_sur).values('surname','ahah_dec_rev')
        oah_mod = oah_stats(oah)

        #statistics -- imd
        imd = OaNamesIMD.objects.filter(surname=clean_sur).values('surname','imd_dec')
        imd_mod = imd_stats(imd)

        #statistics -- bband
        bband = OaNamesBBAND.objects.filter(surname=clean_sur).values('surname','bbandcd')
        bband_mod = bband_stats(bband)

        #statistics -- iuc
        iuc = OaNamesIUC.objects.filter(surname=clean_sur).values('surname','iuccd','iucnm')
        iuc_mod = iuc_stats(iuc)

        #statistics -- crvul
        crvul = OaNamesCRVUL.objects.filter(surname=clean_sur).values('surname','crvulcd','crvulnm')
        crvul_mod = crvul_stats(crvul)

        #combine data
        search = {'surname': re.sub(r'[\W^0-9^]+',' ',search_sur).title(),
                'source': source,
                'years': years,
                'hr_freq': hr_freq,
                'cr_freq': cr_freq,
                'contours': contour_collection,
                'foremh': fore_male_hist,
                'forefh': fore_female_hist,
                'foremc': fore_male_cont,
                'forefc': fore_female_cont,
                'partop': par_top[:10].tolist(),
                'oatop': oa_top[:10].tolist(),
                'oacat': list(oac_mod),
                'oahlth': oah_mod,
                'oaimd': imd_mod,
                'bband': bband_mod,
                'iuc': iuc_mod,
                'crvul': crvul_mod,}

        #save to db
        if not ren_sur:
            rendered = RenderedNames(clean_sur,source,years,hr_freq,cr_freq,contour_collection,1)
            rendered.save()

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

def forenames_stats(forenames):

    #empty
    if not forenames:
        fore_female = ['No forenames found']
        fore_male = ['No forenames found']

    #names
    else:
        fore_female = []
        fore_male = []

        #male,female
        for f in forenames:
            if(f['sex'] == 'F'):
                fore_female.append(f['forename'])
            else:
                fore_male.append(f['forename'])

    #return
    return(fore_female,fore_male)

def parish_stats(parishes):

    #empty
    if not parishes:
        par_top = ['No parishes found']

    #parishes
    else:
        par_top = []

        #regcnty, parish
        for p in parishes:
            regcnty = p['regcnty'].title()
            parish = p['parish']

            #parish
            if parish == '-':
                parjoin = regcnty
            else:
                parjoin = regcnty + ': ' + parish
            par_top.append(parjoin)

    #shuffle order
    par_top = np.unique(par_top)
    random.shuffle(par_top)

    #return
    return(par_top)

def oa_stats(oas):

    #empty
    if not oas:
        oa_top = ['No OA\'s found']

    #oas
    else:
        oa_top = []

        #oa, lad
        for o in oas:
            lad = OaLookup.objects.filter(oa11=o['oa']).values('ladnm')[0]
            oajoin = lad['ladnm'] + ': ' + o['oa']
            oa_top.append(oajoin)

    #shuffle order
    oa_top = np.unique(oa_top)
    random.shuffle(oa_top)

    #return
    return(oa_top)

def oac_stats(oac):

    #empty
    if not oac:
        oac_sn = ['No classification found']
        oac_gn = ['No classification found']
        oac_sg = '9a'
    #oac
    else:
        oac_gn = oac[0]['oagroupnm']
        oac_sg = oac[0]['oagroupcd']
        oac_sn = CatLookup.objects.filter(groupcd=oac_sg).values('supergroupnm')[0]['supergroupnm']
    #return
    return(oac_sn,oac_gn,oac_sg)

def oah_stats(oah):

    #empty
    if not oah:
        oah_dc = 11 #data not available
    #oah
    else:
        oah_dc = oah[0]['ahah_dec_rev']
    #return
    return(oah_dc)

def imd_stats(imd):

    #empty
    if not imd:
        imd_dc = 11 #data not available
    #imd
    else:
        imd_dc = imd[0]['imd_dec']
    #return
    return(imd_dc)

def bband_stats(bband):

    #empty
    if not bband:
        bband_sc = 12
    #bband
    else:
        bband_sc = bband[0]['bbandcd']
    #return
    return(bband_sc)

def iuc_stats(iuc):

    #empty
    if not iuc:
        iuc_sc = [11, 'No classification found']
    #iuc
    else:
        iuc_sc = [iuc[0]['iuccd'],iuc[0]['iucnm']]
    #return
    return(iuc_sc)

def crvul_stats(crvul):

    #empty
    if not crvul:
        crvul_sc = [11, 'No classification found']
    #crvul
    else:
        crvul_sc = [crvul[0]['crvulcd'],crvul[0]['crvulnm']]
    #return
    return(crvul_sc)

def location(request):

    #user location
    lon = request.POST['longitude']
    lat = request.POST['latitude']

    #reproject
    inProj = Proj(init='epsg:4326')
    outProj = Proj(init='epsg:27700')
    locprj = list(transform(inProj,outProj,lon,lat))
    pnt = fromstr('POINT('+str(locprj[0])+' ' +str(locprj[1])+')',srid=27700)

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

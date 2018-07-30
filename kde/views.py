#JTVD - 2018

#libraries
from django.shortcuts import render
from django.contrib.gis.geos import fromstr
from django.http import HttpResponse
from .models import KdeLookup, KdeGridxy, KdevClus1998, KdevClus1999, KdevClus2000, KdevClus2001, KdevClus2002, KdevClus2003, KdevClus2004, KdevClus2005, KdevClus2006, KdevClus2007, KdevClus2008, KdevClus2009, KdevClus2010, KdevClus2011, KdevClus2012, KdevClus2013, KdevClus2014, KdevClus2015, KdevClus2016, KdevClus2017, LsoaTopnames
from .contour import to_concave_points
from pyproj import Proj, transform
from sklearn.cluster import dbscan
import json
import pandas as pd
import sys
import re

#reconstruct grid -- keep in memory
xy = KdeGridxy.objects.values('x','y')
gridc = pd.DataFrame.from_records(xy)

#search view
def str_to_class(classname):
    return getattr(sys.modules[__name__], classname)

def search(request):

    #query db
    if request.method == 'GET':
        search_sur = (request.GET['q']).lower()
        sclean = re.sub(r'[\W^0-9]+', ' ', search_sur)
    elif request.method == 'POST':
        search_sur = (request.POST['q']).lower()
        sclean = re.sub(r'[\W^0-9]+', ' ', search_sur)
    db_sur = KdeLookup.objects.filter(surname=sclean)

    #validate year
    if request.method == 'GET' and 'y' in request.GET:
        year_sel = (request.GET['y'])
    elif request.method == 'POST' and 'y' in request.POST:
        year_sel = (request.POST['y'])
    else:
        year_sel = []

    #validate search
    qvalid=True
    if len(sclean) == 0:
        qvalid=False

    #if not in db
    if not db_sur:
        years = []
        contourprj = []
        freqs= []

    #if in database
    if db_sur:
        data = KdeLookup.objects.filter(surname=sclean).values()[0]
        available = {key: value for key, value in data.items() if value != None}
        years = [str(year[4:]) for year in list(available.keys()) if year.startswith('freq')]

        freq_chart = {key: value for key, value in data.items() if key.startswith('freq')}
        freqs = [str(value) for value in freq_chart.values()]
        freqs = [0 if x=='None' else int(x) for x in freqs]
        if not year_sel:
            year_sel = years[0]

        #get uid
        uid_key = "uid" + str(year_sel)
        uid_sel = int(available.get(uid_key))

        #get data
        kdev = str_to_class("KdevClus" + (str(year_sel)))
        year_data = str(kdev.objects.filter(uid=uid_sel).values('kde'))
        val = [int(x) for x in year_data[21:-5].split(',')]

        #add selected values
        gridc['val'] = val
        gridc['id'] = gridc.index
        level = 55
        kde_sel = gridc[(gridc['val'] >= level)]
        coord = [[int(x[1]),int(x[0])] for x in (list(zip(kde_sel.x,kde_sel.y)))]
        cs, lbls = dbscan(coord, eps=2000)
        kde_sel = kde_sel.copy()
        kde_sel['group'] = lbls

        #identify for each group concave points
        contourp = to_concave_points(kde_sel, coord)

        #British National Grid to WGS84
        inProj = Proj(init='epsg:27700')
        outProj = Proj(init='epsg:4326')

        #contour reprojected data
        contourprj = []
        for contour in contourp:
            tmp_prj = []
            for coord in contour:
                pwgs84 = transform(inProj,outProj, coord[0],coord[1])
                pwgs84_order = [pwgs84[1], pwgs84[0]]
                tmp_prj.append(list(pwgs84_order))
            contourprj.append(tmp_prj)

        #return if search from home
        if request.method == 'GET':

            print(db_sur)


            #return view
            return render(request,"search.html",{'search_sur':sclean.title(),'db_sur':db_sur,'data':years,'freqs':freqs,'year_sel':year_sel,'qvalid':qvalid,'contourprj':contourprj})

        #return if search from searhc
        if request.method == 'POST':

            search = {
                    'search_sur': sclean.title(),
                    'db_sur': [],
                    'data': years,
                    'freqs': freqs,
                    'year_sel': year_sel,
                    'qvalid': qvalid,
                    'contourprj': contourprj,
                    }

            print(db_sur)

            #return data
            return HttpResponse(json.dumps(search),content_type="application/json")

    #if not in db
    else:
        print(db_sur)
        #return emtpy
        return render(request,"search.html",{'search_sur':search_sur.title(),'db_sur':db_sur,'data':years,'freqs':freqs,'year_sel':year_sel,'qvalid':qvalid,'contourprj':contourprj})

def location(request):

    if request.method == 'POST':

        #user location
        lon = request.POST['longitude']
        lat = request.POST['latitude']
        #reproject
        inProj = Proj(init='epsg:4326')
        outProj = Proj(init='epsg:27700')
        locprj = list(transform(inProj,outProj, lon,lat))
        pnt = fromstr('POINT(' +str(locprj[0]) + ' ' +str(locprj[1]) + ')', srid=27700)

        #spatial query for topnames
        lsoa = LsoaTopnames.objects.filter(shape__contains=pnt)
        div = {key: value for key, value in lsoa.values()[0].items()}
        tnlist = [str(x).title() for x in div['topnames'][1:-1].split(',')]
        unique = div['unique_n']
        total = div['total_n']
        alpha = div['diversity_a']

        loclist = {'topnames': tnlist,
                   'unique': unique,
                   'total': total,
                   'alpha': alpha
                   }
        #return data
        return HttpResponse(json.dumps(loclist),content_type="application/json")

#libraries
from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from .statistics import *
from re import sub
import json
import zlib

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

        #search: in db
        name_db = names_all.objects.filter(surname=name_search).values('period')
        if name_db:
            search = {'surname':'db'}
            return HttpResponse(json.dumps(search),content_type="application/json")

        #search: not found
        elif not name_db:
            search = {'surname':'none'}
            return HttpResponse(json.dumps(search),content_type="application/json")

    #search: found
    elif name_found:

        try:

            #surname data
            year_exclusion=[0,1997,*range(1999,2006,1),*range(2007,2016,1)]
            search_data = names_kde.objects.filter(surname=name_search).exclude(year__in=year_exclusion).order_by('year').values('year','freq')

            #if empty due to year selection
            if not search_data:
                search = {'surname':'db'}
                return HttpResponse(json.dumps(search),content_type="application/json")

            #available years with kde
            kdeyears = [y.get('year') for y in search_data]

            #actual frequencies
            years = [1851,1861,*range(1881,1921,10),*range(1997,2017,1)]
            avbls = names_frq.objects.filter(surname=name_search).values('year','freq')
            freqs = [0 for f in range(0,26)]
            for a in avbls:
                freqs[years.index(a.get('year'))] = a.get('freq')

            #surname statistics
            name_stats = surname_statistics(name_search)

            #output
            search = {'surname': name_input.title(),'years': kdeyears,'freqs': freqs,'stats': name_stats}

            #return data
            return HttpResponse(json.dumps(search),content_type="application/json")

        except:
            return HttpResponse(status=500)

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
        search = {'surname':'none'}
        return HttpResponse(json.dumps(search),content_type="application/json")

    #search: found
    elif name_found:

        #surname data
        search_data = names_kde.objects.filter(surname=name_search).order_by('year').values()

        #available years
        years = [1851,1861,*range(1881,1921,10),*range(1997,2017,1)]
        avbls = search_data.values('year','freq')
        freqs = [0 for f in range(0,26)]
        for a in avbls:
            freqs[years.index(a.get('year'))] = a.get('freq')
        years = [y.get('year') for y in avbls]

        #surname statistics
        name_stats = surname_statistics(name_search)
        name_kde = [kde for kde in search_data.values('kde')]

        #output
        search = {'surname': name_input.title(),'years': years,'freqs': freqs,'kdes': name_kde,'stats': name_stats}

        #return data
        return HttpResponse(json.dumps(search),content_type="application/json")

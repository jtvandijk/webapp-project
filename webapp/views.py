from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from kde.models import KdeLookup
import sys

def index(request):

    def distinct_count(column):
        coln = (column + ('__isnull'))
        dist_f = KdeLookup.objects.filter(coln=False).distinct().count()
        return(dist_f)

    data_freqs = []
    for i in range(1998,2017):

        year = 'freq'+str(i)
        print(year)
        freq_y = distinct_count(year)
        data_freqs.append(freq_y)

    print(data_freqs)


    return render(request,'index.html',{'data_freqs':data_freqs})

from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from kde.models import KdeLookup
import sys

def index(request):

    def str_to_class(classname):
        return getattr(sys.modules[__name__], classname)

    def distinct_count(column):
        coln = str_to_class(column + (str(__isnull)))
        dist_f = KdeLookup.objects.filter(coln=False).distinct().count()
        return(dist_f)



    f2017 = distinct_count('freq2017')

    print(f2017)



    return render(request, "index.html", {'data_freqs' = data_freqs})

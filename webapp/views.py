from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from kde.models import KdeLookup

def index(request):

    data_freqs=[]
    data_freqs.append(KdeLookup.objects.filter(freq1998__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq1999__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2000__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2001__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2002__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2003__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2004__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2005__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2006__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2007__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2008__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2009__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2010__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2011__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2012__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2013__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2014__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2015__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2016__isnull=False).distinct().count())
    data_freqs.append(KdeLookup.objects.filter(freq2017__isnull=False).distinct().count())

    return render(request, "index.html", {'data_freqs':data_freqs})

from django.shortcuts import render
from kde.models import KdeLookup

def index(request):

    data_freqs=[]
    data_freqs.append(KdeLookup.objects.filter(freq1998__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq1999__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2000__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2001__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2002__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2003__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2004__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2005__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2006__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2007__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2008__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2009__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2010__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2011__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2012__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2013__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2014__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2015__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2016__isnull=False).count())
    data_freqs.append(KdeLookup.objects.filter(freq2017__isnull=False).count())

    return render(request,"index.html",{'data_freqs':data_freqs})

#JTVD - 2019

#libraries
from django.shortcuts import render
from kde.models import KdeLookup

#index views
def index(request):

    #absolute frequencies
    hr_freq=[]

    #historic census
    hr_freq.append(KdeLookup.objects.filter(freq1851__isnull=False).count())
    hr_freq.append(KdeLookup.objects.filter(freq1861__isnull=False).count())
    hr_freq.append(KdeLookup.objects.filter(freq1881__isnull=False).count())
    hr_freq.append(KdeLookup.objects.filter(freq1891__isnull=False).count())
    hr_freq.append(KdeLookup.objects.filter(freq1901__isnull=False).count())
    hr_freq.append(KdeLookup.objects.filter(freq1911__isnull=False).count())

    #consumer registers
    cr_freq=[]
    cr_freq.append(KdeLookup.objects.filter(freq1997__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq1998__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq1999__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2000__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2001__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2002__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2003__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2004__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2005__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2006__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2007__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2008__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2009__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2010__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2011__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2012__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2013__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2014__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2015__isnull=False).count())
    cr_freq.append(KdeLookup.objects.filter(freq2016__isnull=False).count())

    #return
    return render(request,'index.html',{'hr_freq':hr_freq,'cr_freq':cr_freq})

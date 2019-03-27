#JTVD - 2019

#libraries
from django.shortcuts import render
from kde.models import KdeLookup

#index views
def index(request):

    #return
    return render(request,'index.html')

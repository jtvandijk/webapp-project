#django
from django.shortcuts import render

#index views
def index(request):

    #return
    return render(request,'index.html')

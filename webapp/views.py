from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from kde.models import KdeLookup

def index(request):

    f2017 = KdeLookup.objects.filter(freq2017__isnull=False).distinct()

    print(f2017)

        # available = {key: value for key, value in data.items() if value != None}
        # years = [str(year[4:]) for year in list(available.keys()) if year.startswith('freq')]
        #
        # freq_chart = {key: value for key, value in data.items() if key.startswith('freq')}
        # freqs = [str(value) for value in freq_chart.values()]
        # freqs = [0 if x=='None' else int(x) for x in freqs]

    return render(request, "index.html")

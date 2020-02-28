#django
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

#patterns
urlpatterns = [
    path('gbnames/',views.index, name='home'),
    path('gbnames/search/',views.search, name='search'),
    path('gbnames/location/',views.location, name='location'),
] + static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)

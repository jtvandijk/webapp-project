"""
webapp URL Configuration
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from kde import views as kde_views

urlpatterns = [
    path('udl-namekde/', views.index, name='home'),
    path('udl-namekde/admin/', admin.site.urls),
    path('udl-namekde/search/', kde_views.search, name='search'),
    path('udl-namekde/location/', kde_views.location, name='location'),
    path('udl-namekde/geography/', kde_views.geography, name='geography'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

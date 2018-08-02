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
    path('', views.index, name='home'),
    path('admin/', admin.site.urls),
    path('search/', kde_views.search, name='search'),
    path('location/', kde_views.location, name='location'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

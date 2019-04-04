#webapp URL Configuration

#libraries
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from kde import views as kde_views

#patterns
# urlpatterns = [
#     path('', views.index, name='home'),
#     path('admin/', admin.site.urls,name='admin'),
#     path('search/', kde_views.search, name='search'),
#     path('parish/', kde_views.locate_parish, name='parish'),
#     path('oas/', kde_views.locate_oas, name='oa'),
# ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns = [
    path('udl-namekde/', views.index, name='home'),
    path('udl-namekde/admin/', admin.site.urls),
    path('udl-namekde/search/', kde_views.search, name='search'),
    path('udl-namekde/parish/', kde_views.locate_parish, name='parish'),
    path('udl-namekde/oas/', kde_views.locate_oas, name='oa'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

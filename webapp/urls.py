#django
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from kde import views as kde_views
from . import views

#patterns
urlpatterns = [
    # path('', views.index, name='home'),
    # path('search/', kde_views.search, name='search'),
    # path('location/', kde_views.locate_admin, name='location'),
    # path('udl-namekde/', views.index, name='home'),
    # path('udl-namekde/search/', kde_views.search, name='search'),
    # path('udl-namekde/location/', kde_views.locate_admin, name='location'),
    path('gbnames/', views.index, name='home'),
    path('gbnames/search/', kde_views.search, name='search'),
    path('gbnames/location/', kde_views.locate_admin, name='location'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

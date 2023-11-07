#django
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

#patterns
urlpatterns = [
    path('', views.index, name='home'),
    path('search/', views.search, name='search'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

#django
from django.core.wsgi import get_wsgi_application

#libraries
import os

#settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings")
application = get_wsgi_application()

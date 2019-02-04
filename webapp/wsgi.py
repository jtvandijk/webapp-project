#wsgi

#libraries
import os
from django.core.wsgi import get_wsgi_application

#settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings")
application = get_wsgi_application()

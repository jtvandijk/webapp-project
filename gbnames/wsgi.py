#django
import os
from django.core.wsgi import get_wsgi_application

#settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gbnames.settings')
application = get_wsgi_application()

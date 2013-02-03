import os, sys

#sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()

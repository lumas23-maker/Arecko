import os
from django.core.wsgi import get_wsgi_application

# Updated 'your_project_name' to 'core'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
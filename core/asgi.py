import os
from django.core.asgi import get_asgi_application

# We change 'your_project_name' to 'core'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_asgi_application()
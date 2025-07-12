# Sqride/Sqride/production.py

from .settings import *

import os

DEBUG = False

# Use environment variable for secret key in production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'unsafe-default-key')

ALLOWED_HOSTS = [
    'api.sqride.com',
    'sqride.com',
    # Add your server IP/domain here
]

# CORS settings for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://sqride.com",
    "https://api.sqride.com",
]

# Secure cookies
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True



# Database (example for PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'sqride'),
        'USER': os.environ.get('POSTGRES_USER', 'sqrideuser'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Static and media files (adjust as needed)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Any other production-specific settings...
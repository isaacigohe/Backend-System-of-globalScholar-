# core_backend/settings/production.py
from .base import *
from decouple import config
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='backend-system-of-globalscholar.onrender.com',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# CORS allows React frontend to call this API
INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware'] + MIDDLEWARE

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True

# WhiteNoise serves Django admin static files in production
MIDDLEWARE += ['whitenoise.middleware.WhiteNoiseMiddleware']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Render provides DATABASE_URL automatically from the attached PostgreSQL instance
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

# Basic security headers
SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'
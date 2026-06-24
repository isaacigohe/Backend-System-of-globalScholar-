# core_backend/settings/production.py

from .base import *
from decouple import config
import os
import dj_database_url

DEBUG = False

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
DEFAULT_HOSTS = [
    RENDER_EXTERNAL_HOSTNAME,
    '.onrender.com',
    'backend-system-of-globalscholar.onrender.com',
]
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default=','.join([host for host in DEFAULT_HOSTS if host]),
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# ── Database ─────────────────────────────────────────────────────────────────
# Reads DATABASE_URL from Render environment variables
# Fixes older postgres:// URLs to postgresql:// which Django 4+ requires

raw_db_url = config('DATABASE_URL', default='')

if raw_db_url.startswith('postgres://'):
    raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = raw_db_url

DATABASES = {
    'default': dj_database_url.config(
        default=raw_db_url,
        conn_max_age=600,
        ssl_require=True,
    )
}

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allows the React frontend to make API calls to this Django backend

INSTALLED_APPS += ['corsheaders']

MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware'] + MIDDLEWARE

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CORS_ALLOW_CREDENTIALS = True

# ── Static Files ──────────────────────────────────────────────────────────────
# WhiteNoise serves Django admin CSS/JS in production without a separate server

MIDDLEWARE += ['whitenoise.middleware.WhiteNoiseMiddleware']

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATIC_ROOT = BASE_DIR / 'staticfiles'

# ── Security ──────────────────────────────────────────────────────────────────

SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'

# Required for Django admin to work on HTTPS (Render uses HTTPS)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default=','.join([
        f'https://{RENDER_EXTERNAL_HOSTNAME}' if RENDER_EXTERNAL_HOSTNAME else '',
        'https://backend-system-of-globalscholar.onrender.com',
    ]).strip(','),
    cast=lambda v: [s.strip() for s in v.split(',')]
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging: stream Django errors to stdout so Render captures stack traces
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
# core_backend/settings/production.py

from .base import *
from decouple import config
import os
import dj_database_url

DEBUG = False

# Accept Render's hostname if provided and common onrender subdomains
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
DEFAULT_HOSTS = [RENDER_EXTERNAL_HOSTNAME, '.onrender.com', 'backend-system-of-globalscholar.onrender.com']
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default=','.join([host for host in DEFAULT_HOSTS if host]),
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# ── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(default=config('DATABASE_URL'))
}

# ── CORS ──────────────────────────────────────────────────────────────────────
# CORS is already configured in base.py - only override if needed
# DO NOT add corsheaders to INSTALLED_APPS again (it's already in base.py)

# If you need to override CORS_ALLOWED_ORIGINS for production:
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://frontend-theta-bay-81.vercel.app,http://localhost:5173',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

CORS_ALLOW_CREDENTIALS = True

# ── Static Files ──────────────────────────────────────────────────────────────
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ── Security ──────────────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://backend-system-of-globalscholar.onrender.com',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': True},
        'django.security': {'handlers': ['console'], 'level': 'ERROR', 'propagate': True},
    },
}
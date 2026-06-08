from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Looser password validation in dev so test users are easy to create
AUTH_PASSWORD_VALIDATORS = []
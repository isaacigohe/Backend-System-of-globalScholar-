#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py migrate

# Hardcoding the password via a bash pipe
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_backend.settings.production')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='isaac@globalscholar.com').exists():
    User.objects.create_superuser('isaac@globalscholar.com', 'Scholar2026Secure', first_name='Isaac', last_name='Admin')
    print('Superuser created successfully!')
else:
    print('Superuser already exists.')
"
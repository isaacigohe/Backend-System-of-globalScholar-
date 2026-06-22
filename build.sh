#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Programmatically create your live superuser natively on the cloud database
python -c "
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
email_address = 'isaachome@gmail.com'

if not User.objects.filter(email=email_address).exists():
    User.objects.create_superuser(
        email=email_address,
        password='RenderSecure123!',
        first_name='Isaac',
        last_name='Igohe',
        role='HOME_ADMIN'
    )
    print('✅ Superuser account created successfully via build script!')
else:
    print('ℹ️ Superuser account already exists, skipping.')
"
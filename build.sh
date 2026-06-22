#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install dependencies
pip install -r requirements.txt

# 2. Collect static files
python manage.py collectstatic --no-input

# 3. Run database migrations
python manage.py migrate

# 4. Create your superuser cleanly using Django's shell command
cat <<EOF | python manage.py shell
import os
import django
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
EOF
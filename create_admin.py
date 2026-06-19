import os
import django

# This tells Django to look inside your 'core_backend' folder for settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
email = "isaac@gmail.com"
password = "Secure1234"  # Put the password you want here

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print("🚀 SUPERUSER CREATED SUCCESSFULLY VIA SCRIPT!")
else:
    print("✅ Superuser already exists.")
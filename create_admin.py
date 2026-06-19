import os
import django

# Make sure this matches the exact folder name containing your settings.py file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GlobalScholar.settings') 
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
email = "isaac@gmail.com"
password = "YourSecurePassword123!"  # Put the password you want here

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print("🚀 SUPERUSER CREATED SUCCESSFULLY VIA SCRIPT!")
else:
    print("✅ Superuser already exists.")
#!/usr/bin/env bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files for Django admin CSS
python manage.py collectstatic --no-input

# Run migrations — if database is temporarily unreachable, build continues
python manage.py migrate --no-input || echo "Migration failed — will retry on next deploy"
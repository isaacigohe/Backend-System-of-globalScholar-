web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn core_backend.wsgi --bind 0.0.0.0:$PORT

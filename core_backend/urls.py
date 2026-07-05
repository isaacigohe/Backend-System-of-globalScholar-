from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.core.management import call_command

# Temporary migration trigger — remove after first successful migration
def run_migrations(request):
    if request.GET.get('key') != 'globalscholar2024':
        return HttpResponse('Unauthorized', status=401)
    try:
        call_command('migrate', '--no-input')
        return HttpResponse('Migrations completed successfully')
    except Exception as e:
        return HttpResponse(f'Migration failed: {str(e)}', status=500)

API_PREFIX = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('run-migrations/', run_migrations),
    path(API_PREFIX, include('users.urls')),
    path(API_PREFIX, include('universities.urls')),
    path(API_PREFIX, include('applications.urls')),
    path(API_PREFIX, include('notifications.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

API_PREFIX = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(API_PREFIX, include("users.urls")),
    path(API_PREFIX, include("universities.urls")),
    path(API_PREFIX, include("applications.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
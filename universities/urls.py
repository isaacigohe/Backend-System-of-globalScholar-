from django.urls import path

from .views import (
    UniversityListCreateView,
    UniversityDetailView,
    ProgramListCreateView,
    ProgramDetailView,
)

urlpatterns = [
    path("universities/", UniversityListCreateView.as_view(), name="university-list"),
    path("universities/<int:pk>/", UniversityDetailView.as_view(), name="university-detail"),
    path(
        "universities/<int:university_id>/programs/",
        ProgramListCreateView.as_view(),
        name="program-list",
    ),
    path("programs/<int:pk>/", ProgramDetailView.as_view(), name="program-detail"),
]
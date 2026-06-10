from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters

from users.permissions import IsAdminOrCoordinator
from .models import University, Program
from .serializers import (
    UniversitySerializer,
    UniversityListSerializer,
    ProgramSerializer,
)


class UniversityFilter(django_filters.FilterSet):
    country = django_filters.CharFilter(lookup_expr="icontains")
    min_gpa = django_filters.NumberFilter(
        field_name="minimum_gpa", lookup_expr="lte",
        label="Maximum minimum GPA (show universities requiring at most this GPA)",
    )
    max_gpa_requirement = django_filters.NumberFilter(
        field_name="minimum_gpa", lookup_expr="lte"
    )
    advisory_level = django_filters.CharFilter(
        field_name="travel_advisory_level", lookup_expr="exact"
    )
    language = django_filters.CharFilter(
        field_name="primary_language", lookup_expr="iexact"
    )

    class Meta:
        model = University
        fields = ["country", "min_gpa", "advisory_level", "language"]


class UniversityListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/universities/        — list all, paginated, filterable
    POST /api/v1/universities/        — create (admin/coordinator only)

    Filter params: ?country=Germany&min_gpa=3.0&language=English
    Search params: ?search=Berlin
    Order params:  ?ordering=minimum_gpa or ?ordering=-name
    """
    queryset = University.objects.prefetch_related("programs").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UniversityFilter
    search_fields = ["name", "country", "city"]
    ordering_fields = ["name", "country", "minimum_gpa", "created_at"]
    ordering = ["country", "name"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UniversityListSerializer
        return UniversitySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsAdminOrCoordinator()]


class UniversityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/universities/<id>/   — full detail with nested programs
    PATCH  /api/v1/universities/<id>/   — update (admin/coordinator only)
    DELETE /api/v1/universities/<id>/   — delete (admin/coordinator only)
    """
    queryset = University.objects.prefetch_related("programs").all()
    serializer_class = UniversitySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsAdminOrCoordinator()]


class ProgramListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/universities/<university_id>/programs/
    POST /api/v1/universities/<university_id>/programs/
    """
    serializer_class = ProgramSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "degree_level", "application_deadline"]

    def get_queryset(self):
        university_id = self.kwargs["university_id"]
        return Program.objects.filter(university_id=university_id)

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsAdminOrCoordinator()]

    def perform_create(self, serializer):
        university_id = self.kwargs["university_id"]
        serializer.save(university_id=university_id)


class ProgramDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/programs/<id>/
    PATCH  /api/v1/programs/<id>/
    DELETE /api/v1/programs/<id>/
    """
    queryset = Program.objects.select_related("university").all()
    serializer_class = ProgramSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated()]
        return [IsAdminOrCoordinator()]
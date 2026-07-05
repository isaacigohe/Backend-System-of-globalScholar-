from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.pagination import PageNumberPagination
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


# ── Custom Pagination ──────────────────────────────────────────────────────────
class UniversityPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 20


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
    GET  /api/v1/universities/   — PUBLIC. No token needed.
                                   Anyone can browse universities before registering.
                                   Paginated: 5 universities per page.

    POST /api/v1/universities/   — Admin/Coordinator only.

    Filter params: ?country=Germany&min_gpa=3.0&language=English
    Search params: ?search=Berlin
    Order params:  ?ordering=minimum_gpa or ?ordering=-name
    Page params:   ?page=2 (for pagination)
    """
    queryset = University.objects.prefetch_related("programs").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UniversityFilter
    search_fields = ["name", "country", "city"]
    ordering_fields = ["name", "country", "minimum_gpa", "created_at"]
    ordering = ["country", "name"]
    pagination_class = UniversityPagination  # ADD THIS

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UniversityListSerializer
        return UniversitySerializer

    def get_serializer_context(self):
        """Add request to context for generating absolute image URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        if self.request.method == "GET":
            # PUBLIC — no login required to browse universities
            return [permissions.AllowAny()]
        return [IsAdminOrCoordinator()]


class UniversityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/universities/<id>/   — PUBLIC. Full detail with nested programs.
                                          Anyone can view a university's full profile.
    PATCH  /api/v1/universities/<id>/   — Admin/Coordinator only.
    DELETE /api/v1/universities/<id>/   — Admin/Coordinator only.
    """
    queryset = University.objects.prefetch_related("programs").all()
    serializer_class = UniversitySerializer

    def get_serializer_context(self):
        """Add request to context for generating absolute image URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        if self.request.method == "GET":
            # PUBLIC — no login required to view university details and programs
            return [permissions.AllowAny()]
        return [IsAdminOrCoordinator()]


class ProgramListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/universities/<university_id>/programs/  — PUBLIC.
    POST /api/v1/universities/<university_id>/programs/  — Admin/Coordinator only.
    """
    serializer_class = ProgramSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["name", "degree_level", "application_deadline"]

    def get_queryset(self):
        university_id = self.kwargs["university_id"]
        return Program.objects.filter(university_id=university_id)

    def get_permissions(self):
        if self.request.method == "GET":
            # PUBLIC — anyone can browse what programs a university offers
            return [permissions.AllowAny()]
        return [IsAdminOrCoordinator()]

    def perform_create(self, serializer):
        university_id = self.kwargs["university_id"]
        serializer.save(university_id=university_id)


class ProgramDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/programs/<id>/   — PUBLIC. Full program detail.
    PATCH  /api/v1/programs/<id>/   — Admin/Coordinator only.
    DELETE /api/v1/programs/<id>/   — Admin/Coordinator only.
    """
    queryset = Program.objects.select_related("university").all()
    serializer_class = ProgramSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            # PUBLIC — anyone can view a specific program's details
            return [permissions.AllowAny()]
        return [IsAdminOrCoordinator()]
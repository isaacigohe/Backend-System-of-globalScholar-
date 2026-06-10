from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters

from users.permissions import IsStudent, IsAdminOrCoordinator, IsOwnerOrAdmin
from users.throttles import FileUploadRateThrottle
from .models import Application, DocumentChecklist, CreditTransferLog
from .serializers import (
    ApplicationSerializer,
    ApplicationListSerializer,
    DocumentChecklistSerializer,
    CreditTransferLogSerializer,
)


class ApplicationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(
        field_name="status", lookup_expr="exact"
    )
    destination_country = django_filters.CharFilter(
        field_name="destination_university__country", lookup_expr="icontains"
    )
    min_gpa = django_filters.NumberFilter(
        field_name="gpa_at_submission", lookup_expr="gte"
    )
    university_name = django_filters.CharFilter(
        field_name="destination_university__name", lookup_expr="icontains"
    )

    class Meta:
        model = Application
        fields = ["status", "destination_country", "min_gpa", "university_name"]


class ApplicationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/applications/
      — Students see only their own applications.
      — Admins/Coordinators see all applications.

    POST /api/v1/applications/
      — Students only. Creates a DRAFT application.

    Filter params: ?status=SUBMITTED&destination_country=Germany&min_gpa=3.2
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ApplicationFilter
    search_fields = [
        "destination_university__name",
        "destination_university__country",
        "student__first_name",
        "student__last_name",
    ]
    ordering_fields = ["created_at", "submitted_at", "status", "gpa_at_submission"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user

        if user.is_student:
            return Application.objects.select_related(
                "student", "destination_university", "program"
            ).filter(student=user)

        if user.is_home_admin or user.is_host_coordinator:
            return Application.objects.select_related(
                "student", "destination_university", "program", "reviewed_by"
            ).all()

        return Application.objects.none()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ApplicationListSerializer
        return ApplicationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsStudent()]
        return [permissions.IsAuthenticated()]


class ApplicationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/applications/<id>/   — Student sees own; Admin sees all
    PATCH /api/v1/applications/<id>/   — Admin/Coordinator advances pipeline status
    """
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user

        if user.is_student:
            return Application.objects.filter(student=user)

        return Application.objects.select_related(
            "student", "destination_university", "reviewed_by"
        ).all()


class SubmitApplicationView(APIView):
    """
    POST /api/v1/applications/<id>/submit/
    Students submit their own DRAFT application, moving it to SUBMITTED.
    This is a discrete action endpoint rather than a generic PATCH so the
    intent is unambiguous in API logs.
    """
    permission_classes = [IsStudent]

    def post(self, request, pk):
        application = Application.objects.filter(
            pk=pk, student=request.user
        ).first()

        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if application.status != Application.Status.DRAFT:
            return Response(
                {
                    "detail": (
                        f"Only DRAFT applications can be submitted. "
                        f"This application is currently '{application.status}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = Application.Status.SUBMITTED
        application.submitted_at = timezone.now()
        application.gpa_at_submission = request.user.gpa
        application.save(update_fields=["status", "submitted_at", "gpa_at_submission"])

        serializer = ApplicationSerializer(application, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdvanceApplicationView(APIView):
    """
    POST /api/v1/applications/<id>/advance/
    Admin/Coordinator moves an application to the next pipeline stage.
    Body: { "status": "UNDER_REVIEW" }
    """
    permission_classes = [IsAdminOrCoordinator]

    def post(self, request, pk):
        application = Application.objects.select_related(
            "destination_university", "student"
        ).filter(pk=pk).first()

        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ApplicationSerializer(
            application,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DocumentChecklistListView(generics.ListAPIView):
    """
    GET /api/v1/applications/<application_id>/documents/
    Returns all checklist items for an application.
    Students see only their own. Admins see all.
    """
    serializer_class = DocumentChecklistSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        application_id = self.kwargs["application_id"]
        user = self.request.user

        if user.is_student:
            return DocumentChecklist.objects.filter(
                application_id=application_id,
                application__student=user,
            ).select_related("reviewed_by")

        return DocumentChecklist.objects.filter(
            application_id=application_id,
        ).select_related("reviewed_by")


class DocumentUploadView(generics.UpdateAPIView):
    """
    PATCH /api/v1/documents/<id>/upload/
    Student uploads a file. Throttled to 3 uploads/min.
    Automatically flips verification_status to AWAITING_REVIEW.
    """
    serializer_class = DocumentChecklistSerializer
    permission_classes = [IsStudent, IsOwnerOrAdmin]
    throttle_classes = [FileUploadRateThrottle]
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        return DocumentChecklist.objects.filter(
            application__student=self.request.user
        )


class DocumentReviewView(generics.UpdateAPIView):
    """
    PATCH /api/v1/documents/<id>/review/
    Admin reviews an uploaded document and sets verification_status.
    If setting ACTION_REQUIRED, admin_comment is mandatory (enforced in serializer).
    """
    serializer_class = DocumentChecklistSerializer
    permission_classes = [IsAdminOrCoordinator]
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        return DocumentChecklist.objects.select_related(
            "application__student", "reviewed_by"
        ).all()


class CreditTransferLogListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/applications/<application_id>/credits/
    POST /api/v1/applications/<application_id>/credits/
    Host Coordinator submits credit mappings. Students can view.
    """
    serializer_class = CreditTransferLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        application_id = self.kwargs["application_id"]
        user = self.request.user

        if user.is_student:
            return CreditTransferLog.objects.filter(
                application_id=application_id,
                application__student=user,
            )

        return CreditTransferLog.objects.filter(application_id=application_id)

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminOrCoordinator()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        application_id = self.kwargs["application_id"]
        serializer.save(
            application_id=application_id,
            submitted_by=self.request.user,
        )


class CreditTransferLogDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/credits/<id>/
    PATCH /api/v1/credits/<id>/
    """
    serializer_class = CreditTransferLogSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return CreditTransferLog.objects.select_related(
            "application__student", "submitted_by"
        ).all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAdminOrCoordinator()]
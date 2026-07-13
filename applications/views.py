from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import django_filters
from notifications.utils import create_notification

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
      — Home Admins see all applications.
      — Host Coordinators see only applications for their assigned university.

    POST /api/v1/applications/
      — Students only. Creates a DRAFT application.
      — Checks if student has an existing draft and notifies them.

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

        if user.is_home_admin:
            return Application.objects.select_related(
                "student", "destination_university", "program", "reviewed_by"
            ).all()

        if user.is_host_coordinator:
            if user.host_university:
                return Application.objects.select_related(
                    "student", "destination_university", "program", "reviewed_by"
                ).filter(destination_university=user.host_university)
            return Application.objects.none()

        return Application.objects.none()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ApplicationListSerializer
        return ApplicationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsStudent()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        # ── Check if student has a draft in progress ────────────────────────
        existing_draft = Application.objects.filter(
            student=request.user,
            status=Application.Status.DRAFT
        ).first()
        
        if existing_draft:
            return Response(
                {
                    "detail": "You have a draft application already in progress.",
                    "draft_id": existing_draft.id,
                    "university": existing_draft.destination_university.name,
                    "continue_link": f"/api/v1/applications/{existing_draft.id}/"
                },
                status=status.HTTP_409_CONFLICT
            )
        
        return super().create(request, *args, **kwargs)


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

        if user.is_home_admin:
            return Application.objects.select_related(
                "student", "destination_university", "reviewed_by"
            ).all()

        if user.is_host_coordinator:
            if user.host_university:
                return Application.objects.select_related(
                    "student", "destination_university", "reviewed_by"
                ).filter(destination_university=user.host_university)
            return Application.objects.none()

        return Application.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


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

        # ── FIX: Create documents immediately on submission ──────────────────
        document_types = [
            DocumentChecklist.DocumentType.PASSPORT_SCAN,
            DocumentChecklist.DocumentType.ACADEMIC_TRANSCRIPT,
            DocumentChecklist.DocumentType.PERSONAL_STATEMENT,
            DocumentChecklist.DocumentType.REFERENCE_LETTER,
            DocumentChecklist.DocumentType.BANK_STATEMENT,
            DocumentChecklist.DocumentType.MEDICAL_CLEARANCE,
            DocumentChecklist.DocumentType.INSURANCE_PROOF,
            DocumentChecklist.DocumentType.VISA_COPY,
            DocumentChecklist.DocumentType.HOUSING_CONFIRMATION,
        ]
        
        for doc_type in document_types:
            DocumentChecklist.objects.get_or_create(
                application=application,
                document_type=doc_type,
                defaults={
                    'is_mandatory': True,
                    'verification_status': DocumentChecklist.VerificationStatus.PENDING
                }
            )

        # ── Send notification to student ────────────────────────────────────
        create_notification(
            user=request.user,
            notification_type="APPLICATION_SUBMITTED",
            title="📤 Application Submitted",
            message=f"Your application to {application.destination_university.name} has been submitted. Please upload your documents in the Compliance Checklist Vault.",
            link="/student",
            related_application_id=application.id
        )

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
        user = request.user
        
        # Get application with filtering for coordinators
        if user.is_host_coordinator:
            if not user.host_university:
                return Response(
                    {"detail": "You are not assigned to any university."},
                    status=status.HTTP_403_FORBIDDEN
                )
            application = Application.objects.select_related(
                "destination_university", "student"
            ).filter(pk=pk, destination_university=user.host_university).first()
        else:
            application = Application.objects.select_related(
                "destination_university", "student"
            ).filter(pk=pk).first()

        if application is None:
            return Response(
                {"detail": "Application not found or not assigned to your university."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if the status transition is valid
        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"detail": "Status is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate transition
        S = Application.Status
        valid_transitions = {
            S.SUBMITTED: [S.UNDER_REVIEW, S.REJECTED],
            S.UNDER_REVIEW: [S.HOST_REVIEW, S.REJECTED],
            S.HOST_REVIEW: [S.APPROVED, S.REJECTED],
        }
        
        current_status = application.status
        allowed_next = valid_transitions.get(current_status, [])
        
        if new_status not in allowed_next:
            return Response(
                {
                    "detail": (
                        f"Invalid status transition: '{current_status}' → '{new_status}'. "
                        f"Allowed next statuses: {allowed_next}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the status
        application.status = new_status
        
        # Set timestamps
        now = timezone.now()
        if new_status == S.UNDER_REVIEW:
            application.reviewed_at = now
            application.reviewed_by = user
        elif new_status == S.HOST_REVIEW:
            application.reviewed_at = now
            application.reviewed_by = user
        elif new_status in [S.APPROVED, S.REJECTED]:
            application.decision_at = now
        
        application.save()

        # ── Send notification to student about status change ────────────────
        status_messages = {
            "UNDER_REVIEW": "Your application is now under review by the Home Admin.",
            "HOST_REVIEW": "Your application has been forwarded to the Host Coordinator for final review.",
        }
        message = status_messages.get(new_status, f"Your application status has been updated to {new_status}.")
        
        create_notification(
            user=application.student,
            notification_type=f"APPLICATION_{new_status}",
            title=f"📋 Application Status: {new_status.replace('_', ' ').title()}",
            message=message,
            link="/student",
            related_application_id=application.id
        )

        serializer = ApplicationSerializer(application, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApproveApplicationView(APIView):
    """
    POST /api/v1/applications/<id>/approve/
    Host Coordinator directly approves an application.
    Moves status to APPROVED immediately (bypasses pipeline).
    """
    permission_classes = [IsAdminOrCoordinator]

    def post(self, request, pk):
        user = request.user
        
        # Get application with filtering for coordinators
        if user.is_host_coordinator:
            if not user.host_university:
                return Response(
                    {"detail": "You are not assigned to any university."},
                    status=status.HTTP_403_FORBIDDEN
                )
            application = Application.objects.filter(
                pk=pk,
                destination_university=user.host_university
            ).first()
        else:
            application = Application.objects.filter(pk=pk).first()
        
        if application is None:
            return Response(
                {"detail": "Application not found or not assigned to your university."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can only approve applications in review stages
        if application.status not in [
            Application.Status.SUBMITTED,
            Application.Status.UNDER_REVIEW,
            Application.Status.HOST_REVIEW
        ]:
            return Response(
                {"detail": f"Application in '{application.status}' cannot be approved directly."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = Application.Status.APPROVED
        application.decision_at = timezone.now()
        application.reviewed_by = user
        application.save(update_fields=["status", "decision_at", "reviewed_by"])
        
        # ── Send notification to student ────────────────────────────────────
        create_notification(
            user=application.student,
            notification_type="APPLICATION_APPROVED",
            title="🎉 Application Approved!",
            message=f"Your application to {application.destination_university.name} has been approved by {user.get_full_name()}. Congratulations!",
            link="/student",
            related_application_id=application.id
        )
        
        # ── Send notification to coordinator ────────────────────────────────
        create_notification(
            user=user,
            notification_type="APPLICATION_APPROVED",
            title="Application Approved",
            message=f"You approved {application.student.get_full_name()}'s application to {application.destination_university.name}.",
            link=f"/coordinator",
            related_application_id=application.id
        )
        
        serializer = ApplicationSerializer(application, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RejectApplicationView(APIView):
    """
    POST /api/v1/applications/<id>/reject/
    Host Coordinator directly rejects an application.
    Requires rejection_reason in request body.
    """
    permission_classes = [IsAdminOrCoordinator]

    def post(self, request, pk):
        user = request.user
        
        # Get application with filtering for coordinators
        if user.is_host_coordinator:
            if not user.host_university:
                return Response(
                    {"detail": "You are not assigned to any university."},
                    status=status.HTTP_403_FORBIDDEN
                )
            application = Application.objects.filter(
                pk=pk,
                destination_university=user.host_university
            ).first()
        else:
            application = Application.objects.filter(pk=pk).first()
        
        if application is None:
            return Response(
                {"detail": "Application not found or not assigned to your university."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get rejection reason
        rejection_reason = request.data.get("rejection_reason")
        if not rejection_reason or not rejection_reason.strip():
            return Response(
                {"detail": "Rejection reason is mandatory."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Can only reject applications in review stages
        if application.status not in [
            Application.Status.SUBMITTED,
            Application.Status.UNDER_REVIEW,
            Application.Status.HOST_REVIEW
        ]:
            return Response(
                {"detail": f"Application in '{application.status}' cannot be rejected directly."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = Application.Status.REJECTED
        application.decision_at = timezone.now()
        application.reviewed_by = user
        application.rejection_reason = rejection_reason
        application.save(update_fields=["status", "decision_at", "reviewed_by", "rejection_reason"])
        
        # ── Send notification to student ────────────────────────────────────
        create_notification(
            user=application.student,
            notification_type="APPLICATION_REJECTED",
            title="❌ Application Rejected",
            message=f"Your application to {application.destination_university.name} has been rejected. Reason: {rejection_reason}",
            link="/student",
            related_application_id=application.id
        )
        
        # ── Send notification to coordinator ────────────────────────────────
        create_notification(
            user=user,
            notification_type="APPLICATION_REJECTED",
            title="Application Rejected",
            message=f"You rejected {application.student.get_full_name()}'s application to {application.destination_university.name}.",
            link=f"/coordinator",
            related_application_id=application.id
        )
        
        serializer = ApplicationSerializer(application, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentChecklistListView(generics.ListAPIView):
    """
    GET /api/v1/applications/<application_id>/documents/
    Returns all checklist items for an application.
    Students see only their own. Admins see all. Coordinators see their university's.
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

        if user.is_home_admin:
            return DocumentChecklist.objects.filter(
                application_id=application_id,
            ).select_related("reviewed_by")

        if user.is_host_coordinator:
            if user.host_university:
                return DocumentChecklist.objects.filter(
                    application_id=application_id,
                    application__destination_university=user.host_university,
                ).select_related("reviewed_by")
            return DocumentChecklist.objects.none()

        return DocumentChecklist.objects.none()


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


class StudentDocumentUploadView(APIView):
    """
    POST /api/v1/applications/<application_id>/upload-documents/
    Student uploads documents for their application.
    One file per document type.
    """
    permission_classes = [IsStudent]

    def post(self, request, application_id):
        # Get the application
        application = Application.objects.filter(
            pk=application_id,
            student=request.user
        ).first()
        
        if application is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get uploaded files
        files = request.FILES
        
        if not files:
            return Response(
                {"detail": "Please upload at least one document."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Map document types to file fields
        doc_type_map = {
            'passport': DocumentChecklist.DocumentType.PASSPORT_SCAN,
            'transcript': DocumentChecklist.DocumentType.ACADEMIC_TRANSCRIPT,
            'language_test': DocumentChecklist.DocumentType.LANGUAGE_TEST_RESULT,
            'personal_statement': DocumentChecklist.DocumentType.PERSONAL_STATEMENT,
            'reference_letter': DocumentChecklist.DocumentType.REFERENCE_LETTER,
            'bank_statement': DocumentChecklist.DocumentType.BANK_STATEMENT,
            'visa': DocumentChecklist.DocumentType.VISA_COPY,
            'medical': DocumentChecklist.DocumentType.MEDICAL_CLEARANCE,
            'insurance': DocumentChecklist.DocumentType.INSURANCE_PROOF,
            'housing': DocumentChecklist.DocumentType.HOUSING_CONFIRMATION,
        }
        
        uploaded_docs = []
        errors = []
        
        for field_name, file_obj in files.items():
            doc_type = doc_type_map.get(field_name.lower())
            if doc_type:
                try:
                    # Try to find existing document
                    doc_checklist = DocumentChecklist.objects.filter(
                        application=application,
                        document_type=doc_type
                    ).first()
                    
                    if doc_checklist:
                        # Update existing document
                        doc_checklist.file_attachment = file_obj
                        doc_checklist.uploaded_at = timezone.now()
                        doc_checklist.verification_status = DocumentChecklist.VerificationStatus.AWAITING_REVIEW
                        doc_checklist.save()
                    else:
                        # Create new document
                        doc_checklist = DocumentChecklist.objects.create(
                            application=application,
                            document_type=doc_type,
                            file_attachment=file_obj,
                            uploaded_at=timezone.now(),
                            verification_status=DocumentChecklist.VerificationStatus.AWAITING_REVIEW
                        )
                    
                    uploaded_docs.append(doc_checklist)
                except Exception as e:
                    errors.append(f"{field_name}: {str(e)}")
            else:
                errors.append(f"Unknown document type: {field_name}")
        
        # Send notification for upload confirmation
        if uploaded_docs:
            create_notification(
                user=request.user,
                notification_type="DOCUMENT_UPLOADED",
                title="📄 Documents Uploaded",
                message=f"Successfully uploaded {len(uploaded_docs)} document(s) for your application to {application.destination_university.name}.",
                link="/student",
                related_application_id=application.id
            )
        
        serializer = DocumentChecklistSerializer(uploaded_docs, many=True)
        
        response_data = {
            "message": f"Successfully uploaded {len(uploaded_docs)} document(s).",
            "documents": serializer.data
        }
        
        if errors:
            response_data["errors"] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)


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
        user = self.request.user
        
        if user.is_home_admin:
            return DocumentChecklist.objects.select_related(
                "application__student", "reviewed_by"
            ).all()
        
        if user.is_host_coordinator:
            if user.host_university:
                return DocumentChecklist.objects.select_related(
                    "application__student", "reviewed_by"
                ).filter(application__destination_university=user.host_university)
            return DocumentChecklist.objects.none()
        
        return DocumentChecklist.objects.none()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        old_status = instance.verification_status
        new_status = serializer.validated_data.get('verification_status')
        
        self.perform_update(serializer)
        
        # ── Send notification based on status change ────────────────────────
        if new_status and new_status != old_status:
            student = instance.application.student
            
            if new_status == DocumentChecklist.VerificationStatus.APPROVED:
                create_notification(
                    user=student,
                    notification_type="DOCUMENT_APPROVED",
                    title="✅ Document Approved",
                    message=f"Your {instance.get_document_type_display()} for {instance.application.destination_university.name} has been approved.",
                    link="/student",
                    related_application_id=instance.application.id
                )
            elif new_status == DocumentChecklist.VerificationStatus.ACTION_REQUIRED:
                admin_comment = serializer.validated_data.get('admin_comment', 'Please review and resubmit.')
                create_notification(
                    user=student,
                    notification_type="DOCUMENT_ACTION_REQUIRED",
                    title="⚠️ Document Action Required",
                    message=f"Your {instance.get_document_type_display()} needs attention: {admin_comment}",
                    link="/student",
                    related_application_id=instance.application.id
                )
        
        return Response(serializer.data)


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

        if user.is_home_admin:
            return CreditTransferLog.objects.filter(application_id=application_id)

        if user.is_host_coordinator:
            if user.host_university:
                return CreditTransferLog.objects.filter(
                    application_id=application_id,
                    application__destination_university=user.host_university,
                )
            return CreditTransferLog.objects.none()

        return CreditTransferLog.objects.none()

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
        user = self.request.user
        
        if user.is_home_admin:
            return CreditTransferLog.objects.select_related(
                "application__student", "submitted_by"
            ).all()
        
        if user.is_host_coordinator:
            if user.host_university:
                return CreditTransferLog.objects.select_related(
                    "application__student", "submitted_by"
                ).filter(application__destination_university=user.host_university)
            return CreditTransferLog.objects.none()
        
        return CreditTransferLog.objects.none()

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAdminOrCoordinator()]
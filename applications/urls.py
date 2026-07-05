from django.urls import path

from .views import (
    ApplicationListCreateView,
    ApplicationDetailView,
    SubmitApplicationView,
    AdvanceApplicationView,
    ApproveApplicationView,
    RejectApplicationView,
    DocumentChecklistListView,
    DocumentUploadView,
    StudentDocumentUploadView,
    DocumentReviewView,
    CreditTransferLogListCreateView,
    CreditTransferLogDetailView,
)

urlpatterns = [
    # ── Applications ──────────────────────────────────────────────────────────
    path("applications/", ApplicationListCreateView.as_view(), name="application-list"),
    path("applications/<int:pk>/", ApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/submit/", SubmitApplicationView.as_view(), name="application-submit"),
    path("applications/<int:pk>/advance/", AdvanceApplicationView.as_view(), name="application-advance"),
    
    # ── Approve/Reject (Host Coordinator actions) ────────────────────────────
    path("applications/<int:pk>/approve/", ApproveApplicationView.as_view(), name="application-approve"),
    path("applications/<int:pk>/reject/", RejectApplicationView.as_view(), name="application-reject"),
    
    # ── Documents ─────────────────────────────────────────────────────────────
    path(
        "applications/<int:application_id>/documents/",
        DocumentChecklistListView.as_view(),
        name="document-list",
    ),
    path("documents/<int:pk>/upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("documents/<int:pk>/review/", DocumentReviewView.as_view(), name="document-review"),
    
    # ── Student Document Upload (Bulk) ──────────────────────────────────────
    path(
        "applications/<int:application_id>/upload-documents/",
        StudentDocumentUploadView.as_view(),
        name="student-document-upload",
    ),
    
    # ── Credits ───────────────────────────────────────────────────────────────
    path(
        "applications/<int:application_id>/credits/",
        CreditTransferLogListCreateView.as_view(),
        name="credit-list",
    ),
    path("credits/<int:pk>/", CreditTransferLogDetailView.as_view(), name="credit-detail"),
]
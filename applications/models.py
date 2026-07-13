from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Application(models.Model):
    """
    The central workflow object in GlobalScholar.

    An Application links one Student to one destination University (and
    optionally a specific Program). Its 'status' field is the single source
    of truth for where in the pipeline the record sits.

    Pipeline:
        DRAFT → SUBMITTED → UNDER_REVIEW → COMPLIANCE_PHASE → APPROVED
                                                             ↘ REJECTED
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        HOST_REVIEW = "HOST_REVIEW", "Host Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    # ── Parties ───────────────────────────────────────────────────────────────
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
        limit_choices_to={"role": "STUDENT"},
    )
    destination_university = models.ForeignKey(
        "universities.University",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    program = models.ForeignKey(
        "universities.Program",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
        limit_choices_to={"role__in": ["HOME_ADMIN", "HOST_COORD"]},
        help_text="The admin or coordinator currently responsible for this application.",
    )

    # ── Pipeline state ────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    # ── Applicant's academic snapshot (captured at submission time) ────────────
    # We snapshot GPA at submission so historical records stay accurate even
    # if the student's profile GPA is later updated.
    gpa_at_submission = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Student's GPA at the time this application was submitted.",
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)

    # ── Rejection reasoning ───────────────────────────────────────────────────
    rejection_reason = models.TextField(
        blank=True,
        default="",
        help_text="Mandatory explanation populated by admin when status is set to REJECTED.",
    )

    # ── Internal notes ────────────────────────────────────────────────────────
    admin_notes = models.TextField(
        blank=True,
        default="",
        help_text="Internal notes visible only to HOME_ADMIN and HOST_COORD.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gs_applications"
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        ordering = ["-created_at"]
        # CONSTRAINT REMOVED: Students can now apply to multiple programs/universities
        # at the same time. No restriction on duplicate applications.

    def __str__(self):
        return (
            f"Application #{self.pk} | {self.student.get_full_name()} → "
            f"{self.destination_university.name} [{self.status}]"
        )

    def clean(self):
        """
        Model-level guardrail: student GPA must meet university minimum.
        Called automatically by full_clean() and by our serializer's validate().
        Using explicit if/else per architectural rules — no bare except swallowing.
        """
        if self.student_id and self.destination_university_id:
            student = self.student
            university = self.destination_university

            if student.gpa is None:
                raise ValidationError(
                    {
                        "student": (
                            "This student does not have a GPA on record. "
                            "Please update the student profile before submitting an application."
                        )
                    }
                )

            if student.gpa < university.minimum_gpa:
                raise ValidationError(
                    {
                        "gpa": (
                            f"Eligibility check failed. Student GPA ({student.gpa}) is below "
                            f"the minimum required by {university.name} ({university.minimum_gpa}). "
                            f"The student needs a GPA of at least {university.minimum_gpa} to apply."
                        )
                    }
                )


class DocumentChecklist(models.Model):
    """
    Represents a single required document for an Application.

    Rows in this table are auto-created by a post_save signal the moment
    an Application enters COMPLIANCE_PHASE. Each row tracks the upload
    state and admin verification of one document type.
    """

    class DocumentType(models.TextChoices):
        PASSPORT_SCAN = "PASSPORT_SCAN", "Passport Scan"
        VISA_COPY = "VISA_COPY", "Visa Copy"
        BANK_STATEMENT = "BANK_STATEMENT", "Bank Statement"
        ACADEMIC_TRANSCRIPT = "ACADEMIC_TRANSCRIPT", "Academic Transcript"
        LANGUAGE_TEST_RESULT = "LANGUAGE_TEST_RESULT", "Language Test Result"
        REFERENCE_LETTER = "REFERENCE_LETTER", "Reference Letter"
        PERSONAL_STATEMENT = "PERSONAL_STATEMENT", "Personal Statement"
        MEDICAL_CLEARANCE = "MEDICAL_CLEARANCE", "Medical Clearance"
        INSURANCE_PROOF = "INSURANCE_PROOF", "Proof of Health Insurance"
        HOUSING_CONFIRMATION = "HOUSING_CONFIRMATION", "Housing Confirmation Letter"

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending — Awaiting Student Upload"
        AWAITING_REVIEW = "AWAITING_REVIEW", "Awaiting Admin Review"
        APPROVED = "APPROVED", "Approved"
        ACTION_REQUIRED = "ACTION_REQUIRED", "Action Required — Resubmit"

    # ── Ownership ─────────────────────────────────────────────────────────────
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="document_checklist",
    )

    # ── Document identity ─────────────────────────────────────────────────────
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Mandatory documents block approval if not submitted and approved.",
    )

    # ── Student upload ────────────────────────────────────────────────────────
    file_attachment = models.FileField(
        upload_to="documents/%Y/%m/",
        null=True,
        blank=True,
        help_text="Uploaded by the student. Null until student uploads.",
    )
    uploaded_at = models.DateTimeField(null=True, blank=True)

    # ── Admin review ──────────────────────────────────────────────────────────
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    admin_comment = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Required when verification_status is ACTION_REQUIRED. "
            "Explains exactly what the student must correct and resubmit."
        ),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gs_document_checklist"
        verbose_name = "Document Checklist Item"
        verbose_name_plural = "Document Checklist Items"
        ordering = ["application", "document_type"]
        unique_together = [["application", "document_type"]]

    def __str__(self):
        return (
            f"{self.get_document_type_display()} | "
            f"App #{self.application_id} | {self.verification_status}"
        )

    def clean(self):
        """
        Explicit if/else guard: admin_comment is mandatory when marking
        a document as ACTION_REQUIRED. No silent failures allowed.
        """
        if self.verification_status == self.VerificationStatus.ACTION_REQUIRED:
            if not self.admin_comment or not self.admin_comment.strip():
                raise ValidationError(
                    {
                        "admin_comment": (
                            "An admin comment is mandatory when marking a document as "
                            "'Action Required'. Please provide specific instructions "
                            "so the student knows exactly what to correct and resubmit."
                        )
                    }
                )


class CreditTransferLog(models.Model):
    """
    Maps a course taken at the destination (host) university to its
    equivalent at the student's home institution for graduation credit.

    Populated by the Host Coordinator after the student's semester ends.
    """

    class TransferStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Home Institution Review"
        APPROVED = "APPROVED", "Approved for Transfer"
        DENIED = "DENIED", "Denied — Does Not Meet Requirements"
        PARTIAL = "PARTIAL", "Partial Credit Approved"

    # ── Ownership ─────────────────────────────────────────────────────────────
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="credit_transfer_logs",
    )

    # ── Host-side course ──────────────────────────────────────────────────────
    host_course_code = models.CharField(
        max_length=50,
        help_text="Course code as listed by the host university (e.g. 'CS-401').",
    )
    host_course_name = models.CharField(max_length=300)
    host_credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Number of credits awarded by the host institution.",
    )
    host_grade = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Grade received at the host institution (e.g. 'A', 'B+', '85').",
    )

    # ── Home-side mapping ─────────────────────────────────────────────────────
    home_equivalent_course_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Corresponding home institution course code this maps to.",
    )
    home_equivalent_course_name = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )
    home_credits_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Credits officially recognized by the home institution after transfer approval.",
    )

    # ── Workflow ──────────────────────────────────────────────────────────────
    transfer_status = models.CharField(
        max_length=10,
        choices=TransferStatus.choices,
        default=TransferStatus.PENDING,
        db_index=True,
    )
    denial_reason = models.TextField(
        blank=True,
        default="",
        help_text="Required if transfer_status is DENIED or PARTIAL.",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_credit_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gs_credit_transfer_logs"
        verbose_name = "Credit Transfer Log"
        verbose_name_plural = "Credit Transfer Logs"
        ordering = ["-created_at"]
        unique_together = [["application", "host_course_code"]]

    def __str__(self):
        return (
            f"{self.host_course_code} ({self.host_credits} cr) → "
            f"App #{self.application_id} [{self.transfer_status}]"
        )

    def clean(self):
        """
        Explicit if/else guard: denial_reason is mandatory when a transfer
        is denied or only partially approved.
        """
        denied_statuses = [
            self.TransferStatus.DENIED,
            self.TransferStatus.PARTIAL,
        ]
        if self.transfer_status in denied_statuses:
            if not self.denial_reason or not self.denial_reason.strip():
                raise ValidationError(
                    {
                        "denial_reason": (
                            "A denial reason is mandatory when a credit transfer is marked as "
                            f"'{self.get_transfer_status_display()}'. Please explain which "
                            "graduation requirements are not met and why the credits cannot "
                            "be fully recognized."
                        )
                    }
                )
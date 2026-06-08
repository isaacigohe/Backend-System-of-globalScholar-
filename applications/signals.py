from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Application, DocumentChecklist


# These are the documents every student must submit when entering compliance,
# regardless of destination. Extend this list or make it dynamic per-university
# in a future iteration.
UNIVERSAL_COMPLIANCE_DOCUMENTS = [
    DocumentChecklist.DocumentType.PASSPORT_SCAN,
    DocumentChecklist.DocumentType.BANK_STATEMENT,
    DocumentChecklist.DocumentType.ACADEMIC_TRANSCRIPT,
    DocumentChecklist.DocumentType.PERSONAL_STATEMENT,
    DocumentChecklist.DocumentType.REFERENCE_LETTER,
    DocumentChecklist.DocumentType.MEDICAL_CLEARANCE,
    DocumentChecklist.DocumentType.INSURANCE_PROOF,
]

# Language test is only required if the destination university flags it.
CONDITIONAL_LANGUAGE_TEST = DocumentChecklist.DocumentType.LANGUAGE_TEST_RESULT

# Visa and housing are required if the destination country differs from
# the student's home institution country. For now we always include them
# and let the admin waive them via is_mandatory=False if not applicable.
TRAVEL_DOCUMENTS = [
    DocumentChecklist.DocumentType.VISA_COPY,
    DocumentChecklist.DocumentType.HOUSING_CONFIRMATION,
]


@receiver(post_save, sender=Application)
def create_compliance_checklist(sender, instance, created, **kwargs):
    """
    Fires every time an Application is saved.

    If the application just entered COMPLIANCE_PHASE and no checklist items
    exist yet, we auto-generate the full document checklist for this student.

    Explicit if/else flow — no try/except masking logic errors.
    """
    if instance.status != Application.Status.COMPLIANCE_PHASE:
        # Application is not in compliance phase — nothing to do.
        return

    existing_count = DocumentChecklist.objects.filter(
        application=instance
    ).count()

    if existing_count > 0:
        # Checklist already exists (e.g. signal fired again on an unrelated save).
        # Do not duplicate rows.
        return

    # Build the full list of document types for this application.
    document_types_to_create = list(UNIVERSAL_COMPLIANCE_DOCUMENTS)
    document_types_to_create.extend(TRAVEL_DOCUMENTS)

    university = instance.destination_university

    if university.language_test_required:
        document_types_to_create.append(CONDITIONAL_LANGUAGE_TEST)

    # Bulk-create all checklist rows in a single database round-trip.
    checklist_items = [
        DocumentChecklist(
            application=instance,
            document_type=doc_type,
            is_mandatory=True,
            verification_status=DocumentChecklist.VerificationStatus.PENDING,
        )
        for doc_type in document_types_to_create
    ]

    DocumentChecklist.objects.bulk_create(checklist_items)
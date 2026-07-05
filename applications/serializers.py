from django.utils import timezone
from rest_framework import serializers

from users.serializers import UserPublicSerializer
from universities.serializers import UniversityListSerializer, UniversitySerializer, ProgramSerializer
from .models import Application, DocumentChecklist, CreditTransferLog


class DocumentChecklistSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    document_type_display = serializers.SerializerMethodField()

    class Meta:
        model = DocumentChecklist
        fields = [
            "id", "application", "document_type", "document_type_display", 
            "is_mandatory", "file_attachment", "uploaded_at",
            "verification_status", "status_display", "admin_comment",
            "reviewed_by", "reviewed_by_name", "reviewed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "application", "document_type", "is_mandatory",
            "reviewed_by", "reviewed_by_name", "reviewed_at",
            "created_at", "updated_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name()
        return None
    
    def get_status_display(self, obj):
        return obj.get_verification_status_display()
    
    def get_document_type_display(self, obj):
        return obj.get_document_type_display()

    def validate(self, attrs):
        verification_status = attrs.get(
            "verification_status",
            self.instance.verification_status if self.instance else None,
        )
        admin_comment = attrs.get(
            "admin_comment",
            self.instance.admin_comment if self.instance else "",
        )

        if verification_status == DocumentChecklist.VerificationStatus.ACTION_REQUIRED:
            if not admin_comment or not admin_comment.strip():
                raise serializers.ValidationError(
                    {
                        "admin_comment": (
                            "An admin comment is mandatory when marking a document as "
                            "'Action Required'. Provide specific instructions so the "
                            "student knows exactly what to correct and resubmit."
                        )
                    }
                )
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")

        new_status = validated_data.get("verification_status")
        if new_status and new_status != instance.verification_status:
            if request and request.user.is_authenticated:
                validated_data["reviewed_by"] = request.user
                validated_data["reviewed_at"] = timezone.now()

        if "file_attachment" in validated_data and validated_data["file_attachment"]:
            validated_data["uploaded_at"] = timezone.now()
            validated_data["verification_status"] = (
                DocumentChecklist.VerificationStatus.AWAITING_REVIEW
            )

        return super().update(instance, validated_data)


class CreditTransferLogSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.SerializerMethodField()
    transfer_status_display = serializers.SerializerMethodField()

    class Meta:
        model = CreditTransferLog
        fields = [
            "id", "application",
            "host_course_code", "host_course_name", "host_credits", "host_grade",
            "home_equivalent_course_code", "home_equivalent_course_name",
            "home_credits_awarded", "transfer_status", "transfer_status_display", 
            "denial_reason",
            "submitted_by", "submitted_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "submitted_by", "submitted_by_name", "created_at", "updated_at"]

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.get_full_name()
        return None
    
    def get_transfer_status_display(self, obj):
        return obj.get_transfer_status_display()

    def validate(self, attrs):
        transfer_status = attrs.get(
            "transfer_status",
            self.instance.transfer_status if self.instance else None,
        )
        denial_reason = attrs.get(
            "denial_reason",
            self.instance.denial_reason if self.instance else "",
        )

        denied_statuses = [
            CreditTransferLog.TransferStatus.DENIED,
            CreditTransferLog.TransferStatus.PARTIAL,
        ]

        if transfer_status in denied_statuses:
            if not denial_reason or not denial_reason.strip():
                raise serializers.ValidationError(
                    {
                        "denial_reason": (
                            "A denial reason is mandatory when a credit transfer is "
                            "marked as Denied or Partial. Explain which requirements "
                            "are not met."
                        )
                    }
                )

        if attrs.get("host_credits") is not None and attrs["host_credits"] <= 0:
            raise serializers.ValidationError(
                {"host_credits": "Host credits must be a positive number."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["submitted_by"] = request.user
        return super().create(validated_data)


class ApplicationSerializer(serializers.ModelSerializer):
    """
    FULL detail serializer for application detail page.
    Includes complete university details, programs, documents, and credits.
    """
    student_detail = UserPublicSerializer(source="student", read_only=True)
    university_detail = UniversitySerializer(
        source="destination_university", read_only=True
    )
    program_detail = ProgramSerializer(source="program", read_only=True)
    document_checklist = DocumentChecklistSerializer(many=True, read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "student", "student_detail",
            "destination_university", "university_detail",
            "program", "program_detail",
            "reviewed_by", "reviewed_by_name",
            "status", "status_display",
            "gpa_at_submission",
            "submitted_at", "reviewed_at", "decision_at",
            "rejection_reason", "admin_notes",
            "document_checklist",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "student", "student_detail", "university_detail", "program_detail",
            "reviewed_by", "reviewed_by_name",
            "gpa_at_submission", "submitted_at", "reviewed_at", "decision_at",
            "document_checklist", "created_at", "updated_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name()
        return None
    
    def get_status_display(self, obj):
        return obj.get_status_display()

    def validate(self, attrs):
        request = self.context.get("request")
        student = request.user if request else None

        if self.instance is None:
            destination_university = attrs.get("destination_university")

            if student is None or not student.is_student:
                raise serializers.ValidationError(
                    "Only students can create applications."
                )

            if student.requires_gpa_check:
                if student.gpa is None:
                    raise serializers.ValidationError(
                        {
                            "student": (
                                "Your profile does not have a GPA on record. "
                                "Please update your profile before applying."
                            )
                        }
                    )

                if destination_university is not None:
                    if student.gpa < destination_university.minimum_gpa:
                        raise serializers.ValidationError(
                            {
                                "gpa": (
                                    f"Your GPA ({student.gpa}) does not meet the minimum "
                                    f"required by {destination_university.name} "
                                    f"({destination_university.minimum_gpa}). "
                                    f"You need at least {destination_university.minimum_gpa} to apply."
                                )
                            }
                        )

        new_status = attrs.get("status")
        if new_status and self.instance:
            current_status = self.instance.status
            self._validate_status_transition(current_status, new_status, attrs)

        return attrs

    def _validate_status_transition(self, current_status, new_status, attrs):
        S = Application.Status

        valid_transitions = {
            S.DRAFT: [S.SUBMITTED],
            S.SUBMITTED: [S.UNDER_REVIEW, S.REJECTED],
            S.UNDER_REVIEW: [S.COMPLIANCE_PHASE, S.REJECTED],
            S.COMPLIANCE_PHASE: [S.APPROVED, S.REJECTED],
            S.APPROVED: [],
            S.REJECTED: [],
        }

        allowed_next = valid_transitions.get(current_status, [])

        if new_status not in allowed_next:
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Invalid status transition: '{current_status}' → '{new_status}'. "
                        f"Allowed next statuses from '{current_status}': "
                        f"{[s for s in allowed_next] if allowed_next else 'none (terminal state)'}."
                    )
                }
            )

        if new_status == S.REJECTED:
            rejection_reason = attrs.get(
                "rejection_reason",
                self.instance.rejection_reason if self.instance else "",
            )
            if not rejection_reason or not rejection_reason.strip():
                raise serializers.ValidationError(
                    {
                        "rejection_reason": (
                            "A rejection reason is mandatory when rejecting an application."
                        )
                    }
                )

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["student"] = request.user
        validated_data["gpa_at_submission"] = request.user.gpa
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_status = validated_data.get("status")
        now = timezone.now()

        if new_status and new_status != instance.status:
            S = Application.Status

            if new_status == S.SUBMITTED:
                validated_data["submitted_at"] = now
                validated_data["gpa_at_submission"] = instance.student.gpa

            elif new_status == S.UNDER_REVIEW:
                validated_data["reviewed_at"] = now
                request = self.context.get("request")
                if request and request.user.is_authenticated:
                    validated_data["reviewed_by"] = request.user

            elif new_status in [S.APPROVED, S.REJECTED]:
                validated_data["decision_at"] = now

        return super().update(instance, validated_data)


class ApplicationListSerializer(serializers.ModelSerializer):
    """
    LIGHTWEIGHT serializer for dashboard list views.
    Includes enough info for the dashboard cards.
    """
    student_name = serializers.SerializerMethodField()
    university_name = serializers.SerializerMethodField()
    university_country = serializers.SerializerMethodField()
    university_city = serializers.SerializerMethodField()
    university_image = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "student", "student_name",
            "destination_university", "university_name", 
            "university_country", "university_city", "university_image",
            "program", "program_name",
            "status", "status_display",
            "gpa_at_submission", "submitted_at", "created_at",
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name()

    def get_university_name(self, obj):
        return obj.destination_university.name

    def get_university_country(self, obj):
        return obj.destination_university.country
    
    def get_university_city(self, obj):
        return obj.destination_university.city or ""
    
    def get_university_image(self, obj):
        request = self.context.get('request')
        if obj.destination_university.image:
            if request:
                return request.build_absolute_uri(obj.destination_university.image.url)
            return obj.destination_university.image.url
        return None
    
    def get_program_name(self, obj):
        if obj.program:
            return obj.program.name
        return None
    
    def get_status_display(self, obj):
        return obj.get_status_display()
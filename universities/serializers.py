from rest_framework import serializers
from .models import University, Program


class ProgramSerializer(serializers.ModelSerializer):
    # ── Make description optional ──────────────────────────────────────────
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default='',
        help_text="Brief description of the program, benefits, and what students can expect."
    )

    class Meta:
        model = Program
        fields = [
            "id", "university", "name", "degree_level", "duration_semesters",
            "tuition_per_semester_usd", "credits_transferable",
            "application_deadline", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_duration_semesters(self, value):
        if value < 1 or value > 20:
            raise serializers.ValidationError(
                "Duration must be between 1 and 20 semesters."
            )
        return value

    def validate_tuition_per_semester_usd(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Tuition cannot be a negative value."
            )
        return value

    def create(self, validated_data):
        # If description is not provided, set it to empty string
        if 'description' not in validated_data or validated_data.get('description') is None:
            validated_data['description'] = ''
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # If description is not provided in update, keep existing
        if 'description' not in validated_data:
            validated_data['description'] = instance.description
        return super().update(instance, validated_data)


class UniversitySerializer(serializers.ModelSerializer):
    """
    FULL detail serializer for university detail page.
    Includes ALL programs and complete university information.
    """
    programs = ProgramSerializer(many=True, read_only=True)
    program_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = [
            "id", "name", "display_name", "country", "city", "location", "website",
            "image", "image_url",
            "minimum_gpa", "primary_language",
            "language_test_required", "minimum_language_score",
            "max_international_students",
            "travel_advisory_level", "advisory_last_updated",
            "program_count", "programs",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "travel_advisory_level", "advisory_last_updated",
            "created_at", "updated_at",
        ]

    def get_program_count(self, obj):
        return obj.programs.count()
    
    def get_image_url(self, obj):
        """Return the full URL for the university image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_display_name(self, obj):
        """Return formatted display name"""
        return obj.name
    
    def get_location(self, obj):
        """Return formatted location (city, country)"""
        if obj.city:
            return f"{obj.city}, {obj.country}"
        return obj.country

    def validate_minimum_gpa(self, value):
        if value < 0 or value > 4.0:
            raise serializers.ValidationError(
                "Minimum GPA must be between 0.00 and 4.00."
            )
        return value

    def validate_minimum_language_score(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Language score cannot be negative."
            )
        return value


class UniversityListSerializer(serializers.ModelSerializer):
    """
    LIGHTWEIGHT serializer for landing page list views.
    Fast and small - only essential fields for browsing.
    """
    program_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = [
            "id", "name", "display_name", "country", "city", "location",
            "image_url", "minimum_gpa", "primary_language",
            "travel_advisory_level", "program_count",
        ]

    def get_program_count(self, obj):
        return obj.programs.count()
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_location(self, obj):
        if obj.city:
            return f"{obj.city}, {obj.country}"
        return obj.country
    
    def get_display_name(self, obj):
        return obj.name
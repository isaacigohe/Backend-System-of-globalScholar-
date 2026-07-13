from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from universities.models import University

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    host_university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=False,
        allow_null=True,
        help_text="Required for HOST_COORD - select your university"
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name', 'last_name', 
            'role', 'host_university',
            'gpa', 'major', 'home_institution', 'enrollment_year', 'student_type'
        ]

    def validate(self, attrs):
        role = attrs.get('role')
        host_university = attrs.get('host_university')
        
        # ── Block registration as SUPER_ADMIN ──────────────────────────────────
        if role == User.Role.SUPER_ADMIN:
            raise serializers.ValidationError({
                'role': 'Super Admin accounts cannot be created through registration.'
            })
        
        # ── HOST_COORD MUST select a university ────────────────────────────────
        if role == User.Role.HOST_COORD:
            if not host_university:
                raise serializers.ValidationError({
                    'host_university': 'Host Coordinators must select the university they represent.'
                })
            attrs['is_verified'] = False  # Needs Super Admin approval
        
        # ── HOME_ADMIN needs verification ──────────────────────────────────────
        elif role == User.Role.HOME_ADMIN:
            attrs['is_verified'] = False  # Needs Super Admin approval
        
        # ── STUDENT auto-verified ──────────────────────────────────────────────
        elif role == User.Role.STUDENT:
            if not attrs.get('student_type'):
                raise serializers.ValidationError({
                    'student_type': 'Student type is required for students.'
                })
            attrs['is_verified'] = True
        
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ... rest of serializers remain the same
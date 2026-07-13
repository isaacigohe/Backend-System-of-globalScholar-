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
        help_text="Required for HOST_COORD - the university they represent."
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
        
        # ── Block registration as SUPER_ADMIN ──────────────────────────────────
        if role == User.Role.SUPER_ADMIN:
            raise serializers.ValidationError({
                'role': 'Super Admin accounts cannot be created through registration.'
            })
        
        # ── HOST_COORD requires a university ────────────────────────────────────
        if role == User.Role.HOST_COORD:
            if not attrs.get('host_university'):
                raise serializers.ValidationError({
                    'host_university': 'Host Coordinators must select the university they represent.'
                })
            attrs['is_verified'] = False
        
        # ── HOME_ADMIN needs verification ────────────────────────────────────────
        if role == User.Role.HOME_ADMIN:
            attrs['is_verified'] = False
        
        # ── STUDENT auto-verified ──────────────────────────────────────────────
        if role == User.Role.STUDENT:
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


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_verified_display = serializers.SerializerMethodField()
    host_university_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role',
            'host_university', 'host_university_name',
            'gpa', 'major', 'home_institution', 'enrollment_year', 'student_type',
            'is_verified', 'is_verified_display', 'verified_at',
            'date_joined'
        ]
        read_only_fields = ['id', 'email', 'role', 'date_joined', 'is_verified', 'verified_at']

    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_is_verified_display(self, obj):
        return "Verified" if obj.is_verified else "Pending Verification"
    
    def get_host_university_name(self, obj):
        if obj.host_university:
            return obj.host_university.name
        return None


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profiles with role-based permissions"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 
            'gpa', 'major', 'home_institution', 'enrollment_year', 'student_type'
        ]
        
    def validate(self, attrs):
        user = self.instance
        role = user.role
        
        # Host Coordinators cannot change university through profile
        if role == User.Role.HOST_COORD:
            if 'host_university' in attrs:
                raise serializers.ValidationError({
                    'host_university': 'Host Coordinators cannot change their assigned university.'
                })
        
        # Students must have student_type if they are updating student fields
        if role == User.Role.STUDENT:
            if 'student_type' in attrs and not attrs.get('student_type'):
                raise serializers.ValidationError({
                    'student_type': 'Student type is required for students.'
                })
        
        return attrs


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role']

    def get_full_name(self, obj):
        return obj.get_full_name()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Check if user is verified (for HOME_ADMIN and HOST_COORD)
        if self.user.role in [User.Role.HOME_ADMIN, User.Role.HOST_COORD]:
            if not self.user.is_verified:
                raise serializers.ValidationError({
                    'detail': 'Your account is pending verification by a Super Admin. Please wait for approval.',
                    'requires_verification': True
                })
        
        # Add user info to token response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'full_name': self.user.get_full_name(),
            'role': self.user.role,
            'is_verified': self.user.is_verified,
            'host_university': self.user.host_university_id if self.user.host_university else None,
            'host_university_name': self.user.host_university.name if self.user.host_university else None,
        }
        
        return data


# ── Super Admin Serializers ──────────────────────────────────────────────────
class AdminVerificationSerializer(serializers.Serializer):
    """Serializer for verifying/rejecting admins"""
    user_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=['verify', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)
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
        help_text="Required if role is HOST_COORD"
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
        
        # Host Coordinators MUST have a host_university
        if role == User.Role.HOST_COORD and not host_university:
            raise serializers.ValidationError({
                'host_university': 'Host Coordinators must select a university.'
            })
        
        # Students must have student-specific fields
        if role == User.Role.STUDENT:
            if not attrs.get('student_type'):
                raise serializers.ValidationError({
                    'student_type': 'Student type is required for students.'
                })
        
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'host_university',
            'gpa', 'major', 'home_institution', 'enrollment_year', 'student_type',
            'date_joined'
        ]
        read_only_fields = ['id', 'email', 'role', 'date_joined']


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role']

    def get_full_name(self, obj):
        return obj.get_full_name()


class GlobalScholarTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user info to token response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'host_university': self.user.host_university_id if self.user.host_university else None,
        }
        
        return data              
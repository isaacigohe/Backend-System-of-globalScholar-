from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Used for POST /api/v1/auth/register/
    Handles creation of all three role types with role-specific validation.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields  = [
            "id", "email", "first_name", "last_name", "role",
            "password", "password_confirm",
            "gpa", "major", "home_institution", "enrollment_year",
            "student_type",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        # ── Password match ─────────────────────────────────────────────────
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        role = attrs.get("role", User.Role.STUDENT)
            
        
    # ── Student-specific mandatory fields ──────────────────────────────
        if role == User.Role.STUDENT:
            student_type = attrs.get("student_type", User.StudentType.UNDERGRADUATE)

            # University students must provide GPA and major
            university_types = [
                User.StudentType.UNDERGRADUATE,
                User.StudentType.POSTGRADUATE,
            ]

            if student_type in university_types:
                if not attrs.get("gpa"):
                    raise serializers.ValidationError(
                        {"gpa": "GPA is required for undergraduate and postgraduate students."}
                    )
                if attrs.get("gpa") and (attrs["gpa"] < 0 or attrs["gpa"] > 4.0):
                    raise serializers.ValidationError(
                        {"gpa": "GPA must be between 0.00 and 4.00."}
                    )
                if not attrs.get("major"):
                    raise serializers.ValidationError(
                        {"major": "Major is required for undergraduate and postgraduate students."}
                    )
                if not attrs.get("home_institution"):
                    raise serializers.ValidationError(
                        {"home_institution": "Home institution is required for undergraduate and postgraduate students."}
                    )
            else:
                # High school and independent learners — GPA and major are optional
                # home_institution is still useful but not mandatory
                if attrs.get("gpa") and (attrs["gpa"] < 0 or attrs["gpa"] > 4.0):
                    raise serializers.ValidationError(
                        {"gpa": "GPA must be between 0.00 and 4.00 if provided."}
                    )

        else:
            if attrs.get("gpa") is not None:
                raise serializers.ValidationError(
                    {"gpa": "GPA is only applicable to Student accounts."}
                )
            if attrs.get("major"):
                raise serializers.ValidationError(
                    {"major": "Major is only applicable to Student accounts."}
                )

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Safe read-only representation. Returned in nested contexts (e.g. inside
    ApplicationSerializer) where we want identity info but not credentials.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Used for GET/PATCH /api/v1/users/me/
    Students can update their own profile. Admins cannot change their role
    here — that requires a separate admin action.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name", "role",
            "gpa", "major", "home_institution", "enrollment_year", "student_type", "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "date_joined", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def validate(self, attrs):
        user = self.instance

        if user.is_student:
            gpa = attrs.get("gpa", user.gpa)
            if gpa is not None:
                if gpa < 0 or gpa > 4.0:
                    raise serializers.ValidationError(
                        {"gpa": "GPA must be between 0.00 and 4.00."}
                    )
        else:
            if attrs.get("gpa") is not None:
                raise serializers.ValidationError(
                    {"gpa": "Only students have a GPA field."}
                )

        return attrs


class GlobalScholarTokenSerializer(TokenObtainPairSerializer):
    """
    Extends SimpleJWT's default token serializer to embed role and name
    directly in the token payload so the frontend doesn't need a second
    /me/ call just to know who logged in.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name()
        token["email"] = user.email
        return token
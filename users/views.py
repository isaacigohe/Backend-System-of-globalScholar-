from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    CustomTokenObtainPairSerializer,
)
from .throttles import LoginRateThrottle
from .permissions import IsSuperAdmin

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Open endpoint — no authentication required.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh JWT tokens.
    Throttled to 5 requests/min via LoginRateThrottle.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return response


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the refresh token so it cannot be reused.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "A refresh token is required to log out."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT,
        )


class MyProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/users/me/   — returns the authenticated user's profile
    PATCH /api/v1/users/me/  — updates allowed fields
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class UpdateProfileView(generics.UpdateAPIView):
    """
    PATCH /api/v1/users/update-profile/
    Allow users to update their profile information.
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# ── SUPER ADMIN VIEWS ─────────────────────────────────────────────────────────

class UnverifiedAdminsListView(generics.ListAPIView):
    """
    GET /api/v1/users/unverified-admins/
    Returns all unverified HOME_ADMIN and HOST_COORD users.
    Super Admin only.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        # ── FIX: Get ALL unverified admins ──────────────────────────────────
        queryset = User.objects.filter(
            role__in=[User.Role.HOME_ADMIN, User.Role.HOST_COORD],
            is_verified=False,
            is_active=True
        ).select_related('host_university', 'verified_by').order_by('-date_joined')
        
        print(f"🔍 Found {queryset.count()} unverified admins")  # Debug log
        return queryset


class VerifyAdminView(APIView):
    """
    POST /api/v1/users/<user_id>/verify/
    Super Admin verifies a HOME_ADMIN or HOST_COORD user.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if user.role not in [User.Role.HOME_ADMIN, User.Role.HOST_COORD]:
            return Response(
                {"detail": f"User with role '{user.role}' cannot be verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.is_verified:
            return Response(
                {"detail": "User is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_verified = True
        user.verified_by = request.user
        user.verified_at = timezone.now()
        user.save()
        
        try:
            from notifications.utils import create_notification
            create_notification(
                user=user,
                notification_type="ADMIN_VERIFIED",
                title="✅ Account Verified",
                message=f"Your {user.get_role_display()} account has been verified by {request.user.get_full_name()}. You can now access the admin dashboard.",
                link="/login",
            )
            create_notification(
                user=request.user,
                notification_type="ADMIN_VERIFIED",
                title="✅ Admin Verified",
                message=f"You verified {user.get_full_name()} ({user.email}) as a {user.get_role_display()}.",
                link="/super-admin",
            )
        except ImportError:
            pass
        
        return Response({
            "detail": f"{user.get_full_name()} has been verified.",
            "user": UserProfileSerializer(user).data
        })


class RejectAdminView(APIView):
    """
    POST /api/v1/users/<user_id>/reject/
    Super Admin rejects/deletes an unverified HOME_ADMIN or HOST_COORD user.
    """
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if user.role not in [User.Role.HOME_ADMIN, User.Role.HOST_COORD]:
            return Response(
                {"detail": f"User with role '{user.role}' cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.is_verified:
            return Response(
                {"detail": "Verified users cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from notifications.utils import create_notification
            create_notification(
                user=user,
                notification_type="ADMIN_REJECTED",
                title="❌ Account Rejected",
                message=f"Your {user.get_role_display()} account registration has been rejected by {request.user.get_full_name()}. Please contact support if you believe this is an error.",
                link="/register",
            )
        except ImportError:
            pass
        
        user.delete()
        
        return Response({
            "detail": f"Unverified admin {user.get_full_name()} has been rejected and removed."
        })


class SearchUsersView(generics.ListAPIView):
    """
    GET /api/v1/users/search/?q=search_term
    Search for users by email or name. Super Admin only.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return User.objects.none()
        
        return User.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).select_related('host_university', 'verified_by')


class AllUsersView(generics.ListAPIView):
    """
    GET /api/v1/users/all/
    Get all users with filtering by role. Super Admin only.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        queryset = User.objects.all().select_related('host_university', 'verified_by')
        role_filter = self.request.query_params.get('role')
        if role_filter:
            queryset = queryset.filter(role=role_filter)
        return queryset
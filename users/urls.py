from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    MyProfileView,
    UnverifiedAdminsListView,
    VerifyAdminView,
    RejectAdminView,
    SearchUsersView,
    AllUsersView,
)

urlpatterns = [
    # ── Authentication ─────────────────────────────────────────────────────────
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # ── User Profile ──────────────────────────────────────────────────────────
    path("users/me/", MyProfileView.as_view(), name="user-me"),

    # ── Super Admin Routes ────────────────────────────────────────────────────
    path("users/unverified-admins/", UnverifiedAdminsListView.as_view(), name="unverified-admins"),
    path("users/<int:user_id>/verify/", VerifyAdminView.as_view(), name="verify-admin"),
    path("users/<int:user_id>/reject/", RejectAdminView.as_view(), name="reject-admin"),
    path("users/search/", SearchUsersView.as_view(), name="search-users"),
    path("users/all/", AllUsersView.as_view(), name="all-users"),
]
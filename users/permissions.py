from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model

User = get_user_model()


class IsStudent(BasePermission):
    """Allows access only to users with the STUDENT role."""
    message = "Access restricted to Students only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_student
        )


class IsHomeAdmin(BasePermission):
    """Allows access only to users with the HOME_ADMIN role."""
    message = "Access restricted to Home Administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_home_admin
        )


class IsHostCoordinator(BasePermission):
    """Allows access only to users with the HOST_COORD role."""
    message = "Access restricted to Host Coordinators only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_host_coordinator
        )


class IsSuperAdmin(BasePermission):
    """Allows access only to users with the SUPER_ADMIN role."""
    message = "Access restricted to Super Administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_super_admin
        )


class IsAdminOrCoordinator(BasePermission):
    """Allows access to HOME_ADMIN or HOST_COORD — staff roles."""
    message = "Access restricted to administrative staff only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_home_admin or request.user.is_host_coordinator)
        )


class IsAdminOrSuperAdmin(BasePermission):
    """Allows access to HOME_ADMIN or SUPER_ADMIN."""
    message = "Access restricted to Administrators or Super Administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_home_admin or request.user.is_super_admin)
        )


class IsCoordinatorOrSuperAdmin(BasePermission):
    """Allows access to HOST_COORD or SUPER_ADMIN."""
    message = "Access restricted to Coordinators or Super Administrators only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_host_coordinator or request.user.is_super_admin)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission.
    Students can only access their own objects.
    Admins and coordinators can access any object.
    Super Admins can access any object.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        # Super Admin, Home Admin, and Host Coordinator have full access
        if request.user.is_super_admin or request.user.is_home_admin or request.user.is_host_coordinator:
            return True

        # For Application objects
        if hasattr(obj, "student"):
            return obj.student == request.user

        # For DocumentChecklist objects (go through application)
        if hasattr(obj, "application"):
            return obj.application.student == request.user

        # For CreditTransferLog objects
        if hasattr(obj, "application"):
            return obj.application.student == request.user

        # For User objects
        if hasattr(obj, "id"):
            return obj.id == request.user.id

        return False


class IsVerifiedAdmin(BasePermission):
    """
    Allows access only to verified HOME_ADMIN and HOST_COORD users.
    Unverified admins cannot access admin features.
    """
    message = "Your admin account is pending verification. Please wait for approval."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super Admin is always allowed
        if request.user.is_super_admin:
            return True
        
        # HOME_ADMIN and HOST_COORD must be verified
        if request.user.is_home_admin or request.user.is_host_coordinator:
            return request.user.is_verified
        
        # STUDENT doesn't need verification for this permission
        return True


class IsVerifiedHomeAdmin(BasePermission):
    """
    Allows access only to verified HOME_ADMIN users.
    """
    message = "Access restricted to verified Home Administrators only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return bool(
            request.user.is_home_admin and
            request.user.is_verified
        )


class IsVerifiedHostCoordinator(BasePermission):
    """
    Allows access only to verified HOST_COORD users.
    """
    message = "Access restricted to verified Host Coordinators only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return bool(
            request.user.is_host_coordinator and
            request.user.is_verified
        )
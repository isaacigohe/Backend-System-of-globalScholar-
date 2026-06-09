from rest_framework.permissions import BasePermission


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


class IsAdminOrCoordinator(BasePermission):
    """Allows access to HOME_ADMIN or HOST_COORD — staff roles."""
    message = "Access restricted to administrative staff only."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_home_admin or request.user.is_host_coordinator)
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission.
    Students can only access their own objects.
    Admins and coordinators can access any object.
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.is_home_admin or request.user.is_host_coordinator:
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

        return False
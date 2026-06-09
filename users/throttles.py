from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """
    Limits login attempts to 5 per minute per IP address.
    Applied directly on the token obtain view.
    Rate is defined in settings.DEFAULT_THROTTLE_RATES['login'].
    """
    scope = "login"


class FileUploadRateThrottle(ScopedRateThrottle):
    """
    Limits document upload submissions to 3 per minute per authenticated user.
    Applied on the DocumentChecklist upload view.
    Rate is defined in settings.DEFAULT_THROTTLE_RATES['file_upload'].
    """
    scope = "file_upload"
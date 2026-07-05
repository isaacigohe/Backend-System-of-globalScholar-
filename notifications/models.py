from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """
    System notifications for users (students, admins, coordinators).
    """
    
    class NotificationType(models.TextChoices):
        APPLICATION_APPROVED = "APPLICATION_APPROVED", "Application Approved"
        APPLICATION_REJECTED = "APPLICATION_REJECTED", "Application Rejected"
        APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED", "Application Submitted"
        APPLICATION_UNDER_REVIEW = "APPLICATION_UNDER_REVIEW", "Application Under Review"
        DOCUMENT_APPROVED = "DOCUMENT_APPROVED", "Document Approved"
        DOCUMENT_ACTION_REQUIRED = "DOCUMENT_ACTION_REQUIRED", "Document Action Required"
        CREDIT_TRANSFER_APPROVED = "CREDIT_TRANSFER_APPROVED", "Credit Transfer Approved"
        MESSAGE = "MESSAGE", "General Message"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(blank=True, default="")
    is_read = models.BooleanField(default=False)
    related_application_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gs_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.notification_type} - {self.created_at}"
from .models import Notification


def create_notification(user, notification_type, title, message, link="", related_application_id=None):
    """
    Helper function to create a notification.
    """
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        related_application_id=related_application_id
    )
    return notification
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "message", 
            "link", "is_read", "related_application_id", "created_at"
        ]
        read_only_fields = ["id", "created_at"]
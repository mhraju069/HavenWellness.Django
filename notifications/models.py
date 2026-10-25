from django.db import models
from django.conf import settings


class Device(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.token[:20]}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('general', 'General'),
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('system', 'System'),
        ('reminder', 'Reminder'),
    )

    AUDIENCE_CHOICES = (
        ('user', 'User Specific'),
        ('admin', 'Admin Only'),
        ('all', 'All Users'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='user', help_text="Target audience: user, admin, or all")
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    link = models.CharField(max_length=500, null=True, blank=True, help_text="Direct target link/path for frontend redirection")

    data = models.JSONField(default=dict, blank=True, help_text="Extra payload such as booking_id, details, etc.")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.title} ({'Read' if self.is_read else 'Unread'})"
from django.db import models
from django.conf import settings

# Create your models here.

class SupportChat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_chats")
    status = models.CharField(max_length=20, choices=[('open', 'Open'), ('closed', 'Closed')], default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat {self.id} - {self.user.username}"


class SupportMessage(models.Model):
    TYPE_CHOICES = [('user', 'User'),('admin', 'Admin'),]
    message = models.TextField()
    chat = models.ForeignKey(SupportChat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message {self.id} - {self.sender.username} - {self.type}"

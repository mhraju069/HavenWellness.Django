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


class TermsAndConditions(models.Model):
    effective_date = models.DateField(blank=True, null=True)
    acceptance_of_terms = models.TextField(blank=True, null=True)
    user_responsibilities = models.TextField(blank=True, null=True)
    ticket_purchase = models.TextField(blank=True, null=True)
    refund_policy = models.TextField(blank=True, null=True)
    limitation_of_liability = models.TextField(blank=True, null=True)
    changes_to_terms = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Terms and Conditions"


class PrivacyPolicy(models.Model):
    effective_date = models.DateField(blank=True, null=True)
    info_we_collect = models.TextField(blank=True, null=True)
    how_we_use_data = models.TextField(blank=True, null=True)
    child_safety = models.TextField(blank=True, null=True)
    user_rights = models.TextField(blank=True, null=True)
    security = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Privacy Policy"


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question


class ContactInfo(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=255)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


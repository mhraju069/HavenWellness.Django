from django.db import models
from django.conf import settings

# Create your models here.


class SupportMessage(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages"
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        sender_name = self.name or (self.sender.username if self.sender else "Anonymous")
        return f"Message {self.id} from {sender_name}"


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
    email = models.EmailField()
    phone = models.CharField(max_length=255)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Contact Info ({self.email})"


class SocialMediaLink(models.Model):
    MEDIA_CHOICES = (
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter')
    )
    media_type = models.CharField(max_length=255, choices=MEDIA_CHOICES, unique=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.media_type
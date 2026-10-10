from django.db import models
from django.utils import timezone
from django.conf import settings

class SessionPass(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    entry_limit = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.price}"


class SessionPassFeatures(models.Model):
    session_pass = models.ForeignKey(SessionPass, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.feature} - {self.session_pass.name}"


class SubscriptionPlans(models.Model):
    PLAN_TYPE = (
        ('weekly','Weekly'),
        ('unlimited','Unlimited'),
    )
    PLAN_CATEGORY = (
        ('sauna','Sauna'),
        ('saltroom','Saltroom'),
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE, default='weekly')
    plan_category = models.CharField(max_length=20, choices=PLAN_CATEGORY, default='sauna')
    max_reservations = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.price}"


class SubscriptionPlanFeatures(models.Model):
    subscription_plan = models.ForeignKey(SubscriptionPlans, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.feature} - {self.subscription_plan.name}"


class Payments(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    BOOKING_CATEGORY = (
        ('sauna', 'Sauna'),
        ('saltroom', 'Saltroom'),
        ('activities', 'Activities'),
    )

    booking_id = models.CharField(max_length=100, db_index=True)
    booking_type = models.CharField(max_length=20, choices=BOOKING_CATEGORY, default='sauna')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='eur')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    client_secret = models.TextField(null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_id} | {self.amount} {self.currency} | {self.payment_status}"
from requests import packages
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
    max_reservations = models.PositiveIntegerField(default=10, help_text="Max concurrent active reservations for unlimited plan")
    duration_weeks = models.PositiveIntegerField(default=4, help_text="Duration of subscription in weeks (default: 4 weeks)")
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
        ('packages', 'Packages'),
        ('session_pass', 'Session Pass'),
        ('subscription', 'Subscription'),
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


class ClientPurchase(models.Model):
    PURCHASE_TYPE = (
        ('session_pass', 'Session Pass'),
        ('subscription', 'Subscription'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    purchase_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    purchase_type = models.CharField(max_length=20, choices=PURCHASE_TYPE)

    session_pass = models.ForeignKey(SessionPass, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    subscription_plan = models.ForeignKey(SubscriptionPlans, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='eur')

    # Validity & Limits
    start_date = models.DateTimeField(null=True, blank=True, help_text="Activation/start date (when purchased or paid)")
    end_date = models.DateTimeField(null=True, blank=True, help_text="End/expiry date (null for 10 Session Pass; 4 weeks from start for Subscriptions)")

    total_sessions = models.PositiveIntegerField(default=0, help_text="Total sessions allowed (10 for session pass; 4 for weekly subscription; 0 for unlimited)")
    remaining_sessions = models.PositiveIntegerField(default=0, help_text="Remaining sessions left to book (for session pass or weekly)")
    sessions_per_week = models.PositiveIntegerField(default=0, help_text="1 for once-a-week subscription; 0 for session pass or unlimited")
    max_active_reservations = models.PositiveIntegerField(default=0, help_text="Max concurrent active bookings (e.g. 10 for Unlimited, 1 for Weekly)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def booking_id(self):
        return self.purchase_id

    @property
    def total_price(self):
        return self.amount

    @property
    def is_expired(self):
        if self.end_date:
            return timezone.now() > self.end_date
        return False

    def __str__(self):
        return f"{self.purchase_id} | {self.purchase_type} | {self.name} | {self.payment_status}"

    def calculate_validity_and_limits(self, base_time=None):
        """
        Calculates and populates start_date, end_date, sessions, and limits based on pass or plan type.
        - Session Pass: No end_date, total_sessions = 10, remaining_sessions = 10.
        - Once a week subscription: 4 weeks duration, 1 session/week (total 4), max 1 concurrent reservation.
        - Unlimited subscription: 4 weeks duration, unlimited sessions, max 10 concurrent reservations.
        """
        now = base_time or self.created_at or timezone.now()
        if not self.start_date:
            self.start_date = now

        if self.purchase_type == 'session_pass':
            self.end_date = None
            limit = self.session_pass.entry_limit if self.session_pass else 10
            self.total_sessions = limit
            if self.remaining_sessions == 0:
                self.remaining_sessions = limit
            self.sessions_per_week = 0
            self.max_active_reservations = limit
        elif self.purchase_type == 'subscription' and self.subscription_plan:
            plan = self.subscription_plan
            duration_weeks = getattr(plan, 'duration_weeks', 4) or 4
            from datetime import timedelta
            self.end_date = self.start_date + timedelta(weeks=duration_weeks)

            if plan.plan_type == 'weekly':
                self.sessions_per_week = 1
                self.total_sessions = duration_weeks * 1  # 4 sessions over 4 weeks
                if self.remaining_sessions == 0:
                    self.remaining_sessions = self.total_sessions
                self.max_active_reservations = 1
            elif plan.plan_type == 'unlimited':
                self.sessions_per_week = 0
                self.total_sessions = 0  # 0 indicates unlimited
                self.remaining_sessions = 0
                self.max_active_reservations = plan.max_reservations or 10

    def save(self, *args, **kwargs):
        if not self.start_date or (self.purchase_type == 'subscription' and not self.end_date):
            self.calculate_validity_and_limits()

        if not self.id:
            super().save(*args, **kwargs)
            if not self.purchase_id:
                prefix = "PASS" if self.purchase_type == 'session_pass' else "SUB"
                self.purchase_id = f"{prefix}-{self.id:04d}"
                super().save(update_fields=['purchase_id'])
        else:
            if not self.purchase_id:
                prefix = "PASS" if self.purchase_type == 'session_pass' else "SUB"
                self.purchase_id = f"{prefix}-{self.id:04d}"
            super().save(*args, **kwargs)
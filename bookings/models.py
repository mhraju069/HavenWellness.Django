from django.db import models
from datetime import timedelta, time, datetime
from django.utils import timezone
import random, string, ast
from django.conf import settings
from services.models import Service, AddOnExtra, MembershipPlan, ServiceType

User = settings.AUTH_USER_MODEL


class BookingSettings(models.Model):
    open_time = models.TimeField(default=time(6, 0))
    close_time = models.TimeField(default=time(18, 0))
    cancel_before = models.DurationField(default=timedelta(hours=24))
    advance_before = models.DurationField(default=timedelta(days=30))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return "Booking Settings"


class UserMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    sessions_used_this_period = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.plan.billing_period_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.plan.name} (Valid till {self.end_date})"

    @property
    def is_valid(self):
        return self.is_active and self.start_date <= timezone.now().date() <= self.end_date


class UserSessionPass(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_passes")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    total_sessions = models.PositiveIntegerField(default=10)
    remaining_sessions = models.PositiveIntegerField(default=10)
    purchase_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.valid_until:
            self.valid_until = timezone.now().date() + timedelta(days=365)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.service.name} 10-Pass ({self.remaining_sessions}/{self.total_sessions} remaining)"

    @property
    def is_valid(self):
        return self.is_active and self.remaining_sessions > 0 and timezone.now().date() <= self.valid_until


class Slot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True, related_name="slots")
    max_capacity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        srv_name = self.service.name if self.service else "Slot"
        return f"{srv_name} | Max Capacity: {self.max_capacity}"


class TimeSlot(models.Model):
    @staticmethod
    def generate_slots(open_time, close_time, duration_minutes):
        slots = []
        dummy_date = datetime.now().date()
        current_dt = datetime.combine(dummy_date, open_time)
        end_dt = datetime.combine(dummy_date, close_time)

        while current_dt + timedelta(minutes=duration_minutes) <= end_dt:
            time_str = current_dt.strftime("%I.%M %p").lstrip('0')
            slot_value = f"('{time_str}', '{time_str}')"
            slots.append(slot_value)
            current_dt += timedelta(minutes=duration_minutes)
        return slots
    
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    time = models.CharField(max_length=100)
    date = models.DateField()
    booked_capacity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        srv_name = self.slot.service.name if (self.slot and self.slot.service) else "Slot"
        return f"{srv_name} | {self.date} | {self.time}"

    def available_capacity(self):
        return self.slot.max_capacity - self.booked_capacity

    def get_time_display(self):
        try:
            time_val = ast.literal_eval(self.time)
            if isinstance(time_val, (list, tuple)):
                return time_val[0]
            return str(time_val)
        except (ValueError, SyntaxError):
            return self.time


class Booking(models.Model):
    Status = [("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("pending", "Pending")]
    PaymentStatus = [
        ("pending", "Pending"), 
        ("paid", "Paid"), 
        ("membership_used", "Membership Used"), 
        ("session_pass_used", "Session Pass Used"), 
        ("on_site", "On Site")
    ]
    PAYMENT_METHODS = [
        ("ideal", "iDEAL"),
        ("credit_card", "Credit Card"),
        ("membership", "Membership"),
        ("session_pass", "10-Session Pass"),
        ("on_site", "On Site"),
    ]
    
    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True, related_name="bookings")
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, null=True, blank=True)
    
    booking_type = models.CharField(max_length=50, choices=ServiceType.choices, default="private_sauna")
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    cleaning_buffer_until = models.DateTimeField(null=True, blank=True)
    
    guests_count = models.IntegerField(default=1)
    duration_hours = models.PositiveIntegerField(default=3, help_text="Used for Private Sauna (3 or 4 hours)")
    
    # Lunchroom celebration details
    is_celebrating = models.BooleanField(default=False)
    celebration_what = models.CharField(max_length=150, blank=True, null=True)
    celebration_who = models.CharField(max_length=150, blank=True, null=True)
    celebration_age = models.CharField(max_length=20, blank=True, null=True)
    celebration_interests = models.TextField(blank=True, null=True)
    
    selected_extras = models.ManyToManyField(AddOnExtra, blank=True)
    
    name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status, default='pending')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='ideal')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus, default='pending')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        srv = self.service.name if self.service else self.booking_type
        return f"{srv} | {self.date} | {self.start_time} | {self.status}"

    def save(self, *args, **kwargs):
        if self.user:
            if not self.name:
                self.name = getattr(self.user, 'name', None) or getattr(self.user, 'email', None)
            if not self.email:
                self.email = getattr(self.user, 'email', None)
        
        if not self.id:
            super().save(*args, **kwargs)

        if not self.booking_id:
            self.booking_id = f"BK-{self.id:04d}"
            super().save(update_fields=['booking_id'])


class AccessCode(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="access_code")
    code = models.CharField(max_length=100, editable=False, unique=True, db_index=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(1000, 9999)}"
        duration = 60
        if self.booking and self.booking.service:
            duration = getattr(self.booking.service, 'duration_minutes', 60)
        self.valid_until = self.valid_from + timedelta(minutes=duration)

        if self.valid_until < timezone.now():
            self.is_active = False
        else:
            self.is_active = True

        super().save(*args, **kwargs)

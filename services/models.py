from django.db import models

class ServiceType(models.TextChoices):
    LUNCHROOM = "lunchroom", "Lunchroom"
    PRIVATE_SAUNA = "private_sauna", "Private Sauna"
    SHARED_SAUNA = "shared_sauna", "Shared Sauna"
    SALT_ROOM = "salt_room", "Salt Room"
    ACTIVITY = "activity", "Activity / Workshop"
    EVENT = "event", "Event / Party Room"
    PACKAGE = "package", "Package"


class Service(models.Model):
    name = models.CharField(max_length=150)
    service_type = models.CharField(max_length=50, choices=ServiceType.choices, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="services/", null=True, blank=True)
    min_capacity = models.PositiveIntegerField(default=1)
    max_capacity = models.PositiveIntegerField(default=6)
    duration_minutes = models.PositiveIntegerField(default=60)
    buffer_minutes = models.PositiveIntegerField(default=0, help_text="Cleaning/Changeover time in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.name}"


class ServiceOpeningHour(models.Model):
    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="opening_hours")
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('service', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week)
        if self.is_closed:
            return f"{self.service.name} - {day_name}: CLOSED"
        return f"{self.service.name} - {day_name}: {self.open_time} - {self.close_time}"


class ServiceScheduleException(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="schedule_exceptions", null=True, blank=True, help_text="Null means applies to all services")
    date = models.DateField()
    open_time = models.TimeField(null=True, blank=True, help_text="Null if closed whole day")
    close_time = models.TimeField(null=True, blank=True, help_text="Null if closed whole day")
    is_blocked = models.BooleanField(default=True, help_text="True to block entire day")
    reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        target = self.service.name if self.service else "All Services"
        status_str = "BLOCKED" if self.is_blocked else f"{self.open_time} - {self.close_time}"
        return f"{target} on {self.date}: {status_str}"


class BlockedSlot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="blocked_slots")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.service.name} blocked on {self.date} ({self.start_time} - {self.end_time})"


class SaltRoomPricing(models.Model):
    single_session_price = models.DecimalField(max_digits=10, decimal_places=2, default=25.00)
    max_capacity = models.PositiveIntegerField(default=2)
    session_duration_minutes = models.PositiveIntegerField(default=60)
    buffer_minutes = models.PositiveIntegerField(default=10)
    pass_10_price = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    pass_10_sessions = models.PositiveIntegerField(default=10)
    pass_10_validity_days = models.PositiveIntegerField(default=365)
    membership_once_a_week_price = models.DecimalField(max_digits=10, decimal_places=2, default=70.00)
    membership_unlimited_price = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    is_available = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Salt Room Pricing: Single €{self.single_session_price} | 10-Pass €{self.pass_10_price}"


class AddOnExtra(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    services = models.ManyToManyField(Service, blank=True, related_name="addons")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (€{self.price})"


class EventInquiry(models.Model):
    EVENT_TYPES = [
        ('birthday', 'Birthday'),
        ('wedding', 'Wedding'),
        ('baby_shower', 'Baby Shower'),
        ('corporate', 'Corporate Party'),
        ('anniversary', 'Anniversary'),
        ('private_party', 'Private Party'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('quoted', 'Quoted'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    preferred_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    expected_guests = models.PositiveIntegerField()
    food_preferences = models.TextField(blank=True, null=True)
    drink_preferences = models.TextField(blank=True, null=True)
    entertainment_preferences = models.TextField(blank=True, null=True)
    additional_requests = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Event Inquiry: {self.get_event_type_display()} on {self.preferred_date} by {self.name}"


class ServicePackage(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    services = models.ManyToManyField(Service, related_name="packages")
    is_custom_inquiry = models.BooleanField(default=False)
    image = models.ImageField(upload_to="packages/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Package: {self.title} (€{self.price})"


class MembershipPlan(models.Model):
    PLAN_TYPES = [
        ('shared_sauna_weekly', 'Shared Sauna - Once a Week (€60 / 4wks)'),
        ('shared_sauna_unlimited', 'Shared Sauna - Unlimited (€100 / 4wks)'),
        ('salt_room_weekly', 'Salt Room - Once a Week (€70 / 4wks)'),
        ('salt_room_unlimited', 'Salt Room - Unlimited (€100 / 4wks)'),
    ]
    name = models.CharField(max_length=100)
    plan_code = models.CharField(max_length=50, choices=PLAN_TYPES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period_days = models.PositiveIntegerField(default=28)
    sessions_per_period = models.PositiveIntegerField(null=True, blank=True, help_text="Null if unlimited")
    max_active_future_bookings = models.PositiveIntegerField(default=10, help_text="Max active future bookings for unlimited plan")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="membership_plans")

    def __str__(self):
        return f"{self.name} (€{self.price}/4wks)"


# Legacy / Existing Models
class SaunaSeesion(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, default="")
    description = models.TextField()
    images = models.ImageField(upload_to="sauna_seesion", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PrivateSauna(models.Model):
    base_price_3hrs = models.DecimalField(max_digits=10, decimal_places=2, default=250.00)
    base_price_4hrs = models.DecimalField(max_digits=10, decimal_places=2, default=300.00)
    max_person = models.PositiveIntegerField(default=6)
    extra_person_price = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Private Sauna: 3h €{self.base_price_3hrs} | 4h €{self.base_price_4hrs}"


class SharedSauna(models.Model):
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=19.95)
    is_available = models.BooleanField(default=True)
    max_person = models.PositiveIntegerField(default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shared Sauna: €{self.price_per_person}/person"


class Activities(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, default="")
    description = models.TextField()
    images = models.ImageField(upload_to="activity", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ActivitySession(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    images = models.ImageField(upload_to="activity_session", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    max_participants = models.PositiveIntegerField(default=15)
    host_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"


class ActivitiesFeature(models.Model):
    activity = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.feature}"


class ServiceFeature(models.Model):
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.feature}"


class ExcludeDate(models.Model):
    date = models.DateField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exclude Date for {self.date}"
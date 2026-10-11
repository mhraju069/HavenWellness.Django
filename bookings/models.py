from django.db import models
from django.conf import settings
from services.models import Activities

User = settings.AUTH_USER_MODEL


class SaunaBooking(models.Model):
    SAUNA_TYPES = (
        ('shared', 'Shared Sauna'),
        ('private', 'Private Sauna'),
    )

    TIME_SLOTS = (
        ('90_mins', '90 Minutes'),
        ('3_hours', '3 Hours'),
        ('4_hours', '4 Hours'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )

    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sauna_bookings')

    # Sauna details
    sauna_type = models.CharField(max_length=20, choices=SAUNA_TYPES, default='shared')
    booking_date = models.DateField()
    booking_time = models.TimeField()
    time_slot = models.CharField(max_length=20, choices=TIME_SLOTS, default='3_hours', help_text="3 Hours or 4 Hours slot")
    capacity = models.PositiveIntegerField(default=1, help_text="Capacity / guest count")

    # Guest details (Must be required)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Special request / comment (Nullable)
    special_request = models.TextField(null=True, blank=True)

    # Extra features selected
    selected_features = models.JSONField(default=list, blank=True, null=True, help_text="List of selected extra features")

    # Price & status
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_id} | {self.sauna_type} | {self.name} | {self.booking_date}"

    def get_feature_names(self):
        """
        Returns list of human-readable feature titles/names.
        Handles both strings, IDs, and dicts stored in selected_features.
        """
        if not self.selected_features:
            return []

        from services.models import PrivateSaunaFeatures, SharedSaunaFeatures

        names = []
        for item in self.selected_features:
            if isinstance(item, dict):
                names.append(item.get('feature') or item.get('name') or str(item))
            elif isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                feat_id = int(item)
                # Check private features first, then shared features
                feat = (
                    PrivateSaunaFeatures.objects.filter(id=feat_id).first()
                    or SharedSaunaFeatures.objects.filter(id=feat_id).first()
                )
                if feat and feat.feature:
                    names.append(feat.feature)
                elif feat:
                    names.append(getattr(feat, 'feature_en', None) or f"Add-on #{feat_id}")
                else:
                    names.append(f"Add-on #{feat_id}")
            else:
                names.append(str(item))
        return names

    def save(self, *args, **kwargs):
        if self.selected_features:
            resolved_names = self.get_feature_names()
            if resolved_names:
                self.selected_features = resolved_names

        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            if self.sauna_type == 'shared':
                self.booking_id = f"SS-{self.id:04d}"
            else:
                self.booking_id = f"PS-{self.id:04d}"
            super().save(update_fields=['booking_id', 'selected_features'])
        else:
            super().save(*args, **kwargs)


class LunchroomBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )
    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lunchroom_bookings')
    booking_date = models.DateField()
    booking_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1, help_text="Capacity / guest count")
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    special_request = models.TextField(null=True, blank=True)

    #Celebration
    celebration_type = models.CharField(max_length=20, null=True, blank=True)
    celebration_date = models.DateField(null=True, blank=True)
    name_of_celebrant = models.CharField(max_length=100, null=True, blank=True)
    age_of_celebrant = models.PositiveIntegerField(null=True, blank=True)
    hobbies = models.CharField(max_length=100, null=True, blank=True)
    celebration_details = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.booking_id} | {self.name} | {self.booking_date}"

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            self.booking_id = f"LR-{self.id:04d}"
            super().save(update_fields=['booking_id'])
        else:
            super().save(*args, **kwargs)


class ActivityBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )

    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_bookings')
    activity = models.ForeignKey(Activities, on_delete=models.CASCADE, related_name='activity_bookings')
    capacity = models.PositiveIntegerField(default=1, help_text="Capacity / guest count")
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    special_request = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        activity_title = self.activity.title if self.activity else "Activity"
        return f"{self.booking_id} | {self.name} | {activity_title}"

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            self.booking_id = f"ACT-{self.id:04d}"
            super().save(update_fields=['booking_id'])
        else:
            super().save(*args, **kwargs)


class EventBooking(models.Model):
    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='event_bookings')
    date = models.DateField(help_text="Event Date")
    start_time = models.TimeField(help_text="Event Start Time")
    end_time = models.TimeField(help_text="Event End Time")
    guests = models.PositiveIntegerField(default=1, help_text="Number of guests")

    food_preference = models.TextField(null=True, blank=True, help_text="Food preference")
    drink_preference = models.TextField(null=True, blank=True, help_text="Drink preference")
    music_preference = models.TextField(null=True, blank=True, help_text="Music preference")
    notes = models.TextField(null=True, blank=True)

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.booking_id} | {self.name} | {self.date}"

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            self.booking_id = f"EVNT-{self.id:04d}"
            super().save(update_fields=['booking_id'])
        else:
            super().save(*args, **kwargs)


class PackageBooking(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )

    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='package_bookings')
    date = models.DateField(help_text="Package Date")
    guests = models.PositiveIntegerField(default=1, help_text="Number of guests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(null=True, blank=True)

    booked_services_ids = models.JSONField(default=list, help_text="List of included service ids, e.g. [{'private_sauna':'PS-001'}, {'lunchroom':'LR-001'}]")
    service_names = models.JSONField(default=list, blank=True, help_text="List of service names for custom packages, e.g. ['Private Sauna', 'Lunchroom', 'Yoga Activity']")

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    is_custom = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.booking_id} | {self.name} | {self.date}"

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            self.booking_id = f"PKG-{self.id:04d}"
            super().save(update_fields=['booking_id'])
        else:
            super().save(*args, **kwargs)


class SaltRoomBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )

    booking_id = models.CharField(max_length=100, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='saltroom_bookings')

    name = models.CharField(max_length=100, default="")
    email = models.EmailField(default="")
    phone = models.CharField(max_length=20, default="", blank=True)
    special_request = models.TextField(null=True, blank=True)

    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=1)

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    used_pass = models.BooleanField(default=False)
    used_subscription = models.BooleanField(default=False)
    client_purchase = models.ForeignKey('payments.ClientPurchase', on_delete=models.SET_NULL, null=True, blank=True, related_name='saltroom_bookings')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_id} | {self.name or (self.user.email if self.user else 'Guest')} | {self.date} {self.start_time}"

    def save(self, *args, **kwargs):
        if self.payment_status == 'paid':
            self.is_paid = True
        elif not self.is_paid:
            self.payment_status = self.payment_status or 'pending'

        if not self.id:
            super().save(*args, **kwargs)
        if not self.booking_id:
            self.booking_id = f"SR-{self.id:04d}"
            super().save(update_fields=['booking_id', 'is_paid', 'payment_status', 'status'])
        else:
            super().save(*args, **kwargs)
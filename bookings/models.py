from django.db import models
from django.conf import settings

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
from django.db import models
from services.models import Service
from datetime import timedelta
from django.utils import timezone
import random,string
from django.conf import settings
User = settings.AUTH_USER_MODEL

# Create your models here.


class Slot(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE)
    max_capacity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.title} | {self.max_capacity}"


class TimeSlot(models.Model):
    TIMES = [
        ('6.00 AM', '6.00 AM'),
        ('7.00 AM', '7.00 AM'),
        ('8.00 AM', '8.00 AM'),
        ('9.00 AM', '9.00 AM'),
        ('10.00 AM', '10.00 AM'),
        ('11.00 AM', '11.00 AM'),
        ('12.00 PM', '12.00 PM'),
        ('1.00 PM', '1.00 PM'),
        ('2.00 PM', '2.00 PM'),
        ('3.00 PM', '3.00 PM'),
        ('4.00 PM', '4.00 PM'),
        ('5.00 PM', '5.00 PM'),
        ('6.00 PM', '6.00 PM'),
    ]
    
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)
    time = models.CharField(max_length=20, choices=TIMES)
    date = models.DateField()
    booked_capacity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.slot.service.title} | {self.date} | {self.time}"

    def available_capacity(self):
        return self.slot.max_capacity - self.booked_capacity



class Booking(models.Model):
    Status = [("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    PaymentStatus = [("pending", "Pending"), ("paid", "Paid"), ("on_spot", "On Spot")]
    
    name = models.CharField(max_length=100,blank=True, null=True)
    phone = models.CharField(max_length=15,blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    booking_id = models.CharField(max_length=100,editable=False,db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    guests_count = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status, default='pending')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.title} | {self.time_slot.date} | {self.time_slot.time} | {self.status} "

    def save(self, *args, **kwargs):

        if not self.name:
            self.name = self.user.name or None
        if not self.email:
            self.email = self.user.email or None
        
        if not self.id:
            super().save(*args, **kwargs)

        if not self.booking_id:
            self.booking_id = f"BK-{self.id:03d}"
            super().save(update_fields=['booking_id'])
          


class AccessCode(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, editable=False,unique=True,db_index=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{random.choices(string.ascii_uppercase, k=3)}-{random.randint(1000, 9999)}"
        self.valid_until = self.valid_from + timedelta(minutes=self.booking.service.duration)
        super().save(*args, **kwargs)



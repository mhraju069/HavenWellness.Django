from django.db import models
from services.models import Service
from datetime import timedelta

# Create your models here.


class TimeSlot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_capacity = models.IntegerField(default=1)
    booked_capacity = models.IntegerField(default=0)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = self.start_time + timedelta(minutes=self.service.duration)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.service.title} | {self.date} | {self.start_time} - {self.end_time}"


class Booking(models.Model):
    Status = [("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")]
    PaymentStatus = [("pending", "Pending"), ("paid", "Paid"), ("on_spot", "On Spot")]
    
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    booking_id = models.CharField(max_length=100, unique=True,primary_key=True,editable=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    guests_count = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status, default='pending')
    payment_status = models.CharField(max_length=20, choices=PaymentStatus, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service.title} | {self.time_slot.date} | {self.time_slot.start_time} - {self.time_slot.end_time} | {self.status} "

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = f"BK-{self.id:03d}"
        super().save(*args, **kwargs)


class AccessCode(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    code = models.CharField(max_length=100, editable=False,unique=True,primary_key=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(default=self.valid_until)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{random.choices(string.ascii_uppercase, k=3)}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)
    
    def valid_until(self):
        return self.valid_from + timedelta(minutes=self.booking.service.duration)
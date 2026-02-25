from django.db import models

# Create your models here.


class Service(models.Model):
    TYPE_CHOICES = [
        ('private_sauna', 'Private Sauna'),
        ('shared_sauna', 'Shared Sauna'),
        ('arrangement', 'Arrangement'),
        ('activity', 'Activity'),
        ('lunchroom', 'Lunchroom'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
        ('on_spot', 'On Spot Payment'),
    ]
    title = models.TextField(choices=TYPE_CHOICES, default='private_sauna',unique=True,primary_key=True)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    capacity = models.IntegerField(default=1)
    duration = models.IntegerField(default=60)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='full')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} | {self.capacity} | {self.price}"


class ServiceImage(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='services/images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image for {self.service.title}"


class ServiceFeature(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.service.title} | {self.feature}"
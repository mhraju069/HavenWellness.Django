from django.db import models

# Create your models here.


class Service(models.Model):
    TYPE_CHOICES = [
        ('private_sauna', 'Private Sauna'),
        ('shared_sauna', 'Shared Sauna'),
        ('arrangement', 'Arrangement'),
        ('activity', 'Activity'),
        ('restaurant', 'Restaurant'),
    ]
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    capacity = models.IntegerField(default=1)
    duration = models.IntegerField(default=60)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='private_sauna')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} | {self.type}"


class ServiceImage(models.Model):
    title = models.CharField(max_length=100, blank=True, null=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='services/images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image for {self.service.title} | {self.service.type}"

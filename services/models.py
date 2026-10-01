from django.db import models

# Create your models here.


class Service(models.Model):
    TYPE_CHOICES = [
        ('sauna', 'Sauna'),
        ('arrangement', 'Arrangement'),
        ('activity', 'Activity'),
        ('lunchroom', 'Lunchroom'),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
        ('on_spot', 'On Spot Payment'),
    ]
    service_type = models.TextField(choices=TYPE_CHOICES, default='sauna')
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='services/images/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='full')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} | {self.price}"



class ServiceFeature(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.service.title} | {self.feature}"


class ExcludeDate(models.Model):
    service = models.ManyToManyField(Service, related_name='exclude_dates')
    date = models.DateField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exclude Date for {self.service.title} | {self.date}"
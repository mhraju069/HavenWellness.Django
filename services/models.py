from django.core.files import images
from django.db import models

# Create your models here.
class Services(models.Model):
    SERVICE_TYPES = [
        ('sauna', 'Sauna'),
        ('activity', 'Activity'),
        ('saltroom', 'Saltroom'),
        ('package', 'Package'),
        ('event', 'Event'),
        ('lunchroom', 'Lunchroom'),
    ]
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, default="")
    description = models.TextField()
    type = models.CharField(max_length=100, choices=SERVICE_TYPES)
    image = models.ImageField(upload_to="services", null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title




class PrivateSauna(models.Model):
    base_price_3hrs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    base_price_4hrs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_person = models.PositiveIntegerField(default=6)
    extra_person_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.base_price_3hrs} | {self.base_price_4hrs}"


class PrivateSaunaFeatures(models.Model):
    sauna = models.ForeignKey(PrivateSauna, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.feature}"




class SharedSauna(models.Model):
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    max_person = models.PositiveIntegerField(default=6)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.price_per_person}"


class SharedSaunaFeatures(models.Model):
    sauna = models.ForeignKey(SharedSauna, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.feature}"




class Activities(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    images = models.ImageField(upload_to="activity_session", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"


class ActivitiesFeature(models.Model):
    activity = models.ForeignKey(Activities, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.feature}"




class Lunchroom(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, default="")
    description = models.TextField()
    images = models.ImageField(upload_to="lunchroom", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"




class Saltroom(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100, default="")
    description = models.TextField()
    images = models.ImageField(upload_to="saltroom", null=True, blank=True)
    price_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=25)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title}"


class SaltroomFeatures(models.Model):
    saltroom = models.ForeignKey(Saltroom, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Feature for {self.feature}"




class Packages(models.Model):
    title = models.CharField(max_length=100)
    packages = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to="package", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f" {self.title} | {self.price}"


class PackageFeatures(models.Model):
    package = models.ForeignKey(Packages, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=100)

    def __str__(self):
        return f" {self.package.title} | {self.feature}"













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
from django.contrib import admin
from .models import Service, ServiceFeature
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(Service, ModelAdmin)
admin.site.register(ServiceFeature, ModelAdmin)

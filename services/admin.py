from django.contrib import admin
from .models import Service, ServiceImage, ServiceFeature
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(Service, ModelAdmin)
admin.site.register(ServiceImage, ModelAdmin)
admin.site.register(ServiceFeature, ModelAdmin)

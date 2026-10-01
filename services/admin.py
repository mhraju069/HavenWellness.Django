from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(PrivateSauna, ModelAdmin)
admin.site.register(SharedSauna, ModelAdmin)
admin.site.register(ServiceFeature, ModelAdmin)

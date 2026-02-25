from .models import *
from django.contrib import admin
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(Slot, ModelAdmin)
admin.site.register(TimeSlot, ModelAdmin)
admin.site.register(Booking, ModelAdmin)
admin.site.register(AccessCode, ModelAdmin)
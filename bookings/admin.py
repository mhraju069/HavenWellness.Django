from django.contrib import admin
from .models import Slot, TimeSlot, Booking, AccessCode, UserMembership, UserSessionPass, BookingSettings
from unfold.admin import ModelAdmin

admin.site.register(BookingSettings, ModelAdmin)
admin.site.register(UserMembership, ModelAdmin)
admin.site.register(UserSessionPass, ModelAdmin)
admin.site.register(Slot, ModelAdmin)
admin.site.register(TimeSlot, ModelAdmin)
admin.site.register(Booking, ModelAdmin)
admin.site.register(AccessCode, ModelAdmin)
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SaunaBooking


@admin.register(SaunaBooking)
class SaunaBookingAdmin(ModelAdmin):
    list_display = ['booking_id', 'sauna_type', 'name', 'email', 'phone', 'booking_date', 'booking_time', 'time_slot', 'capacity', 'status', 'payment_status']
    list_filter = ['sauna_type', 'time_slot', 'status', 'payment_status', 'booking_date']
    search_fields = ['booking_id', 'name', 'email', 'phone']
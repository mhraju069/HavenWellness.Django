from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking


@admin.register(SaunaBooking)
class SaunaBookingAdmin(ModelAdmin):
    list_display = ['booking_id', 'sauna_type', 'name', 'email', 'phone', 'booking_date', 'booking_time', 'time_slot', 'capacity', 'status', 'payment_status']
    list_filter = ['sauna_type', 'time_slot', 'status', 'payment_status', 'booking_date']
    search_fields = ['booking_id', 'name', 'email', 'phone']


@admin.register(LunchroomBooking)
class LunchroomBookingAdmin(ModelAdmin):
    list_display = ['booking_id', 'name', 'email', 'phone', 'booking_date', 'booking_time', 'capacity', 'status']
    list_filter = ['status', 'booking_date']
    search_fields = ['booking_id', 'name', 'email', 'phone', 'name_of_celebrant']


@admin.register(ActivityBooking)
class ActivityBookingAdmin(ModelAdmin):
    list_display = ['booking_id', 'name', 'email', 'phone', 'activity', 'capacity', 'total_price', 'status', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'activity']
    search_fields = ['booking_id', 'name', 'email', 'phone', 'activity__title']


@admin.register(EventBooking)
class EventBookingAdmin(ModelAdmin):
    list_display = ['booking_id', 'name', 'email', 'phone', 'date', 'start_time', 'end_time', 'guests', 'created_at']
    list_filter = ['date']
    search_fields = ['booking_id', 'name', 'email', 'phone']
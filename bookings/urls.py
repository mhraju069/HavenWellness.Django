from django.urls import path
from .views import (
    SaunaBookingAPIView,
    LunchroomBookingAPIView,
    ActivityBookingAPIView,
    EventBookingAPIView,
    PackageBookingAPIView,
    SaltRoomBookingAPIView,
    BookingDetailAPIView,
    UserBookingsAPIView,
)

urlpatterns = [
    path('my-bookings/', UserBookingsAPIView.as_view(), name='my-bookings'),
    path('sauna/', SaunaBookingAPIView.as_view(), name='sauna-booking'),
    path('sauna/confirm/', SaunaBookingAPIView.as_view(), name='sauna-booking-confirm'),
    path('saltroom/', SaltRoomBookingAPIView.as_view(), name='saltroom-booking'),
    path('saltroom/confirm/', SaltRoomBookingAPIView.as_view(), name='saltroom-booking-confirm'),
    path('lunchroom/', LunchroomBookingAPIView.as_view(), name='lunchroom-booking'),
    path('lunchroom/confirm/', LunchroomBookingAPIView.as_view(), name='lunchroom-booking-confirm'),
    path('activities/', ActivityBookingAPIView.as_view(), name='activity-booking'),
    path('activities/confirm/', ActivityBookingAPIView.as_view(), name='activity-booking-confirm'),
    path('events/', EventBookingAPIView.as_view(), name='event-booking'),
    path('events/confirm/', EventBookingAPIView.as_view(), name='event-booking-confirm'),
    path('packages/', PackageBookingAPIView.as_view(), name='package-booking'),
    path('packages/confirm/', PackageBookingAPIView.as_view(), name='package-booking-confirm'),
    path('<str:booking_id>/', BookingDetailAPIView.as_view(), name='booking-detail'),
]
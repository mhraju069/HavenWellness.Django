from django.urls import path
from .views import (
    SaunaBookingAPIView,
    LunchroomBookingAPIView,
    ActivityBookingAPIView,
    EventBookingAPIView,
)

urlpatterns = [
    path('sauna/', SaunaBookingAPIView.as_view(), name='sauna-booking'),
    path('sauna/confirm/', SaunaBookingAPIView.as_view(), name='sauna-booking-confirm'),
    path('lunchroom/', LunchroomBookingAPIView.as_view(), name='lunchroom-booking'),
    path('lunchroom/confirm/', LunchroomBookingAPIView.as_view(), name='lunchroom-booking-confirm'),
    path('activities/', ActivityBookingAPIView.as_view(), name='activity-booking'),
    path('activities/confirm/', ActivityBookingAPIView.as_view(), name='activity-booking-confirm'),
    path('events/', EventBookingAPIView.as_view(), name='event-booking'),
    path('events/confirm/', EventBookingAPIView.as_view(), name='event-booking-confirm'),
]
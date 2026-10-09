from django.urls import path
from .views import SaunaBookingAPIView

urlpatterns = [
    path('sauna/', SaunaBookingAPIView.as_view(), name='sauna-booking'),
    path('sauna/confirm/', SaunaBookingAPIView.as_view(), name='sauna-booking-confirm'),
]
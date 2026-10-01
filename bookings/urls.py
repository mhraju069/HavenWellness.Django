from django.urls import path
from .views import *

urlpatterns = [
    path('', BookingAPIView.as_view()),
    path('slots/', TimeSlotAPIView.as_view()),
    path('available-slots/', GetAvailableSlotsAPIView.as_view(), name='available-slots'),
]       
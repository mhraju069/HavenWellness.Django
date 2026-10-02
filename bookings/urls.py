from django.urls import path
from .views import (
    BookingAPIView, TimeSlotAPIView, GetAvailableSlotsAPIView,
    UserMembershipAPIView, UserSessionPassAPIView
)

urlpatterns = [
    path('', BookingAPIView.as_view()),
    path('slots/', TimeSlotAPIView.as_view()),
    path('available-slots/', GetAvailableSlotsAPIView.as_view(), name='available-slots'),
    path('memberships/', UserMembershipAPIView.as_view()),
    path('session-passes/', UserSessionPassAPIView.as_view()),
]
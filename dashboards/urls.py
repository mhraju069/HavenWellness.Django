from django.urls import path
from .views import *

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('reservations/', ReservationListView.as_view(), name='reservation-list'),
    path('capacity/', CapacityListView.as_view(), name='capacity-list'),
]
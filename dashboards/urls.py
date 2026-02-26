from django.urls import path
from .views import *

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('reservations/', ReservationListView.as_view(), name='reservation-list'),
    path('capacity/', CapacityListView.as_view(), name='capacity-list'),
    path('services/', ServiceApiView.as_view(), name='services'),
    path('payments/', PaymentListView.as_view(), name='payment-list'),
    path('access-codes/', AccessCodeListView.as_view(), name='access-code-list'),
]   
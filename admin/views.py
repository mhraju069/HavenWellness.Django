from django.shortcuts import render
from rest_framework.views import APIView
from bookings.models import Booking, AccessCode
from django.utils import timezone
# Create your views here.

class DashboardView(APIView):
    def get(self, request):
        today_reservations = Booking.objects.filter(date=timezone.now().date()).count()
        upcoming_reservations = Booking.objects.filter(date__gt=timezone.now().date()).count()
        active_codes = AccessCode.objects.filter(is_active=True).count()
        pending_payments = Booking.objects.filter(payment_status='on_site',status='pending').count()
        
        

        
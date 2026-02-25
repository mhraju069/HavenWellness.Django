from django.shortcuts import render
from rest_framework.views import APIView
from bookings.models import Booking, AccessCode
from bookings.serializers import BookingSerializer
from django.utils import timezone
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from services.models import Service
# Create your views here.

class DashboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.now().date()

        today_reservations = Booking.objects.filter(time_slot__date=today).count()
        upcoming_reservations = Booking.objects.filter(time_slot__date__gt=today).count()
        active_codes = AccessCode.objects.filter(valid_until__gt=timezone.now()).count()
        pending_payments = Booking.objects.filter(payment_status='on_site', status='pending').count()

        today_bookings_qs = Booking.objects.filter(time_slot__date=today).order_by('-created_at')

        res = {}
        for service in Service.objects.all():
            res[service.title] = today_bookings_qs.filter(service=service).count()

        return Response({
            "today_reservations": today_reservations,
            "upcoming_reservations": upcoming_reservations,
            "active_codes": active_codes,
            "pending_payments": pending_payments,
            "today_bookings_list": BookingSerializer(today_bookings_qs, many=True).data,
            "service_bookings_count": res
        })
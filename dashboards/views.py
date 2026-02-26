from django.shortcuts import render
from rest_framework.views import APIView
from bookings.models import *
from bookings.serializers import *
from services.serializers import *
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from services.models import Service
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAdminUser, AllowAny
from django.db.models import Count, Sum
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


class ReservationListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['service', 'status', 'payment_status', 'time_slot__date']
    ordering_fields = ['created_at', 'time_slot__date', 'total_amount']
    ordering = ['-created_at']



class CapacityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        services = Service.objects.all()

        slots = []
        for service in services:
            slot_obj = Slot.objects.filter(service=service).first()
            if not slot_obj:
                continue

            total_booked = TimeSlot.objects.filter(
                slot__service=service
            ).aggregate(total=Sum('booked_capacity'))['total'] or 0
            total_timeslots = TimeSlot.objects.filter(slot__service=service).count()
            total_capacity = slot_obj.max_capacity * total_timeslots

            slots.append({
                "service": service.title,
                "total_capacity": total_capacity,
                "total_booked": total_booked,
                "total_available": total_capacity - total_booked,
            })

        return Response({"services": ServiceSerializer(services, many=True).data,"capacity": slots})
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAdminUser, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from bookings.models import Booking, Slot, TimeSlot, AccessCode
from bookings.serializers import BookingSerializer, AccessCodeSerializer
from services.models import Service, ExcludeDate
from services.serializers import ServiceSerializer
from payments.models import Payments
from payments.serializers import PaymentSerializer

from .serializers import (
    DashboardExcludeDateSerializer,
    DashboardSummaryResponseSerializer,
    CapacityListResponseSerializer,
    ServiceStatsResponseSerializer,
)


@extend_schema(
    tags=['Dashboard'],
    summary="Get admin dashboard overview metrics and today's bookings",
    responses={200: DashboardSummaryResponseSerializer}
)
class DashboardView(APIView):
    permission_classes = [AllowAny]
    serializer_class = DashboardSummaryResponseSerializer

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


@extend_schema(
    tags=['Dashboard'],
    summary="List all reservations with filtering and ordering",
    responses={200: BookingSerializer(many=True)}
)
class ReservationListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['service', 'status', 'payment_status', 'time_slot__date']
    ordering_fields = ['created_at', 'time_slot__date']
    ordering = ['-created_at']


@extend_schema(
    tags=['Dashboard'],
    summary="Get capacity status breakdown per service",
    responses={200: CapacityListResponseSerializer}
)
class CapacityListView(APIView):
    permission_classes = [AllowAny]
    serializer_class = CapacityListResponseSerializer

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

        return Response({"services": ServiceSerializer(services, many=True).data, "capacity": slots})


@extend_schema(
    tags=['Dashboard'],
    summary="Get service statistics and aggregated details",
    responses={200: ServiceStatsResponseSerializer}
)
class ServiceApiView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ServiceStatsResponseSerializer

    def get(self, request):
        services = Service.objects.all()

        total_services = services.count()
        total_active_services = services.filter(is_active=True).count()
        total_capacity = services.aggregate(total=Sum('capacity'))['total'] or 0
        average_price = services.aggregate(total=Avg('price'))['total'] or 0
        average_duration = services.aggregate(total=Avg('duration'))['total'] or 0

        return Response({
            "total_services": total_services,
            "total_active_services": total_active_services,
            "total_capacity": total_capacity,
            "average_price": average_price,
            "average_duration": average_duration,
            "services": ServiceSerializer(services, many=True).data
        })


@extend_schema(
    tags=['Dashboard'],
    summary="List all completed/paid payment records",
    responses={200: PaymentSerializer(many=True)}
)
class PaymentListView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PaymentSerializer

    def get(self, request):
        payments = Payments.objects.filter(payment_status='paid')
        return Response(PaymentSerializer(payments, many=True).data)


@extend_schema(
    tags=['Dashboard'],
    summary="List active access codes for sauna services",
    responses={200: AccessCodeSerializer(many=True)}
)
class AccessCodeListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AccessCodeSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['booking__service', 'is_used', 'is_active']
    ordering_fields = ['valid_from', 'valid_until']
    ordering = ['-valid_from']

    def get_queryset(self):
        return AccessCode.objects.filter(is_active=True)


@extend_schema(
    tags=['Dashboard'],
    summary="List or create excluded date entries for services",
    responses={200: DashboardExcludeDateSerializer(many=True), 201: DashboardExcludeDateSerializer}
)
class ExcludeDateListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = DashboardExcludeDateSerializer
    queryset = ExcludeDate.objects.all()


@extend_schema(
    tags=['Dashboard'],
    summary="Retrieve, update or delete an excluded date entry",
    responses={200: DashboardExcludeDateSerializer}
)
class ExcludeDateUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [AllowAny]
    serializer_class = DashboardExcludeDateSerializer
    queryset = ExcludeDate.objects.all()
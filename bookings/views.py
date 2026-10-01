from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Q

from .serializers import TimeSlotSerializer, BookingSerializer, AvailableTimeSlotSerializer
from .models import Slot, TimeSlot, BookingSettings, Booking
from services.models import ExcludeDate
from core.permissions import IsAdmin


@extend_schema(
    tags=['Bookings'],
    summary="Get available time slots for a given date and service",
    parameters=[
        OpenApiParameter("date", OpenApiTypes.DATE, OpenApiParameter.QUERY, description="Booking date (YYYY-MM-DD)", required=True),
        OpenApiParameter("service", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Service title (e.g. private_sauna)", required=True),
    ],
    responses={
        200: TimeSlotSerializer(many=True),
        400: OpenApiTypes.OBJECT,
    }
)
class TimeSlotAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TimeSlot.objects.none()

        date = self.request.query_params.get('date')
        service = self.request.query_params.get('service')
        if not date or not service:
            return TimeSlot.objects.none()

        slot = Slot.objects.filter(service__title=service).first()
        if not slot:
            return TimeSlot.objects.none()

        if ExcludeDate.objects.filter(service__title=service, date=date).exists():
            return TimeSlot.objects.none()

        if TimeSlot.objects.filter(date=date, slot=slot).exists():
            return TimeSlot.objects.filter(date=date, slot=slot)

        # Get booking settings to determine open/close times
        settings = BookingSettings.objects.first()
        if not settings:
            for time_val in TimeSlot.TIMES:
                TimeSlot.objects.create(date=date, time=time_val, slot=slot)
        else:
            duration = slot.service.duration
            dynamic_times = TimeSlot.generate_slots(settings.open_time, settings.close_time, duration)
            for time_val in dynamic_times:
                TimeSlot.objects.create(date=date, time=time_val, slot=slot)

        return TimeSlot.objects.filter(date=date, slot=slot)

    def list(self, request, *args, **kwargs):
        date = request.query_params.get('date')
        service = request.query_params.get('service')
        if not date or not service:
            return Response({"status": False, "log": "date and service query parameters are required"}, status=status.HTTP_400_BAD_REQUEST)

        if ExcludeDate.objects.filter(service__title=service, date=date).exists():
            return Response({"status": False, "log": "No slots available on this date"}, status=status.HTTP_400_BAD_REQUEST)

        slot = Slot.objects.filter(service__title=service).first()
        if not slot:
            return Response({"status": False, "log": "Slot not found"}, status=status.HTTP_400_BAD_REQUEST)

        return super().list(request, *args, **kwargs)


@extend_schema(
    tags=['Bookings'],
    summary="List or create bookings for the authenticated user",
    responses={
        200: BookingSerializer(many=True),
        201: BookingSerializer,
    }
)
class BookingAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or self.request.user.is_anonymous:
            return Booking.objects.none()
        return Booking.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(
    tags=['Bookings'],
    summary="Get detailed available and booked slots breakdown for a date and service",
    parameters=[
        OpenApiParameter("date", OpenApiTypes.DATE, OpenApiParameter.QUERY, description="Booking date (YYYY-MM-DD)", required=True),
        OpenApiParameter("service_type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Service title or type (e.g. private_sauna, shared_sauna, sauna)", required=True),
    ],
    responses={
        200: AvailableTimeSlotSerializer(many=True),
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    }
)
class GetAvailableSlotsAPIView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AvailableTimeSlotSerializer
    
    def get(self, request, *args, **kwargs):
        date = request.query_params.get('date')
        if not date:
            return Response({"status": False, "log": "date query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        service_type = request.query_params.get('service_type') or request.query_params.get('service')
        if not service_type:
            return Response({"status": False, "log": "service_type query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Find matching slot by service title or service_type
        slot_qs = Slot.objects.filter(
            Q(service__title__iexact=service_type) | Q(service__service_type__iexact=service_type)
        )
        if str(service_type).isdigit():
            slot_qs = Slot.objects.filter(Q(service__id=int(service_type)) | Q(service__title__iexact=service_type))
            
        slot = slot_qs.first()
        if not slot:
            return Response({"status": False, "log": f"Slot configuration not found for service: '{service_type}'"}, status=status.HTTP_404_NOT_FOUND)

        # Check if date is marked as excluded for this service
        if ExcludeDate.objects.filter(service=slot.service, date=date).exists():
            return Response({
                "status": True,
                "is_excluded": True,
                "message": "Date is excluded for this service",
                "service": slot.service.title,
                "date": date,
                "data": []
            }, status=status.HTTP_200_OK)

        # Auto-generate TimeSlots for date if not created yet
        if not TimeSlot.objects.filter(date=date, slot=slot).exists():
            settings = BookingSettings.objects.first()
            if not settings:
                for time_val in TimeSlot.TIMES:
                    TimeSlot.objects.create(date=date, time=time_val, slot=slot)
            else:
                duration = getattr(slot.service, 'duration', 60)
                dynamic_times = TimeSlot.generate_slots(settings.open_time, settings.close_time, duration)
                for time_val in dynamic_times:
                    TimeSlot.objects.create(date=date, time=time_val, slot=slot)

        time_slots = TimeSlot.objects.filter(date=date, slot=slot).order_by('id')
        serialized_data = AvailableTimeSlotSerializer(time_slots, many=True).data

        available_count = sum(1 for slot_data in serialized_data if slot_data['is_available'])
        booked_count = sum(1 for slot_data in serialized_data if slot_data['is_booked'])

        return Response({
            "status": True,
            "service": slot.service.title,
            "service_type": slot.service.service_type,
            "date": date,
            "max_capacity": slot.max_capacity,
            "total_slots": len(serialized_data),
            "available_slots_count": available_count,
            "booked_slots_count": booked_count,
            "data": serialized_data
        }, status=status.HTTP_200_OK)

    
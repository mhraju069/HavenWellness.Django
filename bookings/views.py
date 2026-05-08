from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import *
from rest_framework.permissions import IsAuthenticated
from services.models import Service,ExcludeDate
from core.permissions import IsAdmin
# Create your views here.


class TimeSlotAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer
    
    def get_queryset(self):

        date = self.request.query_params.get('date')
        service = self.request.query_params.get('service')
        slot = Slot.objects.filter(service__title=service).first()

        if date in ExcludeDate.objects.filter(service__title=service).values_list('date', flat=True):
            return Response({"status":False,"log":"No slots available on this date"}, status=status.HTTP_400_BAD_REQUEST)

        if not slot:
            return Response({"status":False,"log":"Slot not found"}, status=status.HTTP_400_BAD_REQUEST)

        if TimeSlot.objects.filter(date=date,slot=slot).exists():
            return TimeSlot.objects.filter(date=date,slot=slot)

        # Get booking settings to determine open/close times
        settings = BookingSettings.objects.first()
        if not settings:
            # Fallback if no settings exist
            for time_val in TimeSlot.TIMES:
                TimeSlot.objects.create(date=date, time=time_val, slot=slot)
        else:
            # Generate dynamic slots based on service duration
            duration = slot.service.duration
            dynamic_times = TimeSlot.generate_slots(settings.open_time, settings.close_time, duration)
            for time_val in dynamic_times:
                TimeSlot.objects.create(date=date, time=time_val, slot=slot)
        
        return TimeSlot.objects.filter(date=date,slot=slot)


class BookingAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    


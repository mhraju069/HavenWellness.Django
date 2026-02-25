from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from .models import *
from rest_framework.permissions import IsAuthenticated
from services.models import Service
from core.permissions import IsAdmin
from rest_framework import serializers
# Create your views here.


class TimeSlotAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer
    
    def get_queryset(self):

        date = self.request.query_params.get('date')
        service = self.request.query_params.get('service')
        slot = Slot.objects.filter(service__title=service).first()

        if not slot:
            raise serializers.ValidationError({"status":False,"log":"Slot not found"})

        if TimeSlot.objects.filter(date=date,slot=slot).exists():
            return TimeSlot.objects.filter(date=date,slot=slot)

        for time in TimeSlot.TIMES:
            TimeSlot.objects.create(date=date,time=time,slot=slot)
        
        return TimeSlot.objects.filter(date=date,slot=slot)


class BookingAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    


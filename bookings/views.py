from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import BookingSerializer, SlotSerializer, TimeSlotSerializer
from .models import Slot, TimeSlot
from rest_framework.permissions import IsAuthenticated
from services.models import Service
from core.permissions import IsAdmin
# Create your views here.


class TimeSlotAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeSlotSerializer
    
    def get_queryset(self):

        date = self.request.query_params.get('date')
        service = self.request.query_params.get('service')
        slot = Slot.objects.get(service__title=service)

        if TimeSlot.objects.filter(date=date,slot=slot).exists():
            return TimeSlot.objects.filter(date=date,slot=slot)

        for time in TimeSlot.TIMES:
            TimeSlot.objects.create(date=date,time=time,slot=slot)
        
        return TimeSlot.objects.filter(date=date,slot=slot)

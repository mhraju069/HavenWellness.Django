from .models import Service
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ServiceSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, RetrieveDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.

class ServiceAPIView(ListCreateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

    def get_queryset(self):
        return Service.objects.filter(is_active=True).order_by('-created_at')
    

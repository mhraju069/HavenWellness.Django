from .models import ExcludeDate
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import  ExcludeDateSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


@extend_schema(
    tags=['Services'],
    summary="List or create excluded dates for services",
    responses={200: ExcludeDateSerializer(many=True), 201: ExcludeDateSerializer}
)
class ExcludeDateAPIView(ListCreateAPIView):
    serializer_class = ExcludeDateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service']

    def get_queryset(self):
        return ExcludeDate.objects.all().order_by('-created_at')


@extend_schema(
    tags=['Services'],
    summary="Retrieve or delete an excluded date for a service",
    responses={200: ExcludeDateSerializer}
)
class ExcludeDateDestroyAPIView(RetrieveDestroyAPIView):
    serializer_class = ExcludeDateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service']

    def get_queryset(self):
        return ExcludeDate.objects.all().order_by('-created_at')
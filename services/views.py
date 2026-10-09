from .models import *
from payments.models import SubscriptionPlans, SessionPass
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


class AllServicesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List all Services",
        parameters=[
            OpenApiParameter(name="type", description="Filter by service type (sauna, activity, saltroom, package, event, lunchroom)", required=False, type=str),
        ],
        responses={200: ServicesSerializer(many=True)},
    )
    def get(self, request):
        service_type = request.query_params.get('type')
        data = Services.objects.all().order_by('-created_at')
        if service_type:
            data = data.filter(type=service_type)
        serializer = ServicesSerializer(data, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "All Service List",
        })


class SaunaServiceView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Sauna Services",
        responses={200: SaunaServiceSerializer},
    )
    def get(self, request):
        private_sauna = PrivateSauna.objects.prefetch_related('features').all()
        shared_sauna = SharedSauna.objects.prefetch_related('features').all()

        serializer = SaunaServiceSerializer({
            "private_sauna": private_sauna,
            "shared_sauna": shared_sauna,
        }, context={'request': request})

        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Sauna Service List",
        })


class ActivitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Activity Sessions",
        responses={200: ActivitiesSerializer(many=True)},
    )
    def get(self, request):
        activities = Activities.objects.prefetch_related('features').all()
        serializer = ActivitiesSerializer(activities, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Activity Session List",
        })


class SaltroomServiceView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Saltroom Services",
        responses={200: SaltroomServiceSerializer},
    )
    def get(self, request):
        saltroom = Saltroom.objects.prefetch_related('features').all()
        subscription_plans = SubscriptionPlans.objects.prefetch_related('features').filter(plan_category='saltroom')
        session_pass = SessionPass.objects.prefetch_related('features').all()

        serializer = SaltroomServiceSerializer({
            "saltroom": saltroom,
            "subscription_plans": subscription_plans,
            "session_pass": session_pass,
        }, context={'request': request})

        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Saltroom Service List",
        })



class PackagesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Packages",
        responses={200: PackagesSerializer(many=True)},
    )
    def get(self, request):
        package = Packages.objects.prefetch_related('features').all()
        serializer = PackagesSerializer(package, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Package List",
        })


        











# @extend_schema(
#     tags=['Services'],
#     summary="List or create excluded dates for services",
#     responses={200: ExcludeDateSerializer(many=True), 201: ExcludeDateSerializer}
# )
# class ExcludeDateAPIView(ListCreateAPIView):
#     serializer_class = ExcludeDateSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['service']

#     def get_queryset(self):
#         return ExcludeDate.objects.all().order_by('-created_at')


# @extend_schema(
#     tags=['Services'],
#     summary="Retrieve or delete an excluded date for a service",
#     responses={200: ExcludeDateSerializer}
# )
# class ExcludeDateDestroyAPIView(RetrieveDestroyAPIView):
#     serializer_class = ExcludeDateSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['service']

#     def get_queryset(self):
#         return ExcludeDate.objects.all().order_by('-created_at')
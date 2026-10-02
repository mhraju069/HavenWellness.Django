from .models import *
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
        responses={200: AllServicesSerializer},
    )
    def get(self, request):
        sauna_seesion = SaunaSeesion.objects.all()
        activity_session = Activities.objects.all()

        serializer = AllServicesSerializer({
            "sauna_seesion": sauna_seesion,
            "activity_session": activity_session,
        })

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
        private_sauna = PrivateSauna.objects.all()
        shared_sauna = SharedSauna.objects.all()

        serializer = SaunaServiceSerializer({
            "private_sauna": private_sauna,
            "shared_sauna": shared_sauna,
        })

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
        responses={200: ActivitySessionSerializer(many=True)},
    )
    def get(self, request):
        activity_sessions = ActivitySession.objects.prefetch_related('features').all()
        serializer = ActivitySessionSerializer(activity_sessions, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Activity Session List",
        })


class SaltRoomView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Get Salt Room Details & Pricing",
        responses={200: SaltRoomPricingSerializer},
    )
    def get(self, request):
        pricing = SaltRoomPricing.objects.first()
        if not pricing:
            pricing = SaltRoomPricing.objects.create()
        
        # Calculated start times starting from 06:00 (1h session + 10m changeover)
        calculated_slots = [
            "06:00", "07:10", "08:20", "09:30", "10:40", "11:50",
            "13:00", "14:10", "15:20", "16:30", "17:40", "18:50",
            "20:00", "21:10", "22:20"
        ]
        
        serializer = SaltRoomPricingSerializer(pricing)
        return Response({
            "success": True,
            "data": {
                "pricing": serializer.data,
                "time_slots": calculated_slots,
            },
            "message": "Salt Room Info",
        })


class AddOnExtraView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Available Add-ons / Extras",
        responses={200: AddOnExtraSerializer(many=True)},
    )
    def get(self, request):
        addons = AddOnExtra.objects.filter(is_available=True)
        serializer = AddOnExtraSerializer(addons, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Add-ons List",
        })


class EventInquiryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Submit Event / Party Room Inquiry",
        request=EventInquirySerializer,
        responses={201: EventInquirySerializer},
    )
    def post(self, request):
        serializer = EventInquirySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Event Inquiry submitted successfully. We will contact you shortly with a customized proposal!",
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "errors": serializer.errors,
            "message": "Validation Error",
        }, status=status.HTTP_400_BAD_REQUEST)


class ServicePackageView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Service Packages",
        responses={200: ServicePackageSerializer(many=True)},
    )
    def get(self, request):
        packages = ServicePackage.objects.filter(is_active=True)
        serializer = ServicePackageSerializer(packages, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Package List",
        })


class MembershipPlanView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="List Available Membership Plans",
        responses={200: MembershipPlanSerializer(many=True)},
    )
    def get(self, request):
        plans = MembershipPlan.objects.all()
        serializer = MembershipPlanSerializer(plans, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Membership Plans List",
        })


class ServiceScheduleView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Get Opening Hours and Exception Dates for Services",
        responses={200: ServiceSerializer(many=True)},
    )
    def get(self, request):
        services = Service.objects.filter(is_active=True)
        serializer = ServiceSerializer(services, many=True)
        exceptions = ServiceScheduleExceptionSerializer(ServiceScheduleException.objects.all(), many=True)
        return Response({
            "success": True,
            "data": {
                "services": serializer.data,
                "exceptions": exceptions.data,
            },
            "message": "Services Schedule & Opening Hours",
        })
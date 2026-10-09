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
        data = Services.objects.all()
        if service_type:
            data = data.filter(type=service_type)
        serializer = ServicesSerializer(data, many=True, context={'request': request})
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "All Service List",
        })


class ServiceDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Get Service Details by Type",
        parameters=[
            OpenApiParameter(
                name="type",
                description="Service type: 'sauna', 'activity', 'saltroom', 'package', 'lunchroom', 'event'",
                required=False,
                type=str,
            ),
        ],
    )
    def get(self, request, service_type):
        s_type = service_type.lower()

        if not s_type:
            return Response({
                "success": False,
                "message": "Service type is required. Valid options: sauna, activity, saltroom, package, lunchroom, event."
            }, status=status.HTTP_400_BAD_REQUEST)

        s_type = s_type.lower()

        if s_type == 'sauna':
            private_sauna = PrivateSauna.objects.prefetch_related('features').all()
            shared_sauna = SharedSauna.objects.prefetch_related('features').all()
            serializer = SaunaServiceSerializer({
                "private_sauna": private_sauna,
                "shared_sauna": shared_sauna,
            }, context={'request': request})
            return Response({
                "success": True,
                "type": "sauna",
                "data": serializer.data,
                "message": "Sauna Service Details",
            })

        elif s_type in ['activity', 'activities']:
            activities = Activities.objects.prefetch_related('features').all()
            serializer = ActivitiesSerializer(activities, many=True, context={'request': request})
            return Response({
                "success": True,
                "type": "activity",
                "data": serializer.data,
                "message": "Activity Session List",
            })

        elif s_type == 'saltroom':
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
                "type": "saltroom",
                "data": serializer.data,
                "message": "Saltroom Service Details",
            })

        elif s_type in ['package', 'packages']:
            packages = Packages.objects.prefetch_related('features').all()
            serializer = PackagesSerializer(packages, many=True, context={'request': request})
            return Response({
                "success": True,
                "type": "package",
                "data": serializer.data,
                "message": "Package List",
            })

        elif s_type == 'lunchroom':
            lunchrooms = Lunchroom.objects.all()
            serializer = LunchroomSerializer(lunchrooms, many=True, context={'request': request})
            return Response({
                "success": True,
                "type": "lunchroom",
                "data": serializer.data,
                "message": "Lunchroom List",
            })

        elif s_type == 'event':
            return Response({
                "success": True,
                "type": "event",
                "data": [],
                "message": "Event List",
            })

        else:
            return Response({
                "success": False,
                "message": f"Invalid service type '{s_type}'. Valid types: sauna, activity, saltroom, package, lunchroom, event."
            }, status=status.HTTP_400_BAD_REQUEST)








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
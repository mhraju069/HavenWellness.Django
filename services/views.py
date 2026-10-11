from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import *
from payments.models import SubscriptionPlans, SessionPass
from bookings.models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking
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
    def get(self, request, service_type=None):
        s_type = (service_type or request.query_params.get('type') or '').lower()

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
            today = timezone.localdate()
            activities = Activities.objects.prefetch_related('features').filter(
                models.Q(date__gte=today) | models.Q(date__isnull=True)
            ).order_by('date', 'open_time')
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


class GetSlotView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Get available slots for a service (sauna, package, lunchroom, activity, etc.)",
        parameters=[
            OpenApiParameter(name="type", description="Service Type: 'package', 'sauna', 'private_sauna', 'shared_sauna', 'lunchroom', 'activity'", required=False, type=str),
            OpenApiParameter(name="sub_type", description="Optional Sub-service Type filter for packages (e.g. sauna, private_sauna, shared_sauna, lunchroom, activity)", required=False, type=str),
            OpenApiParameter(name="date", description="Date (YYYY-MM-DD)", required=True, type=str),
        ],
    )
    def get(self, request, service_type=None):
        s_type = (service_type or request.query_params.get('type') or '').lower()
        sub_type = (request.query_params.get('sub_type') or '').lower()
        date_str = request.query_params.get('date')

        if not date_str:
            return Response({
                "success": False,
                "message": "Date query parameter 'date' (YYYY-MM-DD) is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({
                "success": False,
                "message": "Invalid date format. Please use YYYY-MM-DD."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Check if date is blocked (BlockDate)
        if BlockDate.objects.filter(date=target_date).exists():
            return Response({
                "success": False,
                "is_blocked": True,
                "date": date_str,
                "data": {},
                "message": "No slots available. This date is blocked."
            }, status=status.HTTP_200_OK)

        # 2. Determine opening and closing times
        special_opening = SpecialOpeningDate.objects.filter(date=target_date).first()
        if special_opening:
            open_time = special_opening.open_time
            close_time = special_opening.close_time
        else:
            settings_obj = ServiceSettings.objects.first()
            if settings_obj:
                open_time = settings_obj.open_time
                close_time = settings_obj.close_time
            else:
                open_time = time(9, 0)
                close_time = time(21, 0)

        open_dt = datetime.combine(target_date, open_time)
        close_dt = datetime.combine(target_date, close_time)

        # -------------------------------------------------------------
        # A. PRIVATE SAUNA SLOT CALCULATION (3h/4h sessions + 30m buffer)
        # -------------------------------------------------------------
        private_bookings = SaunaBooking.objects.filter(
            booking_date=target_date,
            sauna_type='private'
        ).exclude(status='cancelled')

        private_booked_intervals = []
        for pb in private_bookings:
            pb_start = datetime.combine(target_date, pb.booking_time)
            session_hours = 4 if pb.time_slot == '4_hours' else 3
            pb_end = pb_start + timedelta(hours=session_hours + 0.5)
            private_booked_intervals.append((pb_start, pb_end))

        def generate_private_slots(duration_hours):
            session_td = timedelta(hours=duration_hours)
            step_td = timedelta(hours=duration_hours + 0.5)
            slots = []
            curr_dt = open_dt

            while curr_dt + session_td <= close_dt:
                candidate_start = curr_dt
                candidate_session_end = candidate_start + session_td
                candidate_buffer_end = candidate_start + step_td

                overlap = False
                max_overlap_end = None

                for b_start, b_end in private_booked_intervals:
                    if max(candidate_start, b_start) < min(candidate_buffer_end, b_end):
                        overlap = True
                        if max_overlap_end is None or b_end > max_overlap_end:
                            max_overlap_end = b_end

                if overlap and max_overlap_end:
                    curr_dt = max_overlap_end
                else:
                    slots.append({
                        "start_time": candidate_start.strftime("%H:%M"),
                        "end_time": candidate_session_end.strftime("%H:%M"),
                        "buffer_end_time": candidate_buffer_end.strftime("%H:%M"),
                        "time_slot": f"{duration_hours}_hours"
                    })
                    curr_dt = candidate_buffer_end

            return slots

        private_3_hours = generate_private_slots(3)
        private_4_hours = generate_private_slots(4)

        # -------------------------------------------------------------
        # B. SHARED SAUNA SLOT CALCULATION (90m session + 15m buffer)
        # -------------------------------------------------------------
        shared_sauna_model = SharedSauna.objects.first()
        shared_max_capacity = shared_sauna_model.max_person if shared_sauna_model else 6

        shared_bookings = SaunaBooking.objects.filter(
            booking_date=target_date,
            sauna_type='shared'
        ).exclude(status='cancelled')

        def generate_shared_slots():
            session_td = timedelta(minutes=90)
            step_td = timedelta(minutes=105)
            slots = []
            curr_dt = open_dt

            while curr_dt + session_td <= close_dt:
                candidate_start = curr_dt
                candidate_session_end = candidate_start + session_td
                candidate_buffer_end = candidate_start + step_td

                booked_cap = 0
                for sb in shared_bookings:
                    sb_start = datetime.combine(target_date, sb.booking_time)
                    sb_buffer_end = sb_start + timedelta(minutes=105)
                    if max(candidate_start, sb_start) < min(candidate_buffer_end, sb_buffer_end):
                        booked_cap += sb.capacity

                remaining_cap = max(0, shared_max_capacity - booked_cap)
                is_available = (remaining_cap > 0)
                is_fully_booked = (booked_cap >= shared_max_capacity)

                slots.append({
                    "start_time": candidate_start.strftime("%H:%M"),
                    "end_time": candidate_session_end.strftime("%H:%M"),
                    "buffer_end_time": candidate_buffer_end.strftime("%H:%M"),
                    "duration": "90_mins",
                    "max_capacity": shared_max_capacity,
                    "booked_capacity": booked_cap,
                    "remaining_capacity": remaining_cap,
                    "is_available": is_available,
                    "is_fully_booked": is_fully_booked,
                })

                curr_dt = candidate_buffer_end

            return slots

        shared_slots = generate_shared_slots()

        # -------------------------------------------------------------
        # C. LUNCHROOM AVAILABILITY INFO (Flexible time within open hours)
        # -------------------------------------------------------------
        lunch_bookings_count = LunchroomBooking.objects.filter(
            booking_date=target_date
        ).exclude(status='cancelled').count()

        lunchroom_data = {
            "is_available": True,
            "open_time": open_time.strftime("%H:%M"),
            "close_time": close_time.strftime("%H:%M"),
            "existing_bookings_count": lunch_bookings_count,
            "info": "Lunchroom accommodates flexible dining during opening hours. Choose any preferred arrival time."
        }

        # -------------------------------------------------------------
        # D. ACTIVITIES AVAILABILITY FOR THE DATE
        # -------------------------------------------------------------
        activities_on_date = Activities.objects.prefetch_related('features').filter(
            date=target_date,
            is_available=True
        ).order_by('open_time')
        activities_serializer = ActivitiesSerializer(activities_on_date, many=True, context={'request': request})

        # -------------------------------------------------------------
        # Construct Response by Service Type / Package
        # -------------------------------------------------------------
        data = {}

        is_package = s_type in ['package', 'packages']

        # Sauna data
        sauna_dict = {
            "private_sauna": {
                "slots": {
                    "3_hours": private_3_hours,
                    "4_hours": private_4_hours
                }
            },
            "shared_sauna": {
                "max_capacity_per_slot": shared_max_capacity,
                "slots": shared_slots,
            }
        }

        if is_package:
            # Package slots: Include all sub-services or filtered sub_type
            if sub_type in ['private_sauna']:
                data["private_sauna"] = sauna_dict["private_sauna"]
            elif sub_type in ['shared_sauna']:
                data["shared_sauna"] = sauna_dict["shared_sauna"]
            elif sub_type in ['sauna']:
                data["sauna"] = sauna_dict
            elif sub_type in ['lunchroom']:
                data["lunchroom"] = lunchroom_data
            elif sub_type in ['activity', 'activities']:
                data["activities"] = activities_serializer.data
            else:
                # Return combined package slots for all sub-services
                data["sauna"] = sauna_dict
                data["lunchroom"] = lunchroom_data
                data["activities"] = activities_serializer.data
        elif s_type in ['lunchroom']:
            data = lunchroom_data
        elif s_type in ['activity', 'activities']:
            data = {
                "activities": activities_serializer.data
            }
        elif s_type in ['private_sauna']:
            data = {"private_sauna": sauna_dict["private_sauna"]}
        elif s_type in ['shared_sauna']:
            data = {"shared_sauna": sauna_dict["shared_sauna"]}
        else:
            # Default / sauna
            data = sauna_dict

        return Response({
            "success": True,
            "is_blocked": False,
            "date": date_str,
            "service_type": s_type or "sauna",
            "open_time": open_time.strftime("%H:%M"),
            "close_time": close_time.strftime("%H:%M"),
            "data": data,
            "message": "Available Slots",
        }, status=status.HTTP_200_OK)



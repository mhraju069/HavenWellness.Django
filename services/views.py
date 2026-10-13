from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import *
from payments.models import SubscriptionPlans, SessionPass, ClientPurchase
from bookings.models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, SaltRoomBooking
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

            # Check authenticated customer memberships, session passes, and limits
            user = request.user if request.user and request.user.is_authenticated else None
            user_membership_data = {
                "is_authenticated": bool(user),
                "has_active_pass": False,
                "has_active_subscription": False,
                "session_pass": None,
                "subscription": None,
                "total_available_sessions": 0,
            }

            if user:
                now = timezone.now()

                # 1. Active Session Passes (passes do not expire or have no end_date, must be paid/confirmed with remaining_sessions > 0)
                active_passes = ClientPurchase.objects.filter(
                    user=user,
                    purchase_type='session_pass',
                    payment_status='paid',
                    status='confirmed',
                    remaining_sessions__gt=0,
                ).order_by('-created_at')

                latest_pass = active_passes.first()
                if latest_pass:
                    total_pass_sessions = sum(p.remaining_sessions for p in active_passes)
                    user_membership_data["has_active_pass"] = True
                    user_membership_data["session_pass"] = {
                        "purchase_id": latest_pass.purchase_id,
                        "name": latest_pass.session_pass.name if latest_pass.session_pass else "Session Pass",
                        "remaining_sessions": latest_pass.remaining_sessions,
                        "total_sessions": latest_pass.total_sessions,
                        "total_remaining_across_all_passes": total_pass_sessions,
                        "max_active_reservations": latest_pass.max_active_reservations or 10,
                        "status": latest_pass.status,
                        "payment_status": latest_pass.payment_status,
                    }
                    user_membership_data["total_available_sessions"] += total_pass_sessions

                # 2. Active Subscriptions (saltroom or general, paid/confirmed, and end_date in future)
                active_sub = ClientPurchase.objects.filter(
                    user=user,
                    purchase_type='subscription',
                    payment_status='paid',
                    status='confirmed',
                ).filter(
                    models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)
                ).filter(
                    models.Q(subscription_plan__plan_category='saltroom') | models.Q(subscription_plan__isnull=True)
                ).order_by('-created_at').first()

                if active_sub:
                    plan = active_sub.subscription_plan
                    is_unlimited = plan and plan.plan_type == 'unlimited'
                    user_membership_data["has_active_subscription"] = True
                    user_membership_data["subscription"] = {
                        "purchase_id": active_sub.purchase_id,
                        "name": plan.name if plan else "Subscription Plan",
                        "plan_type": plan.plan_type if plan else "unlimited",
                        "plan_category": plan.plan_category if plan else "saltroom",
                        "start_date": active_sub.start_date,
                        "end_date": active_sub.end_date,
                        "is_unlimited": is_unlimited,
                        "remaining_sessions": active_sub.remaining_sessions,
                        "total_sessions": active_sub.total_sessions,
                        "sessions_per_week": active_sub.sessions_per_week,
                        "max_active_reservations": active_sub.max_active_reservations or (10 if is_unlimited else 1),
                        "status": active_sub.status,
                        "payment_status": active_sub.payment_status,
                    }
                    if not is_unlimited:
                        user_membership_data["total_available_sessions"] += active_sub.remaining_sessions

            serializer = SaltroomServiceSerializer({
                "saltroom": saltroom,
                "subscription_plans": subscription_plans,
                "session_pass": session_pass,
                "user_membership": user_membership_data,
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
            OpenApiParameter(name="type", description="Service Type: 'package', 'sauna', 'private_sauna', 'shared_sauna', 'lunchroom', 'activity', 'saltroom'", required=False, type=str),
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
        # E. SALTROOM AVAILABILITY (Session-based, not slot-based)
        # -------------------------------------------------------------
        saltroom_data = None
        if s_type in ['saltroom', 'package', 'packages'] or sub_type == 'saltroom':
            saltroom_obj = Saltroom.objects.first()
            user = request.user if request.user and request.user.is_authenticated else None
            user_membership_data = {
                "is_authenticated": bool(user),
                "has_active_pass": False,
                "has_active_subscription": False,
                "session_pass": None,
                "subscription": None,
                "total_available_sessions": 0,
            }

            if user:
                now = timezone.now()

                active_passes = ClientPurchase.objects.filter(
                    user=user,
                    purchase_type='session_pass',
                    payment_status='paid',
                    status='confirmed',
                    remaining_sessions__gt=0,
                ).order_by('-created_at')

                latest_pass = active_passes.first()
                if latest_pass:
                    total_pass_sessions = sum(p.remaining_sessions for p in active_passes)
                    user_membership_data["has_active_pass"] = True
                    user_membership_data["session_pass"] = {
                        "purchase_id": latest_pass.purchase_id,
                        "name": latest_pass.session_pass.name if latest_pass.session_pass else "Session Pass",
                        "remaining_sessions": latest_pass.remaining_sessions,
                        "total_sessions": latest_pass.total_sessions,
                        "total_remaining_across_all_passes": total_pass_sessions,
                        "max_active_reservations": latest_pass.max_active_reservations or 10,
                        "status": latest_pass.status,
                        "payment_status": latest_pass.payment_status,
                    }
                    user_membership_data["total_available_sessions"] += total_pass_sessions

                active_subs = ClientPurchase.objects.filter(
                    user=user,
                    purchase_type='subscription',
                    payment_status='paid',
                    status='confirmed',
                ).filter(
                    models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)
                ).filter(
                    models.Q(subscription_plan__plan_category='saltroom') | models.Q(subscription_plan__isnull=True)
                ).order_by('-created_at')

                # Separate weekly vs unlimited subscriptions
                weekly_sub = active_subs.filter(subscription_plan__plan_type='weekly').first()
                unlimited_sub = active_subs.filter(subscription_plan__plan_type='unlimited').first()

                # Start of week (Monday) and end of week (Sunday) for target_date
                start_of_week = target_date - timedelta(days=target_date.weekday())
                end_of_week = start_of_week + timedelta(days=6)

                # Process Weekly Subscription
                weekly_sub_data = None
                if weekly_sub:
                    w_plan = weekly_sub.subscription_plan
                    w_valid = True
                    if weekly_sub.start_date and target_date < weekly_sub.start_date.date():
                        w_valid = False
                    if weekly_sub.end_date and target_date > weekly_sub.end_date.date():
                        w_valid = False

                    w_week_bookings = SaltRoomBooking.objects.filter(
                        client_purchase=weekly_sub,
                        date__gte=start_of_week,
                        date__lte=end_of_week,
                    ).exclude(status='cancelled').count()

                    w_future_res = SaltRoomBooking.objects.filter(
                        client_purchase=weekly_sub,
                        status='confirmed',
                        date__gte=now.date(),
                    ).count()
                    w_max_res = weekly_sub.max_active_reservations or 1

                    w_avail_date = True
                    w_avail_week = True
                    w_reason = None

                    if not w_valid:
                        w_avail_date = False
                        w_avail_week = False
                        w_reason = "Selected date falls outside this subscription validity period."
                    elif weekly_sub.remaining_sessions <= 0:
                        w_avail_date = False
                        w_avail_week = False
                        w_reason = "No remaining sessions left in this weekly subscription."
                    elif w_week_bookings >= (weekly_sub.sessions_per_week or 1):
                        w_avail_date = False
                        w_avail_week = False
                        w_reason = f"Weekly session limit ({weekly_sub.sessions_per_week or 1}/week) already reached for this week."

                    weekly_sub_data = {
                        "purchase_id": weekly_sub.purchase_id,
                        "name": w_plan.name if w_plan else "Weekly Subscription",
                        "plan_type": "weekly",
                        "plan_category": "saltroom",
                        "start_date": weekly_sub.start_date,
                        "end_date": weekly_sub.end_date,
                        "is_unlimited": False,
                        "remaining_sessions": weekly_sub.remaining_sessions,
                        "total_sessions": weekly_sub.total_sessions,
                        "sessions_per_week": weekly_sub.sessions_per_week or 1,
                        "max_active_reservations": w_max_res,
                        "status": weekly_sub.status,
                        "payment_status": weekly_sub.payment_status,
                        "is_available_for_date": w_avail_date,
                        "is_available_for_today": w_avail_date,
                        "is_available_for_week": w_avail_week,
                        "week_bookings_count": w_week_bookings,
                        "unavailable_reason": w_reason,
                    }
                    user_membership_data["total_available_sessions"] += weekly_sub.remaining_sessions

                # Process Unlimited Subscription
                unlimited_sub_data = None
                if unlimited_sub:
                    u_plan = unlimited_sub.subscription_plan
                    u_valid = True
                    if unlimited_sub.start_date and target_date < unlimited_sub.start_date.date():
                        u_valid = False
                    if unlimited_sub.end_date and target_date > unlimited_sub.end_date.date():
                        u_valid = False

                    # Max 10 concurrent active upcoming reservations
                    u_future_res = SaltRoomBooking.objects.filter(
                        client_purchase=unlimited_sub,
                        status='confirmed',
                        date__gte=now.date(),
                    ).count()
                    u_max_res = unlimited_sub.max_active_reservations or (u_plan.max_reservations if u_plan else 10) or 10

                    u_avail_date = True
                    u_reason = None

                    if not u_valid:
                        u_avail_date = False
                        u_reason = "Selected date falls outside this subscription validity period."
                    elif u_future_res >= u_max_res:
                        u_avail_date = False
                        u_reason = f"Maximum concurrent reservations limit ({u_max_res}) reached. You currently have {u_future_res} active bookings."

                    unlimited_sub_data = {
                        "purchase_id": unlimited_sub.purchase_id,
                        "name": u_plan.name if u_plan else "Unlimited Subscription",
                        "plan_type": "unlimited",
                        "plan_category": "saltroom",
                        "start_date": unlimited_sub.start_date,
                        "end_date": unlimited_sub.end_date,
                        "is_unlimited": True,
                        "remaining_sessions": "unlimited",
                        "active_reservations_count": u_future_res,
                        "max_active_reservations": u_max_res,
                        "status": unlimited_sub.status,
                        "payment_status": unlimited_sub.payment_status,
                        "is_available_for_date": u_avail_date,
                        "is_available_for_today": u_avail_date,
                        "is_available_for_week": u_avail_date,  # Unlimited has no weekly limit
                        "unavailable_reason": u_reason,
                    }

                # Set user_membership_data flags
                user_membership_data["has_active_subscription"] = bool(weekly_sub or unlimited_sub)
                user_membership_data["has_active_weekly_subscription"] = bool(weekly_sub)
                user_membership_data["has_active_unlimited_subscription"] = bool(unlimited_sub)
                user_membership_data["weekly_subscription"] = weekly_sub_data
                user_membership_data["unlimited_subscription"] = unlimited_sub_data

                # Default 'subscription' object: Prefer the one that is currently available, or the first active one
                best_sub = None
                if unlimited_sub_data and unlimited_sub_data["is_available_for_date"]:
                    best_sub = unlimited_sub_data
                elif weekly_sub_data and weekly_sub_data["is_available_for_date"]:
                    best_sub = weekly_sub_data
                else:
                    best_sub = unlimited_sub_data or weekly_sub_data
                user_membership_data["subscription"] = best_sub



            # Calculate saltroom slots and check existing bookings for target_date
            duration_td = saltroom_obj.duration if saltroom_obj and saltroom_obj.duration else timedelta(minutes=60)
            buffer_td = saltroom_obj.buffer_time if saltroom_obj and saltroom_obj.buffer_time else timedelta(minutes=10)
            max_capacity = saltroom_obj.max_capacity if saltroom_obj and saltroom_obj.max_capacity else 2

            step_td = duration_td + buffer_td
            saltroom_bookings = SaltRoomBooking.objects.filter(
                date=target_date
            ).exclude(status='cancelled')

            saltroom_slots = []
            curr_dt = open_dt
            while curr_dt + duration_td <= close_dt:
                slot_start = curr_dt
                slot_end = slot_start + duration_td
                slot_buffer_end = slot_start + step_td

                # Count bookings overlapping this slot
                booked_capacity = 0
                for sb in saltroom_bookings:
                    sb_start = datetime.combine(target_date, sb.start_time)
                    sb_end = datetime.combine(target_date, sb.end_time)
                    # Overlap if max(slot_start, sb_start) < min(slot_end, sb_end)
                    if max(slot_start, sb_start) < min(slot_end, sb_end):
                        booked_capacity += sb.capacity

                remaining_capacity = max(0, max_capacity - booked_capacity)
                is_available = (remaining_capacity > 0)
                is_fully_booked = (booked_capacity >= max_capacity)

                saltroom_slots.append({
                    "start_time": slot_start.strftime("%H:%M"),
                    "end_time": slot_end.strftime("%H:%M"),
                    "buffer_end_time": slot_buffer_end.strftime("%H:%M"),
                    "duration_minutes": int(duration_td.total_seconds() // 60),
                    "buffer_minutes": int(buffer_td.total_seconds() // 60),
                    "max_capacity": max_capacity,
                    "booked_capacity": booked_capacity,
                    "remaining_capacity": remaining_capacity,
                    "is_available": is_available,
                    "is_fully_booked": is_fully_booked,
                })

                curr_dt = slot_buffer_end

            available_slots_only = [s for s in saltroom_slots if s["is_available"]]

            saltroom_data = {
                "is_available": len(available_slots_only) > 0,
                "open_time": open_time.strftime("%H:%M"),
                "close_time": close_time.strftime("%H:%M"),
                "duration_minutes": int(duration_td.total_seconds() // 60),
                "buffer_minutes": int(buffer_td.total_seconds() // 60),
                "max_capacity": max_capacity,
                "price_per_person": str(saltroom_obj.price_per_person) if saltroom_obj else "25.00",
                "total_slots_count": len(saltroom_slots),
                "available_slots_count": len(available_slots_only),
                "slots": saltroom_slots,
                "available_slots": available_slots_only,
                "user_membership": user_membership_data,
            }

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
            elif sub_type in ['saltroom']:
                data["saltroom"] = saltroom_data
            else:
                # Return combined package slots for all sub-services
                data["sauna"] = sauna_dict
                data["lunchroom"] = lunchroom_data
                data["activities"] = activities_serializer.data
                data["saltroom"] = saltroom_data
        elif s_type == 'saltroom':
            data = saltroom_data
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



from datetime import datetime, date, time
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema

from bookings.models import (
    SaunaBooking,
    LunchroomBooking,
    ActivityBooking,
    EventBooking,
    PackageBooking,
    SaltRoomBooking
)
from payments.models import ClientPurchase
from .serializers import UserDashboardResponseSerializer


def parse_booking_datetime(b_date, b_time=None):
    """
    Safely creates a datetime from date and optional time.
    """
    if not b_date:
        return timezone.now()
    if not b_time:
        b_time = time(0, 0)
    return datetime.combine(b_date, b_time)


def serialize_sauna_booking(b):
    dt = parse_booking_datetime(b.booking_date, b.booking_time)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "sauna",
        "service_name": f"{b.get_sauna_type_display() if hasattr(b, 'get_sauna_type_display') else b.sauna_type.title()} Sauna",
        "date": b.booking_date.strftime("%Y-%m-%d"),
        "time": b.booking_time.strftime("%H:%M") if b.booking_time else "",
        "end_time": None,
        "guests": b.capacity,
        "status": b.status,
        "payment_status": b.payment_status,
        "total_price": str(b.total_price),
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "sauna_type": b.sauna_type,
            "time_slot": b.time_slot,
            "selected_features": b.selected_features or [],
            "special_request": b.special_request or "",
        }
    }


def serialize_lunchroom_booking(b):
    dt = parse_booking_datetime(b.booking_date, b.booking_time)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "lunchroom",
        "service_name": "Lunchroom",
        "date": b.booking_date.strftime("%Y-%m-%d"),
        "time": b.booking_time.strftime("%H:%M") if b.booking_time else "",
        "end_time": None,
        "guests": b.capacity,
        "status": b.status,
        "payment_status": getattr(b, 'payment_status', 'confirmed'),
        "total_price": "0.00",
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "celebration_type": b.celebration_type or "",
            "celebration_date": b.celebration_date.strftime("%Y-%m-%d") if b.celebration_date else None,
            "name_of_celebrant": b.name_of_celebrant or "",
            "age_of_celebrant": b.age_of_celebrant,
            "hobbies": b.hobbies or "",
            "celebration_details": b.celebration_details or "",
            "special_request": b.special_request or "",
        }
    }


def serialize_activity_booking(b):
    act_time = getattr(b.activity, 'open_time', None) if b.activity else None
    act_date = getattr(b.activity, 'date', None) if b.activity else None
    target_date = act_date or b.created_at.date()
    dt = parse_booking_datetime(target_date, act_time)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "activity",
        "service_name": b.activity.title if b.activity and b.activity.title else "Activity",
        "date": target_date.strftime("%Y-%m-%d"),
        "time": act_time.strftime("%H:%M") if act_time else "",
        "end_time": b.activity.close_time.strftime("%H:%M") if (b.activity and b.activity.close_time) else None,
        "guests": b.capacity,
        "status": b.status,
        "payment_status": b.payment_status,
        "total_price": str(b.total_price),
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "activity_id": b.activity.id if b.activity else None,
            "special_request": b.special_request or "",
        }
    }


def serialize_saltroom_booking(b):
    dt = parse_booking_datetime(b.date, b.start_time)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "saltroom",
        "service_name": "Salt Room",
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.start_time.strftime("%H:%M") if b.start_time else "",
        "end_time": b.end_time.strftime("%H:%M") if b.end_time else None,
        "guests": b.capacity,
        "status": b.status,
        "payment_status": b.payment_status,
        "total_price": str(b.total_price),
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "used_pass": b.used_pass,
            "used_subscription": b.used_subscription,
            "is_paid": b.is_paid,
            "special_request": b.special_request or "",
        }
    }


def serialize_package_booking(b):
    dt = parse_booking_datetime(b.date, None)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "package",
        "service_name": "Package Experience",
        "date": b.date.strftime("%Y-%m-%d"),
        "time": "",
        "end_time": None,
        "guests": b.guests,
        "status": b.status,
        "payment_status": b.payment_status,
        "total_price": str(b.total_price),
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "is_custom": b.is_custom,
            "service_names": b.service_names or [],
            "booked_services_ids": b.booked_services_ids or [],
            "notes": b.notes or "",
        }
    }


def serialize_event_booking(b):
    dt = parse_booking_datetime(b.date, b.start_time)
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "event",
        "service_name": "Special Event",
        "date": b.date.strftime("%Y-%m-%d"),
        "time": b.start_time.strftime("%H:%M") if b.start_time else "",
        "end_time": b.end_time.strftime("%H:%M") if b.end_time else None,
        "guests": b.guests,
        "status": getattr(b, 'status', 'confirmed'),
        "payment_status": getattr(b, 'payment_status', 'pending'),
        "total_price": "0.00",
        "access_code": b.booking_id,
        "datetime": dt,
        "details": {
            "food_preference": b.food_preference or "",
            "drink_preference": b.drink_preference or "",
            "music_preference": b.music_preference or "",
            "notes": b.notes or "",
        }
    }


def serialize_client_purchase(p):
    plan_name = p.session_pass.name if p.session_pass else (p.subscription_plan.name if p.subscription_plan else p.name)
    category = "pass" if p.purchase_type == "session_pass" else (p.subscription_plan.plan_category if p.subscription_plan else "subscription")
    plan_type = p.subscription_plan.plan_type if p.subscription_plan else None

    # Calculate active concurrent reservations for unlimited subscription
    active_reservations_count = 0
    remaining_sessions = p.remaining_sessions
    total_sessions = p.total_sessions

    if plan_type == 'unlimited':
        now_date = timezone.now().date()
        active_reservations_count = SaltRoomBooking.objects.filter(
            client_purchase=p,
            status='confirmed',
            date__gte=now_date,
        ).count()
        max_res = p.max_active_reservations or (p.subscription_plan.max_reservations if p.subscription_plan else 10) or 10
        total_sessions = max_res
        remaining_sessions = max(0, max_res - active_reservations_count)

    return {
        "purchase_id": p.purchase_id,
        "purchase_type": p.purchase_type,
        "name": plan_name,
        "category": category,
        "amount": str(p.amount),
        "currency": p.currency,
        "total_sessions": total_sessions,
        "remaining_sessions": remaining_sessions,
        "active_reservations_count": active_reservations_count,
        "sessions_per_week": p.sessions_per_week,
        "max_active_reservations": p.max_active_reservations,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "status": p.status,
        "payment_status": p.payment_status,
        "is_expired": p.is_expired,
        "details": {
            "plan_type": plan_type,
            "duration_weeks": p.subscription_plan.duration_weeks if p.subscription_plan else None,
            "active_reservations_count": active_reservations_count,
        }
    }


class UserDashboardView(APIView):
    """
    User Dashboard API providing:
    1. Home Section:
       - metrics: total_bookings, upcoming_bookings, upcoming_booking_dates, active_subscriptions, upcoming_saunas
       - next_visit: Immediate next upcoming booking or event
       - subscriptions_and_passes: Active subscriptions and session passes
       - next_visits: Next 5 upcoming visits after next_visit
       - other_upcoming_visits: All other upcoming visits
    2. My Bookings Section:
       - upcoming: All upcoming bookings
       - past: All past bookings
    3. Access Codes Section:
       - Sauna bookings (Private Sauna & Shared Sauna) with booking ID as access code
    4. Profile Section:
       - User profile details
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Dashboard'],
        summary="User Dashboard with comprehensive Home (Metrics, Next Visit, Subscriptions, Next 5 Visits), My Bookings, Access Codes, and Profile",
        responses={200: UserDashboardResponseSerializer}
    )
    def get(self, request):
        user = request.user
        email = user.email

        # 1. Query all bookings linked to user or email
        user_filter = Q(user=user) | Q(email__iexact=email)

        sauna_qs = SaunaBooking.objects.filter(user_filter)
        lunchroom_qs = LunchroomBooking.objects.filter(user_filter)
        activity_qs = ActivityBooking.objects.filter(user_filter)
        saltroom_qs = SaltRoomBooking.objects.filter(user_filter)
        package_qs = PackageBooking.objects.filter(user_filter)
        event_qs = EventBooking.objects.filter(user_filter)

        all_items = []
        for b in sauna_qs:
            all_items.append(serialize_sauna_booking(b))
        for b in lunchroom_qs:
            all_items.append(serialize_lunchroom_booking(b))
        for b in activity_qs:
            all_items.append(serialize_activity_booking(b))
        for b in saltroom_qs:
            all_items.append(serialize_saltroom_booking(b))
        for b in package_qs:
            all_items.append(serialize_package_booking(b))
        for b in event_qs:
            all_items.append(serialize_event_booking(b))

        now = timezone.now()
        now_dt = now.replace(tzinfo=None) if timezone.is_aware(now) else now

        upcoming_items = []
        past_items = []

        for item in all_items:
            b_dt = item["datetime"]
            if timezone.is_aware(b_dt):
                b_dt = b_dt.replace(tzinfo=None)

            # Exclude cancelled bookings from upcoming
            if b_dt >= now_dt and item.get("status") != "cancelled":
                upcoming_items.append(item)
            else:
                past_items.append(item)

        # Sort upcoming by earliest date/time first
        upcoming_items.sort(key=lambda x: x["datetime"])
        # Sort past by latest date/time first
        past_items.sort(key=lambda x: x["datetime"], reverse=True)

        # Extract dates of upcoming bookings
        upcoming_booking_dates = []
        seen_dates = set()
        for item in upcoming_items:
            d_str = item.get("date")
            if d_str and d_str not in seen_dates:
                seen_dates.add(d_str)
                upcoming_booking_dates.append(d_str)

        # Upcoming sauna bookings count
        upcoming_saunas_count = sum(1 for item in upcoming_items if item.get("service_type") == "sauna")

        # Strip internal datetime helper before output
        for item in upcoming_items + past_items:
            item.pop("datetime", None)

        # 2. Query Subscriptions & Passes
        purchase_filter = Q(user=user) | Q(email__iexact=email)
        active_purchases_qs = ClientPurchase.objects.filter(
            purchase_filter,
            payment_status='paid',
            status='confirmed',
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gt=now)
        ).order_by('-created_at')

        active_subscriptions_list = []
        for p in active_purchases_qs:
            if not p.is_expired:
                active_subscriptions_list.append(serialize_client_purchase(p))

        # 3. Home section calculations
        total_bookings_count = len(all_items)
        upcoming_bookings_count = len(upcoming_items)
        active_subscriptions_count = len(active_subscriptions_list)

        home_metrics = {
            "total_bookings": total_bookings_count,
            "upcoming_bookings": upcoming_bookings_count,
            "upcoming_booking_dates": upcoming_booking_dates,
            "active_subscriptions": active_subscriptions_count,
            "upcoming_saunas": upcoming_saunas_count,
        }

        # Immediate next upcoming booking/event
        next_visit = upcoming_items[0] if upcoming_items else None
        # Next 5 visits right after immediate next visit
        next_visits = upcoming_items[1:6] if len(upcoming_items) > 1 else []
        # Remaining upcoming visits
        other_upcoming_visits = upcoming_items[1:] if len(upcoming_items) > 1 else []

        # 4. Access Codes section (Sauna bookings: Private and Shared)
        access_code_private = []
        access_code_shared = []
        access_code_all = []

        for b in sauna_qs.order_by('-booking_date', '-booking_time'):
            code_item = {
                "booking_id": b.booking_id,
                "access_code": b.booking_id,
                "sauna_type": b.sauna_type,
                "date": b.booking_date.strftime("%Y-%m-%d"),
                "time": b.booking_time.strftime("%H:%M") if b.booking_time else "",
                "time_slot": b.time_slot,
                "status": b.status,
                "payment_status": b.payment_status,
                "guests": b.capacity,
                "details": {
                    "selected_features": b.selected_features or [],
                    "special_request": b.special_request or "",
                    "total_price": str(b.total_price),
                }
            }
            if b.sauna_type == 'private':
                access_code_private.append(code_item)
            else:
                access_code_shared.append(code_item)
            access_code_all.append(code_item)

        # 5. Profile Section
        profile_data = {
            "id": user.id,
            "name": user.name or "",
            "email": user.email,
            "phone": user.phone or "",
            "image": request.build_absolute_uri(user.image.url) if (user.image and hasattr(user.image, 'url')) else None,
            "language": user.language or "en",
            "role": user.role or "user",
            "date_joined": user.date_joined,
        }

        return Response({
            "success": True,
            "home": {
                "metrics": home_metrics,
                "next_visit": next_visit,
                "subscriptions_and_passes": active_subscriptions_list,
                "next_visits": next_visits,
                "other_upcoming_visits": other_upcoming_visits,
            },
            "my_bookings": {
                "upcoming": upcoming_items,
                "past": past_items,
            },
            "access_codes": {
                "private_sauna": access_code_private,
                "shared_sauna": access_code_shared,
                "all_sauna": access_code_all,
            },
            "profile": profile_data,
        }, status=status.HTTP_200_OK)
from decimal import Decimal
from django.contrib.auth import get_user_model
import math
from datetime import datetime, date, time, timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from services.serializers import ServicesSerializer

from bookings.models import (
    SaunaBooking,
    LunchroomBooking,
    ActivityBooking,
    EventBooking,
    PackageBooking,
    SaltRoomBooking
)
from payments.models import ClientPurchase, Payments
from .serializers import (
    UserDashboardResponseSerializer,
    AdminBookingItemSerializer,
    AdminBookingsPaginationResponseSerializer,
    AdminBookingDetailResponseSerializer,
    AdminBookingStatusUpdateSerializer,
    AdminPaymentsResponseSerializer,
    MonthlyPaymentsSummarySerializer,
    ServicePaymentBreakdownItemSerializer,
    AdminPaymentListItemSerializer,
    AdminAccessCodeItemSerializer,
    AdminAccessCodesSummarySerializer,
    AdminAccessCodesResponseSerializer,
    AdminAccessCodeDetailResponseSerializer,
    BlockDateItemSerializer,
    BlockDateCreateUpdateSerializer,
    SpecialOpeningDateItemSerializer,
    SpecialOpeningDateCreateUpdateSerializer,
    AdminDatesSummarySerializer,
    AdminDatesOverviewResponseSerializer,
    AdminDateActionResponseSerializer,
    AdminUsersPaginationResponseSerializer,
    AdminUserUpdateSerializer,
    AdminUserActionResponseSerializer,
)


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
    s_disp = b.get_sauna_type_display() if hasattr(b, 'get_sauna_type_display') else b.sauna_type.title()
    s_title = s_disp if 'sauna' in s_disp.lower() else f"{s_disp} Sauna"
    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": "sauna",
        "service_name": s_title,
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


from services.models import (
    Services,
    PrivateSauna,
    PrivateSaunaFeatures,
    SharedSauna,
    SharedSaunaFeatures,
    Activities,
    ActivitiesFeature,
    Lunchroom,
    Saltroom,
    SaltroomFeatures,
    Packages,
    PackageFeatures,
    ServiceSettings,
    BlockDate,
    SpecialOpeningDate
)


DEMO_SERVICES_CONFIG = {
    'sauna': {
        'title': 'Sauna Experience',
        'subtitle': 'Relax and rejuvenate in our premium sauna facilities',
        'description': 'Enjoy both private and shared sauna experiences crafted for your well-being.',
    },
    'saltroom': {
        'title': 'Salt Room',
        'subtitle': 'Therapeutic halotherapy environment for healing and deep breathing',
        'description': 'Breathe clean, ionized air infused with natural mineral salts for respiratory and skin health.',
    },
    'activity': {
        'title': 'Wellness Activities',
        'subtitle': 'Join our guided wellness and relaxation sessions',
        'description': 'Explore interactive sessions, workshops, and wellness activities designed for health and harmony.',
    },
    'lunchroom': {
        'title': 'Lunchroom',
        'subtitle': 'Healthy, nourishing organic meals and beverages',
        'description': 'Savor fresh, nutrient-rich food and refreshing juices prepared with locally sourced ingredients.',
    },
    'package': {
        'title': 'Wellness Packages',
        'subtitle': 'Comprehensive wellness bundles for total rejuvenation',
        'description': 'Choose from our curated wellness packages combining sauna, salt room, and dining experiences.',
    },
    'event': {
        'title': 'Events & Gatherings',
        'subtitle': 'Special workshops, retreats, and private group events',
        'description': 'Host or join special wellness events, seasonal retreats, and celebrations.',
    },
}

TYPE_MAPPING = {
    'activities': 'activity',
    'activity': 'activity',
    'packages': 'package',
    'package': 'package',
    'events': 'event',
    'event': 'event',
    'saunas': 'sauna',
    'sauna': 'sauna',
    'saltrooms': 'saltroom',
    'saltroom': 'saltroom',
    'lunchrooms': 'lunchroom',
    'lunchroom': 'lunchroom',
    'private_sauna': 'sauna',
    'shared_sauna': 'sauna',
    'private-sauna': 'sauna',
    'shared-sauna': 'sauna',
}


def get_or_create_service_with_demo(raw_type=None, service_id=None):
    """
    Retrieves the service matching id or type. If it does not exist in the database,
    it automatically creates the service with demo data and translation fields,
    ensuring the frontend always receives valid data.
    """
    service_obj = None
    raw_str = (raw_type or '').strip()

    if raw_str.isdigit():
        service_obj = Services.objects.filter(id=int(raw_str)).first()
    elif service_id and str(service_id).isdigit():
        service_obj = Services.objects.filter(id=int(service_id)).first()

    svc_type_param = raw_str.lower()
    canonical_type = TYPE_MAPPING.get(svc_type_param, svc_type_param)

    if not service_obj and canonical_type:
        service_obj = Services.objects.filter(type=canonical_type).first()
        if not service_obj:
            service_obj = Services.objects.filter(title__iexact=svc_type_param).first()

    if not service_obj:
        valid_types = [t[0] for t in Services.SERVICE_TYPES]
        target_type = canonical_type if canonical_type in valid_types else 'sauna'
        demo_info = DEMO_SERVICES_CONFIG.get(target_type, {
            'title': (raw_str or target_type).replace('_', ' ').title(),
            'subtitle': f'Experience our {(raw_str or target_type).replace("_", " ")} service',
            'description': f'High quality {(raw_str or target_type).replace("_", " ")} services designed for wellness.',
        })

        service_obj, _ = Services.objects.get_or_create(
            type=target_type,
            defaults={
                'title': demo_info['title'],
                'subtitle': demo_info.get('subtitle', ''),
                'description': demo_info.get('description', ''),
            }
        )
        for lang in ['en', 'nl', 'de']:
            for field in ['title', 'subtitle', 'description']:
                attr = f"{field}_{lang}"
                if hasattr(service_obj, attr) and not getattr(service_obj, attr):
                    setattr(service_obj, attr, getattr(service_obj, field, ''))
        service_obj.save()

    return service_obj


class AdminServiceDetailView(APIView):
    """
    Admin Dashboard API to retrieve full service details along with related models,
    features, settings, and all multilingual translation fields (en, nl, de).
    Accepts service_type in URL path, or 'id' / 'type' in query parameters.
    If data does not exist in backend, demo data is automatically created and returned.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Get Admin Service Details with Multi-language and Features",
    )
    def get(self, request, service_type=None):
        # 1. Resolve or get_or_create service with demo data
        service_id = request.query_params.get('id')
        raw_type = (service_type or request.query_params.get('type') or '').strip()

        service_obj = get_or_create_service_with_demo(raw_type=raw_type, service_id=service_id)

        # 2. Main Service Data with full multi-language fields
        service_data = {
            "id": service_obj.id,
            "type": service_obj.type,
            "title": service_obj.title,
            "title_en": getattr(service_obj, 'title_en', service_obj.title),
            "title_nl": getattr(service_obj, 'title_nl', service_obj.title),
            "title_de": getattr(service_obj, 'title_de', service_obj.title),
            "subtitle": service_obj.subtitle,
            "subtitle_en": getattr(service_obj, 'subtitle_en', service_obj.subtitle),
            "subtitle_nl": getattr(service_obj, 'subtitle_nl', service_obj.subtitle),
            "subtitle_de": getattr(service_obj, 'subtitle_de', service_obj.subtitle),
            "description": service_obj.description,
            "description_en": getattr(service_obj, 'description_en', service_obj.description),
            "description_nl": getattr(service_obj, 'description_nl', service_obj.description),
            "description_de": getattr(service_obj, 'description_de', service_obj.description),
            "image": request.build_absolute_uri(service_obj.image.url) if (service_obj.image and hasattr(service_obj.image, 'url')) else None,
            "created_at": service_obj.created_at,
            "updated_at": service_obj.updated_at,
        }

        # 3. Service Settings / Operating Hours (with demo fallback)
        settings_qs = ServiceSettings.objects.filter(service=service_obj)
        if not settings_qs.exists():
            default_setting, _ = ServiceSettings.objects.get_or_create(
                service=service_obj,
                defaults={
                    "week_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    "open_time": "09:00:00",
                    "close_time": "21:00:00",
                    "is_closed": False,
                }
            )
            settings_qs = ServiceSettings.objects.filter(service=service_obj)

        settings_data = []
        for s in settings_qs:
            settings_data.append({
                "id": s.id,
                "week_days": s.week_days or [],
                "open_time": s.open_time.strftime("%H:%M") if s.open_time else "09:00",
                "close_time": s.close_time.strftime("%H:%M") if s.close_time else "21:00",
                "is_closed": s.is_closed,
            })

        # 4. Service-Specific Related Details & Features
        s_type = service_obj.type
        details_data = {}

        if s_type == 'sauna':
            # Private Sauna demo fallback
            if not PrivateSauna.objects.exists():
                ps = PrivateSauna.objects.create(
                    base_price_3hrs=75.00,
                    base_price_4hrs=95.00,
                    max_person=6,
                    extra_person_price=20.00,
                    is_available=True
                )
                PrivateSaunaFeatures.objects.create(sauna=ps, feature='Towel & Bathrobe', price=0)
                PrivateSaunaFeatures.objects.create(sauna=ps, feature='Essential Oils', price=5.00)

            # Shared Sauna demo fallback
            if not SharedSauna.objects.exists():
                ss = SharedSauna.objects.create(
                    price_per_person=25.00,
                    max_person=12,
                    is_available=True
                )
                SharedSaunaFeatures.objects.create(sauna=ss, feature='Access to Pool & Steam', price=0)

            private_saunas = PrivateSauna.objects.prefetch_related('features').all()
            private_list = []
            for p in private_saunas:
                feats = []
                for f in p.features.all():
                    feats.append({
                        "id": f.id,
                        "feature": f.feature,
                        "feature_en": getattr(f, 'feature_en', f.feature),
                        "feature_nl": getattr(f, 'feature_nl', f.feature),
                        "feature_de": getattr(f, 'feature_de', f.feature),
                        "price": str(f.price),
                    })
                private_list.append({
                    "id": p.id,
                    "base_price_3hrs": str(p.base_price_3hrs),
                    "base_price_4hrs": str(p.base_price_4hrs),
                    "max_person": p.max_person,
                    "extra_person_price": str(p.extra_person_price),
                    "is_available": p.is_available,
                    "features": feats,
                })

            shared_saunas = SharedSauna.objects.prefetch_related('features').all()
            shared_list = []
            for sh in shared_saunas:
                feats = []
                for f in sh.features.all():
                    feats.append({
                        "id": f.id,
                        "feature": f.feature,
                        "feature_en": getattr(f, 'feature_en', f.feature),
                        "feature_nl": getattr(f, 'feature_nl', f.feature),
                        "feature_de": getattr(f, 'feature_de', f.feature),
                        "price": str(f.price),
                    })
                shared_list.append({
                    "id": sh.id,
                    "price_per_person": str(sh.price_per_person),
                    "max_person": sh.max_person,
                    "is_available": sh.is_available,
                    "features": feats,
                })

            details_data = {
                "private_sauna": private_list,
                "shared_sauna": shared_list,
            }

        elif s_type == 'activity':
            if not Activities.objects.exists():
                act = Activities.objects.create(
                    title="Yoga & Mindfulness Session",
                    description="Daily morning yoga and mindfulness session for balance and relaxation.",
                    capacity=12,
                    host="Emma Davis",
                    price=25.00,
                    is_available=True,
                    additional_notes="Mats and water provided."
                )
                ActivitiesFeature.objects.create(activity=act, feature="Yoga Mat & Props")
                ActivitiesFeature.objects.create(activity=act, feature="Guided Breathwork")

            activities = Activities.objects.prefetch_related('features').all()
            act_list = []
            for a in activities:
                feats = []
                for f in a.features.all():
                    feats.append({
                        "id": f.id,
                        "feature": f.feature,
                        "feature_en": getattr(f, 'feature_en', f.feature),
                        "feature_nl": getattr(f, 'feature_nl', f.feature),
                        "feature_de": getattr(f, 'feature_de', f.feature),
                    })
                act_list.append({
                    "id": a.id,
                    "title": a.title,
                    "title_en": getattr(a, 'title_en', a.title),
                    "title_nl": getattr(a, 'title_nl', a.title),
                    "title_de": getattr(a, 'title_de', a.title),
                    "description": a.description,
                    "description_en": getattr(a, 'description_en', a.description),
                    "description_nl": getattr(a, 'description_nl', a.description),
                    "description_de": getattr(a, 'description_de', a.description),
                    "date": a.date.strftime("%Y-%m-%d") if a.date else None,
                    "open_time": a.open_time.strftime("%H:%M") if a.open_time else None,
                    "close_time": a.close_time.strftime("%H:%M") if a.close_time else None,
                    "capacity": a.capacity,
                    "host": a.host,
                    "price": str(a.price),
                    "is_available": a.is_available,
                    "additional_notes": a.additional_notes,
                    "additional_notes_en": getattr(a, 'additional_notes_en', a.additional_notes),
                    "additional_notes_nl": getattr(a, 'additional_notes_nl', a.additional_notes),
                    "additional_notes_de": getattr(a, 'additional_notes_de', a.additional_notes),
                    "image": request.build_absolute_uri(a.images.url) if (a.images and hasattr(a.images, 'url')) else None,
                    "images": request.build_absolute_uri(a.images.url) if (a.images and hasattr(a.images, 'url')) else None,
                    "features": feats,
                })
            details_data = {
                "activities": act_list
            }

        elif s_type == 'saltroom':
            if not Saltroom.objects.exists():
                sr = Saltroom.objects.create(
                    title="Salt Room Therapy",
                    subtitle="Microclimate Halotherapy",
                    description="Pure medical-grade Himalayan salt microclimate for respiratory health and deep relaxation.",
                    max_capacity=6,
                    price_per_person=30.00,
                    duration=timedelta(minutes=45),
                    buffer_time=timedelta(minutes=15)
                )
                SaltroomFeatures.objects.create(saltroom=sr, feature="Medical-grade Himalayan Salt")
                SaltroomFeatures.objects.create(saltroom=sr, feature="Zero-gravity Heated Recliners")

            saltrooms = Saltroom.objects.prefetch_related('features').all()
            salt_list = []
            for sr in saltrooms:
                feats = []
                for f in sr.features.all():
                    feats.append({
                        "id": f.id,
                        "feature": f.feature,
                        "feature_en": getattr(f, 'feature_en', f.feature),
                        "feature_nl": getattr(f, 'feature_nl', f.feature),
                        "feature_de": getattr(f, 'feature_de', f.feature),
                    })
                dur_minutes = int(sr.duration.total_seconds() // 60) if sr.duration else 60
                buf_minutes = int(sr.buffer_time.total_seconds() // 60) if sr.buffer_time else 10
                salt_list.append({
                    "id": sr.id,
                    "title": sr.title,
                    "title_en": getattr(sr, 'title_en', sr.title),
                    "title_nl": getattr(sr, 'title_nl', sr.title),
                    "title_de": getattr(sr, 'title_de', sr.title),
                    "subtitle": sr.subtitle,
                    "subtitle_en": getattr(sr, 'subtitle_en', sr.subtitle),
                    "subtitle_nl": getattr(sr, 'subtitle_nl', sr.subtitle),
                    "subtitle_de": getattr(sr, 'subtitle_de', sr.subtitle),
                    "description": sr.description,
                    "description_en": getattr(sr, 'description_en', sr.description),
                    "description_nl": getattr(sr, 'description_nl', sr.description),
                    "description_de": getattr(sr, 'description_de', sr.description),
                    "max_capacity": sr.max_capacity,
                    "price_per_person": str(sr.price_per_person),
                    "duration_minutes": dur_minutes,
                    "buffer_minutes": buf_minutes,
                    "images": request.build_absolute_uri(sr.images.url) if (sr.images and hasattr(sr.images, 'url')) else None,
                    "features": feats,
                })
            details_data = {
                "saltroom": salt_list
            }

        elif s_type == 'lunchroom':
            if not Lunchroom.objects.exists():
                Lunchroom.objects.create(
                    title="Organic Wellness Lunchroom",
                    subtitle="Nourishing Fresh Dining",
                    description="Delicious organic meals, cold-pressed juices, and healthy snacks made from local ingredients."
                )

            lunchrooms = Lunchroom.objects.all()
            lunch_list = []
            for lr in lunchrooms:
                lunch_list.append({
                    "id": lr.id,
                    "title": lr.title,
                    "title_en": getattr(lr, 'title_en', lr.title),
                    "title_nl": getattr(lr, 'title_nl', lr.title),
                    "title_de": getattr(lr, 'title_de', lr.title),
                    "subtitle": lr.subtitle,
                    "subtitle_en": getattr(lr, 'subtitle_en', lr.subtitle),
                    "subtitle_nl": getattr(lr, 'subtitle_nl', lr.subtitle),
                    "subtitle_de": getattr(lr, 'subtitle_de', lr.subtitle),
                    "description": lr.description,
                    "description_en": getattr(lr, 'description_en', lr.description),
                    "description_nl": getattr(lr, 'description_nl', lr.description),
                    "description_de": getattr(lr, 'description_de', lr.description),
                    "images": request.build_absolute_uri(lr.images.url) if (lr.images and hasattr(lr.images, 'url')) else None,
                })
            details_data = {
                "lunchroom": lunch_list
            }

        elif s_type == 'package':
            if not Packages.objects.exists():
                pkg = Packages.objects.create(
                    title="Total Rejuvenation Package",
                    description="Experience our ultimate package combining 3 hours of private sauna, 45 minutes of salt room, and organic lunch.",
                    price=140.00,
                    packages=['private_sauna', 'saltroom', 'lunchroom']
                )
                PackageFeatures.objects.create(package=pkg, feature="Full Access to Wellness Amenities")
                PackageFeatures.objects.create(package=pkg, feature="Complimentary Herbal Teas & Lunch")

            packages = Packages.objects.prefetch_related('features').all()
            pkg_list = []
            for pk in packages:
                feats = []
                for f in pk.features.all():
                    feats.append({
                        "id": f.id,
                        "feature": f.feature,
                        "feature_en": getattr(f, 'feature_en', f.feature),
                        "feature_nl": getattr(f, 'feature_nl', f.feature),
                        "feature_de": getattr(f, 'feature_de', f.feature),
                    })
                pkg_list.append({
                    "id": pk.id,
                    "title": pk.title,
                    "title_en": getattr(pk, 'title_en', pk.title),
                    "title_nl": getattr(pk, 'title_nl', pk.title),
                    "title_de": getattr(pk, 'title_de', pk.title),
                    "description": pk.description,
                    "description_en": getattr(pk, 'description_en', pk.description),
                    "description_nl": getattr(pk, 'description_nl', pk.description),
                    "description_de": getattr(pk, 'description_de', pk.description),
                    "price": str(pk.price),
                    "packages": pk.packages or [],
                    "image": request.build_absolute_uri(pk.image.url) if (pk.image and hasattr(pk.image, 'url')) else None,
                    "images": request.build_absolute_uri(pk.image.url) if (pk.image and hasattr(pk.image, 'url')) else None,
                    "features": feats,
                })
            details_data = {
                "packages": pkg_list
            }

        elif s_type == 'event':
            details_data = {
                "events": [
                    {
                        "id": 1,
                        "title": "Full Moon Sound Healing & Sauna",
                        "description": "An evening of meditative sound therapy followed by a detoxifying sauna session.",
                        "date": "2026-11-01",
                        "open_time": "18:00",
                        "close_time": "21:00",
                        "capacity": 15,
                        "price": "45.00",
                        "is_available": True
                    }
                ]
            }

        return Response({
            "success": True,
            "service": service_data,
            "settings": settings_data,
            "details": details_data,
            "message": f"Admin details for service '{service_obj.title}'",
        }, status=status.HTTP_200_OK)

    def patch(self, request, service_type=None):
        service_id = request.data.get('id') or request.query_params.get('id')
        raw_type = (service_type or request.data.get('type') or request.query_params.get('type') or '').strip()

        service_obj = get_or_create_service_with_demo(raw_type=raw_type, service_id=service_id)

        section = request.data.get('section', 'all')

        # 1. Update Main Service Details
        if section in ['service_details', 'all']:
            for f in ['title', 'title_en', 'title_nl', 'title_de', 'subtitle', 'subtitle_en', 'subtitle_nl', 'subtitle_de', 'description', 'description_en', 'description_nl', 'description_de']:
                if f in request.data:
                    setattr(service_obj, f, request.data[f])
            if 'image' in request.FILES:
                service_obj.image = request.FILES['image']
            service_obj.save()

        # 2. Update Service Opening Hours / Operating Hours Settings
        if section in ['opening_hours', 'service_opening_hours', 'all']:
            settings_list = request.data.get('settings') or request.data.get('opening_hours')
            if settings_list is not None:
                if isinstance(settings_list, str):
                    import json
                    try:
                        settings_list = json.loads(settings_list)
                    except Exception:
                        settings_list = []

                # Replace or update settings for this specific service
                existing_settings = {s.id: s for s in ServiceSettings.objects.filter(service=service_obj)}
                kept_ids = []

                for item in settings_list:
                    s_id = item.get('id')
                    week_days = item.get('week_days') or []
                    open_time = item.get('open_time') or '09:00:00'
                    close_time = item.get('close_time') or '21:00:00'
                    is_closed = bool(item.get('is_closed', False))

                    if s_id and int(s_id) in existing_settings:
                        setting_obj = existing_settings[int(s_id)]
                        setting_obj.week_days = week_days
                        setting_obj.open_time = open_time
                        setting_obj.close_time = close_time
                        setting_obj.is_closed = is_closed
                        setting_obj.save()
                        kept_ids.append(setting_obj.id)
                    else:
                        new_setting = ServiceSettings.objects.create(
                            service=service_obj,
                            week_days=week_days,
                            open_time=open_time,
                            close_time=close_time,
                            is_closed=is_closed
                        )
                        kept_ids.append(new_setting.id)

                # Remove deleted opening hours for this service
                ServiceSettings.objects.filter(service=service_obj).exclude(id__in=kept_ids).delete()

        # 3. Update Service-Specific Settings / Configuration
        if section in ['service_settings', 'all']:
            s_type = service_obj.type
            data = request.data
            action = data.get('action')

            if action == 'delete_feature':
                feat_id = data.get('feature_id') or data.get('id')
                if feat_id:
                    sub = (data.get('sub_type') or '').lower()
                    if s_type == 'sauna':
                        if 'shared' in sub:
                            SharedSaunaFeatures.objects.filter(id=feat_id).delete()
                        else:
                            PrivateSaunaFeatures.objects.filter(id=feat_id).delete()
                    elif s_type == 'saltroom':
                        SaltroomFeatures.objects.filter(id=feat_id).delete()
                    elif s_type == 'activity':
                        ActivitiesFeature.objects.filter(id=feat_id).delete()
                    elif s_type == 'package':
                        PackageFeatures.objects.filter(id=feat_id).delete()
                    return Response({"success": True, "message": f"Feature #{feat_id} deleted successfully."})

            if s_type == 'sauna':
                ps = PrivateSauna.objects.first()
                if not ps:
                    ps = PrivateSauna.objects.create()
                if 'base_price_3hrs' in data: ps.base_price_3hrs = data['base_price_3hrs']
                if 'base_price_4hrs' in data: ps.base_price_4hrs = data['base_price_4hrs']
                if 'max_person' in data: ps.max_person = data['max_person']
                if 'extra_person_price' in data: ps.extra_person_price = data['extra_person_price']
                if 'is_available' in data: ps.is_available = str(data['is_available']).lower() in ['true', '1']
                ps.save()

                # Private Sauna Features
                priv_features = data.get('private_features') or data.get('private_sauna_features')
                if priv_features is not None:
                    if isinstance(priv_features, str):
                        import json
                        try: priv_features = json.loads(priv_features)
                        except Exception: priv_features = []
                    if isinstance(priv_features, list):
                        PrivateSaunaFeatures.objects.filter(sauna=ps).delete()
                        for f_item in priv_features:
                            if isinstance(f_item, dict):
                                f_text = f_item.get('feature_en') or f_item.get('feature') or ''
                                if f_text:
                                    feat_obj = PrivateSaunaFeatures(sauna=ps, feature=f_text, price=f_item.get('price') or 0)
                                    for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
                                        if hasattr(feat_obj, ml_f):
                                            setattr(feat_obj, ml_f, f_item.get(ml_f, f_text))
                                    feat_obj.save()

                ss = SharedSauna.objects.first()
                if not ss:
                    ss = SharedSauna.objects.create()
                if 'price_per_person' in data: ss.price_per_person = data['price_per_person']
                if 'max_person' in data: ss.max_person = data['max_person']
                if 'is_available' in data: ss.is_available = str(data['is_available']).lower() in ['true', '1']
                ss.save()

                # Shared Sauna Features
                shared_features = data.get('shared_features') or data.get('shared_sauna_features')
                if shared_features is not None:
                    if isinstance(shared_features, str):
                        import json
                        try: shared_features = json.loads(shared_features)
                        except Exception: shared_features = []
                    if isinstance(shared_features, list):
                        SharedSaunaFeatures.objects.filter(sauna=ss).delete()
                        for f_item in shared_features:
                            if isinstance(f_item, dict):
                                f_text = f_item.get('feature_en') or f_item.get('feature') or ''
                                if f_text:
                                    feat_obj = SharedSaunaFeatures(sauna=ss, feature=f_text, price=f_item.get('price') or 0)
                                    for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
                                        if hasattr(feat_obj, ml_f):
                                            setattr(feat_obj, ml_f, f_item.get(ml_f, f_text))
                                    feat_obj.save()

            elif s_type == 'saltroom':
                sr = Saltroom.objects.first()
                if not sr:
                    sr = Saltroom.objects.create(title="Salt Room")
                if 'max_capacity' in data: sr.max_capacity = data['max_capacity']
                if 'price_per_person' in data: sr.price_per_person = data['price_per_person']
                if 'duration_minutes' in data:
                    from datetime import timedelta
                    sr.duration = timedelta(minutes=int(data['duration_minutes']))
                if 'buffer_minutes' in data:
                    from datetime import timedelta
                    sr.buffer_time = timedelta(minutes=int(data['buffer_minutes']))
                if 'image' in request.FILES or 'images' in request.FILES:
                    sr.images = request.FILES.get('image') or request.FILES.get('images')
                for ml_field in ['title', 'title_en', 'title_nl', 'title_de', 'subtitle', 'subtitle_en', 'subtitle_nl', 'subtitle_de', 'description', 'description_en', 'description_nl', 'description_de']:
                    if ml_field in data and hasattr(sr, ml_field):
                        setattr(sr, ml_field, data[ml_field])
                sr.save()

                salt_features = data.get('features') or data.get('saltroom_features')
                if salt_features is not None:
                    if isinstance(salt_features, str):
                        import json
                        try: salt_features = json.loads(salt_features)
                        except Exception: salt_features = []
                    if isinstance(salt_features, list):
                        SaltroomFeatures.objects.filter(saltroom=sr).delete()
                        for f_item in salt_features:
                            if isinstance(f_item, dict):
                                f_text = f_item.get('feature_en') or f_item.get('feature') or ''
                                if f_text:
                                    feat_obj = SaltroomFeatures(saltroom=sr, feature=f_text)
                                    for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
                                        if hasattr(feat_obj, ml_f):
                                            setattr(feat_obj, ml_f, f_item.get(ml_f, f_text))
                                    feat_obj.save()

            elif s_type == 'lunchroom':
                lr = Lunchroom.objects.first()
                if not lr:
                    lr = Lunchroom.objects.create(title="Lunchroom")
                if 'image' in request.FILES or 'images' in request.FILES:
                    lr.images = request.FILES.get('image') or request.FILES.get('images')
                for ml_field in ['title', 'title_en', 'title_nl', 'title_de', 'subtitle', 'subtitle_en', 'subtitle_nl', 'subtitle_de', 'description', 'description_en', 'description_nl', 'description_de']:
                    if ml_field in data and hasattr(lr, ml_field):
                        setattr(lr, ml_field, data[ml_field])
                lr.save()

            elif s_type == 'package':
                action = data.get('action')
                pkg_id = data.get('package_id')
                
                # Delete package
                if action == 'delete':
                    if pkg_id:
                        Packages.objects.filter(id=pkg_id).delete()
                        return Response({"success": True, "message": "Package deleted successfully"})
                    return Response({"success": False, "message": "Package ID required for delete"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Create or Update package
                pkg = None
                if pkg_id and str(pkg_id).isdigit() and int(pkg_id) > 0:
                    pkg = Packages.objects.filter(id=int(pkg_id)).first()
                
                if not pkg:
                    pkg = Packages.objects.create(
                        title=data.get('title_en') or data.get('title') or "New Package",
                        description=data.get('description_en') or data.get('description') or "",
                        price=data.get('price') or 0
                    )
                
                if 'price' in data: pkg.price = data['price']
                if 'packages' in data:
                    import json
                    pkg.packages = json.loads(data['packages']) if isinstance(data['packages'], str) else data['packages']
                if 'image' in request.FILES or 'images' in request.FILES:
                    pkg.image = request.FILES.get('image') or request.FILES.get('images')
                # Multilingual fields
                for ml_field in ['title', 'title_en', 'title_nl', 'title_de', 'description', 'description_en', 'description_nl', 'description_de']:
                    if ml_field in data and hasattr(pkg, ml_field):
                        setattr(pkg, ml_field, data[ml_field])
                pkg.save()
                
                # Update features if provided
                if 'features' in data:
                    import json as _json
                    features_raw = data['features']
                    if isinstance(features_raw, str):
                        try: features_raw = _json.loads(features_raw)
                        except: features_raw = []
                    if isinstance(features_raw, list):
                        PackageFeatures.objects.filter(package=pkg).delete()
                        for feat_item in features_raw:
                            if isinstance(feat_item, dict):
                                feat_text = feat_item.get('feature_en') or feat_item.get('feature') or ''
                                if feat_text:
                                    new_feat = PackageFeatures(package=pkg, feature=feat_text)
                                    for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
                                        if hasattr(new_feat, ml_f):
                                            setattr(new_feat, ml_f, feat_item.get(ml_f, feat_text))
                                    new_feat.save()

            elif s_type == 'activity':
                action = data.get('action')
                act_id = data.get('activity_id')
                
                # Delete activity
                if action == 'delete':
                    if act_id:
                        Activities.objects.filter(id=act_id).delete()
                        return Response({"success": True, "message": "Activity deleted successfully"})
                    return Response({"success": False, "message": "Activity ID required for delete"}, status=status.HTTP_400_BAD_REQUEST)
                
                # Create or Update activity
                act = None
                if act_id and str(act_id).isdigit() and int(act_id) > 0:
                    act = Activities.objects.filter(id=int(act_id)).first()
                
                if not act:
                    act = Activities.objects.create(
                        title=data.get('title_en') or data.get('title') or "New Activity",
                        description=data.get('description_en') or data.get('description') or "",
                        price=data.get('price') or 0,
                        capacity=data.get('capacity') or 10,
                        host=data.get('host') or ""
                    )
                
                if 'capacity' in data: act.capacity = data['capacity']
                if 'price' in data: act.price = data['price']
                if 'host' in data: act.host = data['host']
                if 'open_time' in data and data['open_time']: act.open_time = data['open_time']
                if 'close_time' in data and data['close_time']: act.close_time = data['close_time']
                if 'date' in data and data['date']: act.date = data['date']
                if 'is_available' in data: act.is_available = str(data['is_available']).lower() in ['true', '1']
                if 'image' in request.FILES or 'images' in request.FILES:
                    act.images = request.FILES.get('image') or request.FILES.get('images')
                # Multilingual fields
                for ml_field in ['title', 'title_en', 'title_nl', 'title_de', 'description', 'description_en', 'description_nl', 'description_de', 'additional_notes', 'additional_notes_en', 'additional_notes_nl', 'additional_notes_de']:
                    if ml_field in data and hasattr(act, ml_field):
                        setattr(act, ml_field, data[ml_field])
                act.save()
                
                # Update features if provided
                if 'features' in data:
                    import json as _json
                    features_raw = data['features']
                    if isinstance(features_raw, str):
                        try: features_raw = _json.loads(features_raw)
                        except: features_raw = []
                    if isinstance(features_raw, list):
                        ActivitiesFeature.objects.filter(activity=act).delete()
                        for feat_item in features_raw:
                            if isinstance(feat_item, dict):
                                feat_text = feat_item.get('feature_en') or feat_item.get('feature') or ''
                                if feat_text:
                                    new_feat = ActivitiesFeature(activity=act, feature=feat_text)
                                    for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
                                        if hasattr(new_feat, ml_f):
                                            setattr(new_feat, ml_f, feat_item.get(ml_f, feat_text))
                                    new_feat.save()

        return Response({"success": True, "message": f"Updated {section} for {service_obj.title} successfully"})

    def put(self, request, service_type=None):
        return self.patch(request, service_type)

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Delete a Service by ID or Type",
    )
    def delete(self, request, service_type=None):
        service_id = request.data.get('id') or request.query_params.get('id')
        raw_type = (service_type or request.data.get('type') or request.query_params.get('type') or '').strip()

        service_obj = None
        if service_id and str(service_id).isdigit():
            service_obj = Services.objects.filter(id=int(service_id)).first()
        elif raw_type.isdigit():
            service_obj = Services.objects.filter(id=int(raw_type)).first()
        elif raw_type:
            canonical_type = TYPE_MAPPING.get(raw_type.lower(), raw_type.lower())
            service_obj = Services.objects.filter(type=canonical_type).first()
            if not service_obj:
                service_obj = Services.objects.filter(title__iexact=raw_type).first()

        if not service_obj:
            return Response({"success": False, "message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        deleted_title = service_obj.title
        deleted_id = service_obj.id
        service_obj.delete()
        return Response({
            "success": True,
            "message": f"Service '{deleted_title}' (id: {deleted_id}) deleted successfully."
        }, status=status.HTTP_200_OK)


class ServiceCRUDView(APIView):
    """
    Dedicated Admin API for full CRUD operations on Services:
    - GET: List all services or retrieve a single service with its operating hours
    - POST: Create a new service with translations, image, and optional operating hours
    - PUT / PATCH: Update an existing service by ID or type
    - DELETE: Remove a service by ID or type
    """
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=["Admin Service CRUD"],
        summary="List all services or get service details",
        parameters=[
            OpenApiParameter(name="id", description="Service ID", required=False, type=int),
            OpenApiParameter(name="type", description="Service Type (sauna, activity, saltroom, package, event, lunchroom)", required=False, type=str),
        ],
        responses={200: ServicesSerializer(many=True)},
    )
    def get(self, request, pk=None):
        service_id = pk or request.query_params.get('id')
        raw_type = (request.query_params.get('type') or '').strip()

        if service_id or raw_type:
            service_obj = None
            if service_id and str(service_id).isdigit():
                service_obj = Services.objects.filter(id=int(service_id)).first()
            elif raw_type.isdigit():
                service_obj = Services.objects.filter(id=int(raw_type)).first()
            elif raw_type:
                canonical_type = TYPE_MAPPING.get(raw_type.lower(), raw_type.lower())
                service_obj = Services.objects.filter(type=canonical_type).first()
                if not service_obj:
                    service_obj = Services.objects.filter(title__iexact=raw_type).first()

            if not service_obj:
                return Response({
                    "success": False,
                    "message": f"Service '{service_id or raw_type}' not found."
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = ServicesSerializer(service_obj, context={'request': request})
            settings_qs = ServiceSettings.objects.filter(service=service_obj)
            settings_data = [
                {
                    "id": s.id,
                    "week_days": s.week_days or [],
                    "open_time": s.open_time.strftime("%H:%M") if s.open_time else "09:00",
                    "close_time": s.close_time.strftime("%H:%M") if s.close_time else "21:00",
                    "is_closed": s.is_closed,
                }
                for s in settings_qs
            ]
            return Response({
                "success": True,
                "data": serializer.data,
                "settings": settings_data,
            }, status=status.HTTP_200_OK)

        all_services = Services.objects.all().order_by('id')
        serializer = ServicesSerializer(all_services, many=True, context={'request': request})
        return Response({
            "success": True,
            "count": all_services.count(),
            "data": serializer.data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Service CRUD"],
        summary="Create a new Service",
        description="Creates a new service with multi-language fields, image, and optional operating hours.",
        request=ServicesSerializer,
        responses={201: ServicesSerializer},
    )
    def post(self, request):
        data = request.data
        service_type = data.get('type')
        if not service_type:
            return Response({
                "success": False,
                "message": "Field 'type' is required (e.g. sauna, activity, saltroom, package, event, lunchroom)."
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_types = [t[0] for t in Services.SERVICE_TYPES]
        canonical_type = TYPE_MAPPING.get(str(service_type).lower(), str(service_type).lower())
        if canonical_type not in valid_types:
            return Response({
                "success": False,
                "message": f"Invalid service type '{service_type}'. Allowed types: {', '.join(valid_types)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        title = data.get('title') or data.get('title_en') or f"{canonical_type.title()} Service"
        subtitle = data.get('subtitle') or data.get('subtitle_en') or ""
        description = data.get('description') or data.get('description_en') or ""

        service_obj = Services.objects.create(
            type=canonical_type,
            title=title,
            subtitle=subtitle,
            description=description,
        )

        # Multilingual fields
        for f in ['title', 'subtitle', 'description']:
            for lang in ['en', 'nl', 'de']:
                key = f"{f}_{lang}"
                if key in data:
                    setattr(service_obj, key, data[key])
                elif not getattr(service_obj, key, None):
                    setattr(service_obj, key, getattr(service_obj, f, ''))

        if 'image' in request.FILES:
            service_obj.image = request.FILES['image']
        service_obj.save()

        # Handle optional settings/opening_hours
        settings_list = data.get('settings') or data.get('opening_hours')
        if settings_list:
            if isinstance(settings_list, str):
                import json
                try:
                    settings_list = json.loads(settings_list)
                except Exception:
                    settings_list = []
            if isinstance(settings_list, list):
                for item in settings_list:
                    ServiceSettings.objects.create(
                        service=service_obj,
                        week_days=item.get('week_days') or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                        open_time=item.get('open_time') or '09:00:00',
                        close_time=item.get('close_time') or '21:00:00',
                        is_closed=bool(item.get('is_closed', False))
                    )
        else:
            # Default 7-day schedule
            ServiceSettings.objects.create(
                service=service_obj,
                week_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                open_time='09:00:00',
                close_time='21:00:00',
                is_closed=False
            )

        serializer = ServicesSerializer(service_obj, context={'request': request})
        settings_qs = ServiceSettings.objects.filter(service=service_obj)
        settings_data = [
            {
                "id": s.id,
                "week_days": s.week_days or [],
                "open_time": s.open_time.strftime("%H:%M") if s.open_time else "09:00",
                "close_time": s.close_time.strftime("%H:%M") if s.close_time else "21:00",
                "is_closed": s.is_closed,
            }
            for s in settings_qs
        ]
        return Response({
            "success": True,
            "message": f"Service '{service_obj.title}' created successfully.",
            "data": serializer.data,
            "settings": settings_data,
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Admin Service CRUD"],
        summary="Update an existing Service",
        description="Updates an existing service by ID or type with multi-language fields, image, and settings.",
        request=ServicesSerializer,
        responses={200: ServicesSerializer},
    )
    def patch(self, request, pk=None):
        service_id = pk or request.data.get('id') or request.query_params.get('id')
        raw_type = (request.data.get('type') or request.query_params.get('type') or '').strip()

        service_obj = None
        if service_id and str(service_id).isdigit():
            service_obj = Services.objects.filter(id=int(service_id)).first()
        elif raw_type.isdigit():
            service_obj = Services.objects.filter(id=int(raw_type)).first()
        elif raw_type:
            canonical_type = TYPE_MAPPING.get(raw_type.lower(), raw_type.lower())
            service_obj = Services.objects.filter(type=canonical_type).first()
            if not service_obj:
                service_obj = Services.objects.filter(title__iexact=raw_type).first()

        if not service_obj:
            return Response({
                "success": False,
                "message": f"Service '{service_id or raw_type}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'type' in data:
            new_type = TYPE_MAPPING.get(str(data['type']).lower(), str(data['type']).lower())
            valid_types = [t[0] for t in Services.SERVICE_TYPES]
            if new_type in valid_types:
                service_obj.type = new_type

        for f in [
            'title', 'title_en', 'title_nl', 'title_de',
            'subtitle', 'subtitle_en', 'subtitle_nl', 'subtitle_de',
            'description', 'description_en', 'description_nl', 'description_de'
        ]:
            if f in data:
                setattr(service_obj, f, data[f])

        if 'image' in request.FILES:
            service_obj.image = request.FILES['image']
        service_obj.save()

        # Update settings if provided
        settings_list = data.get('settings') or data.get('opening_hours')
        if settings_list is not None:
            if isinstance(settings_list, str):
                import json
                try:
                    settings_list = json.loads(settings_list)
                except Exception:
                    settings_list = []
            if isinstance(settings_list, list):
                ServiceSettings.objects.filter(service=service_obj).delete()
                for item in settings_list:
                    ServiceSettings.objects.create(
                        service=service_obj,
                        week_days=item.get('week_days') or [],
                        open_time=item.get('open_time') or '09:00:00',
                        close_time=item.get('close_time') or '21:00:00',
                        is_closed=bool(item.get('is_closed', False))
                    )

        serializer = ServicesSerializer(service_obj, context={'request': request})
        settings_qs = ServiceSettings.objects.filter(service=service_obj)
        settings_data = [
            {
                "id": s.id,
                "week_days": s.week_days or [],
                "open_time": s.open_time.strftime("%H:%M") if s.open_time else "09:00",
                "close_time": s.close_time.strftime("%H:%M") if s.close_time else "21:00",
                "is_closed": s.is_closed,
            }
            for s in settings_qs
        ]
        return Response({
            "success": True,
            "message": f"Service '{service_obj.title}' updated successfully.",
            "data": serializer.data,
            "settings": settings_data,
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.patch(request, pk)

    @extend_schema(
        tags=["Admin Service CRUD"],
        summary="Delete a Service",
        description="Deletes a service by id or type.",
        parameters=[
            OpenApiParameter(name="id", description="Service ID to delete", required=False, type=int),
            OpenApiParameter(name="type", description="Service Type to delete", required=False, type=str),
        ],
    )
    def delete(self, request, pk=None):
        service_id = pk or request.data.get('id') or request.query_params.get('id')
        raw_type = (request.data.get('type') or request.query_params.get('type') or '').strip()

        service_obj = None
        if service_id and str(service_id).isdigit():
            service_obj = Services.objects.filter(id=int(service_id)).first()
        elif raw_type.isdigit():
            service_obj = Services.objects.filter(id=int(raw_type)).first()
        elif raw_type:
            canonical_type = TYPE_MAPPING.get(raw_type.lower(), raw_type.lower())
            service_obj = Services.objects.filter(type=canonical_type).first()
            if not service_obj:
                service_obj = Services.objects.filter(title__iexact=raw_type).first()

        if not service_obj:
            return Response({
                "success": False,
                "message": f"Service '{service_id or raw_type}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_id = service_obj.id
        deleted_title = service_obj.title
        deleted_type = service_obj.type
        service_obj.delete()

        return Response({
            "success": True,
            "message": f"Service '{deleted_title}' (type: {deleted_type}, id: {deleted_id}) deleted successfully."
        }, status=status.HTTP_200_OK)


def format_time_safe(t_val, default="09:00"):
    if not t_val:
        return default
    if hasattr(t_val, 'strftime'):
        return t_val.strftime("%H:%M")
    s = str(t_val).strip()
    return s[:5] if len(s) >= 5 else s


class ServiceOpeningHoursView(APIView):
    """
    Dedicated Admin API for Opening Hours / Service Settings:
    - GET: List all operating hours or filter by service_id / service_type
    - POST: Create a new operating hour setting for a service
    - PATCH / PUT: Update an existing operating hour setting
    - DELETE: Delete an operating hour setting
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Service Operating Hours"],
        summary="List operating hours / settings",
        parameters=[
            OpenApiParameter(name="service_id", description="Service ID", required=False, type=int),
            OpenApiParameter(name="service_type", description="Service Type (e.g. sauna, saltroom)", required=False, type=str),
            OpenApiParameter(name="id", description="Setting ID", required=False, type=int),
        ],
    )
    def get(self, request, setting_id=None):
        s_id = setting_id or request.query_params.get('id')
        if s_id:
            setting = ServiceSettings.objects.filter(id=s_id).first()
            if not setting:
                return Response({"success": False, "message": "Setting not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "success": True,
                "data": {
                    "id": setting.id,
                    "service_id": setting.service.id if setting.service else None,
                    "service_type": setting.service.type if setting.service else None,
                    "service_title": setting.service.title if setting.service else "Global Default",
                    "week_days": setting.week_days or [],
                    "open_time": format_time_safe(setting.open_time, "09:00"),
                    "close_time": format_time_safe(setting.close_time, "21:00"),
                    "is_closed": setting.is_closed,
                }
            })

        qs = ServiceSettings.objects.all().select_related('service').order_by('id')
        service_id = request.query_params.get('service_id')
        service_type = request.query_params.get('service_type')

        if service_id and str(service_id).isdigit():
            qs = qs.filter(service_id=int(service_id))
        elif service_type:
            canonical = TYPE_MAPPING.get(service_type.lower(), service_type.lower())
            qs = qs.filter(service__type=canonical)

        data = [
            {
                "id": s.id,
                "service_id": s.service.id if s.service else None,
                "service_type": s.service.type if s.service else None,
                "service_title": s.service.title if s.service else "Global Default",
                "week_days": s.week_days or [],
                "open_time": format_time_safe(s.open_time, "09:00"),
                "close_time": format_time_safe(s.close_time, "21:00"),
                "is_closed": s.is_closed,
            }
            for s in qs
        ]
        return Response({"success": True, "count": len(data), "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Service Operating Hours"],
        summary="Create operating hours for a service",
    )
    def post(self, request):
        data = request.data
        service_id = data.get('service_id')
        service_type = data.get('service_type') or data.get('type')

        service_obj = None
        if service_id and str(service_id).isdigit():
            service_obj = Services.objects.filter(id=int(service_id)).first()
        elif service_type:
            service_obj = get_or_create_service_with_demo(raw_type=service_type)

        week_days = data.get('week_days') or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        if isinstance(week_days, str):
            import json
            try:
                week_days = json.loads(week_days)
            except Exception:
                week_days = [d.strip() for d in week_days.split(',') if d.strip()]

        open_time = data.get('open_time') or '09:00:00'
        close_time = data.get('close_time') or '21:00:00'
        is_closed = bool(data.get('is_closed', False))

        setting = ServiceSettings.objects.create(
            service=service_obj,
            week_days=week_days,
            open_time=open_time,
            close_time=close_time,
            is_closed=is_closed
        )

        return Response({
            "success": True,
            "message": "Operating hours created successfully.",
            "data": {
                "id": setting.id,
                "service_id": setting.service.id if setting.service else None,
                "service_type": setting.service.type if setting.service else None,
                "service_title": setting.service.title if setting.service else "Global Default",
                "week_days": setting.week_days or [],
                "open_time": format_time_safe(setting.open_time, "09:00"),
                "close_time": format_time_safe(setting.close_time, "21:00"),
                "is_closed": setting.is_closed,
            }
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Admin Service Operating Hours"],
        summary="Update operating hours",
    )
    def patch(self, request, setting_id=None):
        s_id = setting_id or request.data.get('id') or request.query_params.get('id')
        if not s_id:
            return Response({"success": False, "message": "Setting id is required."}, status=status.HTTP_400_BAD_REQUEST)

        setting = ServiceSettings.objects.filter(id=s_id).first()
        if not setting:
            return Response({"success": False, "message": "Setting not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'week_days' in data:
            wd = data['week_days']
            if isinstance(wd, str):
                import json
                try:
                    wd = json.loads(wd)
                except Exception:
                    wd = [d.strip() for d in wd.split(',') if d.strip()]
            setting.week_days = wd
        if 'open_time' in data:
            setting.open_time = data['open_time']
        if 'close_time' in data:
            setting.close_time = data['close_time']
        if 'is_closed' in data:
            setting.is_closed = bool(data['is_closed'])
        if 'service_id' in data and str(data['service_id']).isdigit():
            svc = Services.objects.filter(id=int(data['service_id'])).first()
            if svc:
                setting.service = svc

        setting.save()

        return Response({
            "success": True,
            "message": "Operating hours updated successfully.",
            "data": {
                "id": setting.id,
                "service_id": setting.service.id if setting.service else None,
                "service_type": setting.service.type if setting.service else None,
                "service_title": setting.service.title if setting.service else "Global Default",
                "week_days": setting.week_days or [],
                "open_time": format_time_safe(setting.open_time, "09:00"),
                "close_time": format_time_safe(setting.close_time, "21:00"),
                "is_closed": setting.is_closed,
            }
        }, status=status.HTTP_200_OK)

    def put(self, request, setting_id=None):
        return self.patch(request, setting_id)

    @extend_schema(
        tags=["Admin Service Operating Hours"],
        summary="Delete operating hours",
    )
    def delete(self, request, setting_id=None):
        s_id = setting_id or request.data.get('id') or request.query_params.get('id')
        if not s_id:
            return Response({"success": False, "message": "Setting id is required."}, status=status.HTTP_400_BAD_REQUEST)

        setting = ServiceSettings.objects.filter(id=s_id).first()
        if not setting:
            return Response({"success": False, "message": "Setting not found."}, status=status.HTTP_404_NOT_FOUND)

        setting.delete()
        return Response({"success": True, "message": f"Operating hours setting #{s_id} deleted successfully."}, status=status.HTTP_200_OK)


class ServiceFeatureManageView(APIView):
    """
    Dedicated Admin API to manage Service Features:
    Supports: Private Sauna Features, Shared Sauna Features, Activities Features, Saltroom Features, Package Features.
    - GET: List features by service_type (and optional sub_type) or retrieve a feature by feature_id
    - POST: Create a new feature with translations and optional price
    - PATCH / PUT: Update an existing feature by feature_id
    - DELETE: Delete a feature by feature_id
    """
    permission_classes = [AllowAny]

    def _resolve_model(self, service_type, sub_type=''):
        st = (service_type or '').lower().strip()
        sub = (sub_type or '').lower().strip()
        if st == 'sauna':
            if 'shared' in sub:
                return SharedSaunaFeatures, SharedSauna, 'sauna', 'shared', True
            return PrivateSaunaFeatures, PrivateSauna, 'sauna', 'private', True
        elif st in ['private_sauna', 'private-sauna']:
            return PrivateSaunaFeatures, PrivateSauna, 'sauna', 'private', True
        elif st in ['shared_sauna', 'shared-sauna']:
            return SharedSaunaFeatures, SharedSauna, 'sauna', 'shared', True
        elif st in ['saltroom', 'saltrooms']:
            return SaltroomFeatures, Saltroom, 'saltroom', None, False
        elif st in ['activity', 'activities']:
            return ActivitiesFeature, Activities, 'activity', None, False
        elif st in ['package', 'packages']:
            return PackageFeatures, Packages, 'package', None, False
        return None, None, None, None, False

    def _find_feature_anywhere(self, feature_id, service_type=None, sub_type=None):
        if service_type:
            feat_model, parent_model, svc_t, sub_t, has_price = self._resolve_model(service_type, sub_type)
            if feat_model:
                feat = feat_model.objects.filter(id=feature_id).first()
                if feat:
                    return feat, feat_model, svc_t, sub_t, has_price

        models_to_check = [
            (PrivateSaunaFeatures, 'sauna', 'private', True),
            (SharedSaunaFeatures, 'sauna', 'shared', True),
            (SaltroomFeatures, 'saltroom', None, False),
            (ActivitiesFeature, 'activity', None, False),
            (PackageFeatures, 'package', None, False),
        ]
        for f_model, svc_t, sub_t, has_price in models_to_check:
            feat = f_model.objects.filter(id=feature_id).first()
            if feat:
                return feat, f_model, svc_t, sub_t, has_price
        return None, None, None, None, False

    @extend_schema(
        tags=["Admin Service Features"],
        summary="List or retrieve service features",
        parameters=[
            OpenApiParameter(name="service_type", description="Service type (sauna, saltroom, activity, package)", required=False, type=str),
            OpenApiParameter(name="sub_type", description="Sub-type for sauna: 'private' or 'shared'", required=False, type=str),
            OpenApiParameter(name="feature_id", description="Feature ID", required=False, type=int),
        ],
    )
    def get(self, request, feature_id=None):
        f_id = feature_id or request.query_params.get('feature_id') or request.query_params.get('id')
        service_type = request.query_params.get('service_type')
        sub_type = request.query_params.get('sub_type') or ''

        if f_id:
            feat, feat_model, svc_t, sub_t, has_price = self._find_feature_anywhere(int(f_id), service_type, sub_type)
            if not feat:
                return Response({"success": False, "message": f"Feature #{f_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "success": True,
                "data": {
                    "id": feat.id,
                    "service_type": svc_t,
                    "sub_type": sub_t,
                    "feature": feat.feature,
                    "feature_en": getattr(feat, 'feature_en', feat.feature),
                    "feature_nl": getattr(feat, 'feature_nl', feat.feature),
                    "feature_de": getattr(feat, 'feature_de', feat.feature),
                    "price": str(feat.price) if has_price else "0",
                }
            })

        if not service_type:
            all_data = {
                "private_sauna": [
                    {"id": f.id, "feature": f.feature, "feature_en": getattr(f, 'feature_en', f.feature), "feature_nl": getattr(f, 'feature_nl', f.feature), "feature_de": getattr(f, 'feature_de', f.feature), "price": str(f.price)}
                    for f in PrivateSaunaFeatures.objects.all()
                ],
                "shared_sauna": [
                    {"id": f.id, "feature": f.feature, "feature_en": getattr(f, 'feature_en', f.feature), "feature_nl": getattr(f, 'feature_nl', f.feature), "feature_de": getattr(f, 'feature_de', f.feature), "price": str(f.price)}
                    for f in SharedSaunaFeatures.objects.all()
                ],
                "saltroom": [
                    {"id": f.id, "feature": f.feature, "feature_en": getattr(f, 'feature_en', f.feature), "feature_nl": getattr(f, 'feature_nl', f.feature), "feature_de": getattr(f, 'feature_de', f.feature)}
                    for f in SaltroomFeatures.objects.all()
                ],
                "activities": [
                    {"id": f.id, "activity_id": f.activity_id, "feature": f.feature, "feature_en": getattr(f, 'feature_en', f.feature), "feature_nl": getattr(f, 'feature_nl', f.feature), "feature_de": getattr(f, 'feature_de', f.feature)}
                    for f in ActivitiesFeature.objects.all()
                ],
                "packages": [
                    {"id": f.id, "package_id": f.package_id, "feature": f.feature, "feature_en": getattr(f, 'feature_en', f.feature), "feature_nl": getattr(f, 'feature_nl', f.feature), "feature_de": getattr(f, 'feature_de', f.feature)}
                    for f in PackageFeatures.objects.all()
                ],
            }
            return Response({"success": True, "data": all_data})

        feat_model, parent_model, svc_t, sub_t, has_price = self._resolve_model(service_type, sub_type)
        if not feat_model:
            return Response({"success": False, "message": f"Unsupported service type '{service_type}'."}, status=status.HTTP_400_BAD_REQUEST)

        feats = feat_model.objects.all()
        list_data = [
            {
                "id": f.id,
                "service_type": svc_t,
                "sub_type": sub_t,
                "feature": f.feature,
                "feature_en": getattr(f, 'feature_en', f.feature),
                "feature_nl": getattr(f, 'feature_nl', f.feature),
                "feature_de": getattr(f, 'feature_de', f.feature),
                "price": str(f.price) if has_price else "0",
            }
            for f in feats
        ]
        return Response({"success": True, "count": len(list_data), "data": list_data})

    @extend_schema(
        tags=["Admin Service Features"],
        summary="Create a new service feature",
    )
    def post(self, request):
        data = request.data
        service_type = data.get('service_type') or data.get('type')
        sub_type = data.get('sub_type') or ''
        feature_text = data.get('feature_en') or data.get('feature')

        if not service_type or not feature_text:
            return Response({
                "success": False,
                "message": "Both 'service_type' and 'feature' (or 'feature_en') are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        feat_model, parent_model, svc_t, sub_t, has_price = self._resolve_model(service_type, sub_type)
        if not feat_model:
            return Response({"success": False, "message": f"Unsupported service type '{service_type}'."}, status=status.HTTP_400_BAD_REQUEST)

        parent_id = data.get('parent_id') or data.get('sauna_id') or data.get('activity_id') or data.get('package_id') or data.get('saltroom_id')
        parent_instance = None
        if parent_id and str(parent_id).isdigit():
            parent_instance = parent_model.objects.filter(id=int(parent_id)).first()

        if not parent_instance:
            parent_instance = parent_model.objects.first()
            if not parent_instance:
                if parent_model == PrivateSauna:
                    parent_instance = PrivateSauna.objects.create()
                elif parent_model == SharedSauna:
                    parent_instance = SharedSauna.objects.create()
                elif parent_model == Saltroom:
                    parent_instance = Saltroom.objects.create(title="Salt Room")
                elif parent_model == Activities:
                    parent_instance = Activities.objects.create(title="Activity Session")
                elif parent_model == Packages:
                    parent_instance = Packages.objects.create(title="Package")

        fk_field = 'sauna'
        if svc_t == 'saltroom': fk_field = 'saltroom'
        elif svc_t == 'activity': fk_field = 'activity'
        elif svc_t == 'package': fk_field = 'package'

        create_kwargs = {
            fk_field: parent_instance,
            'feature': feature_text,
        }
        if has_price:
            create_kwargs['price'] = data.get('price') or 0

        feat_obj = feat_model.objects.create(**create_kwargs)

        for lang in ['en', 'nl', 'de']:
            val = data.get(f"feature_{lang}")
            if val and hasattr(feat_obj, f"feature_{lang}"):
                setattr(feat_obj, f"feature_{lang}", val)
            elif not getattr(feat_obj, f"feature_{lang}", None) and hasattr(feat_obj, f"feature_{lang}"):
                setattr(feat_obj, f"feature_{lang}", feature_text)
        feat_obj.save()

        return Response({
            "success": True,
            "message": f"Feature '{feat_obj.feature}' created successfully.",
            "data": {
                "id": feat_obj.id,
                "service_type": svc_t,
                "sub_type": sub_t,
                "feature": feat_obj.feature,
                "feature_en": getattr(feat_obj, 'feature_en', feat_obj.feature),
                "feature_nl": getattr(feat_obj, 'feature_nl', feat_obj.feature),
                "feature_de": getattr(feat_obj, 'feature_de', feat_obj.feature),
                "price": str(feat_obj.price) if has_price else "0",
            }
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Admin Service Features"],
        summary="Update a service feature",
    )
    def patch(self, request, feature_id=None):
        f_id = feature_id or request.data.get('id') or request.data.get('feature_id') or request.query_params.get('id')
        if not f_id:
            return Response({"success": False, "message": "Feature id is required."}, status=status.HTTP_400_BAD_REQUEST)

        service_type = request.data.get('service_type') or request.query_params.get('service_type')
        sub_type = request.data.get('sub_type') or request.query_params.get('sub_type') or ''

        feat, feat_model, svc_t, sub_t, has_price = self._find_feature_anywhere(int(f_id), service_type, sub_type)
        if not feat:
            return Response({"success": False, "message": f"Feature #{f_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'feature' in data:
            feat.feature = data['feature']
        if 'price' in data and has_price:
            feat.price = data['price']

        for ml_f in ['feature_en', 'feature_nl', 'feature_de']:
            if ml_f in data and hasattr(feat, ml_f):
                setattr(feat, ml_f, data[ml_f])

        feat.save()

        return Response({
            "success": True,
            "message": f"Feature '{feat.feature}' updated successfully.",
            "data": {
                "id": feat.id,
                "service_type": svc_t,
                "sub_type": sub_t,
                "feature": feat.feature,
                "feature_en": getattr(feat, 'feature_en', feat.feature),
                "feature_nl": getattr(feat, 'feature_nl', feat.feature),
                "feature_de": getattr(feat, 'feature_de', feat.feature),
                "price": str(feat.price) if has_price else "0",
            }
        }, status=status.HTTP_200_OK)

    def put(self, request, feature_id=None):
        return self.patch(request, feature_id)

    @extend_schema(
        tags=["Admin Service Features"],
        summary="Delete a service feature",
    )
    def delete(self, request, feature_id=None):
        f_id = feature_id or request.data.get('id') or request.data.get('feature_id') or request.query_params.get('id')
        if not f_id:
            return Response({"success": False, "message": "Feature id is required."}, status=status.HTTP_400_BAD_REQUEST)

        service_type = request.data.get('service_type') or request.query_params.get('service_type')
        sub_type = request.data.get('sub_type') or request.query_params.get('sub_type') or ''

        feat, feat_model, svc_t, sub_t, has_price = self._find_feature_anywhere(int(f_id), service_type, sub_type)
        if not feat:
            return Response({"success": False, "message": f"Feature #{f_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        deleted_text = feat.feature
        feat.delete()
        return Response({
            "success": True,
            "message": f"Feature '{deleted_text}' (#{f_id}) deleted successfully."
        }, status=status.HTTP_200_OK)


def parse_date_safe(date_str):
    """
    Safely parses a date string in YYYY-MM-DD format or 'today' into a datetime.date object.
    """
    if not date_str:
        return None
    s = str(date_str).strip()
    if s.lower() == 'today':
        return timezone.now().date()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def parse_time_safe(time_str):
    """
    Parses a time string in HH:MM or HH:MM:SS format to datetime.time.
    """
    if not time_str:
        return None
    s = str(time_str).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None


def serialize_block_date(bd):
    """
    Serializes a BlockDate model instance with all database fields.
    """
    return {
        "id": bd.id,
        "date": bd.date.strftime("%Y-%m-%d") if bd.date else "",
        "description": bd.description or "",
        "created_at": bd.created_at.isoformat() if bd.created_at else None,
        "updated_at": bd.updated_at.isoformat() if bd.updated_at else None,
    }


def serialize_special_opening_date(so):
    """
    Serializes a SpecialOpeningDate model instance with all database fields.
    """
    return {
        "id": so.id,
        "date": so.date.strftime("%Y-%m-%d") if so.date else "",
        "open_time": so.open_time.strftime("%H:%M") if so.open_time else "",
        "close_time": so.close_time.strftime("%H:%M") if so.close_time else "",
        "description": so.description or "",
        "created_at": so.created_at.isoformat() if so.created_at else None,
        "updated_at": so.updated_at.isoformat() if so.updated_at else None,
    }


class AdminDatesOverviewView(APIView):
    """
    Admin Schedule Dates Overview API:
    Returns both Blocked Dates and Special Opening Dates in a single unified response,
    along with summary metrics and flexible date/month/year/search filtering.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Get all blocked dates and special opening dates",
        description="Returns two sections: 'blocked_dates' and 'special_opening_dates' with all database fields and summary stats.",
        parameters=[
            OpenApiParameter(name="year", description="Filter by year (e.g. 2026)", required=False, type=int),
            OpenApiParameter(name="month", description="Filter by month (1 - 12)", required=False, type=int),
            OpenApiParameter(name="start_date", description="Filter from date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter to date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="upcoming", description="Set to 'true' to only view dates from today onwards", required=False, type=bool),
            OpenApiParameter(name="search", description="Search keyword in descriptions", required=False, type=str),
        ],
        responses={200: AdminDatesOverviewResponseSerializer},
    )
    def get(self, request):
        today = timezone.now().date()

        # Query parameters
        year_param = request.query_params.get('year')
        month_param = request.query_params.get('month')
        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))
        upcoming = request.query_params.get('upcoming', '').strip().lower() in ['true', '1', 'yes']
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()

        # Base QuerySets
        block_qs = BlockDate.objects.all()
        special_qs = SpecialOpeningDate.objects.all()

        # Global stats before filters
        total_blocked_all = block_qs.count()
        total_special_all = special_qs.count()
        upcoming_blocked_count = block_qs.filter(date__gte=today).count()
        upcoming_special_count = special_qs.filter(date__gte=today).count()

        # Apply date filters
        if upcoming:
            block_qs = block_qs.filter(date__gte=today)
            special_qs = special_qs.filter(date__gte=today)

        if year_param and str(year_param).isdigit():
            block_qs = block_qs.filter(date__year=int(year_param))
            special_qs = special_qs.filter(date__year=int(year_param))

        if month_param and str(month_param).isdigit():
            block_qs = block_qs.filter(date__month=int(month_param))
            special_qs = special_qs.filter(date__month=int(month_param))

        if start_date:
            block_qs = block_qs.filter(date__gte=start_date)
            special_qs = special_qs.filter(date__gte=start_date)

        if end_date:
            block_qs = block_qs.filter(date__lte=end_date)
            special_qs = special_qs.filter(date__lte=end_date)

        if search:
            block_qs = block_qs.filter(description__icontains=search)
            special_qs = special_qs.filter(description__icontains=search)

        block_list = [serialize_block_date(bd) for bd in block_qs.order_by('date')]
        special_list = [serialize_special_opening_date(so) for so in special_qs.order_by('date')]

        return Response({
            "success": True,
            "summary": {
                "total_blocked_dates": total_blocked_all,
                "total_special_opening_dates": total_special_all,
                "upcoming_blocked_dates": upcoming_blocked_count,
                "upcoming_special_opening_dates": upcoming_special_count,
            },
            "blocked_dates": block_list,
            "special_opening_dates": special_list,
        }, status=status.HTTP_200_OK)


class AdminBlockDateView(APIView):
    """
    Admin Block Date Management API:
    - GET: List all blocked dates (with search/filters) or retrieve single entry by pk/id
    - POST: Add a new blocked date
    - PATCH / PUT: Update an existing blocked date
    - DELETE: Delete a blocked date
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="List blocked dates or get single blocked date",
        parameters=[
            OpenApiParameter(name="id", description="Blocked Date ID (to retrieve single)", required=False, type=int),
            OpenApiParameter(name="search", description="Search description keyword", required=False, type=str),
            OpenApiParameter(name="date", description="Filter exact date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="upcoming", description="Filter upcoming dates only", required=False, type=bool),
        ],
        responses={200: BlockDateItemSerializer(many=True)},
    )
    def get(self, request, pk=None):
        target_id = pk or request.query_params.get('id')
        if target_id and str(target_id).isdigit():
            bd = BlockDate.objects.filter(id=int(target_id)).first()
            if not bd:
                return Response({
                    "success": False,
                    "message": f"Blocked date with ID {target_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "success": True,
                "data": serialize_block_date(bd)
            }, status=status.HTTP_200_OK)

        qs = BlockDate.objects.all()

        date_param = parse_date_safe(request.query_params.get('date'))
        if date_param:
            qs = qs.filter(date=date_param)

        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        if start_date:
            qs = qs.filter(date__gte=start_date)

        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))
        if end_date:
            qs = qs.filter(date__lte=end_date)

        if request.query_params.get('upcoming', '').strip().lower() in ['true', '1', 'yes']:
            qs = qs.filter(date__gte=timezone.now().date())

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(description__icontains=search)

        qs = qs.order_by('date')
        data = [serialize_block_date(b) for b in qs]

        return Response({
            "success": True,
            "count": len(data),
            "data": data,
            "blocked_dates": data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Add a new blocked date",
        request=BlockDateCreateUpdateSerializer,
        responses={201: AdminDateActionResponseSerializer},
    )
    def post(self, request):
        data = request.data
        raw_date = data.get('date')
        description = (data.get('description') or '').strip()

        target_date = parse_date_safe(raw_date)
        if not target_date:
            return Response({
                "success": False,
                "message": "Valid date in YYYY-MM-DD format is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not description:
            return Response({
                "success": False,
                "message": "Field 'description' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for duplicate
        existing = BlockDate.objects.filter(date=target_date).first()
        if existing:
            return Response({
                "success": False,
                "message": f"Date {target_date.strftime('%Y-%m-%d')} is already blocked (ID: {existing.id})."
            }, status=status.HTTP_400_BAD_REQUEST)

        bd = BlockDate.objects.create(
            date=target_date,
            description=description
        )

        return Response({
            "success": True,
            "message": f"Date {target_date.strftime('%Y-%m-%d')} blocked successfully.",
            "data": serialize_block_date(bd)
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Update a blocked date",
        request=BlockDateCreateUpdateSerializer,
        responses={200: AdminDateActionResponseSerializer},
    )
    def patch(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Blocked date ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        bd = BlockDate.objects.filter(id=int(target_id)).first()
        if not bd:
            return Response({
                "success": False,
                "message": f"Blocked date with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'date' in data:
            new_date = parse_date_safe(data['date'])
            if not new_date:
                return Response({
                    "success": False,
                    "message": "Invalid date format. Expected YYYY-MM-DD."
                }, status=status.HTTP_400_BAD_REQUEST)

            duplicate = BlockDate.objects.filter(date=new_date).exclude(id=bd.id).first()
            if duplicate:
                return Response({
                    "success": False,
                    "message": f"Another blocked date already exists for {new_date.strftime('%Y-%m-%d')}."
                }, status=status.HTTP_400_BAD_REQUEST)
            bd.date = new_date

        if 'description' in data:
            desc = str(data['description']).strip()
            if not desc:
                return Response({
                    "success": False,
                    "message": "Description cannot be empty."
                }, status=status.HTTP_400_BAD_REQUEST)
            bd.description = desc

        bd.save()

        return Response({
            "success": True,
            "message": f"Blocked date for {bd.date.strftime('%Y-%m-%d')} updated successfully.",
            "data": serialize_block_date(bd)
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.patch(request, pk)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Delete a blocked date",
        parameters=[
            OpenApiParameter(name="id", description="Blocked Date ID to delete", required=False, type=int),
        ],
        responses={200: AdminDateActionResponseSerializer},
    )
    def delete(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Blocked date ID is required to delete."
            }, status=status.HTTP_400_BAD_REQUEST)

        bd = BlockDate.objects.filter(id=int(target_id)).first()
        if not bd:
            return Response({
                "success": False,
                "message": f"Blocked date with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_id = bd.id
        deleted_date = bd.date.strftime("%Y-%m-%d") if bd.date else ""
        bd.delete()

        return Response({
            "success": True,
            "message": f"Blocked date for {deleted_date} (ID: {deleted_id}) deleted successfully."
        }, status=status.HTTP_200_OK)


class AdminSpecialOpeningDateView(APIView):
    """
    Admin Special Opening Date Management API:
    - GET: List all special opening dates (with search/filters) or retrieve single entry by pk/id
    - POST: Add a new special opening date with custom opening & closing hours
    - PATCH / PUT: Update an existing special opening date
    - DELETE: Delete a special opening date
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="List special opening dates or get single special opening date",
        parameters=[
            OpenApiParameter(name="id", description="Special Opening Date ID (to retrieve single)", required=False, type=int),
            OpenApiParameter(name="search", description="Search description keyword", required=False, type=str),
            OpenApiParameter(name="date", description="Filter exact date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="upcoming", description="Filter upcoming dates only", required=False, type=bool),
        ],
        responses={200: SpecialOpeningDateItemSerializer(many=True)},
    )
    def get(self, request, pk=None):
        target_id = pk or request.query_params.get('id')
        if target_id and str(target_id).isdigit():
            so = SpecialOpeningDate.objects.filter(id=int(target_id)).first()
            if not so:
                return Response({
                    "success": False,
                    "message": f"Special opening date with ID {target_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)
            return Response({
                "success": True,
                "data": serialize_special_opening_date(so)
            }, status=status.HTTP_200_OK)

        qs = SpecialOpeningDate.objects.all()

        date_param = parse_date_safe(request.query_params.get('date'))
        if date_param:
            qs = qs.filter(date=date_param)

        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        if start_date:
            qs = qs.filter(date__gte=start_date)

        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))
        if end_date:
            qs = qs.filter(date__lte=end_date)

        if request.query_params.get('upcoming', '').strip().lower() in ['true', '1', 'yes']:
            qs = qs.filter(date__gte=timezone.now().date())

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(description__icontains=search)

        qs = qs.order_by('date')
        data = [serialize_special_opening_date(s) for s in qs]

        return Response({
            "success": True,
            "count": len(data),
            "data": data,
            "special_opening_dates": data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Add a new special opening date",
        request=SpecialOpeningDateCreateUpdateSerializer,
        responses={201: AdminDateActionResponseSerializer},
    )
    def post(self, request):
        data = request.data
        raw_date = data.get('date')
        open_time_val = data.get('open_time')
        close_time_val = data.get('close_time')
        description = (data.get('description') or '').strip()

        target_date = parse_date_safe(raw_date)
        if not target_date:
            return Response({
                "success": False,
                "message": "Valid date in YYYY-MM-DD format is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        open_t = parse_time_safe(open_time_val)
        if not open_t:
            return Response({
                "success": False,
                "message": "Valid open_time in HH:MM format is required (e.g. '10:00')."
            }, status=status.HTTP_400_BAD_REQUEST)

        close_t = parse_time_safe(close_time_val)
        if not close_t:
            return Response({
                "success": False,
                "message": "Valid close_time in HH:MM format is required (e.g. '16:00')."
            }, status=status.HTTP_400_BAD_REQUEST)

        if open_t >= close_t:
            return Response({
                "success": False,
                "message": f"close_time ({close_t.strftime('%H:%M')}) must be strictly after open_time ({open_t.strftime('%H:%M')})."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not description:
            return Response({
                "success": False,
                "message": "Field 'description' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        existing = SpecialOpeningDate.objects.filter(date=target_date).first()
        if existing:
            return Response({
                "success": False,
                "message": f"A special opening date already exists for {target_date.strftime('%Y-%m-%d')} (ID: {existing.id})."
            }, status=status.HTTP_400_BAD_REQUEST)

        so = SpecialOpeningDate.objects.create(
            date=target_date,
            open_time=open_t,
            close_time=close_t,
            description=description
        )

        return Response({
            "success": True,
            "message": f"Special opening date for {target_date.strftime('%Y-%m-%d')} added successfully.",
            "data": serialize_special_opening_date(so)
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Update a special opening date",
        request=SpecialOpeningDateCreateUpdateSerializer,
        responses={200: AdminDateActionResponseSerializer},
    )
    def patch(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Special opening date ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        so = SpecialOpeningDate.objects.filter(id=int(target_id)).first()
        if not so:
            return Response({
                "success": False,
                "message": f"Special opening date with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'date' in data:
            new_date = parse_date_safe(data['date'])
            if not new_date:
                return Response({
                    "success": False,
                    "message": "Invalid date format. Expected YYYY-MM-DD."
                }, status=status.HTTP_400_BAD_REQUEST)

            dup = SpecialOpeningDate.objects.filter(date=new_date).exclude(id=so.id).first()
            if dup:
                return Response({
                    "success": False,
                    "message": f"Another special opening date already exists for {new_date.strftime('%Y-%m-%d')}."
                }, status=status.HTTP_400_BAD_REQUEST)
            so.date = new_date

        current_open = so.open_time
        current_close = so.close_time

        if 'open_time' in data:
            new_open = parse_time_safe(data['open_time'])
            if not new_open:
                return Response({
                    "success": False,
                    "message": "Invalid open_time format. Expected HH:MM."
                }, status=status.HTTP_400_BAD_REQUEST)
            current_open = new_open

        if 'close_time' in data:
            new_close = parse_time_safe(data['close_time'])
            if not new_close:
                return Response({
                    "success": False,
                    "message": "Invalid close_time format. Expected HH:MM."
                }, status=status.HTTP_400_BAD_REQUEST)
            current_close = new_close

        if current_open >= current_close:
            return Response({
                "success": False,
                "message": f"close_time ({current_close.strftime('%H:%M')}) must be strictly after open_time ({current_open.strftime('%H:%M')})."
            }, status=status.HTTP_400_BAD_REQUEST)

        so.open_time = current_open
        so.close_time = current_close

        if 'description' in data:
            desc = str(data['description']).strip()
            if not desc:
                return Response({
                    "success": False,
                    "message": "Description cannot be empty."
                }, status=status.HTTP_400_BAD_REQUEST)
            so.description = desc

        so.save()

        return Response({
            "success": True,
            "message": f"Special opening date for {so.date.strftime('%Y-%m-%d')} updated successfully.",
            "data": serialize_special_opening_date(so)
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.patch(request, pk)

    @extend_schema(
        tags=["Admin Dates Management"],
        summary="Delete a special opening date",
        parameters=[
            OpenApiParameter(name="id", description="Special Opening Date ID to delete", required=False, type=int),
        ],
        responses={200: AdminDateActionResponseSerializer},
    )
    def delete(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Special opening date ID is required to delete."
            }, status=status.HTTP_400_BAD_REQUEST)

        so = SpecialOpeningDate.objects.filter(id=int(target_id)).first()
        if not so:
            return Response({
                "success": False,
                "message": f"Special opening date with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_id = so.id
        deleted_date = so.date.strftime("%Y-%m-%d") if so.date else ""
        so.delete()

        return Response({
            "success": True,
            "message": f"Special opening date for {deleted_date} (ID: {deleted_id}) deleted successfully."
        }, status=status.HTTP_200_OK)



def serialize_admin_booking_item(b, service_type=None):
    """
    Standardized serializer for admin booking list & detail view across all 6 booking models.
    """
    if isinstance(b, SaunaBooking) or service_type == 'sauna':
        svc_type = 'sauna'
        s_disp = b.get_sauna_type_display() if hasattr(b, 'get_sauna_type_display') else b.sauna_type.title()
        svc_name = s_disp if 'sauna' in s_disp.lower() else f"{s_disp} Sauna"
        b_date = b.booking_date.strftime("%Y-%m-%d") if b.booking_date else ""
        b_time = b.booking_time.strftime("%H:%M") if b.booking_time else ""
        end_time = None
        guests = b.capacity
        price = str(b.total_price)
        status_val = b.status
        payment_val = b.payment_status
        req = b.special_request or ""
        dt = parse_booking_datetime(b.booking_date, b.booking_time)
        details = {
            "sauna_type": b.sauna_type,
            "time_slot": b.time_slot,
            "selected_features": b.selected_features or [],
            "special_request": req,
        }

    elif isinstance(b, LunchroomBooking) or service_type == 'lunchroom':
        svc_type = 'lunchroom'
        svc_name = "Lunchroom"
        b_date = b.booking_date.strftime("%Y-%m-%d") if b.booking_date else ""
        b_time = b.booking_time.strftime("%H:%M") if b.booking_time else ""
        end_time = None
        guests = b.capacity
        price = "0.00"
        status_val = b.status
        payment_val = getattr(b, 'payment_status', 'confirmed')
        req = b.special_request or ""
        dt = parse_booking_datetime(b.booking_date, b.booking_time)
        details = {
            "celebration_type": b.celebration_type or "",
            "celebration_date": b.celebration_date.strftime("%Y-%m-%d") if b.celebration_date else None,
            "name_of_celebrant": b.name_of_celebrant or "",
            "age_of_celebrant": b.age_of_celebrant,
            "hobbies": b.hobbies or "",
            "celebration_details": b.celebration_details or "",
            "special_request": req,
        }

    elif isinstance(b, ActivityBooking) or service_type == 'activity':
        svc_type = 'activity'
        act_title = b.activity.title if (b.activity and b.activity.title) else "Activity"
        svc_name = act_title
        act_time = getattr(b.activity, 'open_time', None) if b.activity else None
        act_date = getattr(b.activity, 'date', None) if b.activity else None
        target_date = act_date or (b.created_at.date() if b.created_at else timezone.now().date())
        b_date = target_date.strftime("%Y-%m-%d") if target_date else ""
        b_time = act_time.strftime("%H:%M") if act_time else ""
        end_time = b.activity.close_time.strftime("%H:%M") if (b.activity and b.activity.close_time) else None
        guests = b.capacity
        price = str(b.total_price)
        status_val = b.status
        payment_val = b.payment_status
        req = b.special_request or ""
        dt = parse_booking_datetime(target_date, act_time)
        details = {
            "activity_id": b.activity.id if b.activity else None,
            "activity_title": act_title,
            "special_request": req,
        }

    elif isinstance(b, SaltRoomBooking) or service_type == 'saltroom':
        svc_type = 'saltroom'
        svc_name = "Salt Room"
        b_date = b.date.strftime("%Y-%m-%d") if b.date else ""
        b_time = b.start_time.strftime("%H:%M") if b.start_time else ""
        end_time = b.end_time.strftime("%H:%M") if b.end_time else None
        guests = b.capacity
        price = str(b.total_price)
        status_val = b.status
        payment_val = b.payment_status
        req = b.special_request or ""
        dt = parse_booking_datetime(b.date, b.start_time)
        details = {
            "used_pass": b.used_pass,
            "used_subscription": b.used_subscription,
            "is_paid": b.is_paid,
            "special_request": req,
        }

    elif isinstance(b, PackageBooking) or service_type == 'package':
        svc_type = 'package'
        svc_name = "Package Experience"
        b_date = b.date.strftime("%Y-%m-%d") if b.date else ""
        b_time = ""
        end_time = None
        guests = b.guests
        price = str(b.total_price)
        status_val = b.status
        payment_val = b.payment_status
        req = b.notes or ""
        dt = parse_booking_datetime(b.date, None)
        details = {
            "is_custom": b.is_custom,
            "service_names": b.service_names or [],
            "booked_services_ids": b.booked_services_ids or [],
            "notes": b.notes or "",
        }

    elif isinstance(b, EventBooking) or service_type == 'event':
        svc_type = 'event'
        svc_name = "Special Event"
        b_date = b.date.strftime("%Y-%m-%d") if b.date else ""
        b_time = b.start_time.strftime("%H:%M") if b.start_time else ""
        end_time = b.end_time.strftime("%H:%M") if b.end_time else None
        guests = b.guests
        price = "0.00"
        status_val = getattr(b, 'status', 'confirmed')
        payment_val = getattr(b, 'payment_status', 'pending')
        req = b.notes or ""
        dt = parse_booking_datetime(b.date, b.start_time)
        details = {
            "food_preference": b.food_preference or "",
            "drink_preference": b.drink_preference or "",
            "music_preference": b.music_preference or "",
            "notes": b.notes or "",
        }

    else:
        svc_type = getattr(b, 'service_type', 'booking')
        svc_name = getattr(b, 'service_name', 'Booking')
        b_date = ""
        b_time = ""
        end_time = None
        guests = getattr(b, 'capacity', getattr(b, 'guests', 1))
        price = str(getattr(b, 'total_price', '0.00'))
        status_val = getattr(b, 'status', 'confirmed')
        payment_val = getattr(b, 'payment_status', 'pending')
        req = getattr(b, 'special_request', getattr(b, 'notes', '')) or ""
        dt = timezone.now()
        details = {}

    c_name = b.name if (hasattr(b, 'name') and b.name) else (
        getattr(b.user, 'name', None) or getattr(b.user, 'username', '') if getattr(b, 'user', None) else ''
    )
    c_email = b.email if (hasattr(b, 'email') and b.email) else (
        getattr(b.user, 'email', '') if getattr(b, 'user', None) else ''
    )
    c_phone = b.phone if (hasattr(b, 'phone') and b.phone) else (
        getattr(b.user, 'phone', '') if getattr(b, 'user', None) else ''
    )

    created_iso = b.created_at.isoformat() if (hasattr(b, 'created_at') and b.created_at) else None

    return {
        "id": b.id,
        "booking_id": b.booking_id,
        "service_type": svc_type,
        "service_name": svc_name,
        "client_name": c_name or "Guest",
        "client_email": c_email,
        "client_phone": c_phone,
        "user_id": b.user_id if getattr(b, 'user_id', None) else (b.user.id if getattr(b, 'user', None) else None),
        "date": b_date,
        "time": b_time,
        "end_time": end_time,
        "guests": guests,
        "status": status_val,
        "payment_status": payment_val,
        "total_price": price,
        "special_request": req,
        "created_at": created_iso,
        "access_code": b.booking_id,
        "details": details,
        "_sort_created_at": b.created_at if (hasattr(b, 'created_at') and b.created_at) else dt,
        "_sort_datetime": dt,
    }


def find_booking_by_id(booking_id):
    """
    Finds a booking across any of the 6 booking models by booking_id.
    Returns (booking_instance, model_class, service_type).
    """
    if not booking_id:
        return None, None, None

    bid = str(booking_id).strip()
    prefix = bid.upper().split('-')[0] if '-' in bid else ''

    if prefix in ['PS', 'SS', 'SB']:
        b = SaunaBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, SaunaBooking, 'sauna'
    elif prefix in ['LR', 'LB']:
        b = LunchroomBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, LunchroomBooking, 'lunchroom'
    elif prefix == 'ACT':
        b = ActivityBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, ActivityBooking, 'activity'
    elif prefix == 'SR':
        b = SaltRoomBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, SaltRoomBooking, 'saltroom'
    elif prefix == 'PKG':
        b = PackageBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, PackageBooking, 'package'
    elif prefix in ['EVNT', 'EVT']:
        b = EventBooking.objects.filter(booking_id__iexact=bid).first()
        if b:
            return b, EventBooking, 'event'

    # Fallback search across all models
    b = SaunaBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, SaunaBooking, 'sauna'
    b = LunchroomBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, LunchroomBooking, 'lunchroom'
    b = ActivityBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, ActivityBooking, 'activity'
    b = SaltRoomBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, SaltRoomBooking, 'saltroom'
    b = PackageBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, PackageBooking, 'package'
    b = EventBooking.objects.filter(booking_id__iexact=bid).first()
    if b: return b, EventBooking, 'event'

    return None, None, None


class AdminBookingsView(APIView):
    """
    Admin Bookings API providing comprehensive listing, search, filtering, and pagination
    across all services: Sauna, Lunchroom, Activity, Salt Room, Package, and Event.

    Capabilities:
    1. Search:
       - Client name
       - Client email
       - Booking ID (e.g. PS-0001, SR-0002)
       - Service name / title
    2. Filters:
       - service_type (sauna, private_sauna, shared_sauna, lunchroom, activity, saltroom, package, event, all)
       - date (exact booking date: YYYY-MM-DD or 'today')
       - start_date / date_from (booking date from: YYYY-MM-DD)
       - end_date / date_to (booking date to: YYYY-MM-DD)
       - status (pending, confirmed, cancelled)
       - payment_status (pending, paid, paid_with_package)
    3. Pagination:
       - page (default: 1)
       - page_size (default: 10, max: 100)
    4. Single booking detail:
       - Query parameter `?booking_id=...` or URL path `admin/bookings/<booking_id>/`
    5. Booking update:
       - PATCH / PUT to update `status` and `payment_status`
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Bookings"],
        summary="List all bookings with search, filter, and pagination",
        description="Search bookings across all services by client name, email, booking ID, or service name with date and status filters.",
        parameters=[
            OpenApiParameter(name="search", description="Search keyword across Client Name, Email, Phone, Booking ID, and Service Name", required=False, type=str),
            OpenApiParameter(name="service_type", description="Filter by service type: sauna, private_sauna, shared_sauna, lunchroom, activity, saltroom, package, event, all", required=False, type=str),
            OpenApiParameter(name="date", description="Exact booking visit date (YYYY-MM-DD or 'today')", required=False, type=str),
            OpenApiParameter(name="start_date", description="Filter booking dates starting from this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter booking dates up to this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="status", description="Filter by booking status: pending, confirmed, cancelled", required=False, type=str),
            OpenApiParameter(name="payment_status", description="Filter by payment status: pending, paid, paid_with_package", required=False, type=str),
            OpenApiParameter(name="booking_id", description="Direct filter by booking ID", required=False, type=str),
            OpenApiParameter(name="client_name", description="Direct filter by client name", required=False, type=str),
            OpenApiParameter(name="email", description="Direct filter by client email", required=False, type=str),
            OpenApiParameter(name="ordering", description="Sorting field: -created_at (default), created_at, -date, date, -total_price, total_price", required=False, type=str),
            OpenApiParameter(name="page", description="Page number (default: 1)", required=False, type=int),
            OpenApiParameter(name="page_size", description="Number of results per page (default: 10, max: 100)", required=False, type=int),
        ],
        responses={200: AdminBookingsPaginationResponseSerializer},
    )
    def get(self, request, booking_id=None):
        # 1. Single Booking Detail Lookup
        b_id = booking_id or request.query_params.get('booking_id')
        if b_id and not request.query_params.get('search'):
            booking_obj, model_cls, svc_type = find_booking_by_id(b_id)
            if not booking_obj:
                return Response({
                    "success": False,
                    "message": f"Booking '{b_id}' not found."
                }, status=status.HTTP_404_NOT_FOUND)

            item = serialize_admin_booking_item(booking_obj, svc_type)
            item.pop('_sort_created_at', None)
            item.pop('_sort_datetime', None)
            return Response({
                "success": True,
                "data": item
            }, status=status.HTTP_200_OK)

        # 2. Extract Query Parameters
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        search_lower = search.lower()

        raw_service_type = (request.query_params.get('service_type') or request.query_params.get('service') or '').strip().lower()
        status_filter = (request.query_params.get('status') or '').strip().lower()
        payment_filter = (request.query_params.get('payment_status') or '').strip().lower()
        booking_id_filter = (request.query_params.get('booking_id') or '').strip()
        name_filter = (request.query_params.get('client_name') or request.query_params.get('name') or '').strip()
        email_filter = (request.query_params.get('email') or '').strip()

        exact_date = parse_date_safe(request.query_params.get('date'))
        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))

        # Determine which models to query
        query_all = raw_service_type in ['', 'all']
        include_sauna = query_all or raw_service_type in ['sauna', 'saunas', 'private_sauna', 'shared_sauna', 'private-sauna', 'shared-sauna']
        include_lunchroom = query_all or raw_service_type in ['lunchroom', 'lunchrooms']
        include_activity = query_all or raw_service_type in ['activity', 'activities']
        include_saltroom = query_all or raw_service_type in ['saltroom', 'saltrooms', 'salt-room', 'salt_room']
        include_package = query_all or raw_service_type in ['package', 'packages']
        include_event = query_all or raw_service_type in ['event', 'events']

        all_bookings = []

        # 3. Query Sauna Bookings
        if include_sauna:
            qs = SaunaBooking.objects.select_related('user').all()
            if raw_service_type in ['private_sauna', 'private-sauna']:
                qs = qs.filter(sauna_type='private')
            elif raw_service_type in ['shared_sauna', 'shared-sauna']:
                qs = qs.filter(sauna_type='shared')

            if status_filter:
                qs = qs.filter(status__iexact=status_filter)
            if payment_filter:
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(booking_date=exact_date)
            if start_date:
                qs = qs.filter(booking_date__gte=start_date)
            if end_date:
                qs = qs.filter(booking_date__lte=end_date)

            if search:
                if search_lower in ['sauna', 'saunas', 'private sauna', 'shared sauna']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(sauna_type__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'sauna'))

        # 4. Query Lunchroom Bookings
        if include_lunchroom:
            qs = LunchroomBooking.objects.select_related('user').all()
            if status_filter:
                qs = qs.filter(status__icontains=status_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(name_of_celebrant__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(booking_date=exact_date)
            if start_date:
                qs = qs.filter(booking_date__gte=start_date)
            if end_date:
                qs = qs.filter(booking_date__lte=end_date)

            if search:
                if search_lower in ['lunch', 'lunchroom', 'lunch room']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(name_of_celebrant__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(celebration_type__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'lunchroom'))

        # 5. Query Activity Bookings
        if include_activity:
            qs = ActivityBooking.objects.select_related('user', 'activity').all()
            if status_filter:
                qs = qs.filter(status__iexact=status_filter)
            if payment_filter:
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(Q(activity__date=exact_date) | Q(activity__isnull=True, created_at__date=exact_date))
            if start_date:
                qs = qs.filter(Q(activity__date__gte=start_date) | Q(activity__isnull=True, created_at__date__gte=start_date))
            if end_date:
                qs = qs.filter(Q(activity__date__lte=end_date) | Q(activity__isnull=True, created_at__date__lte=end_date))

            if search:
                if search_lower in ['activity', 'activities']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(activity__title__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'activity'))

        # 6. Query Salt Room Bookings
        if include_saltroom:
            qs = SaltRoomBooking.objects.select_related('user').all()
            if status_filter:
                qs = qs.filter(status__iexact=status_filter)
            if payment_filter:
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(date=exact_date)
            if start_date:
                qs = qs.filter(date__gte=start_date)
            if end_date:
                qs = qs.filter(date__lte=end_date)

            if search:
                if search_lower in ['salt', 'saltroom', 'salt room', 'halotherapy']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'saltroom'))

        # 7. Query Package Bookings
        if include_package:
            qs = PackageBooking.objects.select_related('user').all()
            if status_filter:
                qs = qs.filter(status__iexact=status_filter)
            if payment_filter:
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(date=exact_date)
            if start_date:
                qs = qs.filter(date__gte=start_date)
            if end_date:
                qs = qs.filter(date__lte=end_date)

            if search:
                if search_lower in ['package', 'packages', 'pkg']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'package'))

        # 8. Query Event Bookings
        if include_event:
            qs = EventBooking.objects.select_related('user').all()
            if status_filter:
                qs = qs.filter(status__iexact=status_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(date=exact_date)
            if start_date:
                qs = qs.filter(date__gte=start_date)
            if end_date:
                qs = qs.filter(date__lte=end_date)

            if search:
                if search_lower in ['event', 'events', 'special event']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                all_bookings.append(serialize_admin_booking_item(b, 'event'))

        # 9. Sorting
        ordering = (request.query_params.get('ordering') or request.query_params.get('sort_by') or '-created_at').strip()

        if ordering in ['created_at', '+created_at', 'oldest']:
            all_bookings.sort(key=lambda x: str(x.get('_sort_created_at') or ''))
        elif ordering in ['date', '+date', 'date_asc']:
            all_bookings.sort(key=lambda x: (str(x.get('date') or ''), str(x.get('time') or '')))
        elif ordering in ['-date', 'date_desc']:
            all_bookings.sort(key=lambda x: (str(x.get('date') or ''), str(x.get('time') or '')), reverse=True)
        elif ordering in ['total_price', '+total_price', 'price_asc']:
            all_bookings.sort(key=lambda x: float(x.get('total_price') or 0))
        elif ordering in ['-total_price', 'price_desc']:
            all_bookings.sort(key=lambda x: float(x.get('total_price') or 0), reverse=True)
        else:
            # Default newest first
            all_bookings.sort(key=lambda x: str(x.get('_sort_created_at') or ''), reverse=True)

        # 10. Pagination
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(100, int(request.query_params.get('page_size', request.query_params.get('limit', 10)))))
        except (ValueError, TypeError):
            page_size = 10

        total_count = len(all_bookings)
        total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1

        if page > total_pages and total_count > 0:
            page = total_pages

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_bookings[start_idx:end_idx]

        # Clean internal sort helper keys
        for item in paginated_items:
            item.pop('_sort_created_at', None)
            item.pop('_sort_datetime', None)

        return Response({
            "success": True,
            "count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
            "results": paginated_items,
            "data": paginated_items,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Bookings"],
        summary="Update booking status or payment status",
        description="Updates booking status (pending, confirmed, cancelled) and/or payment status (pending, paid, paid_with_package) for any booking.",
        request=AdminBookingStatusUpdateSerializer,
        responses={200: AdminBookingDetailResponseSerializer},
    )
    def patch(self, request, booking_id=None):
        b_id = booking_id or request.data.get('booking_id') or request.query_params.get('booking_id')
        if not b_id:
            return Response({
                "success": False,
                "message": "booking_id is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        booking_obj, model_cls, svc_type = find_booking_by_id(b_id)
        if not booking_obj:
            return Response({
                "success": False,
                "message": f"Booking '{b_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        updated_fields = []
        new_status = request.data.get('status')
        if new_status and hasattr(booking_obj, 'status'):
            booking_obj.status = new_status
            updated_fields.append('status')

        new_payment = request.data.get('payment_status')
        if new_payment and hasattr(booking_obj, 'payment_status'):
            booking_obj.payment_status = new_payment
            if hasattr(booking_obj, 'is_paid'):
                booking_obj.is_paid = (new_payment in ['paid', 'paid_with_package'])
                updated_fields.append('is_paid')
            updated_fields.append('payment_status')

        if updated_fields:
            booking_obj.save(update_fields=updated_fields)
        else:
            booking_obj.save()

        item = serialize_admin_booking_item(booking_obj, svc_type)
        item.pop('_sort_created_at', None)
        item.pop('_sort_datetime', None)

        return Response({
            "success": True,
            "message": f"Booking '{b_id}' updated successfully.",
            "data": item
        }, status=status.HTTP_200_OK)

    def put(self, request, booking_id=None):
        return self.patch(request, booking_id)


class AdminPaymentsView(APIView):
    """
    Admin Payments API providing:
    1. Monthly Summary & Metrics:
       - Total payments collected this month across all paid services.
       - Service-wise breakdown this month for Private Sauna, Shared Sauna, Sauna Total,
         Salt Room, Activity, and Package (excluding free services Lunchroom & Event).
    2. Bookings Payment Records List:
       - Comprehensive list of bookings from payment-generating services with amount,
         currency, payment status, transaction details, client info, and booking details.
    3. Search & Filter:
       - Search by Booking ID, Date, Client Email, or Client Name.
       - Filter by service_type, date range, payment_status, booking_status.
    4. Pagination:
       - Standard page & page_size pagination.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Payments"],
        summary="Admin Payments overview, monthly breakdown, and booking payments list",
        description="Returns this month's total revenue, service-wise breakdown (Sauna, Saltroom, Activity, Package), and searchable/filterable list of booking payments.",
        parameters=[
            OpenApiParameter(name="month", description="Target month for metrics (1-12, default: current month)", required=False, type=int),
            OpenApiParameter(name="year", description="Target year for metrics (default: current year)", required=False, type=int),
            OpenApiParameter(name="search", description="Search keyword across Booking ID, Client Name, Email, and Phone", required=False, type=str),
            OpenApiParameter(name="service_type", description="Filter payments by service: sauna, private_sauna, shared_sauna, saltroom, activity, package, all", required=False, type=str),
            OpenApiParameter(name="payment_status", description="Filter by payment status: paid, paid_with_package, pending, all", required=False, type=str),
            OpenApiParameter(name="date", description="Exact booking or payment date (YYYY-MM-DD or 'today')", required=False, type=str),
            OpenApiParameter(name="start_date", description="Filter booking/payment dates starting from this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter booking/payment dates up to this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="booking_id", description="Direct filter by booking ID", required=False, type=str),
            OpenApiParameter(name="client_name", description="Direct filter by client name", required=False, type=str),
            OpenApiParameter(name="email", description="Direct filter by client email", required=False, type=str),
            OpenApiParameter(name="ordering", description="Sorting: -created_at (default), created_at, -amount, amount, -date, date", required=False, type=str),
            OpenApiParameter(name="page", description="Page number (default: 1)", required=False, type=int),
            OpenApiParameter(name="page_size", description="Number of results per page (default: 10, max: 100)", required=False, type=int),
        ],
        responses={200: AdminPaymentsResponseSerializer},
    )
    def get(self, request):
        now = timezone.now()

        # 1. Parse target month and year for monthly summary metrics
        try:
            target_year = int(request.query_params.get('year', now.year))
        except (ValueError, TypeError):
            target_year = now.year

        try:
            target_month = int(request.query_params.get('month', now.month))
            if target_month < 1 or target_month > 12:
                target_month = now.month
        except (ValueError, TypeError):
            target_month = now.month

        try:
            month_date = date(target_year, target_month, 1)
            month_name = month_date.strftime("%B %Y")
        except ValueError:
            month_date = date(now.year, now.month, 1)
            month_name = month_date.strftime("%B %Y")
            target_year = now.year
            target_month = now.month

        # 2. Compute Monthly Breakdown across Paid Services (Sauna, Saltroom, Activity, Package)
        # We count bookings with payment_status in ['paid', 'paid_with_package'] for the target month
        valid_paid_statuses = ['paid', 'paid_with_package']

        month_filter = Q(created_at__year=target_year, created_at__month=target_month, payment_status__in=valid_paid_statuses)

        # Private Sauna
        priv_sauna_qs = SaunaBooking.objects.filter(month_filter, sauna_type='private')
        priv_sauna_rev = sum((b.total_price for b in priv_sauna_qs), 0)
        priv_sauna_count = priv_sauna_qs.count()

        # Shared Sauna
        shared_sauna_qs = SaunaBooking.objects.filter(month_filter, sauna_type='shared')
        shared_sauna_rev = sum((b.total_price for b in shared_sauna_qs), 0)
        shared_sauna_count = shared_sauna_qs.count()

        # Sauna Combined Total
        sauna_total_rev = priv_sauna_rev + shared_sauna_rev
        sauna_total_count = priv_sauna_count + shared_sauna_count

        # Salt Room
        salt_qs = SaltRoomBooking.objects.filter(month_filter)
        salt_rev = sum((b.total_price for b in salt_qs), 0)
        salt_count = salt_qs.count()

        # Activity
        act_qs = ActivityBooking.objects.filter(month_filter)
        act_rev = sum((b.total_price for b in act_qs), 0)
        act_count = act_qs.count()

        # Package
        pkg_qs = PackageBooking.objects.filter(month_filter)
        pkg_rev = sum((b.total_price for b in pkg_qs), 0)
        pkg_count = pkg_qs.count()

        total_month_rev = sauna_total_rev + salt_rev + act_rev + pkg_rev
        total_month_transactions = sauna_total_count + salt_count + act_count + pkg_count

        services_breakdown_list = [
            {
                "service_type": "private_sauna",
                "service_name": "Private Sauna",
                "revenue": str(priv_sauna_rev),
                "transactions_count": priv_sauna_count
            },
            {
                "service_type": "shared_sauna",
                "service_name": "Shared Sauna",
                "revenue": str(shared_sauna_rev),
                "transactions_count": shared_sauna_count
            },
            {
                "service_type": "sauna",
                "service_name": "Sauna Total",
                "revenue": str(sauna_total_rev),
                "transactions_count": sauna_total_count
            },
            {
                "service_type": "saltroom",
                "service_name": "Salt Room",
                "revenue": str(salt_rev),
                "transactions_count": salt_count
            },
            {
                "service_type": "activity",
                "service_name": "Activity",
                "revenue": str(act_rev),
                "transactions_count": act_count
            },
            {
                "service_type": "package",
                "service_name": "Package Experience",
                "revenue": str(pkg_rev),
                "transactions_count": pkg_count
            }
        ]

        monthly_summary = {
            "month_name": month_name,
            "year": target_year,
            "month": target_month,
            "total_revenue": str(total_month_rev),
            "total_transactions": total_month_transactions,
            "currency": "EUR",
            "services": services_breakdown_list,
        }

        # 3. Query Payments / Bookings List
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        search_lower = search.lower()

        raw_service_type = (request.query_params.get('service_type') or request.query_params.get('service') or '').strip().lower()
        payment_filter = (request.query_params.get('payment_status') or '').strip().lower()
        booking_id_filter = (request.query_params.get('booking_id') or '').strip()
        name_filter = (request.query_params.get('client_name') or request.query_params.get('name') or '').strip()
        email_filter = (request.query_params.get('email') or '').strip()

        exact_date = parse_date_safe(request.query_params.get('date'))
        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))

        # Build in-memory map of Payments table records for linking transactions
        payments_map = {}
        for p in Payments.objects.all():
            if p.booking_id:
                payments_map[p.booking_id.upper().strip()] = p

        query_all = raw_service_type in ['', 'all']
        include_sauna = query_all or raw_service_type in ['sauna', 'saunas', 'private_sauna', 'shared_sauna', 'private-sauna', 'shared-sauna']
        include_saltroom = query_all or raw_service_type in ['saltroom', 'saltrooms', 'salt-room', 'salt_room']
        include_activity = query_all or raw_service_type in ['activity', 'activities']
        include_package = query_all or raw_service_type in ['package', 'packages']

        payment_records = []

        # Helper to format payment item
        def build_payment_item(b, s_type, s_name, b_date_str, b_time_str, guests_count, details_dict, dt):
            bid = b.booking_id
            p_obj = payments_map.get(bid.upper().strip()) if bid else None

            trans_id = p_obj.transaction_id or p_obj.stripe_payment_intent_id if p_obj else None
            currency_code = p_obj.currency.upper() if (p_obj and p_obj.currency) else "EUR"
            p_date_iso = (p_obj.created_at if p_obj else b.created_at).isoformat() if (p_obj and p_obj.created_at or b.created_at) else None

            c_name = b.name if (hasattr(b, 'name') and b.name) else (
                getattr(b.user, 'name', None) or getattr(b.user, 'username', '') if getattr(b, 'user', None) else ''
            )
            c_email = b.email if (hasattr(b, 'email') and b.email) else (
                getattr(b.user, 'email', '') if getattr(b, 'user', None) else ''
            )
            c_phone = b.phone if (hasattr(b, 'phone') and b.phone) else (
                getattr(b.user, 'phone', '') if getattr(b, 'user', None) else ''
            )

            return {
                "id": b.id,
                "booking_id": bid,
                "service_type": s_type,
                "service_name": s_name,
                "client_name": c_name or "Guest",
                "client_email": c_email,
                "client_phone": c_phone,
                "user_id": b.user_id if getattr(b, 'user_id', None) else (b.user.id if getattr(b, 'user', None) else None),
                "amount": str(b.total_price),
                "currency": currency_code,
                "payment_status": b.payment_status,
                "booking_status": b.status,
                "date": b_date_str,
                "time": b_time_str,
                "guests": guests_count,
                "transaction_id": trans_id,
                "payment_date": p_date_iso,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "details": details_dict,
                "_sort_created_at": b.created_at if b.created_at else dt,
                "_sort_amount": float(b.total_price or 0),
            }

        # Query Sauna Bookings
        if include_sauna:
            qs = SaunaBooking.objects.select_related('user').all()
            if raw_service_type in ['private_sauna', 'private-sauna']:
                qs = qs.filter(sauna_type='private')
            elif raw_service_type in ['shared_sauna', 'shared-sauna']:
                qs = qs.filter(sauna_type='shared')

            if payment_filter and payment_filter != 'all':
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(Q(booking_date=exact_date) | Q(created_at__date=exact_date))
            if start_date:
                qs = qs.filter(Q(booking_date__gte=start_date) | Q(created_at__date__gte=start_date))
            if end_date:
                qs = qs.filter(Q(booking_date__lte=end_date) | Q(created_at__date__lte=end_date))

            if search:
                if search_lower in ['sauna', 'saunas', 'private sauna', 'shared sauna']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(sauna_type__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                svc_title = f"{b.get_sauna_type_display() if hasattr(b, 'get_sauna_type_display') else b.sauna_type.title()} Sauna"
                dt = parse_booking_datetime(b.booking_date, b.booking_time)
                payment_records.append(build_payment_item(
                    b=b,
                    s_type=b.sauna_type + "_sauna",
                    s_name=svc_title,
                    b_date_str=b.booking_date.strftime("%Y-%m-%d") if b.booking_date else "",
                    b_time_str=b.booking_time.strftime("%H:%M") if b.booking_time else "",
                    guests_count=b.capacity,
                    details_dict={
                        "sauna_type": b.sauna_type,
                        "time_slot": b.time_slot,
                        "selected_features": b.selected_features or [],
                        "special_request": b.special_request or "",
                    },
                    dt=dt
                ))

        # Query Salt Room Bookings
        if include_saltroom:
            qs = SaltRoomBooking.objects.select_related('user').all()
            if payment_filter and payment_filter != 'all':
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(Q(date=exact_date) | Q(created_at__date=exact_date))
            if start_date:
                qs = qs.filter(Q(date__gte=start_date) | Q(created_at__date__gte=start_date))
            if end_date:
                qs = qs.filter(Q(date__lte=end_date) | Q(created_at__date__lte=end_date))

            if search:
                if search_lower in ['salt', 'saltroom', 'salt room']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                dt = parse_booking_datetime(b.date, b.start_time)
                payment_records.append(build_payment_item(
                    b=b,
                    s_type="saltroom",
                    s_name="Salt Room",
                    b_date_str=b.date.strftime("%Y-%m-%d") if b.date else "",
                    b_time_str=b.start_time.strftime("%H:%M") if b.start_time else "",
                    guests_count=b.capacity,
                    details_dict={
                        "used_pass": b.used_pass,
                        "used_subscription": b.used_subscription,
                        "is_paid": b.is_paid,
                        "special_request": b.special_request or "",
                    },
                    dt=dt
                ))

        # Query Activity Bookings
        if include_activity:
            qs = ActivityBooking.objects.select_related('user', 'activity').all()
            if payment_filter and payment_filter != 'all':
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(Q(activity__date=exact_date) | Q(created_at__date=exact_date))
            if start_date:
                qs = qs.filter(Q(activity__date__gte=start_date) | Q(created_at__date__gte=start_date))
            if end_date:
                qs = qs.filter(Q(activity__date__lte=end_date) | Q(created_at__date__lte=end_date))

            if search:
                if search_lower in ['activity', 'activities']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(activity__title__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                act_time = getattr(b.activity, 'open_time', None) if b.activity else None
                act_date = getattr(b.activity, 'date', None) if b.activity else None
                target_d = act_date or (b.created_at.date() if b.created_at else timezone.now().date())
                dt = parse_booking_datetime(target_d, act_time)
                payment_records.append(build_payment_item(
                    b=b,
                    s_type="activity",
                    s_name=b.activity.title if (b.activity and b.activity.title) else "Activity",
                    b_date_str=target_d.strftime("%Y-%m-%d") if target_d else "",
                    b_time_str=act_time.strftime("%H:%M") if act_time else "",
                    guests_count=b.capacity,
                    details_dict={
                        "activity_id": b.activity.id if b.activity else None,
                        "activity_title": b.activity.title if b.activity else None,
                        "special_request": b.special_request or "",
                    },
                    dt=dt
                ))

        # Query Package Bookings
        if include_package:
            qs = PackageBooking.objects.select_related('user').all()
            if payment_filter and payment_filter != 'all':
                qs = qs.filter(payment_status__iexact=payment_filter)
            if booking_id_filter:
                qs = qs.filter(booking_id__icontains=booking_id_filter)
            if name_filter:
                qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))
            if email_filter:
                qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

            if exact_date:
                qs = qs.filter(Q(date=exact_date) | Q(created_at__date=exact_date))
            if start_date:
                qs = qs.filter(Q(date__gte=start_date) | Q(created_at__date__gte=start_date))
            if end_date:
                qs = qs.filter(Q(date__lte=end_date) | Q(created_at__date__lte=end_date))

            if search:
                if search_lower in ['package', 'packages', 'pkg']:
                    pass
                else:
                    qs = qs.filter(
                        Q(booking_id__icontains=search) |
                        Q(name__icontains=search) |
                        Q(email__icontains=search) |
                        Q(phone__icontains=search) |
                        Q(user__name__icontains=search) |
                        Q(user__email__icontains=search)
                    )

            for b in qs:
                dt = parse_booking_datetime(b.date, None)
                payment_records.append(build_payment_item(
                    b=b,
                    s_type="package",
                    s_name="Package Experience",
                    b_date_str=b.date.strftime("%Y-%m-%d") if b.date else "",
                    b_time_str="",
                    guests_count=b.guests,
                    details_dict={
                        "is_custom": b.is_custom,
                        "service_names": b.service_names or [],
                        "booked_services_ids": b.booked_services_ids or [],
                        "notes": b.notes or "",
                    },
                    dt=dt
                ))

        # 4. Sorting
        ordering = (request.query_params.get('ordering') or request.query_params.get('sort_by') or '-created_at').strip()

        if ordering in ['created_at', '+created_at', 'oldest']:
            payment_records.sort(key=lambda x: str(x.get('_sort_created_at') or ''))
        elif ordering in ['amount', '+amount', 'amount_asc']:
            payment_records.sort(key=lambda x: x.get('_sort_amount', 0))
        elif ordering in ['-amount', 'amount_desc']:
            payment_records.sort(key=lambda x: x.get('_sort_amount', 0), reverse=True)
        elif ordering in ['date', '+date', 'date_asc']:
            payment_records.sort(key=lambda x: (str(x.get('date') or ''), str(x.get('time') or '')))
        elif ordering in ['-date', 'date_desc']:
            payment_records.sort(key=lambda x: (str(x.get('date') or ''), str(x.get('time') or '')), reverse=True)
        else:
            payment_records.sort(key=lambda x: str(x.get('_sort_created_at') or ''), reverse=True)

        # 5. Pagination
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(100, int(request.query_params.get('page_size', request.query_params.get('limit', 10)))))
        except (ValueError, TypeError):
            page_size = 10

        total_count = len(payment_records)
        total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1

        if page > total_pages and total_count > 0:
            page = total_pages

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = payment_records[start_idx:end_idx]

        for item in paginated_items:
            item.pop('_sort_created_at', None)
            item.pop('_sort_amount', None)

        return Response({
            "success": True,
            "monthly_summary": monthly_summary,
            "count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
            "results": paginated_items,
            "data": paginated_items,
        }, status=status.HTTP_200_OK)


class AdminAccessCodesView(APIView):
    """
    Dedicated Admin API for Access Codes:
    Returns Private Sauna and Shared Sauna bookings along with their generated access codes,
    complete booking & client details, date/type filtering, search, and pagination.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Access Codes"],
        summary="List all sauna access codes with search, filter, and pagination",
        description="Returns all Private Sauna and Shared Sauna bookings with access codes (booking_id), client details, date filters, search, and pagination.",
        parameters=[
            OpenApiParameter(name="search", description="Search keyword across Access Code, Booking ID, Client Name, Email, and Phone", required=False, type=str),
            OpenApiParameter(name="sauna_type", description="Filter by sauna type: 'private', 'shared', or 'all'", required=False, type=str),
            OpenApiParameter(name="date", description="Exact booking visit date (YYYY-MM-DD or 'today')", required=False, type=str),
            OpenApiParameter(name="start_date", description="Filter visit dates starting from this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter visit dates up to this date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="status", description="Filter by booking status: pending, confirmed, cancelled", required=False, type=str),
            OpenApiParameter(name="payment_status", description="Filter by payment status: pending, paid, paid_with_package", required=False, type=str),
            OpenApiParameter(name="access_code", description="Direct filter by Access Code / Booking ID", required=False, type=str),
            OpenApiParameter(name="booking_id", description="Direct filter by Booking ID", required=False, type=str),
            OpenApiParameter(name="client_name", description="Direct filter by client name", required=False, type=str),
            OpenApiParameter(name="email", description="Direct filter by client email", required=False, type=str),
            OpenApiParameter(name="ordering", description="Sorting field: -booking_date (default), booking_date, -created_at, created_at, status", required=False, type=str),
            OpenApiParameter(name="page", description="Page number (default: 1)", required=False, type=int),
            OpenApiParameter(name="page_size", description="Number of results per page (default: 10, max: 100)", required=False, type=int),
        ],
        responses={200: AdminAccessCodesResponseSerializer},
    )
    def get(self, request, access_code=None):
        # 1. Single Access Code detail lookup
        target_code = access_code or request.query_params.get('access_code') or request.query_params.get('booking_id')
        if target_code and not request.query_params.get('search'):
            code_str = str(target_code).strip()
            booking = SaunaBooking.objects.select_related('user').filter(
                Q(booking_id__iexact=code_str)
            ).first()

            if not booking:
                return Response({
                    "success": False,
                    "message": f"Sauna access code '{code_str}' not found."
                }, status=status.HTTP_404_NOT_FOUND)

            item = self._serialize_item(booking)
            return Response({
                "success": True,
                "data": item
            }, status=status.HTTP_200_OK)

        # 2. Extract Query Parameters
        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        search_lower = search.lower()

        sauna_type_filter = (request.query_params.get('sauna_type') or request.query_params.get('type') or '').strip().lower()
        status_filter = (request.query_params.get('status') or '').strip().lower()
        payment_filter = (request.query_params.get('payment_status') or '').strip().lower()
        code_filter = (request.query_params.get('access_code') or request.query_params.get('booking_id') or '').strip()
        name_filter = (request.query_params.get('client_name') or request.query_params.get('name') or '').strip()
        email_filter = (request.query_params.get('email') or '').strip()

        exact_date = parse_date_safe(request.query_params.get('date'))
        start_date = parse_date_safe(request.query_params.get('start_date') or request.query_params.get('date_from'))
        end_date = parse_date_safe(request.query_params.get('end_date') or request.query_params.get('date_to'))

        # 3. Base Queryset for Sauna Bookings (Private & Shared)
        qs = SaunaBooking.objects.select_related('user').all()

        # Overall summary counts before filters
        total_all_codes = qs.count()
        total_private = qs.filter(sauna_type='private').count()
        total_shared = qs.filter(sauna_type='shared').count()
        total_confirmed = qs.filter(status='confirmed').count()

        summary_data = {
            "total_codes": total_all_codes,
            "private_sauna_codes": total_private,
            "shared_sauna_codes": total_shared,
            "confirmed_codes": total_confirmed,
        }

        # Apply Filters
        if sauna_type_filter in ['private', 'private_sauna', 'private-sauna']:
            qs = qs.filter(sauna_type='private')
        elif sauna_type_filter in ['shared', 'shared_sauna', 'shared-sauna']:
            qs = qs.filter(sauna_type='shared')

        if status_filter and status_filter != 'all':
            qs = qs.filter(status__iexact=status_filter)

        if payment_filter and payment_filter != 'all':
            qs = qs.filter(payment_status__iexact=payment_filter)

        if code_filter:
            qs = qs.filter(booking_id__icontains=code_filter)

        if name_filter:
            qs = qs.filter(Q(name__icontains=name_filter) | Q(user__name__icontains=name_filter))

        if email_filter:
            qs = qs.filter(Q(email__icontains=email_filter) | Q(user__email__icontains=email_filter))

        if exact_date:
            qs = qs.filter(booking_date=exact_date)
        if start_date:
            qs = qs.filter(booking_date__gte=start_date)
        if end_date:
            qs = qs.filter(booking_date__lte=end_date)

        if search:
            if search_lower in ['private sauna', 'private']:
                qs = qs.filter(sauna_type='private')
            elif search_lower in ['shared sauna', 'shared']:
                qs = qs.filter(sauna_type='shared')
            elif search_lower in ['sauna', 'saunas']:
                pass  # All records are sauna bookings
            else:
                qs = qs.filter(
                    Q(booking_id__icontains=search) |
                    Q(name__icontains=search) |
                    Q(email__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(sauna_type__icontains=search) |
                    Q(user__name__icontains=search) |
                    Q(user__email__icontains=search)
                )

        # 4. Sorting
        ordering = (request.query_params.get('ordering') or request.query_params.get('sort_by') or '-booking_date').strip()
        valid_orderings = {
            'booking_date': ['booking_date', 'booking_time'],
            '-booking_date': ['-booking_date', '-booking_time'],
            'date': ['booking_date', 'booking_time'],
            '-date': ['-booking_date', '-booking_time'],
            'created_at': ['created_at'],
            '-created_at': ['-created_at'],
            'status': ['status'],
            'sauna_type': ['sauna_type'],
        }
        order_fields = valid_orderings.get(ordering, ['-booking_date', '-booking_time'])
        qs = qs.order_by(*order_fields)

        # 5. Pagination
        total_count = qs.count()

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(100, int(request.query_params.get('page_size', request.query_params.get('limit', 10)))))
        except (ValueError, TypeError):
            page_size = 10

        total_pages = max(1, math.ceil(total_count / page_size)) if total_count > 0 else 1
        if page > total_pages and total_count > 0:
            page = total_pages

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_qs = qs[start_idx:end_idx]

        results = [self._serialize_item(b) for b in paginated_qs]

        return Response({
            "success": True,
            "summary": summary_data,
            "count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
            "results": results,
            "data": results,
        }, status=status.HTTP_200_OK)

    def _serialize_item(self, b):
        s_disp = b.get_sauna_type_display() if hasattr(b, 'get_sauna_type_display') else b.sauna_type.title()
        svc_name = s_disp if 'sauna' in s_disp.lower() else f"{s_disp} Sauna"
        c_name = b.name if (hasattr(b, 'name') and b.name) else (
            getattr(b.user, 'name', None) or getattr(b.user, 'username', '') if getattr(b, 'user', None) else ''
        )
        c_email = b.email if (hasattr(b, 'email') and b.email) else (
            getattr(b.user, 'email', '') if getattr(b, 'user', None) else ''
        )
        c_phone = b.phone if (hasattr(b, 'phone') and b.phone) else (
            getattr(b.user, 'phone', '') if getattr(b, 'user', None) else ''
        )

        features = b.get_feature_names() if hasattr(b, 'get_feature_names') else (b.selected_features or [])

        return {
            "id": b.id,
            "booking_id": b.booking_id,
            "access_code": b.booking_id,
            "sauna_type": b.sauna_type,
            "service_name": svc_name,
            "client_name": c_name or "Guest",
            "client_email": c_email,
            "client_phone": c_phone,
            "user_id": b.user_id if getattr(b, 'user_id', None) else (b.user.id if getattr(b, 'user', None) else None),
            "date": b.booking_date.strftime("%Y-%m-%d") if b.booking_date else "",
            "time": b.booking_time.strftime("%H:%M") if b.booking_time else "",
            "time_slot": b.time_slot,
            "guests": b.capacity,
            "status": b.status,
            "payment_status": b.payment_status,
            "total_price": str(b.total_price),
            "special_request": b.special_request or "",
            "selected_features": features,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "details": {
                "sauna_type": b.sauna_type,
                "time_slot": b.time_slot,
                "capacity": b.capacity,
                "selected_features": features,
                "special_request": b.special_request or "",
                "total_price": str(b.total_price),
            }
        }

# ════════════════════════════════════════════════════════════════════════════════
# ADMIN USERS VIEW (List with rich filters, pagination, summary & Update by ID)
# ════════════════════════════════════════════════════════════════════════════════

class AdminUsersView(APIView):
    """
    Admin Users Management API:
    1. GET /api/dashboard/admin/users/
       - List all users with comprehensive filtering (role, is_active, block, language,
         date_joined range, search by name/email/phone/uid).
       - Includes global summary counters (total_users, active_users, blocked_users, admin_users,
         regular_users, joined_this_month).
       - Supports sorting and pagination (page, page_size).
       - Or query single user with `?id=<user_id>` or `admin/users/<user_id>/`.
    2. PATCH / PUT /api/dashboard/admin/users/<user_id>/ (or `?id=<user_id>` or in body)
       - Update user details: name, phone, bio, role, language, is_active, block (suspension),
         password reset, and profile image upload.
    3. DELETE /api/dashboard/admin/users/<user_id>/
       - Delete or deactivate a user account.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Admin Users"],
        summary="List all users with search, multi-filter, and pagination",
        description=(
            "Comprehensive user listing for admin dashboard with filtering by role (admin/user), "
            "status (active/inactive), suspension (blocked/unblocked), language (en/nl/de), "
            "registration date range, keyword search, and pagination."
        ),
        parameters=[
            OpenApiParameter(name="search", description="Search keyword matching Name, Email, Phone, or UID", required=False, type=str),
            OpenApiParameter(name="role", description="Filter by user role: 'admin', 'user', or 'all'", required=False, type=str),
            OpenApiParameter(name="is_active", description="Filter by active status: 'true', 'false', '1', '0'", required=False, type=str),
            OpenApiParameter(name="block", description="Filter by blocked/suspended status: 'true', 'false', '1', '0'", required=False, type=str),
            OpenApiParameter(name="language", description="Filter by language code: 'en', 'nl', 'de'", required=False, type=str),
            OpenApiParameter(name="date", description="Filter users joined on exact date (YYYY-MM-DD or 'today')", required=False, type=str),
            OpenApiParameter(name="start_date", description="Filter users joined on or after date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="end_date", description="Filter users joined on or before date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="id", description="Direct lookup by User ID", required=False, type=int),
            OpenApiParameter(name="ordering", description="Order by field: '-date_joined' (default), 'date_joined', 'name', '-name', 'email', '-email'", required=False, type=str),
            OpenApiParameter(name="page", description="Page number (default: 1)", required=False, type=int),
            OpenApiParameter(name="page_size", description="Number of results per page (default: 10, max: 100)", required=False, type=int),
        ],
        responses={200: AdminUsersPaginationResponseSerializer},
    )
    def get(self, request, user_id=None):
        UserModel = get_user_model()
        uid_param = user_id or request.query_params.get('id')

        # 1. Single User Detail Lookup
        if uid_param:
            user_obj = UserModel.objects.filter(id=uid_param).first()
            if not user_obj:
                return Response({
                    "success": False,
                    "message": f"User with ID '{uid_param}' not found."
                }, status=status.HTTP_404_NOT_FOUND)

            return Response({
                "success": True,
                "data": self._serialize_user(request, user_obj),
            }, status=status.HTTP_200_OK)

        # 2. Global Metrics / Summary
        now = timezone.now()
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_users_count = UserModel.objects.count()
        active_users_count = UserModel.objects.filter(is_active=True).count()
        blocked_users_count = UserModel.objects.filter(block=True).count()
        admin_users_count = UserModel.objects.filter(role='admin').count()
        regular_users_count = UserModel.objects.filter(role='user').count()
        joined_this_month_count = UserModel.objects.filter(date_joined__gte=first_of_month).count()

        summary = {
            "total_users": total_users_count,
            "active_users": active_users_count,
            "blocked_users": blocked_users_count,
            "admin_users": admin_users_count,
            "regular_users": regular_users_count,
            "joined_this_month": joined_this_month_count,
        }

        # 3. Queryset & Filtering
        qs = UserModel.objects.all()

        # Search keyword
        search = (request.query_params.get('search') or '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(uid__icontains=search)
            )

        # Role filter
        role = (request.query_params.get('role') or '').strip().lower()
        if role and role != 'all':
            qs = qs.filter(role=role)

        # is_active filter
        is_active_val = request.query_params.get('is_active')
        if is_active_val is not None and is_active_val != '':
            val_str = str(is_active_val).lower().strip()
            if val_str in ['true', '1']:
                qs = qs.filter(is_active=True)
            elif val_str in ['false', '0']:
                qs = qs.filter(is_active=False)

        # block / suspend filter
        block_val = request.query_params.get('block')
        if block_val is not None and block_val != '':
            b_str = str(block_val).lower().strip()
            if b_str in ['true', '1']:
                qs = qs.filter(block=True)
            elif b_str in ['false', '0']:
                qs = qs.filter(block=False)

        # language filter
        lang = (request.query_params.get('language') or '').strip().lower()
        if lang:
            qs = qs.filter(language=lang)

        # Date filter
        exact_date = (request.query_params.get('date') or '').strip()
        if exact_date:
            if exact_date.lower() == 'today':
                qs = qs.filter(date_joined__date=timezone.now().date())
            else:
                try:
                    target_d = datetime.strptime(exact_date, "%Y-%m-%d").date()
                    qs = qs.filter(date_joined__date=target_d)
                except ValueError:
                    pass

        start_date = (request.query_params.get('start_date') or request.query_params.get('date_from') or '').strip()
        if start_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d").date()
                qs = qs.filter(date_joined__date__gte=sd)
            except ValueError:
                pass

        end_date = (request.query_params.get('end_date') or request.query_params.get('date_to') or '').strip()
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d").date()
                qs = qs.filter(date_joined__date__lte=ed)
            except ValueError:
                pass

        # 4. Ordering
        ordering = (request.query_params.get('ordering') or '-date_joined').strip()
        allowed_ordering = ['date_joined', '-date_joined', 'name', '-name', 'email', '-email', 'id', '-id']
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('-date_joined')

        # 5. Pagination
        total = qs.count()
        page = int(request.query_params.get('page') or 1)
        page_size = int(request.query_params.get('page_size') or 10)
        page_size = max(1, min(page_size, 100))

        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_users = qs[start_idx:end_idx]

        data = [self._serialize_user(request, u) for u in page_users]

        return Response({
            "success": True,
            "summary": summary,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "data": data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Users"],
        summary="Update a user's details, role, status, or password",
        description="Update user profile fields, role, is_active, suspension/block, password, and avatar image.",
        request=AdminUserUpdateSerializer,
        responses={
            200: AdminUserActionResponseSerializer,
            400: AdminUserActionResponseSerializer,
            404: AdminUserActionResponseSerializer,
        }
    )
    def patch(self, request, user_id=None):
        return self._handle_update(request, user_id)

    @extend_schema(
        tags=["Admin Users"],
        summary="Update a user (PUT)",
        request=AdminUserUpdateSerializer,
        responses={200: AdminUserActionResponseSerializer}
    )
    def put(self, request, user_id=None):
        return self._handle_update(request, user_id)

    def _handle_update(self, request, user_id=None):
        UserModel = get_user_model()
        uid = user_id or request.data.get('id') or request.query_params.get('id')
        if not uid:
            return Response({
                "success": False,
                "message": "User ID is required for update."
            }, status=status.HTTP_400_BAD_REQUEST)

        user_obj = UserModel.objects.filter(id=uid).first()
        if not user_obj:
            return Response({
                "success": False,
                "message": f"User with ID '{uid}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # Update text & profile fields
        if 'name' in data:
            user_obj.name = data['name']
        if 'phone' in data:
            user_obj.phone = data['phone']
        if 'bio' in data:
            user_obj.bio = data['bio']
        if 'language' in data:
            lang = str(data['language']).lower().strip()
            if lang in ['en', 'de', 'nl']:
                user_obj.language = lang
        if 'role' in data:
            r = str(data['role']).lower().strip()
            if r in ['admin', 'user']:
                user_obj.role = r
                if r == 'admin':
                    user_obj.is_staff = True
                else:
                    user_obj.is_staff = False
                    user_obj.is_superuser = False
        if 'is_active' in data:
            val = str(data['is_active']).lower().strip()
            user_obj.is_active = val in ['true', '1']
        if 'block' in data:
            val = str(data['block']).lower().strip()
            user_obj.block = val in ['true', '1']
        if 'password' in data and data['password']:
            user_obj.set_password(data['password'])

        if 'image' in request.FILES:
            user_obj.image = request.FILES['image']

        user_obj.save()

        return Response({
            "success": True,
            "message": f"User '{user_obj.email}' updated successfully.",
            "data": self._serialize_user(request, user_obj),
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Admin Users"],
        summary="Delete a user",
        description="Permanently delete a user account from database.",
        responses={200: AdminUserActionResponseSerializer, 404: AdminUserActionResponseSerializer}
    )
    def delete(self, request, user_id=None):
        UserModel = get_user_model()
        uid = user_id or request.data.get('id') or request.query_params.get('id')
        if not uid:
            return Response({
                "success": False,
                "message": "User ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        user_obj = UserModel.objects.filter(id=uid).first()
        if not user_obj:
            return Response({
                "success": False,
                "message": f"User with ID '{uid}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        u_email = user_obj.email
        user_obj.delete()

        return Response({
            "success": True,
            "message": f"User '{u_email}' has been successfully deleted."
        }, status=status.HTTP_200_OK)

    def _serialize_user(self, request, u):
        # Calculate total bookings
        b_count = 0
        total_spent = Decimal("0.00")

        # Reverse booking relations count
        for rel in ['sauna_bookings', 'lunchroom_bookings', 'activity_bookings', 'event_bookings', 'package_bookings', 'saltroom_bookings']:
            if hasattr(u, rel):
                manager = getattr(u, rel)
                b_count += manager.count()

        # Calculate total spent from payments
        if hasattr(u, 'payments'):
            for p in u.payments.filter(payment_status__iexact='paid'):
                if hasattr(p, 'amount') and p.amount:
                    total_spent += Decimal(str(p.amount))

        img_url = None
        if u.image and hasattr(u.image, 'url'):
            try:
                img_url = request.build_absolute_uri(u.image.url)
            except Exception:
                img_url = u.image.url

        return {
            "id": u.id,
            "uid": u.uid,
            "email": u.email,
            "name": u.name or "",
            "phone": u.phone or "",
            "bio": u.bio or "",
            "image": img_url,
            "role": u.role,
            "language": u.language,
            "is_active": u.is_active,
            "block": u.block,
            "date_joined": u.date_joined.strftime("%Y-%m-%d %H:%M:%S") if u.date_joined else None,
            "last_login": u.last_login.strftime("%Y-%m-%d %H:%M:%S") if u.last_login else None,
            "total_bookings": b_count,
            "total_spent": str(total_spent),
        }

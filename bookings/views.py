from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiTypes

from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, PackageBooking, SaltRoomBooking
from .serializers import (
    SaunaBookingSerializer,
    LunchroomBookingSerializer,
    ActivityBookingSerializer,
    EventBookingSerializer,
    PackageBookingSerializer,
    SaltRoomBookingSerializer,
    CancelBookingRequestSerializer,
    CancelBookingResponseSerializer,
)
from payments.views import create_payment_intent_for_booking
from payments.helper import send_booking_confirmation_email


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Sauna Bookings with automatic PaymentIntent generation",
    responses={
        200: SaunaBookingSerializer(many=True),
        201: SaunaBookingSerializer,
    }
)
class SaunaBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SaunaBookingSerializer
    queryset = SaunaBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Automatically generate Stripe PaymentIntent via dj-stripe in single API call
        client_secret = None
        intent_id = None
        try:
            payment, client_secret, intent_id = create_payment_intent_for_booking(booking, currency="eur")
        except Exception as e:
            print("Auto PaymentIntent creation error:", e)

        return Response({
            "success": True,
            "booking_id": booking.booking_id,
            "client_secret": client_secret,
            "payment_intent_id": intent_id,
            "amount": booking.total_price,
            "currency": "eur",
            "data": serializer.data,
            "message": "Sauna booking created successfully. Proceed with Stripe payment using client_secret.",
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Lunchroom Bookings (No payment required)",
    responses={
        200: LunchroomBookingSerializer(many=True),
        201: LunchroomBookingSerializer,
    }
)
class LunchroomBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = LunchroomBookingSerializer
    queryset = LunchroomBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save(status='confirmed')

        # Send confirmation email directly
        try:
            send_booking_confirmation_email(booking)
        except Exception as mail_err:
            print("Lunchroom confirmation email error:", mail_err)

        return Response({
            "success": True,
            "booking_id": booking.booking_id,
            "status": booking.status,
            "data": serializer.data,
            "message": "Lunchroom booking confirmed successfully.",
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Activity Bookings with automatic PaymentIntent generation",
    responses={
        200: ActivityBookingSerializer(many=True),
        201: ActivityBookingSerializer,
    }
)
class ActivityBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ActivityBookingSerializer
    queryset = ActivityBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Automatically generate Stripe PaymentIntent via dj-stripe in single API call
        client_secret = None
        intent_id = None
        try:
            payment, client_secret, intent_id = create_payment_intent_for_booking(booking, currency="eur")
        except Exception as e:
            print("Auto PaymentIntent creation error for Activity Booking:", e)

        return Response({
            "success": True,
            "booking_id": booking.booking_id,
            "client_secret": client_secret,
            "payment_intent_id": intent_id,
            "amount": booking.total_price,
            "currency": "eur",
            "data": serializer.data,
            "message": "Activity booking created successfully. Proceed with Stripe payment using client_secret.",
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Event Bookings / Inquiries (No upfront payment)",
    responses={
        200: EventBookingSerializer(many=True),
        201: EventBookingSerializer,
    }
)
class EventBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = EventBookingSerializer
    queryset = EventBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Send confirmation email
        try:
            send_booking_confirmation_email(booking)
        except Exception as mail_err:
            print("Event booking confirmation email error:", mail_err)

        return Response({
            "success": True,
            "booking_id": booking.booking_id,
            "data": serializer.data,
            "message": "Event inquiry/booking created successfully.",
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Package Bookings (Supports Custom & Standard Packages with PaymentIntent)",
    responses={
        200: PackageBookingSerializer(many=True),
        201: PackageBookingSerializer,
    }
)
class PackageBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PackageBookingSerializer
    queryset = PackageBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        is_custom = serializer.validated_data.get('is_custom', False)
        
        if is_custom:
            # Custom package: No sub-booking creation, no payment required.
            booking = serializer.save(status='pending', payment_status='pending')
            try:
                send_booking_confirmation_email(booking)
            except Exception as mail_err:
                print("Custom package booking confirmation email error:", mail_err)

            return Response({
                "success": True,
                "booking_id": booking.booking_id,
                "is_custom": True,
                "status": booking.status,
                "service_names": booking.service_names,
                "data": serializer.data,
                "message": "Custom package booking request submitted successfully. No upfront payment required.",
            }, status=status.HTTP_201_CREATED)
        else:
            # Standard package: Generate Stripe PaymentIntent if total_price > 0
            booking = serializer.save(status='pending', payment_status='pending')
            client_secret = None
            intent_id = None
            if booking.total_price and float(booking.total_price) > 0:
                try:
                    payment, client_secret, intent_id = create_payment_intent_for_booking(booking, currency="eur")
                except Exception as e:
                    print("Auto PaymentIntent creation error for Package Booking:", e)

            return Response({
                "success": True,
                "booking_id": booking.booking_id,
                "is_custom": False,
                "client_secret": client_secret,
                "payment_intent_id": intent_id,
                "amount": booking.total_price,
                "currency": "eur",
                "data": serializer.data,
                "message": "Package booking created successfully. Proceed with Stripe payment using client_secret.",
            }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Bookings'],
    summary="Create or List Saltroom Bookings (Supports Pass, Subscription, or Direct Stripe Card Payment)",
    responses={
        200: SaltRoomBookingSerializer(many=True),
        201: SaltRoomBookingSerializer,
    }
)
class SaltRoomBookingAPIView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SaltRoomBookingSerializer
    queryset = SaltRoomBooking.objects.all().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        from datetime import datetime, timedelta
        from django.utils import timezone
        from services.models import Saltroom
        from payments.models import ClientPurchase, SessionPass, SubscriptionPlans
        from django.db import models

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        raw_data = request.data if isinstance(request.data, dict) else {}
        payment_mode = data.get('payment_mode') or raw_data.get('payment_mode') or 'card'
        chosen_purchase_id = data.get('purchase_id') or raw_data.get('purchase_id')
        chosen_plan_id = data.get('plan_id') or data.get('purchase_plan_id') or raw_data.get('plan_id') or raw_data.get('purchase_plan_id')
        chosen_pass_id = data.get('pass_id') or data.get('purchase_pass_id') or raw_data.get('pass_id') or raw_data.get('purchase_pass_id')
        req_plan_type = data.get('plan_type') or raw_data.get('plan_type') or ''

        # If payment_mode is card/pass/subscription but plan_id or plan_type is provided:
        if chosen_plan_id:
            # Check if this plan_id is a subscription plan
            sp = SubscriptionPlans.objects.filter(id=chosen_plan_id).first()
            if sp:
                if sp.plan_type == 'unlimited':
                    payment_mode = 'unlimited_subscription'
                elif sp.plan_type == 'weekly':
                    payment_mode = 'weekly_subscription'
                else:
                    payment_mode = 'subscription'
        elif req_plan_type in ['unlimited', 'unlimited_subscription']:
            payment_mode = 'unlimited_subscription'
        elif req_plan_type in ['weekly', 'weekly_subscription']:
            payment_mode = 'weekly_subscription'
        elif chosen_pass_id or req_plan_type in ['pass', 'session_pass']:
            if payment_mode == 'card':
                payment_mode = 'pass'

        user = request.user if request.user and request.user.is_authenticated else None
        if not user and (data.get('email') or raw_data.get('email')):
            from django.contrib.auth import get_user_model
            target_email = data.get('email') or raw_data.get('email')
            user = get_user_model().objects.filter(email__iexact=str(target_email).strip()).first()

        date = data['date']
        start_time = data['start_time']
        capacity = data.get('capacity', 1)
        name = data.get('name') or (user.get_full_name() if user else '') or (user.email if user else '')
        email = data.get('email') or (user.email if user else '')
        phone = data.get('phone', '')
        special_request = data.get('special_request', '')

        saltroom_obj = Saltroom.objects.first()
        duration_td = saltroom_obj.duration if saltroom_obj and saltroom_obj.duration else timedelta(minutes=60)
        max_cap = saltroom_obj.max_capacity if saltroom_obj and saltroom_obj.max_capacity else 2
        price_per_person = saltroom_obj.price_per_person if saltroom_obj else 25

        if capacity > max_cap:
            return Response({
                "success": False,
                "error": f"Requested capacity ({capacity}) exceeds maximum room capacity ({max_cap})."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Auto calculate end_time if not provided
        end_time = data.get('end_time')
        if not end_time:
            dt_start = datetime.combine(date, start_time)
            dt_end = dt_start + duration_td
            end_time = dt_end.time()

        # Check overlapping slot capacity in Saltroom
        overlapping_bookings = SaltRoomBooking.objects.filter(
            date=date
        ).exclude(status='cancelled')

        slot_start_dt = datetime.combine(date, start_time)
        slot_end_dt = datetime.combine(date, end_time)

        already_booked = 0
        for ob in overlapping_bookings:
            ob_start = datetime.combine(date, ob.start_time)
            ob_end = datetime.combine(date, ob.end_time)
            if max(slot_start_dt, ob_start) < min(slot_end_dt, ob_end):
                already_booked += ob.capacity

        if already_booked + capacity > max_cap:
            return Response({
                "success": False,
                "error": f"This slot only has {max(0, max_cap - already_booked)} spot(s) remaining for {capacity} requested."
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        # =========================================================================
        # CASE 1: Book using ACTIVE Session Pass (Already purchased & paid)
        # =========================================================================
        if payment_mode == 'pass':
            if not user:
                return Response({
                    "success": False,
                    "error": "Authentication required to use a session pass."
                }, status=status.HTTP_401_UNAUTHORIZED)

            query = ClientPurchase.objects.filter(
                user=user,
                purchase_type='session_pass',
                payment_status='paid',
                status='confirmed',
                remaining_sessions__gt=0,
            )
            if chosen_purchase_id:
                query = query.filter(purchase_id=chosen_purchase_id)

            client_purchase_obj = query.order_by('-created_at').first()

            # If user has an active pass with sessions left: deduct and confirm instantly
            if client_purchase_obj:
                client_purchase_obj.remaining_sessions = max(0, client_purchase_obj.remaining_sessions - 1)
                client_purchase_obj.save(update_fields=['remaining_sessions'])

                booking = SaltRoomBooking.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    special_request=special_request,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    capacity=capacity,
                    total_price=0,
                    is_paid=True,
                    status='confirmed',
                    payment_status='paid',
                    used_pass=True,
                    used_subscription=False,
                    client_purchase=client_purchase_obj,
                )

                try:
                    send_booking_confirmation_email(booking)
                except Exception as mail_err:
                    print("Saltroom booking confirmation email error:", mail_err)

                return Response({
                    "success": True,
                    "booking_id": booking.booking_id,
                    "payment_mode": "pass",
                    "status": booking.status,
                    "payment_status": booking.payment_status,
                    "is_paid": True,
                    "remaining_sessions": client_purchase_obj.remaining_sessions,
                    "data": SaltRoomBookingSerializer(booking).data,
                    "message": f"Saltroom session booked successfully using active Session Pass ({client_purchase_obj.purchase_id}). 1 session deducted. Remaining: {client_purchase_obj.remaining_sessions}.",
                }, status=status.HTTP_201_CREATED)

            # If user does NOT have an active pass, initiate purchasing a 10-session pass
            session_pass_plan = None
            if chosen_pass_id:
                session_pass_plan = SessionPass.objects.filter(id=chosen_pass_id).first()
            if not session_pass_plan:
                session_pass_plan = SessionPass.objects.first()

            if not session_pass_plan:
                return Response({
                    "success": False,
                    "error": "No Session Pass available in the system to purchase."
                }, status=status.HTTP_400_BAD_REQUEST)

            purchase = ClientPurchase.objects.create(
                user=user,
                purchase_type='session_pass',
                session_pass=session_pass_plan,
                name=name,
                email=email,
                phone=phone,
                amount=session_pass_plan.price,
                currency='eur',
                status='pending',
                payment_status='pending',
            )

            booking = SaltRoomBooking.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                special_request=special_request,
                date=date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                total_price=session_pass_plan.price,
                is_paid=False,
                status='pending',
                payment_status='pending',
                used_pass=True,
                used_subscription=False,
                client_purchase=purchase,
            )

            client_secret = None
            intent_id = None
            try:
                payment, client_secret, intent_id = create_payment_intent_for_booking(purchase, currency="eur")
            except Exception as e:
                print("PaymentIntent creation error for pass purchase with booking:", e)

            return Response({
                "success": True,
                "booking_id": booking.booking_id,
                "purchase_id": purchase.purchase_id,
                "payment_mode": "pass",
                "item_name": session_pass_plan.name,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "is_paid": False,
                "client_secret": client_secret,
                "payment_intent_id": intent_id,
                "amount": purchase.amount,
                "currency": "eur",
                "data": SaltRoomBookingSerializer(booking).data,
                "message": f"Session Pass purchase ({purchase.purchase_id}) initiated for Saltroom booking ({booking.booking_id}). Complete payment to confirm both.",
            }, status=status.HTTP_201_CREATED)

        # =========================================================================
        # CASE 2: Book using SUBSCRIPTION (Active OR New Subscription Purchase)
        # =========================================================================
        elif payment_mode in ['subscription', 'weekly_subscription', 'unlimited_subscription']:
            if not user:
                return Response({
                    "success": False,
                    "error": "Authentication required to use or purchase a subscription."
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Check if user already has an active subscription matching the requirement
            sub_query = ClientPurchase.objects.filter(
                user=user,
                purchase_type='subscription',
                payment_status='paid',
                status='confirmed',
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)
            ).filter(
                models.Q(subscription_plan__plan_category='saltroom') | models.Q(subscription_plan__isnull=True)
            )

            if payment_mode == 'unlimited_subscription':
                sub_query = sub_query.filter(subscription_plan__plan_type='unlimited')
            elif payment_mode == 'weekly_subscription':
                sub_query = sub_query.filter(subscription_plan__plan_type='weekly')

            # If payment_mode is generic 'subscription', find whichever subscription is valid for this date
            if payment_mode == 'subscription' and not chosen_purchase_id:
                # Prioritize one that has valid session for this date
                candidate_subs = list(sub_query.order_by('-created_at'))
                chosen_sub = None
                for c in candidate_subs:
                    c_plan = c.subscription_plan
                    c_is_unlimited = c_plan and c_plan.plan_type == 'unlimited'
                    if c_is_unlimited:
                        c_active_res = SaltRoomBooking.objects.filter(client_purchase=c, status='confirmed', date__gte=now.date()).count()
                        c_max = c.max_active_reservations or (c_plan.max_reservations if c_plan else 10) or 10
                        if c_active_res < c_max:
                            chosen_sub = c
                            break
                    else:
                        start_of_w = date - timedelta(days=date.weekday())
                        end_of_w = start_of_w + timedelta(days=6)
                        c_w_count = SaltRoomBooking.objects.filter(client_purchase=c, date__gte=start_of_w, date__lte=end_of_w).exclude(status='cancelled').count()
                        if c.remaining_sessions > 0 and c_w_count < (c.sessions_per_week or 1):
                            chosen_sub = c
                            break
                client_purchase_obj = chosen_sub or (candidate_subs[0] if candidate_subs else None)
            else:
                client_purchase_obj = sub_query.order_by('-created_at').first()

            if client_purchase_obj:
                # User has an active subscription! Use it.
                plan = client_purchase_obj.subscription_plan
                is_unlimited = plan and plan.plan_type == 'unlimited'
                if not is_unlimited:
                    if client_purchase_obj.remaining_sessions <= 0:
                        return Response({
                            "success": False,
                            "error": "You have exhausted the sessions for this subscription."
                        }, status=status.HTTP_400_BAD_REQUEST)

                    # Enforce weekly limit: 1 session per calendar week (Monday-Sunday)
                    start_of_week = date - timedelta(days=date.weekday())
                    end_of_week = start_of_week + timedelta(days=6)
                    week_bookings = SaltRoomBooking.objects.filter(
                        client_purchase=client_purchase_obj,
                        date__gte=start_of_week,
                        date__lte=end_of_week,
                    ).exclude(status='cancelled').count()

                    if week_bookings >= (client_purchase_obj.sessions_per_week or 1):
                        return Response({
                            "success": False,
                            "error": f"Weekly session limit ({client_purchase_obj.sessions_per_week or 1}/week) already reached for the week of {start_of_week} to {end_of_week}."
                        }, status=status.HTTP_400_BAD_REQUEST)

                    client_purchase_obj.remaining_sessions = max(0, client_purchase_obj.remaining_sessions - 1)
                    client_purchase_obj.save(update_fields=['remaining_sessions'])
                else:
                    # Unlimited subscription: check concurrent active reservations (max 10)
                    active_reservations = SaltRoomBooking.objects.filter(
                        client_purchase=client_purchase_obj,
                        status='confirmed',
                        date__gte=now.date(),
                    ).count()
                    max_allowed = client_purchase_obj.max_active_reservations or (plan.max_reservations if plan else 10) or 10
                    if active_reservations >= max_allowed:
                        return Response({
                            "success": False,
                            "error": f"Maximum concurrent reservations limit ({max_allowed}) reached for your Unlimited plan."
                        }, status=status.HTTP_400_BAD_REQUEST)


                booking = SaltRoomBooking.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=phone,
                    special_request=special_request,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    capacity=capacity,
                    total_price=0,
                    is_paid=True,
                    status='confirmed',
                    payment_status='paid',
                    used_pass=False,
                    used_subscription=True,
                    client_purchase=client_purchase_obj,
                )

                try:
                    send_booking_confirmation_email(booking)
                except Exception as mail_err:
                    print("Saltroom booking confirmation email error:", mail_err)

                return Response({
                    "success": True,
                    "booking_id": booking.booking_id,
                    "payment_mode": "subscription",
                    "status": booking.status,
                    "payment_status": booking.payment_status,
                    "is_paid": True,
                    "is_unlimited": is_unlimited,
                    "remaining_sessions": client_purchase_obj.remaining_sessions if not is_unlimited else "unlimited",
                    "data": SaltRoomBookingSerializer(booking).data,
                    "message": f"Saltroom session booked successfully using active Subscription ({client_purchase_obj.purchase_id}).",
                }, status=status.HTTP_201_CREATED)

            # User DOES NOT have an active subscription: initiate purchasing one!
            sub_plan = None
            if chosen_plan_id:
                sub_plan = SubscriptionPlans.objects.filter(id=chosen_plan_id).first()
            if not sub_plan:
                desired_type = 'unlimited' if payment_mode == 'unlimited_subscription' else 'weekly'
                sub_plan = SubscriptionPlans.objects.filter(plan_category='saltroom', plan_type=desired_type).first()
            if not sub_plan:
                sub_plan = SubscriptionPlans.objects.filter(plan_category='saltroom').first()
            if not sub_plan:
                return Response({
                    "success": False,
                    "error": "No matching Subscription Plan found to purchase."
                }, status=status.HTTP_400_BAD_REQUEST)

            purchase = ClientPurchase.objects.create(
                user=user,
                purchase_type='subscription',
                subscription_plan=sub_plan,
                name=name,
                email=email,
                phone=phone,
                amount=sub_plan.price,
                currency='eur',
                status='pending',
                payment_status='pending',
            )

            booking = SaltRoomBooking.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                special_request=special_request,
                date=date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                total_price=sub_plan.price,
                is_paid=False,
                status='pending',
                payment_status='pending',
                used_pass=False,
                used_subscription=True,
                client_purchase=purchase,
            )

            client_secret = None
            intent_id = None
            try:
                payment, client_secret, intent_id = create_payment_intent_for_booking(purchase, currency="eur")
            except Exception as e:
                print("PaymentIntent creation error for subscription purchase with booking:", e)

            return Response({
                "success": True,
                "booking_id": booking.booking_id,
                "purchase_id": purchase.purchase_id,
                "payment_mode": "subscription",
                "item_name": sub_plan.name,
                "status": booking.status,
                "payment_status": booking.payment_status,
                "is_paid": False,
                "client_secret": client_secret,
                "payment_intent_id": intent_id,
                "amount": purchase.amount,
                "currency": "eur",
                "data": SaltRoomBookingSerializer(booking).data,
                "message": f"{sub_plan.name} purchase ({purchase.purchase_id}) initiated for Saltroom booking ({booking.booking_id}). Complete payment to confirm both.",
            }, status=status.HTTP_201_CREATED)

        # =========================================================================
        # CASE 3: Standard single session direct card payment (€25 * capacity)
        # =========================================================================
        else:
            total_price = float(price_per_person) * capacity

            booking = SaltRoomBooking.objects.create(
                user=user,
                name=name,
                email=email,
                phone=phone,
                special_request=special_request,
                date=date,
                start_time=start_time,
                end_time=end_time,
                capacity=capacity,
                total_price=total_price,
                is_paid=False,
                status='pending',
                payment_status='pending',
                used_pass=False,
                used_subscription=False,
            )

            client_secret = None
            intent_id = None
            try:
                payment, client_secret, intent_id = create_payment_intent_for_booking(booking, currency="eur")
            except Exception as e:
                print("Auto PaymentIntent creation error for SaltRoom Booking:", e)

            return Response({
                "success": True,
                "booking_id": booking.booking_id,
                "payment_mode": "card",
                "status": booking.status,
                "payment_status": booking.payment_status,
                "is_paid": False,
                "client_secret": client_secret,
                "payment_intent_id": intent_id,
                "amount": booking.total_price,
                "currency": "eur",
                "data": SaltRoomBookingSerializer(booking).data,
                "message": "Saltroom booking created successfully. Proceed with Stripe payment using client_secret.",
            }, status=status.HTTP_201_CREATED)


class BookingDetailAPIView(APIView):
    """
    Lookup any booking details by booking_id (e.g. SR-8503, SB-0001, PKG-0001, etc.)
    """
    permission_classes = [AllowAny]

    def get(self, request, booking_id, *args, **kwargs):
        prefix = booking_id.upper().split('-')[0] if '-' in booking_id else ''

        booking = None
        serializer = None

        if prefix == 'SR' or booking_id.startswith('SR-'):
            booking = SaltRoomBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = SaltRoomBookingSerializer(booking)
        elif prefix in ['SB', 'PS', 'SS'] or booking_id.startswith(('SB-', 'PS-', 'SS-')):
            booking = SaunaBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = SaunaBookingSerializer(booking)
        elif prefix == 'PKG' or booking_id.startswith('PKG-'):
            booking = PackageBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = PackageBookingSerializer(booking)
        elif prefix == 'LB' or booking_id.startswith('LB-'):
            booking = LunchroomBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = LunchroomBookingSerializer(booking)
        elif prefix == 'ACT' or booking_id.startswith('ACT-'):
            booking = ActivityBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = ActivityBookingSerializer(booking)
        elif prefix == 'EVT' or booking_id.startswith('EVT-'):
            booking = EventBooking.objects.filter(booking_id__iexact=booking_id).first()
            if booking:
                serializer = EventBookingSerializer(booking)
        else:
            # Fallback search across all booking models
            booking = (
                SaltRoomBooking.objects.filter(booking_id__iexact=booking_id).first()
                or SaunaBooking.objects.filter(booking_id__iexact=booking_id).first()
                or PackageBooking.objects.filter(booking_id__iexact=booking_id).first()
                or LunchroomBooking.objects.filter(booking_id__iexact=booking_id).first()
                or ActivityBooking.objects.filter(booking_id__iexact=booking_id).first()
                or EventBooking.objects.filter(booking_id__iexact=booking_id).first()
            )
            if booking:
                if isinstance(booking, SaltRoomBooking):
                    serializer = SaltRoomBookingSerializer(booking)
                elif isinstance(booking, SaunaBooking):
                    serializer = SaunaBookingSerializer(booking)
                elif isinstance(booking, PackageBooking):
                    serializer = PackageBookingSerializer(booking)
                elif isinstance(booking, LunchroomBooking):
                    serializer = LunchroomBookingSerializer(booking)
                elif isinstance(booking, ActivityBooking):
                    serializer = ActivityBookingSerializer(booking)
                elif isinstance(booking, EventBooking):
                    serializer = EventBookingSerializer(booking)

        if not booking or not serializer:
            return Response({
                "success": False,
                "error": f"Booking with ID '{booking_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "success": True,
            "booking_id": booking.booking_id,
            "status": getattr(booking, 'status', None),
            "payment_status": getattr(booking, 'payment_status', None),
            "is_paid": getattr(booking, 'is_paid', False),
            "data": serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Bookings'],
    summary="List all bookings of all types for the authenticated user",
    responses={200: OpenApiTypes.OBJECT}
)
class UserBookingsAPIView(APIView):
    """
    Returns all bookings across Sauna, Saltroom, Lunchroom, Activity, Package, and Event
    belonging to the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        email = user.email

        from django.db.models import Q

        sauna_bookings = SaunaBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')
        saltroom_bookings = SaltRoomBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')
        lunchroom_bookings = LunchroomBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')
        activity_bookings = ActivityBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')
        package_bookings = PackageBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')
        event_bookings = EventBooking.objects.filter(Q(user=user) | Q(email__iexact=email)).order_by('-created_at')

        return Response({
            "sauna": SaunaBookingSerializer(sauna_bookings, many=True).data,
            "saltroom": SaltRoomBookingSerializer(saltroom_bookings, many=True).data,
            "lunchroom": LunchroomBookingSerializer(lunchroom_bookings, many=True).data,
            "activities": ActivityBookingSerializer(activity_bookings, many=True).data,
            "packages": PackageBookingSerializer(package_bookings, many=True).data,
            "events": EventBookingSerializer(event_bookings, many=True).data,
        }, status=status.HTTP_200_OK)


def get_booking_start_datetime(booking):
    """
    Computes a timezone-aware or naive datetime representing the scheduled start time of a booking.
    Supports all 6 models: SaunaBooking, SaltRoomBooking, ActivityBooking,
    LunchroomBooking, EventBooking, PackageBooking.
    """
    from datetime import datetime, time
    from django.utils import timezone

    b_date = None
    b_time = None

    if isinstance(booking, SaunaBooking):
        b_date = getattr(booking, 'booking_date', None)
        b_time = getattr(booking, 'booking_time', None)
    elif isinstance(booking, SaltRoomBooking):
        b_date = getattr(booking, 'date', None)
        b_time = getattr(booking, 'start_time', None)
    elif isinstance(booking, ActivityBooking):
        act = getattr(booking, 'activity', None)
        b_date = getattr(act, 'date', None) if act else None
        b_time = getattr(act, 'open_time', None) if act else None
        if not b_date and getattr(booking, 'created_at', None):
            b_date = booking.created_at.date()
    elif isinstance(booking, LunchroomBooking):
        b_date = getattr(booking, 'booking_date', None)
        b_time = getattr(booking, 'booking_time', None)
    elif isinstance(booking, EventBooking):
        b_date = getattr(booking, 'date', None)
        b_time = getattr(booking, 'start_time', None)
    elif isinstance(booking, PackageBooking):
        b_date = getattr(booking, 'date', None)
        b_time = None

    if not b_date:
        if hasattr(booking, 'created_at') and booking.created_at:
            return booking.created_at
        return timezone.now()

    if not b_time:
        b_time = time(0, 0)

    naive_dt = datetime.combine(b_date, b_time)
    if timezone.is_aware(timezone.now()):
        try:
            return timezone.make_aware(naive_dt, timezone.get_current_timezone())
        except Exception:
            return naive_dt
    return naive_dt


@extend_schema(
    tags=['Bookings'],
    summary="Cancel a booking (Enforces 24-hour notice & restores pass session credits)",
    description=(
        "Cancels any booking (Sauna, Saltroom, Activity, Lunchroom, Package, Event) "
        "if requested more than 24 hours before the scheduled appointment start time. "
        "If cancellation occurs within 24 hours of start time (or after start time), cancellation is rejected. "
        "For bookings booked with a Session Pass / Membership, the deducted credit is automatically restored."
    ),
    request=CancelBookingRequestSerializer,
    responses={
        200: CancelBookingResponseSerializer,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    }
)
class CancelBookingAPIView(APIView):
    """
    Cancellation endpoint for bookings.
    Accepts booking_id via URL path (POST /api/bookings/<booking_id>/cancel/)
    or request payload/query param `booking_id`.
    """
    permission_classes = [AllowAny]

    def post(self, request, booking_id=None):
        from django.utils import timezone
        from dashboards.views import find_booking_by_id, serialize_admin_booking_item
        from payments.models import ClientPurchase

        target_id = booking_id or request.data.get('booking_id') or request.query_params.get('booking_id')
        if not target_id:
            return Response({
                "success": False,
                "message": "booking_id is required either in the URL or request body."
            }, status=status.HTTP_400_BAD_REQUEST)

        target_id = str(target_id).strip()
        booking_obj, model_cls, svc_type = find_booking_by_id(target_id)
        if not booking_obj:
            return Response({
                "success": False,
                "message": f"Booking '{target_id}' not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Optional security check: if user is authenticated and not staff, verify ownership
        user = request.user
        if user and user.is_authenticated and not user.is_staff:
            booking_user = getattr(booking_obj, 'user', None)
            booking_email = getattr(booking_obj, 'email', None)
            user_matches = (booking_user == user) or (booking_email and booking_email.lower() == (user.email or '').lower())
            if not user_matches and booking_user is not None:
                return Response({
                    "success": False,
                    "message": "You do not have permission to cancel this booking."
                }, status=status.HTTP_403_FORBIDDEN)

        current_status = getattr(booking_obj, 'status', None)
        if current_status == 'cancelled':
            return Response({
                "success": False,
                "message": f"Booking '{target_id}' is already cancelled.",
                "booking_id": booking_obj.booking_id,
                "status": "cancelled",
            }, status=status.HTTP_400_BAD_REQUEST)

        # 24-Hour Policy Check
        start_dt = get_booking_start_datetime(booking_obj)
        now_dt = timezone.now()

        # Align timezone awareness
        if timezone.is_aware(start_dt) and not timezone.is_aware(now_dt):
            now_dt = timezone.make_aware(now_dt, timezone.get_current_timezone())
        elif not timezone.is_aware(start_dt) and timezone.is_aware(now_dt):
            now_dt = timezone.make_naive(now_dt, timezone.get_current_timezone())

        time_difference = start_dt - now_dt
        hours_until_start = time_difference.total_seconds() / 3600.0

        if hours_until_start < 24.0:
            if hours_until_start < 0:
                detail_msg = f"This booking was scheduled for {start_dt.strftime('%Y-%m-%d %H:%M')}, which has already passed."
            else:
                detail_msg = (
                    f"Only {hours_until_start:.1f} hours remaining until start time ({start_dt.strftime('%Y-%m-%d %H:%M')}). "
                    "Cancellations must be made at least 24 hours prior to the scheduled start time."
                )

            return Response({
                "success": False,
                "cancellation_allowed": False,
                "message": f"Cancellation not possible: 24-hour notice policy required. {detail_msg}",
                "booking_id": booking_obj.booking_id,
                "start_time": start_dt.strftime('%Y-%m-%d %H:%M'),
                "hours_until_start": round(hours_until_start, 2),
                "required_notice_hours": 24,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Proceed with Cancellation
        credit_restored = False
        remaining_sessions = None
        restore_info = ""

        # Check if booking used a Session Pass / Membership
        # 1. SaltRoomBooking with used_pass or client_purchase
        cp = getattr(booking_obj, 'client_purchase', None)
        if not cp and getattr(booking_obj, 'used_pass', False):
            # Attempt to locate active/confirmed ClientPurchase for this user/email
            b_user = getattr(booking_obj, 'user', None)
            b_email = getattr(booking_obj, 'email', None)
            cp_qs = ClientPurchase.objects.filter(purchase_type='session_pass')
            if b_user:
                cp = cp_qs.filter(user=b_user).order_by('-created_at').first()
            if not cp and b_email:
                cp = cp_qs.filter(email__iexact=b_email).order_by('-created_at').first()

        if cp:
            # Restore 1 session credit if applicable
            plan_type = getattr(cp.subscription_plan, 'plan_type', None) if getattr(cp, 'subscription_plan', None) else None
            # Do not increment if unlimited subscription
            if plan_type != 'unlimited':
                cp.remaining_sessions = cp.remaining_sessions + 1
                cp.save(update_fields=['remaining_sessions'])
                credit_restored = True
                remaining_sessions = cp.remaining_sessions
                restore_info = f" 1 session credit has been refunded to pass/plan ({cp.purchase_id}). Remaining credits: {cp.remaining_sessions}."

        # Update booking status
        fields_to_update = []
        if hasattr(booking_obj, 'status'):
            booking_obj.status = 'cancelled'
            fields_to_update.append('status')

        # Optional cancellation reason
        reason = request.data.get('reason')
        if reason and hasattr(booking_obj, 'special_request'):
            booking_obj.special_request = f"{getattr(booking_obj, 'special_request', '') or ''}\n[Cancellation Reason: {reason}]".strip()
            fields_to_update.append('special_request')
        elif reason and hasattr(booking_obj, 'notes'):
            booking_obj.notes = f"{getattr(booking_obj, 'notes', '') or ''}\n[Cancellation Reason: {reason}]".strip()
            fields_to_update.append('notes')

        if fields_to_update:
            booking_obj.save(update_fields=fields_to_update)
        else:
            booking_obj.save()

        # If booking is part of a PackageBooking, or if it is a PackageBooking with sub-services, also update sub-services if applicable
        if isinstance(booking_obj, PackageBooking):
            raw_ids = booking_obj.booked_services_ids or []
            for item in raw_ids:
                if isinstance(item, dict):
                    for _, sub_id in item.items():
                        sub_b, _, _ = find_booking_by_id(sub_id)
                        if sub_b and hasattr(sub_b, 'status') and sub_b.status != 'cancelled':
                            sub_b.status = 'cancelled'
                            sub_b.save(update_fields=['status'])
                elif isinstance(item, str):
                    sub_b, _, _ = find_booking_by_id(item)
                    if sub_b and hasattr(sub_b, 'status') and sub_b.status != 'cancelled':
                        sub_b.status = 'cancelled'
                        sub_b.save(update_fields=['status'])

        # Prepare standardized representation
        data_item = serialize_admin_booking_item(booking_obj, svc_type)
        data_item.pop('_sort_created_at', None)
        data_item.pop('_sort_datetime', None)

        return Response({
            "success": True,
            "cancellation_allowed": True,
            "message": f"Booking '{booking_obj.booking_id}' has been cancelled successfully.{restore_info}",
            "booking_id": booking_obj.booking_id,
            "status": "cancelled",
            "payment_status": getattr(booking_obj, 'payment_status', None),
            "credit_restored": credit_restored,
            "remaining_sessions": remaining_sessions,
            "hours_until_start": round(hours_until_start, 2),
            "data": data_item
        }, status=status.HTTP_200_OK)
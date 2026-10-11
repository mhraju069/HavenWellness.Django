from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, PackageBooking, SaltRoomBooking
from .serializers import (
    SaunaBookingSerializer,
    LunchroomBookingSerializer,
    ActivityBookingSerializer,
    EventBookingSerializer,
    PackageBookingSerializer,
    SaltRoomBookingSerializer,
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
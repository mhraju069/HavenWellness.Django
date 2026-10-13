import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import PaymentIntent, Customer, Subscription, Event

from .helper import send_booking_confirmation_email
from .models import Payments, ClientPurchase, SessionPass, SubscriptionPlans
from bookings.models import SaunaBooking, ActivityBooking, PackageBooking, SaltRoomBooking
from .serializers import (
    PaymentsSerializer,
    CreatePaymentIntentRequestSerializer,
    CreatePaymentIntentResponseSerializer,
    PaymentMessageResponseSerializer,
    SessionPassSerializer,
    SubscriptionPlansSerializer,
    PurchaseRequestSerializer,
    ClientPurchaseSerializer,
)


def create_payment_intent_for_booking(booking, currency="eur", payment_method=None):
    price = float(booking.total_price)
    amount_cents = int(round(price * 100))
    if amount_cents <= 0:
        return None, None, None

    # Resolve payment_method_types for Stripe
    # Allow ["card", "ideal"] so frontend can confirm either card or iDEAL smoothly
    if payment_method == "ideal":
        pm_types = ["ideal", "card"]
    elif payment_method in ("card", None, ""):
        pm_types = ["card", "ideal"]
    else:
        pm_types = ["card", "ideal"]

    # Detect booking type
    if hasattr(booking, 'purchase_type'):
        if booking.purchase_type == 'session_pass':
            booking_type_val = 'session_pass'
            booking_label = 'Session Pass'
        else:
            booking_type_val = 'subscription'
            booking_label = 'Subscription'
    elif hasattr(booking, 'start_time') and hasattr(booking, 'date') and (hasattr(booking, 'used_pass') or booking.booking_id.startswith('SR-')):
        booking_type_val = 'saltroom'
        booking_label = 'Saltroom'
    elif hasattr(booking, 'booked_services_ids') or booking.booking_id.startswith('PKG-'):
        booking_type_val = 'packages'
        booking_label = 'Package'
    elif hasattr(booking, 'activity') or booking.booking_id.startswith('ACT-'):
        booking_type_val = 'activities'
        booking_label = 'Activity'
    elif hasattr(booking, 'celebration_type') or booking.booking_id.startswith('LR-'):
        booking_type_val = 'lunchroom'
        booking_label = 'Lunchroom'
    else:
        booking_type_val = 'sauna'
        booking_label = 'Sauna'

    djstripe_customer = None
    if booking.user:
        djstripe_customer = Customer.objects.filter(subscriber=booking.user).first()
    if not djstripe_customer and booking.email:
        djstripe_customer = Customer.objects.filter(email=booking.email).first()
    if not djstripe_customer and booking.email:
        try:
            cust_data = Customer._api_create(email=booking.email, name=booking.name)
            djstripe_customer = Customer.sync_from_stripe_data(cust_data)
            if booking.user:
                djstripe_customer.subscriber = booking.user
                djstripe_customer.save()
        except Exception as cust_err:
            print("djstripe Customer creation warning:", cust_err)

    metadata = {
        'booking_id': booking.booking_id,
        'booking_type': booking_type_val,
        'customer_email': booking.email,
        'customer_name': booking.name,
    }
    if booking_type_val == 'session_pass':
        metadata['purchase_id'] = booking.booking_id
        if getattr(booking, 'session_pass', None):
            metadata['pass_name'] = booking.session_pass.name
    elif booking_type_val == 'subscription':
        metadata['purchase_id'] = booking.booking_id
        if getattr(booking, 'subscription_plan', None):
            metadata['plan_name'] = booking.subscription_plan.name
            metadata['plan_type'] = booking.subscription_plan.plan_type
            metadata['plan_category'] = booking.subscription_plan.plan_category
    elif booking_type_val == 'saltroom':
        metadata['saltroom_booking_id'] = str(booking.id)
    elif booking_type_val == 'activities':
        metadata['activity_booking_id'] = str(booking.id)
        if hasattr(booking, 'activity') and booking.activity:
            metadata['activity_title'] = booking.activity.title
    elif booking_type_val == 'lunchroom':
        metadata['lunchroom_booking_id'] = str(booking.id)
    else:
        metadata['sauna_booking_id'] = str(booking.id)

    intent_kwargs = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "payment_method_types": pm_types,
        "metadata": metadata,
        "description": f"Payment for {booking_label} Booking {booking.booking_id}",
    }
    if djstripe_customer:
        intent_kwargs["customer"] = djstripe_customer.id

    intent_stripe_obj = PaymentIntent._api_create(**intent_kwargs)
    PaymentIntent.sync_from_stripe_data(intent_stripe_obj)

    intent_id = intent_stripe_obj.id
    client_secret = getattr(intent_stripe_obj, 'client_secret', '')

    payment, created = Payments.objects.get_or_create(
        booking_id=booking.booking_id,
        defaults={
            'booking_type': booking_type_val,
            'client': booking.user if booking.user else None,
            'amount': booking.total_price,
            'currency': currency.lower(),
            'payment_status': 'pending',
            'stripe_payment_intent_id': intent_id,
            'client_secret': client_secret,
        }
    )
    if not created:
        payment.booking_type = booking_type_val
        if booking.user:
            payment.client = booking.user
        payment.amount = booking.total_price
        payment.currency = currency.lower()
        payment.stripe_payment_intent_id = intent_id
        payment.client_secret = client_secret
        payment.payment_status = 'pending'
        payment.save()

    return payment, client_secret, intent_id


@extend_schema(
    tags=['Payments'],
    summary="Create Stripe PaymentIntent for Sauna Booking using dj-stripe",
    request=CreatePaymentIntentRequestSerializer,
    responses={
        200: CreatePaymentIntentResponseSerializer,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    }
)
class CreatePaymentIntentAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CreatePaymentIntentRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        booking_id_input = serializer.validated_data.get('booking_id')
        currency = serializer.validated_data.get('currency', 'eur')
        payment_method = request.data.get('payment_method') or serializer.validated_data.get('payment_method')

        booking = (
            SaunaBooking.objects.filter(booking_id=booking_id_input).first()
            or SaltRoomBooking.objects.filter(booking_id=booking_id_input).first()
            or ActivityBooking.objects.filter(booking_id=booking_id_input).first()
            or PackageBooking.objects.filter(booking_id=booking_id_input).first()
            or ClientPurchase.objects.filter(purchase_id=booking_id_input).first()
        )
        if not booking and booking_id_input.isdigit():
            booking = (
                SaunaBooking.objects.filter(id=int(booking_id_input)).first()
                or SaltRoomBooking.objects.filter(id=int(booking_id_input)).first()
                or ActivityBooking.objects.filter(id=int(booking_id_input)).first()
                or ClientPurchase.objects.filter(id=int(booking_id_input)).first()
            )

        if not booking:
            return Response({"error": f"Booking or purchase with ID '{booking_id_input}' not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment, client_secret, intent_id = create_payment_intent_for_booking(
                booking, currency=currency, payment_method=payment_method
            )
            return Response({
                "success": True,
                "client_secret": client_secret,
                "payment_intent_id": intent_id,
                "booking_id": booking.booking_id,
                "amount": booking.total_price,
                "currency": currency.lower()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Payments'],
    summary="List all Session Passes",
    responses={200: SessionPassSerializer(many=True)}
)
class SessionPassListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        passes = SessionPass.objects.all().order_by('id')
        serializer = SessionPassSerializer(passes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Payments'],
    summary="List all Subscription Plans",
    parameters=[
        OpenApiParameter(name='plan_type', type=str, location=OpenApiParameter.QUERY, description="Filter by plan_type: weekly, unlimited"),
        OpenApiParameter(name='plan_category', type=str, location=OpenApiParameter.QUERY, description="Filter by plan_category: sauna, saltroom"),
    ],
    responses={200: SubscriptionPlansSerializer(many=True)}
)
class SubscriptionPlanListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = SubscriptionPlans.objects.all().order_by('id')
        plan_type = request.query_params.get('plan_type')
        plan_category = request.query_params.get('plan_category')
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        if plan_category:
            queryset = queryset.filter(plan_category=plan_category)
        serializer = SubscriptionPlansSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Payments'],
    summary="List all available Plans & Passes (Session Passes and Subscription Plans combined)",
    responses={200: OpenApiTypes.OBJECT}
)
class AllPlansAndPassesListAPIView(APIView):
    """
    Returns all session passes and subscription plans in one response so the frontend
    can render all available pricing tiers/plans in a single request.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        passes = SessionPass.objects.all().order_by('id')
        plans = SubscriptionPlans.objects.all().order_by('id')

        return Response({
            "session_passes": SessionPassSerializer(passes, many=True).data,
            "subscription_plans": SubscriptionPlansSerializer(plans, many=True).data,
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Payments'],
    summary="Purchase a Session Pass or Subscription Plan with automatic Stripe PaymentIntent generation",
    request=PurchaseRequestSerializer,
    responses={
        201: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
    }
)
class PurchasePassOrPlanAPIView(APIView):
    """
    Unified API for purchasing either a Session Pass or a Subscription Plan.
    Requires user to be logged in (IsAuthenticated).
    Creates a ClientPurchase record associated with the user and generates a Stripe PaymentIntent.
    Frontend can directly use `client_secret` to confirm card payment via Stripe Elements/SDK.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PurchaseRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        purchase_type = data['purchase_type']
        user = request.user

        name = data.get('name') or getattr(user, 'name', '') or user.email
        email = data.get('email') or user.email
        phone = data.get('phone') or getattr(user, 'phone', '') or ''
        currency = data.get('currency', 'eur').lower()

        session_pass_obj = None
        subscription_plan_obj = None

        if purchase_type == 'session_pass':
            pass_id = data.get('pass_id')
            session_pass_obj = SessionPass.objects.filter(id=pass_id).first()
            if not session_pass_obj:
                return Response({"error": f"Session pass #{pass_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            price = session_pass_obj.price
        else:
            plan_id = data.get('plan_id')
            subscription_plan_obj = SubscriptionPlans.objects.filter(id=plan_id).first()
            if not subscription_plan_obj:
                return Response({"error": f"Subscription plan #{plan_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            price = subscription_plan_obj.price

        purchase = ClientPurchase.objects.create(
            user=user,
            purchase_type=purchase_type,
            session_pass=session_pass_obj,
            subscription_plan=subscription_plan_obj,
            name=name,
            email=email,
            phone=phone,
            amount=price,
            currency=currency,
            status='pending',
            payment_status='pending',
        )

        client_secret = None
        intent_id = None
        try:
            payment, client_secret, intent_id = create_payment_intent_for_booking(purchase, currency=currency)
        except Exception as e:
            print("Auto PaymentIntent creation error for purchase:", e)
            return Response({
                "success": False,
                "error": f"Failed to generate payment intent: {str(e)}",
                "purchase_id": purchase.purchase_id,
            }, status=status.HTTP_400_BAD_REQUEST)

        purchase_details = ClientPurchaseSerializer(purchase).data

        item_title = session_pass_obj.name if session_pass_obj else subscription_plan_obj.name

        return Response({
            "success": True,
            "purchase_id": purchase.purchase_id,
            "purchase_type": purchase.purchase_type,
            "item_name": item_title,
            "amount": purchase.amount,
            "currency": purchase.currency,
            "start_date": purchase.start_date,
            "end_date": purchase.end_date,
            "total_sessions": purchase.total_sessions,
            "remaining_sessions": purchase.remaining_sessions,
            "sessions_per_week": purchase.sessions_per_week,
            "max_active_reservations": purchase.max_active_reservations,
            "client_secret": client_secret,
            "payment_intent_id": intent_id,
            "data": purchase_details,
            "message": f"{purchase.get_purchase_type_display()} purchase initiated successfully. Proceed with Stripe payment using client_secret.",
        }, status=status.HTTP_201_CREATED)


def confirm_package_sub_bookings(package_booking):
    """
    When a PackageBooking is marked as paid/confirmed, also confirm and mark as paid
    all the included sub-bookings (SaltRoom, Sauna, Lunchroom, Activity).
    """
    from bookings.models import SaunaBooking, LunchroomBooking, ActivityBooking, SaltRoomBooking
    raw_ids = package_booking.booked_services_ids or []
    pkg_amount = package_booking.total_price or 0
    for item in raw_ids:
        if isinstance(item, dict):
            for s_type, ref_id in item.items():
                try:
                    if ref_id.startswith('SR-'):
                        SaltRoomBooking.objects.filter(booking_id=ref_id).update(
                            status='confirmed',
                            payment_status='paid_with_package',
                            is_paid=True,
                            total_price=pkg_amount
                        )
                    elif ref_id.startswith(('PS-', 'SS-', 'SB-')):
                        SaunaBooking.objects.filter(booking_id=ref_id).update(
                            status='confirmed',
                            payment_status='paid_with_package',
                            total_price=pkg_amount
                        )
                    elif ref_id.startswith('LR-'):
                        LunchroomBooking.objects.filter(booking_id=ref_id).update(
                            status='confirmed_with_package'
                        )
                    elif ref_id.startswith('ACT-'):
                        ActivityBooking.objects.filter(booking_id=ref_id).update(
                            status='confirmed',
                            payment_status='paid_with_package',
                            total_price=pkg_amount
                        )
                except Exception as sub_err:
                    print(f"Warning updating sub-booking {ref_id}:", sub_err)


class ConfirmPaymentAPIView(APIView):
    """
    Direct payment confirmation endpoint.
    Frontend can call this right after stripe.confirmCardPayment succeeds to instantly verify
    and update ClientPurchase / Booking and Payments status to 'paid' and 'confirmed'
    without waiting for or relying on local webhooks.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        payment_intent_id = request.data.get('payment_intent_id') or request.data.get('intent_id')
        purchase_id = request.data.get('purchase_id') or request.data.get('booking_id')

        if not payment_intent_id and not purchase_id:
            return Response(
                {"error": "Either payment_intent_id or purchase_id/booking_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Lookup payment record
        payment = None
        if payment_intent_id:
            payment = Payments.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
        if not payment and purchase_id:
            payment = Payments.objects.filter(booking_id=purchase_id).first()

        # 2. Retrieve live status from Stripe
        stripe_status = None
        stripe_intent_id = payment_intent_id or (payment.stripe_payment_intent_id if payment else None)

        if stripe_intent_id:
            try:
                pi_obj = PaymentIntent.objects.filter(id=stripe_intent_id).first()
                if pi_obj:
                    live_pi = pi_obj.api_retrieve()
                    stripe_status = live_pi.get('status')
                else:
                    live_pi = PaymentIntent.api_retrieve(stripe_intent_id)
                    stripe_status = live_pi.get('status')
            except Exception as e:
                # Direct stripe fallback if djstripe method fails
                try:
                    import stripe
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    pi_stripe = stripe.PaymentIntent.retrieve(stripe_intent_id)
                    stripe_status = pi_stripe.get('status')
                except Exception as ex:
                    print("Direct Stripe verify warning:", ex)

        is_paid = stripe_status in ['succeeded', 'processing']

        target_id = purchase_id or (payment.booking_id if payment else None)

        # 3. Update payment record
        if payment and is_paid:
            payment.payment_status = 'paid'
            payment.transaction_id = stripe_intent_id
            payment.save()

        # 4. Update booking/purchase object
        booking_obj = None
        if target_id:
            booking_obj = (
                ClientPurchase.objects.filter(purchase_id=target_id).first()
                or SaunaBooking.objects.filter(booking_id=target_id).first()
                or SaltRoomBooking.objects.filter(booking_id=target_id).first()
                or ActivityBooking.objects.filter(booking_id=target_id).first()
                or PackageBooking.objects.filter(booking_id=target_id).first()
            )

        if booking_obj:
            if is_paid:
                booking_obj.payment_status = 'paid'
                booking_obj.status = 'confirmed'
                if hasattr(booking_obj, 'is_paid'):
                    booking_obj.is_paid = True
                booking_obj.save()

                # If ClientPurchase is paid, also confirm any linked SaltRoomBooking and deduct 1 session
                if isinstance(booking_obj, ClientPurchase):
                    linked_sr_booking = SaltRoomBooking.objects.filter(client_purchase=booking_obj, payment_status='pending').first()
                    if linked_sr_booking:
                        linked_sr_booking.payment_status = 'paid'
                        linked_sr_booking.status = 'confirmed'
                        linked_sr_booking.is_paid = True
                        linked_sr_booking.save()
                        # Deduct session if not unlimited
                        if booking_obj.subscription_plan and booking_obj.subscription_plan.plan_type != 'unlimited':
                            booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                            booking_obj.save(update_fields=['remaining_sessions'])
                        elif booking_obj.purchase_type == 'session_pass':
                            booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                            booking_obj.save(update_fields=['remaining_sessions'])
                        try:
                            send_booking_confirmation_email(linked_sr_booking)
                        except Exception as sr_mail_err:
                            print("Linked Saltroom confirmation email error:", sr_mail_err)

                # If SaltRoomBooking is paid and has linked ClientPurchase pending, confirm purchase too
                elif isinstance(booking_obj, SaltRoomBooking) and booking_obj.client_purchase:
                    cp = booking_obj.client_purchase
                    if cp.payment_status == 'pending':
                        cp.payment_status = 'paid'
                        cp.status = 'confirmed'
                        if cp.subscription_plan and cp.subscription_plan.plan_type != 'unlimited':
                            cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                        elif cp.purchase_type == 'session_pass':
                            cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                        cp.save()

                elif isinstance(booking_obj, PackageBooking):
                    confirm_package_sub_bookings(booking_obj)

                try:
                    send_booking_confirmation_email(booking_obj)
                except Exception as mail_err:
                    print("Confirmation email error:", mail_err)

            return Response({
                "success": is_paid,
                "status": booking_obj.status,
                "payment_status": booking_obj.payment_status,
                "purchase_id": target_id,
                "stripe_status": stripe_status,
                "message": "Payment verified and booking confirmed successfully." if is_paid else f"Payment status is {stripe_status}."
            }, status=status.HTTP_200_OK if is_paid else status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": is_paid,
            "stripe_status": stripe_status,
            "message": "Payment verified."
        }, status=status.HTTP_200_OK if is_paid else status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Payments'],
    summary="Payment success callback status",
    responses={200: PaymentMessageResponseSerializer}
)
class PaymentSuccessView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PaymentMessageResponseSerializer

    def get(self, request):
        ref = request.query_params.get('ref') or request.query_params.get('booking_id')
        payment_intent_id = request.query_params.get('payment_intent') or request.query_params.get('payment_intent_id')

        if ref or payment_intent_id:
            payment = None
            if payment_intent_id:
                payment = Payments.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
            if not payment and ref:
                payment = Payments.objects.filter(booking_id=ref).first()

            target_id = ref or (payment.booking_id if payment else None)

            # Check live stripe
            stripe_intent_id = payment_intent_id or (payment.stripe_payment_intent_id if payment else None)
            is_paid = True
            if stripe_intent_id:
                try:
                    import stripe
                    stripe.api_key = settings.STRIPE_SECRET_KEY
                    pi_stripe = stripe.PaymentIntent.retrieve(stripe_intent_id)
                    is_paid = pi_stripe.get('status') in ['succeeded', 'processing']
                except Exception:
                    pass

            if payment and is_paid:
                payment.payment_status = 'paid'
                payment.transaction_id = stripe_intent_id
                payment.save()

            if target_id and is_paid:
                booking_obj = (
                    ClientPurchase.objects.filter(purchase_id=target_id).first()
                    or SaunaBooking.objects.filter(booking_id=target_id).first()
                    or SaltRoomBooking.objects.filter(booking_id=target_id).first()
                    or ActivityBooking.objects.filter(booking_id=target_id).first()
                    or PackageBooking.objects.filter(booking_id=target_id).first()
                )
                if booking_obj:
                    booking_obj.payment_status = 'paid'
                    booking_obj.status = 'confirmed'
                    booking_obj.save()
                    if isinstance(booking_obj, PackageBooking):
                        confirm_package_sub_bookings(booking_obj)
                    send_booking_confirmation_email(booking_obj)

        return Response({"message": "Payment successful! Your booking is confirmed."})


@extend_schema(
    tags=['Payments'],
    summary="Payment cancel callback status",
    responses={200: PaymentMessageResponseSerializer}
)
class PaymentCancelView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PaymentMessageResponseSerializer

    def get(self, request):
        return Response({"message": "Payment cancelled."})


@extend_schema(
    tags=['Payments'],
    summary="Stripe Webhook Handler (dj-stripe integrated)",
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.STR, 400: OpenApiTypes.STR}
)
@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            return HttpResponse(f"Webhook Invalid Payload: {str(e)}", status=status.HTTP_400_BAD_REQUEST)

        try:
            Event.sync_from_stripe_data(payload)
        except Exception:
            pass

        event_type = payload.get('type')
        stripe_obj = payload.get('data', {}).get('object', {})

        if event_type in ['payment_intent.succeeded', 'checkout.session.completed', 'charge.succeeded']:
            intent_id = stripe_obj.get('id')
            metadata = stripe_obj.get('metadata', {})
            booking_id = metadata.get('booking_id') or metadata.get('booking')

            payment = None
            if intent_id:
                payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
            if not payment and booking_id:
                payment = Payments.objects.filter(booking_id=booking_id).first()

            if payment:
                payment.payment_status = 'paid'
                payment.transaction_id = intent_id
                payment.save()

            target_booking_id = booking_id or (payment.booking_id if payment else None)
            if target_booking_id:
                booking_obj = (
                    SaunaBooking.objects.filter(booking_id=target_booking_id).first()
                    or SaltRoomBooking.objects.filter(booking_id=target_booking_id).first()
                    or ActivityBooking.objects.filter(booking_id=target_booking_id).first()
                    or PackageBooking.objects.filter(booking_id=target_booking_id).first()
                    or ClientPurchase.objects.filter(purchase_id=target_booking_id).first()
                )
                if booking_obj:
                    booking_obj.payment_status = 'paid'
                    booking_obj.status = 'confirmed'
                    if hasattr(booking_obj, 'is_paid'):
                        booking_obj.is_paid = True
                    booking_obj.save()

                    # Handle linked SaltRoomBooking / ClientPurchase
                    if isinstance(booking_obj, ClientPurchase):
                        linked_sr = SaltRoomBooking.objects.filter(client_purchase=booking_obj, payment_status='pending').first()
                        if linked_sr:
                            linked_sr.payment_status = 'paid'
                            linked_sr.status = 'confirmed'
                            linked_sr.is_paid = True
                            linked_sr.save()
                            if booking_obj.subscription_plan and booking_obj.subscription_plan.plan_type != 'unlimited':
                                booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                                booking_obj.save(update_fields=['remaining_sessions'])
                            elif booking_obj.purchase_type == 'session_pass':
                                booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                                booking_obj.save(update_fields=['remaining_sessions'])
                            try:
                                send_booking_confirmation_email(linked_sr)
                            except Exception:
                                pass
                    elif isinstance(booking_obj, SaltRoomBooking) and booking_obj.client_purchase:
                        cp = booking_obj.client_purchase
                        if cp.payment_status == 'pending':
                            cp.payment_status = 'paid'
                            cp.status = 'confirmed'
                            if cp.subscription_plan and cp.subscription_plan.plan_type != 'unlimited':
                                cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                            elif cp.purchase_type == 'session_pass':
                                cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                            cp.save()
                    elif isinstance(booking_obj, PackageBooking):
                        confirm_package_sub_bookings(booking_obj)

                    send_booking_confirmation_email(booking_obj)

        elif event_type in ['payment_intent.payment_failed']:
            intent_id = stripe_obj.get('id')
            if intent_id:
                payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
                if payment:
                    payment.payment_status = 'failed'
                    payment.save()
            metadata = stripe_obj.get('metadata', {})
            booking_id = metadata.get('booking_id') or metadata.get('booking')
            target_booking_id = booking_id or (payment.booking_id if payment else None)
            if target_booking_id:
                booking_obj = (
                    ClientPurchase.objects.filter(purchase_id=target_booking_id).first()
                    or SaltRoomBooking.objects.filter(booking_id=target_booking_id).first()
                )
                if booking_obj:
                    booking_obj.payment_status = 'failed'
                    booking_obj.save()

        return HttpResponse(status=status.HTTP_200_OK)


@djstripe_receiver("payment_intent.succeeded")
def handle_djstripe_payment_succeeded(event, **kwargs):
    payment_intent = event.data.get("object", {})
    intent_id = payment_intent.get("id")
    metadata = payment_intent.get("metadata", {})
    booking_id = metadata.get("booking_id") or metadata.get("booking")

    payment = None
    if intent_id:
        payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
    if not payment and booking_id:
        payment = Payments.objects.filter(booking_id=booking_id).first()

    if payment:
        payment.payment_status = 'paid'
        payment.transaction_id = intent_id
        payment.save()

    target_booking_id = booking_id or (payment.booking_id if payment else None)
    if target_booking_id:
        booking_obj = (
            SaunaBooking.objects.filter(booking_id=target_booking_id).first()
            or SaltRoomBooking.objects.filter(booking_id=target_booking_id).first()
            or ActivityBooking.objects.filter(booking_id=target_booking_id).first()
            or PackageBooking.objects.filter(booking_id=target_booking_id).first()
            or ClientPurchase.objects.filter(purchase_id=target_booking_id).first()
        )
        if booking_obj:
            booking_obj.payment_status = 'paid'
            booking_obj.status = 'confirmed'
            if hasattr(booking_obj, 'is_paid'):
                booking_obj.is_paid = True
            booking_obj.save()

            if isinstance(booking_obj, ClientPurchase):
                linked_sr = SaltRoomBooking.objects.filter(client_purchase=booking_obj, payment_status='pending').first()
                if linked_sr:
                    linked_sr.payment_status = 'paid'
                    linked_sr.status = 'confirmed'
                    linked_sr.is_paid = True
                    linked_sr.save()
                    if booking_obj.subscription_plan and booking_obj.subscription_plan.plan_type != 'unlimited':
                        booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                        booking_obj.save(update_fields=['remaining_sessions'])
                    elif booking_obj.purchase_type == 'session_pass':
                        booking_obj.remaining_sessions = max(0, booking_obj.remaining_sessions - 1)
                        booking_obj.save(update_fields=['remaining_sessions'])
                    try:
                        send_booking_confirmation_email(linked_sr)
                    except Exception:
                        pass
            elif isinstance(booking_obj, SaltRoomBooking) and booking_obj.client_purchase:
                cp = booking_obj.client_purchase
                if cp.payment_status == 'pending':
                    cp.payment_status = 'paid'
                    cp.status = 'confirmed'
                    if cp.subscription_plan and cp.subscription_plan.plan_type != 'unlimited':
                        cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                    elif cp.purchase_type == 'session_pass':
                        cp.remaining_sessions = max(0, cp.remaining_sessions - 1)
                    cp.save()

            send_booking_confirmation_email(booking_obj)



@djstripe_receiver("payment_intent.payment_failed")
def handle_djstripe_payment_failed(event, **kwargs):
    payment_intent = event.data.get("object", {})
    intent_id = payment_intent.get("id")
    metadata = payment_intent.get("metadata", {})
    booking_id = metadata.get("booking_id") or metadata.get("booking")
    payment = None
    if intent_id:
        payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
        if payment:
            payment.payment_status = 'failed'
            payment.save()
    target_booking_id = booking_id or (payment.booking_id if payment else None)
    if target_booking_id:
        booking_obj = ClientPurchase.objects.filter(purchase_id=target_booking_id).first()
        if booking_obj:
            booking_obj.payment_status = 'failed'
            booking_obj.save()
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
from .models import Payments
from bookings.models import SaunaBooking
from .serializers import (
    PaymentsSerializer,
    CreatePaymentIntentRequestSerializer,
    CreatePaymentIntentResponseSerializer,
    PaymentMessageResponseSerializer,
)


def create_payment_intent_for_booking(booking, currency="eur"):
    price = float(booking.total_price)
    amount_cents = int(round(price * 100))
    if amount_cents <= 0:
        return None, None, None

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

    intent_kwargs = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "metadata": {
            'booking_id': booking.booking_id,
            'sauna_booking_id': str(booking.id),
            'customer_email': booking.email,
            'customer_name': booking.name,
        },
        "description": f"Payment for Sauna Booking {booking.booking_id}",
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
            'booking_type': 'sauna',
            'client': booking.user if booking.user else None,
            'amount': booking.total_price,
            'currency': currency.lower(),
            'payment_status': 'pending',
            'stripe_payment_intent_id': intent_id,
            'client_secret': client_secret,
        }
    )
    if not created:
        payment.booking_type = 'sauna'
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

        booking = SaunaBooking.objects.filter(booking_id=booking_id_input).first()
        if not booking and booking_id_input.isdigit():
            booking = SaunaBooking.objects.filter(id=int(booking_id_input)).first()

        if not booking:
            return Response({"error": f"Booking with ID '{booking_id_input}' not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment, client_secret, intent_id = create_payment_intent_for_booking(booking, currency=currency)
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
    summary="Payment success callback status",
    responses={200: PaymentMessageResponseSerializer}
)
class PaymentSuccessView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PaymentMessageResponseSerializer

    def get(self, request):
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
                booking_obj = SaunaBooking.objects.filter(booking_id=target_booking_id).first()
                if booking_obj:
                    booking_obj.payment_status = 'paid'
                    booking_obj.status = 'confirmed'
                    booking_obj.save()
                    send_booking_confirmation_email(booking_obj)

        elif event_type in ['payment_intent.payment_failed']:
            intent_id = stripe_obj.get('id')
            if intent_id:
                payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
                if payment:
                    payment.payment_status = 'failed'
                    payment.save()

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
        booking_obj = SaunaBooking.objects.filter(booking_id=target_booking_id).first()
        if booking_obj:
            booking_obj.payment_status = 'paid'
            booking_obj.status = 'confirmed'
            booking_obj.save()
            send_booking_confirmation_email(booking_obj)


@djstripe_receiver("payment_intent.payment_failed")
def handle_djstripe_payment_failed(event, **kwargs):
    payment_intent = event.data.get("object", {})
    intent_id = payment_intent.get("id")
    if intent_id:
        payment = Payments.objects.filter(stripe_payment_intent_id=intent_id).first()
        if payment:
            payment.payment_status = 'failed'
            payment.save()
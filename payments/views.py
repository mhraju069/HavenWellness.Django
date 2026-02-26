import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Payments
from .serializers import PaymentSerializer
from .helper import create_payment_intent_data
from bookings.models import Booking

# Create your views here.

class GetPaymentLinkView(APIView):
    
    def post(self, request):
        method = request.query_params.get("method", "web")
        booking_id = request.data.get("booking_id")
        
        if not booking_id:
            return Response({"error": "Booking ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        # Payment record search or create
        payment = Payments.objects.create(
            booking=booking,
            client=booking.user,
            service=booking.service,
            amount=float(booking.total_amount),
            payment_status='pending'
        )

        # Payment link or secret data creation
        payment_data = create_payment_intent_data(
            request, 
            booking=booking.id, 
            payment=payment.id, 
            price=float(payment.amount), 
            customer_email=booking.user.email,
            method=method
        )

        return Response({
            "status": True,
            "log": payment_data
        })


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'checkout.session.completed' or event['type'] == 'payment_intent.succeeded':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            booking_id = metadata.get('booking')
            payment_id = metadata.get('payment')
            transaction_id = session.get('id')

            if booking_id and payment_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    payment = Payments.objects.get(id=payment_id)
                    
                    # Update Payment details
                    payment.payment_status = 'paid'
                    payment.transaction_id = transaction_id
                    
                    # Get Invoice URL if available (Checkout sessions usually have this)
                    invoice_id = session.get('invoice')
                    if invoice_id:
                        try:
                            invoice = stripe.Invoice.retrieve(invoice_id)
                            payment.invoice_url = invoice.hosted_invoice_url
                        except Exception as inv_err:
                            print(f"Invoice link retrieval failed: {str(inv_err)}")

                    payment.save()
                    
                    booking.payment_status = 'paid'
                    booking.status = 'confirmed'
                    booking.save()
                    
                    print(f"Booking {booking_id} updated successfully")
                except Exception as e:
                    print(f"Data update failed: {str(e)}")

        return HttpResponse(status=status.HTTP_200_OK)
# import stripe
# import json
# from django.conf import settings
# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.utils.decorators import method_decorator
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

# from .models import Payments
# from .serializers import (
#     PaymentSerializer,
#     GetPaymentLinkRequestSerializer,
#     GetPaymentLinkResponseSerializer,
#     PaymentMessageResponseSerializer,
# )
# from .helper import create_payment_intent_data
# from bookings.models import Booking


# @extend_schema(
#     tags=['Payments'],
#     summary="Generate Stripe checkout payment link or payment intent for a booking",
#     parameters=[
#         OpenApiParameter("method", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Payment flow method ('web' or 'app')", default="web"),
#     ],
#     request=GetPaymentLinkRequestSerializer,
#     responses={
#         200: GetPaymentLinkResponseSerializer,
#         400: OpenApiTypes.OBJECT,
#         404: OpenApiTypes.OBJECT,
#     }
# )
# class GetPaymentLinkView(APIView):
#     serializer_class = GetPaymentLinkRequestSerializer

#     def post(self, request):
#         method = request.query_params.get("method", "web")
#         booking_id = request.data.get("booking_id")
        
#         if not booking_id:
#             return Response({"error": "Booking ID is required"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             booking = Booking.objects.get(id=booking_id)
#         except Booking.DoesNotExist:
#             return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

#         # Payment record search or create
#         payment = Payments.objects.create(
#             booking=booking,
#             client=booking.user,
#             service=booking.service,
#             amount=float(booking.price),
#             payment_status='pending'
#         )

#         try:
#             payment_data = create_payment_intent_data(
#                 request, 
#                 booking=booking.id, 
#                 payment=payment.id, 
#                 price=float(payment.amount), 
#                 customer_email=booking.user.email,
#                 method=method
#             )

#             return Response({
#                 "status": True,
#                 "log": payment_data
#             })
#         except Exception as e:
#             payment.delete()
#             return Response({
#                 "status": False,
#                 "error": str(e)
#             }, status=status.HTTP_400_BAD_REQUEST)


# @extend_schema(
#     tags=['Payments'],
#     summary="Payment success callback page",
#     responses={200: PaymentMessageResponseSerializer}
# )
# class PaymentSuccessView(APIView):
#     permission_classes = []
#     serializer_class = PaymentMessageResponseSerializer

#     def get(self, request):
#         return Response({"message": "Payment successful! Your booking is confirmed."})


# @extend_schema(
#     tags=['Payments'],
#     summary="Payment cancel callback page",
#     responses={200: PaymentMessageResponseSerializer}
# )
# class PaymentCancelView(APIView):
#     permission_classes = []
#     serializer_class = PaymentMessageResponseSerializer

#     def get(self, request):
#         return Response({"message": "Payment cancelled."})


# @extend_schema(
#     tags=['Payments'],
#     summary="Stripe Webhook handler",
#     request=OpenApiTypes.OBJECT,
#     responses={200: OpenApiTypes.STR, 400: OpenApiTypes.STR}
# )
# @method_decorator(csrf_exempt, name='dispatch')
# class StripeWebhookView(APIView):
#     permission_classes = []

#     def post(self, request):
#         payload = request.body
#         sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
#         endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

#         try:
#             event = stripe.Webhook.construct_event(
#                 payload, sig_header, endpoint_secret
#             ) if endpoint_secret else json.loads(payload.decode('utf-8'))
#         except ValueError as e:
#             return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

#         if event.get('type') in ['checkout.session.completed', 'payment_intent.succeeded', 'invoice.paid']:
#             stripe_obj = event['data']['object']
#             metadata = stripe_obj.get('metadata', {})
            
#             booking_id = metadata.get('booking')
#             payment_id = metadata.get('payment')
#             transaction_id = stripe_obj.get('id')

#             if booking_id and payment_id:
#                 try:
#                     booking = Booking.objects.get(id=booking_id)
#                     payment = Payments.objects.get(id=payment_id)
                    
#                     payment.payment_status = 'paid'
#                     payment.transaction_id = transaction_id
#                     payment.save()
                    
#                     booking.payment_status = 'paid'
#                     booking.status = 'confirmed'
#                     booking.save()
#                 except Exception as e:
#                     print("Webhook DB error:", e)

#         return HttpResponse(status=status.HTTP_200_OK)
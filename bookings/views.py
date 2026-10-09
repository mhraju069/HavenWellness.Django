from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import SaunaBooking
from .serializers import SaunaBookingSerializer
from payments.views import create_payment_intent_for_booking


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
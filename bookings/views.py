from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, PackageBooking
from .serializers import (
    SaunaBookingSerializer,
    LunchroomBookingSerializer,
    ActivityBookingSerializer,
    EventBookingSerializer,
    PackageBookingSerializer,
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
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Payments


class PaymentClientSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    email = serializers.EmailField()


class PaymentServiceSerializer(serializers.Serializer):
    name = serializers.CharField()
    duration = serializers.IntegerField()


class PaymentBookingSerializer(serializers.Serializer):
    booking_id = serializers.CharField()
    time_slot = serializers.CharField()
    booking_capacity = serializers.IntegerField()


class PaymentSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    booking = serializers.SerializerMethodField()

    class Meta:
        model = Payments
        fields = '__all__'

    @extend_schema_field(PaymentClientSerializer)
    def get_client(self, obj):
        if not obj.client:
            return None
        return {
            "name": obj.client.name or None,
            "email": obj.client.email,
        }

    @extend_schema_field(PaymentServiceSerializer)
    def get_service(self, obj):
        if not obj.service:
            return None
        return {
            "name": obj.service.title,
            "duration": obj.service.duration,
        }

    @extend_schema_field(PaymentBookingSerializer)
    def get_booking(self, obj):
        if not obj.booking:
            return None
        return {
            "booking_id": obj.booking.booking_id,
            "time_slot": str(obj.booking.time_slot),
            "booking_capacity": getattr(obj.booking, 'guests_count', 1),
        }


class GetPaymentLinkRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=True, help_text="ID of the booking to generate payment link for")


class GetPaymentLinkResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    log = serializers.JSONField(help_text="Stripe Payment Intent / Checkout Session URL or data")


class PaymentMessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import *


class SubscriptionPlanFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlanFeatures
        exclude = ['subscription_plan', 'created_at', 'updated_at']


class SubscriptionPlansSerializer(serializers.ModelSerializer):
    features = SubscriptionPlanFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlans
        exclude = ['created_at', 'updated_at']


class SessionPassFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionPassFeatures
        exclude = ['session_pass', 'created_at', 'updated_at']


class SessionPassSerializer(serializers.ModelSerializer):
    features = SessionPassFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = SessionPass
        exclude = ['created_at', 'updated_at']


class PaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = '__all__'


class CreatePaymentIntentRequestSerializer(serializers.Serializer):
    booking_id = serializers.CharField(help_text="Booking identifier, e.g., PS-0001 or SS-0001", required=True)
    currency = serializers.CharField(default="eur", required=False)


class CreatePaymentIntentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    client_secret = serializers.CharField()
    payment_intent_id = serializers.CharField()
    booking_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentMessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
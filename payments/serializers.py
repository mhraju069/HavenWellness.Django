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
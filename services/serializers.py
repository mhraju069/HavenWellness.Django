from services.models import Activities
from rest_framework import serializers
from .models import *
from payments.serializers import (
    SessionPassSerializer,
    SubscriptionPlansSerializer,
    ClientPurchaseSerializer,
) 


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = [
            'id', 'title', 'subtitle', 'description', 'image', 'type',
            'title_en', 'title_nl', 'title_de',
            'subtitle_en', 'subtitle_nl', 'subtitle_de',
            'description_en', 'description_nl', 'description_de',
        ]


#Activity services

class ActivitiesFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitiesFeature
        fields = ['id', 'feature']


class ActivitiesSerializer(serializers.ModelSerializer):
    features = ActivitiesFeatureSerializer(many=True, read_only=True)
    available_slots = serializers.SerializerMethodField()
    booked_slots = serializers.SerializerMethodField()

    class Meta:
        model = Activities
        exclude = ['created_at', 'updated_at']

    def get_booked_slots(self, obj):
        from bookings.models import ActivityBooking
        from django.db.models import Sum

        total_booked = ActivityBooking.objects.filter(
            activity=obj
        ).exclude(
            status='cancelled'
        ).aggregate(total=Sum('capacity'))['total'] or 0

        return total_booked

    def get_available_slots(self, obj):
        booked = self.get_booked_slots(obj)
        total_capacity = obj.capacity or 0
        return max(0, total_capacity - booked)


#Lunchroom services

class LunchroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lunchroom
        exclude = ['created_at', 'updated_at']


#Saltroom services

class SaltroomFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaltroomFeatures
        exclude = ['saltroom', 'created_at', 'updated_at']


class SaltroomSerializer(serializers.ModelSerializer):
    features = SaltroomFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = Saltroom
        exclude = ['created_at', 'updated_at']


#Sauna services

class PrivateSaunaFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivateSaunaFeatures
        exclude = ['sauna', 'created_at', 'updated_at']


class PrivateSaunaSerializer(serializers.ModelSerializer):
    features = PrivateSaunaFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = PrivateSauna
        exclude = ['created_at', 'updated_at']


class SharedSaunaFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedSaunaFeatures
        exclude = ['sauna', 'created_at', 'updated_at']


class SharedSaunaSerializer(serializers.ModelSerializer):
    features = SharedSaunaFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = SharedSauna
        exclude = ['created_at', 'updated_at']


class SaunaServiceSerializer(serializers.Serializer):
    private_sauna = PrivateSaunaSerializer(many=True, required=False)
    shared_sauna = SharedSaunaSerializer(many=True, required=False)


#Salt room

class SaltroomServiceSerializer(serializers.Serializer):
    saltroom = SaltroomSerializer(many=True, required=False)
    subscription_plans = SubscriptionPlansSerializer(many=True, required=False)
    session_pass = SessionPassSerializer(many=True, required=False)
    user_membership = serializers.DictField(required=False, allow_null=True)


#Package Services

class PackageFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageFeatures
        fields = ['id', 'feature']


class PackagesSerializer(serializers.ModelSerializer):
    features = PackageFeaturesSerializer(many=True, read_only=True)

    class Meta:
        model = Packages
        exclude = ['created_at', 'updated_at']
from services.models import Activities
from rest_framework import serializers
from .models import *
from payments.serializers import SessionPassSerializer, SubscriptionPlansSerializer 


class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        exclude = ['created_at', 'updated_at']



#Activity services

class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        exclude = ['created_at', 'updated_at']


class ActivitiesFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitiesFeature
        fields = ['id', 'feature']



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
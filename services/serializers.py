from services.models import Activities
from rest_framework import serializers
from .models import *


class SaunaSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaunaSeesion
        exclude = ['created_at', 'updated_at']

class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        exclude = ['created_at', 'updated_at']


class ActivitiesFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitiesFeature
        fields = ['id', 'feature']


class ActivitySessionSerializer(serializers.ModelSerializer):
    features = ActivitiesFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ActivitySession
        exclude = ['created_at', 'updated_at']


class AllServicesSerializer(serializers.Serializer):
    sauna_seesion = SaunaSessionSerializer(many=True, required=False)
    activity_session = ActivitiesSerializer(many=True, required=False)



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

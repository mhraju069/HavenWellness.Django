from services.models import Activities
from rest_framework import serializers
from .models import *


class SaunaSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaunaSeesion
        exclude = ['created_at', 'updated_at']

class ActivitySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        exclude = ['created_at', 'updated_at']


class AllServicesSerializer(serializers.Serializer):
    sauna_seesion = SaunaSessionSerializer(many=True, required=False)
    activity_session = ActivitySessionSerializer(many=True, required=False)



class PrivateSaunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivateSauna
        exclude = ['created_at', 'updated_at']


class SharedSaunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedSauna
        exclude = ['created_at', 'updated_at']


class SaunaServiceSerializer(serializers.Serializer):
    private_sauna = PrivateSaunaSerializer(many=True, required=False)
    shared_sauna = SharedSaunaSerializer(many=True, required=False)

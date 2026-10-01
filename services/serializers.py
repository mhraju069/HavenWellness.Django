from rest_framework import serializers
from .models import *

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


class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        fields = ['feature']


class ExcludeDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludeDate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


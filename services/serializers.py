from rest_framework import serializers
from .models import *



class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        fields = ['feature']


class ExcludeDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludeDate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


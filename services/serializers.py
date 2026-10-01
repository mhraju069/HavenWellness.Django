from rest_framework import serializers
from .models import *



class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        fields = ['feature']

class ServiceSerializer(serializers.ModelSerializer):
    features = ServiceFeatureSerializer(many=True, read_only=True)
    class Meta:
        model = Service
        fields = '__all__'

    def get_features(self, obj):
        return obj.features.all()


class ExcludeDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludeDate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


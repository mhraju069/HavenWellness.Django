from rest_framework import serializers
from .models import Service, ServiceImage, ServiceFeature

class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class ServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, read_only=True)
    features = ServiceFeatureSerializer(many=True, read_only=True)
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_images(self, obj):
        return obj.images.all()
    
    def get_features(self, obj):
        return obj.features.all()
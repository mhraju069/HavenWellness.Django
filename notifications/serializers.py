from rest_framework import serializers
from .models import Device, Notification


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ['user']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user']


class DeviceRegisterResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class NotificationListResponseSerializer(serializers.Serializer):
    notifications = NotificationSerializer(many=True)

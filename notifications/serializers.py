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
        fields = [
            'id',
            'title',
            'body',
            'notification_type',
            'audience',
            'link',
            'data',
            'is_read',
            'read_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']



class DeviceRegisterResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class NotificationListResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    notifications = NotificationSerializer(many=True)


class UnreadCountResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkReadResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    unread_count = serializers.IntegerField()
    updated_count = serializers.IntegerField(required=False)

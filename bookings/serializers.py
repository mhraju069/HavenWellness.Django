from rest_framework import serializers
from .models import *

class BookingSerializer(serializers.ModelSerializer):
    guests_count = serializers.IntegerField()
    access_code = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user']

    def validate(self, attrs):
        if attrs['time_slot'].available_capacity() < attrs['guests_count']:
            raise serializers.ValidationError(f"Not enough capacity.Available capacity {attrs['time_slot'].available_capacity()}")
        return attrs

    def create(self, validated_data):
        booking = Booking.objects.create(**validated_data)
        slot = validated_data['time_slot']
        slot.booked_capacity += validated_data['guests_count']
        slot.save()

        return booking

    def get_access_code(self,obj):
        service = obj.service
        if service.title == "private_sauna" or service.title == "shared_sauna":
            data = AccessCode.objects.get_or_create(booking=obj)
            return AccessCodeSerializer(data[0]).data
        return None


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    available_capacity = serializers.SerializerMethodField()
    time = serializers.CharField(source='get_time_display', read_only=True) 
    
    class Meta:
        model = TimeSlot
        fields = '__all__'

    def get_available_capacity(self, obj):
        return obj.available_capacity()


class AccessCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessCode
        fields = '__all__'

from rest_framework import serializers
from .models import *

class BookingSerializer(serializers.ModelSerializer):
    guests_count = serializers.IntegerField()

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user']

    def validate(self, attrs):
        if attrs['time_slot'].available_capacity() < attrs['guests_count']:
            raise serializers.ValidationError(f"Not enough capacity.Available capacity {attrs['time_slot'].available_capacity()}")
        return attrs

    def create(self, validated_data):
        print("validated_data 😊😊😊",validated_data)
        # validated_data['service'] = Service.objects.get(title=validated_data['service'])
        booking = Booking.objects.create(**validated_data)
        slot = validated_data['time_slot']
        slot.booked_capacity += validated_data['guests_count']
        slot.save()
        
        return booking


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    available_capacity = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = '__all__'

    def get_available_capacity(self, obj):
        return obj.available_capacity()


class AccessCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessCode
        fields = '__all__'

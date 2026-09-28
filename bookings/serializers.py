from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking, Slot, TimeSlot, AccessCode


class AccessCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessCode
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    guests_count = serializers.IntegerField(default=1, help_text="Number of guests for the booking")
    access_code = serializers.SerializerMethodField(help_text="Access code details if applicable for sauna services")

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user', 'booking_id']

    def validate(self, attrs):
        time_slot = attrs.get('time_slot')
        guests_count = attrs.get('guests_count', 1)
        if time_slot and time_slot.available_capacity() < guests_count:
            raise serializers.ValidationError({"guests_count": f"Not enough capacity. Available capacity is {time_slot.available_capacity()}"})
        return attrs

    def create(self, validated_data):
        booking = Booking.objects.create(**validated_data)
        slot = validated_data['time_slot']
        slot.booked_capacity += validated_data['guests_count']
        slot.save()
        return booking

    @extend_schema_field(AccessCodeSerializer)
    def get_access_code(self, obj):
        service = obj.service
        if service and service.title in ["private_sauna", "shared_sauna"]:
            data = AccessCode.objects.get_or_create(booking=obj)
            return AccessCodeSerializer(data[0]).data
        return None


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = '__all__'


class TimeSlotSerializer(serializers.ModelSerializer):
    available_capacity = serializers.SerializerMethodField(help_text="Remaining available capacity for the slot")
    time = serializers.CharField(source='get_time_display', read_only=True)

    class Meta:
        model = TimeSlot
        fields = '__all__'

    @extend_schema_field(serializers.IntegerField())
    def get_available_capacity(self, obj):
        return obj.available_capacity()

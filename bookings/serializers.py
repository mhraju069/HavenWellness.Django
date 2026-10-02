from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking, Slot, TimeSlot, AccessCode, UserMembership, UserSessionPass
from services.serializers import AddOnExtraSerializer, ServiceSerializer, MembershipPlanSerializer


class UserMembershipSerializer(serializers.ModelSerializer):
    plan_detail = MembershipPlanSerializer(source='plan', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserMembership
        fields = '__all__'
        read_only_fields = ['user', 'start_date', 'end_date', 'sessions_used_this_period']


class UserSessionPassSerializer(serializers.ModelSerializer):
    service_detail = ServiceSerializer(source='service', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserSessionPass
        fields = '__all__'
        read_only_fields = ['user', 'purchase_date', 'valid_until', 'remaining_sessions']


class AccessCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessCode
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    guests_count = serializers.IntegerField(default=1, help_text="Number of guests for the booking")
    access_code = serializers.SerializerMethodField(help_text="Access code details if applicable for sauna services")
    selected_extras_detail = AddOnExtraSerializer(source='selected_extras', many=True, read_only=True)

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
        time_slot = validated_data.get('time_slot')
        booking = Booking.objects.create(**validated_data)
        if time_slot:
            time_slot.booked_capacity += validated_data.get('guests_count', 1)
            time_slot.save()
        return booking

    @extend_schema_field(AccessCodeSerializer)
    def get_access_code(self, obj):
        service = obj.service
        service_type = obj.booking_type or (service.service_type if service else None)
        if service_type in ["private_sauna", "shared_sauna"]:
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


class AvailableTimeSlotSerializer(serializers.ModelSerializer):
    time = serializers.CharField(source='get_time_display', read_only=True)
    max_capacity = serializers.IntegerField(source='slot.max_capacity', read_only=True)
    booked_capacity = serializers.IntegerField(read_only=True)
    available_capacity = serializers.SerializerMethodField(help_text="Remaining available capacity for the slot")
    is_booked = serializers.SerializerMethodField(help_text="True if slot is fully booked")
    is_available = serializers.SerializerMethodField(help_text="True if slot has available capacity")

    class Meta:
        model = TimeSlot
        fields = [
            'id',
            'time',
            'date',
            'max_capacity',
            'booked_capacity',
            'available_capacity',
            'is_booked',
            'is_available',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_available_capacity(self, obj):
        return max(0, obj.slot.max_capacity - obj.booked_capacity)

    @extend_schema_field(serializers.BooleanField())
    def get_is_booked(self, obj):
        return obj.booked_capacity >= obj.slot.max_capacity

    @extend_schema_field(serializers.BooleanField())
    def get_is_available(self, obj):
        return (obj.slot.max_capacity - obj.booked_capacity) > 0

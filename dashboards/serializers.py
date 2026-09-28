from rest_framework import serializers
from services.models import ExcludeDate
from services.serializers import ServiceSerializer
from bookings.serializers import BookingSerializer

class DashboardExcludeDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludeDate
        fields = '__all__'


class DashboardSummaryResponseSerializer(serializers.Serializer):
    today_reservations = serializers.IntegerField()
    upcoming_reservations = serializers.IntegerField()
    active_codes = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    today_bookings_list = BookingSerializer(many=True)
    service_bookings_count = serializers.DictField(child=serializers.IntegerField())


class CapacityItemSerializer(serializers.Serializer):
    service = serializers.CharField()
    total_capacity = serializers.IntegerField()
    total_booked = serializers.IntegerField()
    total_available = serializers.IntegerField()


class CapacityListResponseSerializer(serializers.Serializer):
    services = ServiceSerializer(many=True)
    capacity = CapacityItemSerializer(many=True)


class ServiceStatsResponseSerializer(serializers.Serializer):
    total_services = serializers.IntegerField()
    total_active_services = serializers.IntegerField()
    total_capacity = serializers.IntegerField()
    average_price = serializers.FloatField()
    average_duration = serializers.FloatField()
    services = ServiceSerializer(many=True)
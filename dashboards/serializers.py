from rest_framework import serializers
from accounts.models import User


class BookingItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    booking_id = serializers.CharField()
    service_type = serializers.CharField()
    service_name = serializers.CharField()
    date = serializers.CharField()
    time = serializers.CharField()
    end_time = serializers.CharField(required=False, allow_null=True)
    guests = serializers.IntegerField(default=1)
    status = serializers.CharField()
    payment_status = serializers.CharField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    access_code = serializers.CharField(required=False, allow_null=True)
    details = serializers.DictField(required=False, default=dict)


class AccessCodeItemSerializer(serializers.Serializer):
    booking_id = serializers.CharField()
    access_code = serializers.CharField()
    sauna_type = serializers.CharField()
    date = serializers.CharField()
    time = serializers.CharField()
    time_slot = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    guests = serializers.IntegerField(default=1)
    details = serializers.DictField(required=False, default=dict)


class AccessCodeSectionSerializer(serializers.Serializer):
    private_sauna = AccessCodeItemSerializer(many=True)
    shared_sauna = AccessCodeItemSerializer(many=True)
    all_sauna = AccessCodeItemSerializer(many=True)


class ProfileSectionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    email = serializers.EmailField()
    phone = serializers.CharField(allow_null=True)
    image = serializers.CharField(allow_null=True)
    language = serializers.CharField()
    role = serializers.CharField()
    date_joined = serializers.DateTimeField()


class ClientPurchaseItemSerializer(serializers.Serializer):
    purchase_id = serializers.CharField()
    purchase_type = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    total_sessions = serializers.IntegerField()
    remaining_sessions = serializers.IntegerField()
    active_reservations_count = serializers.IntegerField(default=0, required=False)
    sessions_per_week = serializers.IntegerField()
    max_active_reservations = serializers.IntegerField()
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    payment_status = serializers.CharField()
    is_expired = serializers.BooleanField()
    details = serializers.DictField(required=False, default=dict)


class HomeSummaryMetricsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField(help_text="Overall total bookings count across all services (past + upcoming)")
    upcoming_bookings = serializers.IntegerField(help_text="Count of all upcoming bookings")
    upcoming_booking_dates = serializers.ListField(child=serializers.CharField(), help_text="List of upcoming visit dates (YYYY-MM-DD)")
    active_subscriptions = serializers.IntegerField(help_text="Count of active subscriptions & passes")
    upcoming_saunas = serializers.IntegerField(help_text="Count of upcoming sauna bookings")


class HomeSectionSerializer(serializers.Serializer):
    metrics = HomeSummaryMetricsSerializer()
    next_visit = BookingItemSerializer(allow_null=True, help_text="Immediate next upcoming booking/event")
    subscriptions_and_passes = ClientPurchaseItemSerializer(many=True, help_text="List of active subscriptions, memberships and passes")
    next_visits = BookingItemSerializer(many=True, help_text="Next 5 upcoming visits after the immediate next visit")
    other_upcoming_visits = BookingItemSerializer(many=True, help_text="All other upcoming visits")


class MyBookingsSectionSerializer(serializers.Serializer):
    upcoming = BookingItemSerializer(many=True)
    past = BookingItemSerializer(many=True)


class UserDashboardResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    home = HomeSectionSerializer()
    my_bookings = MyBookingsSectionSerializer()
    access_codes = AccessCodeSectionSerializer()
    profile = ProfileSectionSerializer()
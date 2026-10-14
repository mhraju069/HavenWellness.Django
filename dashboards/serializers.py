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


class AdminBookingItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    booking_id = serializers.CharField(help_text="Unique booking reference, e.g. PS-0001, SR-0002")
    service_type = serializers.CharField(help_text="Type of service: sauna, lunchroom, activity, saltroom, package, event")
    service_name = serializers.CharField(help_text="Display name of the booked service")
    client_name = serializers.CharField(allow_null=True, required=False, help_text="Full name of client / celebrant")
    client_email = serializers.CharField(allow_null=True, required=False, help_text="Email address of client")
    client_phone = serializers.CharField(allow_null=True, required=False, help_text="Phone number of client")
    user_id = serializers.IntegerField(allow_null=True, required=False, help_text="Linked user ID if registered user")
    date = serializers.CharField(help_text="Booking appointment / visit date (YYYY-MM-DD)")
    time = serializers.CharField(help_text="Booking start time (HH:MM)")
    end_time = serializers.CharField(allow_null=True, required=False, help_text="Booking end time if applicable")
    guests = serializers.IntegerField(default=1, help_text="Guest count / capacity")
    status = serializers.CharField(help_text="Booking status: pending, confirmed, cancelled")
    payment_status = serializers.CharField(help_text="Payment status: pending, paid, paid_with_package")
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total price charged")
    special_request = serializers.CharField(allow_null=True, required=False, allow_blank=True, help_text="Special requests or notes from client")
    created_at = serializers.DateTimeField(required=False, allow_null=True, help_text="Creation timestamp")
    access_code = serializers.CharField(required=False, allow_null=True, help_text="Access code for entry / check-in")
    details = serializers.DictField(required=False, default=dict, help_text="Service-specific configuration and add-ons")


class AdminBookingsPaginationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    count = serializers.IntegerField(help_text="Total matching bookings count")
    total_pages = serializers.IntegerField(help_text="Total pages available")
    current_page = serializers.IntegerField(help_text="Current page index (1-based)")
    page_size = serializers.IntegerField(help_text="Items returned per page")
    has_next = serializers.BooleanField(help_text="Whether next page exists")
    has_previous = serializers.BooleanField(help_text="Whether previous page exists")
    next_page = serializers.IntegerField(allow_null=True, help_text="Next page number or null")
    previous_page = serializers.IntegerField(allow_null=True, help_text="Previous page number or null")
    results = AdminBookingItemSerializer(many=True, help_text="List of booking objects")
    data = AdminBookingItemSerializer(many=True, required=False, help_text="Alias for results")


class AdminBookingDetailResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(required=False)
    data = AdminBookingItemSerializer()


class AdminBookingStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'cancelled'],
        required=False,
        help_text="Update booking status"
    )
    payment_status = serializers.ChoiceField(
        choices=['pending', 'paid', 'paid_with_package'],
        required=False,
        help_text="Update payment status"
    )
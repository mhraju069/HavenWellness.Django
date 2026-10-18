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


class ServicePaymentBreakdownItemSerializer(serializers.Serializer):
    service_type = serializers.CharField(help_text="Service type key, e.g. sauna, private_sauna, shared_sauna, saltroom, activity, package")
    service_name = serializers.CharField(help_text="Human-readable service title")
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total revenue generated by this service this month")
    transactions_count = serializers.IntegerField(help_text="Number of paid bookings/transactions for this service this month")


class MonthlyPaymentsSummarySerializer(serializers.Serializer):
    month_name = serializers.CharField(help_text="Month and year name, e.g. October 2026")
    year = serializers.IntegerField(help_text="Year number")
    month = serializers.IntegerField(help_text="Month number (1-12)")
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total payments collected this month across all paid services")
    total_transactions = serializers.IntegerField(help_text="Total number of paid transactions this month")
    currency = serializers.CharField(default="EUR", help_text="Currency code")
    services = ServicePaymentBreakdownItemSerializer(many=True, help_text="List of service-by-service revenue breakdown for this month")


class AdminPaymentListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    booking_id = serializers.CharField(help_text="Unique booking reference ID, e.g. PKG-0022, ACT-0007")
    service_type = serializers.CharField(help_text="Service type: sauna, private_sauna, shared_sauna, saltroom, activity, package")
    service_name = serializers.CharField(help_text="Service display name")
    client_name = serializers.CharField(allow_null=True, required=False, help_text="Name of client")
    client_email = serializers.CharField(allow_null=True, required=False, help_text="Client email address")
    client_phone = serializers.CharField(allow_null=True, required=False, help_text="Client phone number")
    user_id = serializers.IntegerField(allow_null=True, required=False, help_text="Linked user ID")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Payment amount / total price")
    currency = serializers.CharField(default="EUR", help_text="Currency code")
    payment_status = serializers.CharField(help_text="Payment status: paid, paid_with_package, pending")
    booking_status = serializers.CharField(help_text="Booking status: confirmed, pending, cancelled")
    date = serializers.CharField(help_text="Booking date (YYYY-MM-DD)")
    time = serializers.CharField(allow_null=True, required=False, help_text="Booking time")
    guests = serializers.IntegerField(default=1, help_text="Number of guests / capacity")
    transaction_id = serializers.CharField(allow_null=True, required=False, help_text="Payment transaction ID or Stripe Payment Intent ID")
    payment_date = serializers.DateTimeField(allow_null=True, required=False, help_text="Timestamp of payment or booking creation")
    created_at = serializers.DateTimeField(allow_null=True, required=False, help_text="Timestamp when booking was created")
    details = serializers.DictField(required=False, default=dict, help_text="Service-specific booking details")


class AdminPaymentsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    monthly_summary = MonthlyPaymentsSummarySerializer(help_text="Monthly payments overview and service-by-service breakdown")
    count = serializers.IntegerField(help_text="Total matching payment records count")
    total_pages = serializers.IntegerField(help_text="Total pages available")
    current_page = serializers.IntegerField(help_text="Current page index (1-based)")
    page_size = serializers.IntegerField(help_text="Items returned per page")
    has_next = serializers.BooleanField(help_text="Whether next page exists")
    has_previous = serializers.BooleanField(help_text="Whether previous page exists")
    next_page = serializers.IntegerField(allow_null=True, help_text="Next page number")
    previous_page = serializers.IntegerField(allow_null=True, help_text="Previous page number")
    results = AdminPaymentListItemSerializer(many=True, help_text="List of payment / booking items")
    data = AdminPaymentListItemSerializer(many=True, required=False, help_text="Alias for results")


class AdminAccessCodeItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    booking_id = serializers.CharField(help_text="Unique booking ID reference, e.g. PS-0070, SS-0001")
    access_code = serializers.CharField(help_text="Access code for entry/gate/sauna, e.g. PS-0070")
    sauna_type = serializers.CharField(help_text="Type of sauna: 'private' or 'shared'")
    service_name = serializers.CharField(help_text="Display title: 'Private Sauna' or 'Shared Sauna'")
    client_name = serializers.CharField(allow_null=True, required=False, help_text="Full client name")
    client_email = serializers.CharField(allow_null=True, required=False, help_text="Client email address")
    client_phone = serializers.CharField(allow_null=True, required=False, help_text="Client phone number")
    user_id = serializers.IntegerField(allow_null=True, required=False, help_text="Linked user ID")
    date = serializers.CharField(help_text="Sauna booking date (YYYY-MM-DD)")
    time = serializers.CharField(help_text="Sauna booking start time (HH:MM)")
    time_slot = serializers.CharField(help_text="Time slot length, e.g. '3_hours', '4_hours', '90_mins'")
    guests = serializers.IntegerField(default=1, help_text="Capacity / number of persons")
    status = serializers.CharField(help_text="Booking status: pending, confirmed, cancelled")
    payment_status = serializers.CharField(help_text="Payment status: pending, paid, paid_with_package")
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total price charged")
    special_request = serializers.CharField(allow_null=True, required=False, allow_blank=True, help_text="Special requests")
    selected_features = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="List of selected features/add-ons")
    created_at = serializers.DateTimeField(required=False, allow_null=True, help_text="Booking creation timestamp")
    details = serializers.DictField(required=False, default=dict, help_text="Detailed booking attributes")


class AdminAccessCodesSummarySerializer(serializers.Serializer):
    total_codes = serializers.IntegerField(help_text="Total access codes count")
    private_sauna_codes = serializers.IntegerField(help_text="Total Private Sauna access codes")
    shared_sauna_codes = serializers.IntegerField(help_text="Total Shared Sauna access codes")
    confirmed_codes = serializers.IntegerField(help_text="Total confirmed active access codes")


class AdminAccessCodesResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    summary = AdminAccessCodesSummarySerializer(help_text="High-level counts summary")
    count = serializers.IntegerField(help_text="Total matching access codes count")
    total_pages = serializers.IntegerField(help_text="Total pages available")
    current_page = serializers.IntegerField(help_text="Current page index (1-based)")
    page_size = serializers.IntegerField(help_text="Items returned per page")
    has_next = serializers.BooleanField(help_text="Whether next page exists")
    has_previous = serializers.BooleanField(help_text="Whether previous page exists")
    next_page = serializers.IntegerField(allow_null=True, help_text="Next page number")
    previous_page = serializers.IntegerField(allow_null=True, help_text="Previous page number")
    results = AdminAccessCodeItemSerializer(many=True, help_text="List of sauna booking access codes")
    data = AdminAccessCodeItemSerializer(many=True, required=False, help_text="Alias for results")


class AdminAccessCodeDetailResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    data = AdminAccessCodeItemSerializer()


# ============================================================================
# Admin Dates Management Serializers (Blocked Dates & Special Opening Dates)
# ============================================================================

class BlockDateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Unique ID of the blocked date entry")
    date = serializers.CharField(help_text="Blocked calendar date (YYYY-MM-DD)")
    description = serializers.CharField(help_text="Reason or description for blocking this date")
    created_at = serializers.DateTimeField(required=False, help_text="Creation timestamp")
    updated_at = serializers.DateTimeField(required=False, help_text="Last update timestamp")


class BlockDateCreateUpdateSerializer(serializers.Serializer):
    date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], help_text="Date to block (YYYY-MM-DD)")
    description = serializers.CharField(required=True, allow_blank=False, help_text="Reason for blocking this date")


class SpecialOpeningDateItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Unique ID of the special opening date entry")
    date = serializers.CharField(help_text="Special opening date (YYYY-MM-DD)")
    open_time = serializers.CharField(help_text="Facility opening time (HH:MM)")
    close_time = serializers.CharField(help_text="Facility closing time (HH:MM)")
    description = serializers.CharField(help_text="Reason or description for special opening hours")
    created_at = serializers.DateTimeField(required=False, help_text="Creation timestamp")
    updated_at = serializers.DateTimeField(required=False, help_text="Last update timestamp")


class SpecialOpeningDateCreateUpdateSerializer(serializers.Serializer):
    date = serializers.DateField(format="%Y-%m-%d", input_formats=["%Y-%m-%d"], help_text="Special opening date (YYYY-MM-DD)")
    open_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%H:%M:%S"], help_text="Opening time (HH:MM)")
    close_time = serializers.TimeField(format="%H:%M", input_formats=["%H:%M", "%H:%M:%S"], help_text="Closing time (HH:MM)")
    description = serializers.CharField(required=True, allow_blank=False, help_text="Reason or details for special opening hours")

    def validate(self, data):
        open_t = data.get('open_time')
        close_t = data.get('close_time')
        if open_t and close_t and open_t >= close_t:
            raise serializers.ValidationError({"close_time": "close_time must be strictly after open_time."})
        return data


class AdminDatesSummarySerializer(serializers.Serializer):
    total_blocked_dates = serializers.IntegerField(help_text="Total blocked dates count")
    total_special_opening_dates = serializers.IntegerField(help_text="Total special opening dates count")
    upcoming_blocked_dates = serializers.IntegerField(help_text="Upcoming blocked dates count from today onwards")
    upcoming_special_opening_dates = serializers.IntegerField(help_text="Upcoming special opening dates count from today onwards")


class AdminDatesOverviewResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    summary = AdminDatesSummarySerializer(help_text="Summary counters for dates")
    blocked_dates = BlockDateItemSerializer(many=True, help_text="All blocked dates with all fields")
    special_opening_dates = SpecialOpeningDateItemSerializer(many=True, help_text="All special opening dates with all fields")


class AdminDateActionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.DictField(required=False)

# ════════════════════════════════════════════════════════════════════════════════
# ADMIN USERS SERIALIZERS
# ════════════════════════════════════════════════════════════════════════════════

class AdminUserItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="User ID")
    uid = serializers.CharField(allow_null=True, required=False, help_text="User UID")
    email = serializers.EmailField(help_text="User Email")
    name = serializers.CharField(allow_null=True, required=False, help_text="User Full Name")
    phone = serializers.CharField(allow_null=True, required=False, help_text="User Phone Number")
    bio = serializers.CharField(allow_null=True, required=False, help_text="User Bio")
    image = serializers.CharField(allow_null=True, required=False, help_text="Profile Image URL")
    role = serializers.CharField(help_text="User Role: user, admin")
    language = serializers.CharField(help_text="User Language: en, nl, de")
    is_active = serializers.BooleanField(help_text="Active user status")
    block = serializers.BooleanField(help_text="User suspension/block status")
    date_joined = serializers.CharField(allow_null=True, required=False, help_text="Date Joined (YYYY-MM-DD HH:MM:SS)")
    last_login = serializers.CharField(allow_null=True, required=False, help_text="Last Login (YYYY-MM-DD HH:MM:SS)")
    total_bookings = serializers.IntegerField(help_text="Total bookings made by this user")
    total_spent = serializers.CharField(help_text="Total amount spent by user across paid bookings")


class AdminUsersMetricsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField(help_text="Total number of registered users")
    active_users = serializers.IntegerField(help_text="Total active users")
    blocked_users = serializers.IntegerField(help_text="Total blocked/suspended users")
    admin_users = serializers.IntegerField(help_text="Total admin users")
    regular_users = serializers.IntegerField(help_text="Total regular users")
    joined_this_month = serializers.IntegerField(help_text="Users joined in current month")


class AdminUsersPaginationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    summary = AdminUsersMetricsSerializer(help_text="Global user metrics and counts")
    total = serializers.IntegerField(help_text="Total matching users after filtering")
    page = serializers.IntegerField(help_text="Current page number")
    page_size = serializers.IntegerField(help_text="Page size")
    total_pages = serializers.IntegerField(help_text="Total pages")
    data = AdminUserItemSerializer(many=True, help_text="List of users for the current page")


class AdminUserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="User full name")
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="User phone number")
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="User biography")
    role = serializers.ChoiceField(choices=['user', 'admin'], required=False, help_text="User role: 'user' or 'admin'")
    language = serializers.ChoiceField(choices=['en', 'nl', 'de'], required=False, help_text="Language: en, nl, de")
    is_active = serializers.BooleanField(required=False, help_text="User active status (true/false)")
    block = serializers.BooleanField(required=False, help_text="User suspended/blocked status (true/false)")
    password = serializers.CharField(required=False, allow_blank=False, write_only=True, min_length=6, help_text="New password for user (optional)")
    image = serializers.ImageField(required=False, allow_null=True, help_text="Profile image file upload")


class AdminUserActionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(help_text="Response message")
    data = AdminUserItemSerializer(required=False, help_text="Updated user data")

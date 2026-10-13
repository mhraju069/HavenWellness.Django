from rest_framework import serializers
from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, PackageBooking, SaltRoomBooking


class PackageBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=True, help_text="Guest Phone Number (Required)")
    date = serializers.DateField(required=True, help_text="Package Date (YYYY-MM-DD)")
    guests = serializers.IntegerField(required=False, default=1, help_text="Number of guests")
    booked_services_ids = serializers.JSONField(
        required=False,
        default=list,
        help_text="List of sub-service IDs, e.g. [{'private_sauna':'PS-001'}, {'lunchroom':'LR-001'}] or ['PS-001', 'ACT-002']"
    )
    service_names = serializers.JSONField(
        required=False,
        default=list,
        help_text=(
            "For CUSTOM packages only: list of selected service names, "
            "e.g. ['Private Sauna', 'Lunchroom', 'Yoga Activity']. "
            "These are stored as-is and no sub-bookings are created."
        )
    )
    is_custom = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    # Sub-service booking inputs for standard packages
    sauna_booking = serializers.JSONField(required=False, write_only=True, allow_null=True)
    lunchroom_booking = serializers.JSONField(required=False, write_only=True, allow_null=True)
    activity_booking = serializers.JSONField(required=False, write_only=True, allow_null=True)
    saltroom_booking = serializers.JSONField(required=False, write_only=True, allow_null=True)
    saltroom = serializers.JSONField(required=False, write_only=True, allow_null=True)
    saltroom_time = serializers.CharField(required=False, write_only=True, allow_null=True, allow_blank=True)
    saltroom_start_time = serializers.CharField(required=False, write_only=True, allow_null=True, allow_blank=True)
    saltroom_end_time = serializers.CharField(required=False, write_only=True, allow_null=True, allow_blank=True)

    class Meta:
        model = PackageBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Populate detailed information about included sub-bookings
        details = []
        raw_ids = instance.booked_services_ids or []
        for item in raw_ids:
            if isinstance(item, dict):
                for s_type, ref_id in item.items():
                    sub_info = {'service_type': s_type, 'booking_id': ref_id}
                    if ref_id.startswith(('PS-', 'SS-', 'SB-')):
                        s_obj = SaunaBooking.objects.filter(booking_id=ref_id).first()
                        if s_obj:
                            sub_info.update({
                                'date': str(s_obj.booking_date) if s_obj.booking_date else '',
                                'booking_time': str(s_obj.booking_time) if s_obj.booking_time else '',
                                'time_slot': getattr(s_obj, 'time_slot', ''),
                                'capacity': getattr(s_obj, 'capacity', 1),
                                'status': getattr(s_obj, 'status', ''),
                            })
                    elif ref_id.startswith('SR-'):
                        sr_obj = SaltRoomBooking.objects.filter(booking_id=ref_id).first()
                        if sr_obj:
                            sub_info.update({
                                'date': str(sr_obj.date) if sr_obj.date else '',
                                'start_time': str(sr_obj.start_time) if sr_obj.start_time else '',
                                'end_time': str(sr_obj.end_time) if sr_obj.end_time else '',
                                'capacity': getattr(sr_obj, 'capacity', 1),
                                'status': getattr(sr_obj, 'status', ''),
                            })
                    elif ref_id.startswith('LR-'):
                        l_obj = LunchroomBooking.objects.filter(booking_id=ref_id).first()
                        if l_obj:
                            sub_info.update({
                                'date': str(l_obj.booking_date) if l_obj.booking_date else '',
                                'booking_time': str(l_obj.booking_time) if l_obj.booking_time else '',
                                'status': getattr(l_obj, 'status', ''),
                            })
                    elif ref_id.startswith('ACT-'):
                        a_obj = ActivityBooking.objects.filter(booking_id=ref_id).first()
                        if a_obj:
                            act_date = str(a_obj.activity.date) if a_obj.activity and getattr(a_obj.activity, 'date', None) else ''
                            act_time = str(a_obj.activity.open_time) if a_obj.activity and getattr(a_obj.activity, 'open_time', None) else ''
                            sub_info.update({
                                'activity_title': a_obj.activity.title if a_obj.activity else '',
                                'date': act_date,
                                'booking_time': act_time,
                                'capacity': getattr(a_obj, 'capacity', 1),
                                'status': getattr(a_obj, 'status', ''),
                            })
                    details.append(sub_info)
        rep['booked_services_details'] = details
        return rep

    def create(self, validated_data):
        from datetime import datetime, timedelta, time
        from services.models import Saltroom

        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user

        is_custom = validated_data.get('is_custom', False)

        if is_custom:
            # Custom package: NO sub-bookings created, NO payment.
            # Just store service names in the service_names JSON field.
            service_names = validated_data.get('service_names', [])
            if not isinstance(service_names, list):
                service_names = []
            validated_data['service_names'] = service_names
            validated_data['booked_services_ids'] = []  # empty for custom
            return super().create(validated_data)

        # --- Standard package: create sub-bookings ---
        sauna_data = self.initial_data.get('sauna_booking') or self.initial_data.get('sauna')
        lunchroom_data = self.initial_data.get('lunchroom_booking') or self.initial_data.get('lunchroom')
        activity_data = self.initial_data.get('activity_booking') or self.initial_data.get('activity')

        booked_services_ids = validated_data.get('booked_services_ids', [])
        if not isinstance(booked_services_ids, list):
            booked_services_ids = []

        package_price = validated_data.get('total_price', 0)

        # 1. Create Sauna Booking if sauna_data provided
        if sauna_data and isinstance(sauna_data, dict):
            from .serializers import SaunaBookingSerializer
            s_data = dict(sauna_data)
            s_data.setdefault('name', validated_data.get('name'))
            s_data.setdefault('email', validated_data.get('email'))
            s_data.setdefault('phone', validated_data.get('phone'))
            s_data.setdefault('booking_date', str(validated_data.get('date')))
            s_data.setdefault('booking_time', '10:00:00')
            s_data.setdefault('total_price', package_price)
            s_serializer = SaunaBookingSerializer(data=s_data, context=self.context)
            if s_serializer.is_valid(raise_exception=True):
                s_booking = s_serializer.save()
                raw_stype = s_data.get('sauna_type', 'sauna')
                if raw_stype in ['private', 'shared']:
                    stype = f"{raw_stype}_sauna"
                else:
                    stype = raw_stype
                booked_services_ids.append({stype: s_booking.booking_id})

        # 2. Create Lunchroom Booking if lunchroom_data provided
        if lunchroom_data and isinstance(lunchroom_data, dict):
            from .serializers import LunchroomBookingSerializer
            l_data = dict(lunchroom_data)
            l_data.setdefault('name', validated_data.get('name'))
            l_data.setdefault('email', validated_data.get('email'))
            l_data.setdefault('phone', validated_data.get('phone'))
            l_data.setdefault('booking_date', str(validated_data.get('date')))
            l_data.setdefault('booking_time', '12:00:00')
            l_serializer = LunchroomBookingSerializer(data=l_data, context=self.context)
            if l_serializer.is_valid(raise_exception=True):
                l_booking = l_serializer.save()
                booked_services_ids.append({'lunchroom': l_booking.booking_id})

        # 3. Create Activity Booking if activity_data provided
        if activity_data and isinstance(activity_data, dict):
            from .serializers import ActivityBookingSerializer
            a_data = dict(activity_data)
            a_data.setdefault('name', validated_data.get('name'))
            a_data.setdefault('email', validated_data.get('email'))
            a_data.setdefault('phone', validated_data.get('phone'))
            a_data.setdefault('total_price', package_price)
            a_serializer = ActivityBookingSerializer(data=a_data, context=self.context)
            if a_serializer.is_valid(raise_exception=True):
                a_booking = a_serializer.save()
                booked_services_ids.append({'activity': a_booking.booking_id})

        # 4. Create Salt Room Booking if saltroom input provided
        saltroom_input = (
            self.initial_data.get('saltroom_booking')
            or self.initial_data.get('saltroom')
            or self.initial_data.get('salt_room')
            or self.initial_data.get('saltroom_time')
            or self.initial_data.get('saltroom_start_time')
        )
        if saltroom_input:
            from .serializers import SaltRoomBookingSerializer
            if isinstance(saltroom_input, str):
                sr_data = {'start_time': saltroom_input}
            elif isinstance(saltroom_input, dict):
                sr_data = dict(saltroom_input)
            else:
                sr_data = {}

            # Handle flexible time keys
            if 'start_time' not in sr_data and 'time' in sr_data:
                sr_data['start_time'] = sr_data['time']
            if 'start_time' not in sr_data and self.initial_data.get('saltroom_time'):
                sr_data['start_time'] = self.initial_data.get('saltroom_time')
            if 'start_time' not in sr_data and self.initial_data.get('saltroom_start_time'):
                sr_data['start_time'] = self.initial_data.get('saltroom_start_time')

            sr_data.setdefault('start_time', '11:00:00')

            # Normalize start_time (HH:MM -> HH:MM:00)
            s_time_raw = str(sr_data['start_time']).strip()
            if len(s_time_raw.split(':')) == 2:
                s_time_raw = f"{s_time_raw}:00"
                sr_data['start_time'] = s_time_raw

            sr_data.setdefault('name', validated_data.get('name'))
            sr_data.setdefault('email', validated_data.get('email'))
            sr_data.setdefault('phone', validated_data.get('phone', ''))
            sr_data.setdefault('date', str(validated_data.get('date')))
            sr_data.setdefault('capacity', validated_data.get('guests', 1))
            sr_data.setdefault('total_price', package_price)
            sr_data.setdefault('payment_mode', 'card')

            # Auto calculate end_time if missing
            if not sr_data.get('end_time'):
                sr_end_time = self.initial_data.get('saltroom_end_time')
                if sr_end_time:
                    if len(str(sr_end_time).split(':')) == 2:
                        sr_end_time = f"{sr_end_time}:00"
                    sr_data['end_time'] = sr_end_time
                else:
                    salt_obj = Saltroom.objects.first()
                    duration_td = salt_obj.duration if salt_obj and salt_obj.duration else timedelta(minutes=60)
                    try:
                        parsed_start = datetime.strptime(s_time_raw, "%H:%M:%S").time()
                        target_d = validated_data.get('date')
                        dt_start = datetime.combine(target_d, parsed_start)
                        dt_end = dt_start + duration_td
                        sr_data['end_time'] = dt_end.time().strftime("%H:%M:%S")
                    except Exception:
                        sr_data['end_time'] = "12:00:00"

            sr_serializer = SaltRoomBookingSerializer(data=sr_data, context=self.context)
            if sr_serializer.is_valid(raise_exception=True):
                sr_booking = sr_serializer.save()
                booked_services_ids.append({'saltroom': sr_booking.booking_id})

        # Pop write-only sub-booking input fields from validated_data
        for f in [
            'sauna_booking', 'lunchroom_booking', 'activity_booking',
            'saltroom_booking', 'saltroom', 'saltroom_time',
            'saltroom_start_time', 'saltroom_end_time'
        ]:
            validated_data.pop(f, None)

        validated_data['booked_services_ids'] = booked_services_ids
        return super().create(validated_data)



class SaunaBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=True, help_text="Guest Phone Number (Required)")
    special_request = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="Special Request or Comment (Optional)")

    class Meta:
        model = SaunaBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def validate_selected_features(self, value):
        """
        Convert IDs into actual feature names so the database and admin panel
        always store the human-readable add-on names instead of numeric IDs.
        """
        if not value or not isinstance(value, list):
            return value

        from services.models import PrivateSaunaFeatures, SharedSaunaFeatures

        resolved = []
        for item in value:
            if isinstance(item, dict):
                name = item.get('feature') or item.get('name') or str(item)
                resolved.append(name)
            elif isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                feat_id = int(item)
                feat = (
                    PrivateSaunaFeatures.objects.filter(id=feat_id).first()
                    or SharedSaunaFeatures.objects.filter(id=feat_id).first()
                )
                if feat and feat.feature:
                    resolved.append(feat.feature)
                elif feat and getattr(feat, 'feature_en', None):
                    resolved.append(feat.feature_en)
                else:
                    resolved.append(str(item))
            else:
                resolved.append(str(item))
        return resolved

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class LunchroomBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=True, help_text="Guest Phone Number (Required)")
    special_request = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="Special Request or Comment (Optional)")
    celebration_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    celebration_date = serializers.DateField(required=False, allow_null=True)
    name_of_celebrant = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    age_of_celebrant = serializers.IntegerField(required=False, allow_null=True)
    hobbies = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    celebration_details = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = LunchroomBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class ActivityBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=True, help_text="Guest Phone Number (Required)")
    special_request = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text="Special Request or Comment (Optional)")

    class Meta:
        model = ActivityBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.activity:
            rep['activity_details'] = {
                'id': instance.activity.id,
                'title': instance.activity.title,
                'date': str(instance.activity.date) if instance.activity.date else None,
                'open_time': str(instance.activity.open_time) if instance.activity.open_time else None,
                'close_time': str(instance.activity.close_time) if instance.activity.close_time else None,
                'price': str(instance.activity.price),
                'host': instance.activity.host,
            }
        return rep

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user

        # Auto calculate total_price if zero or not provided: activity.price * capacity
        activity = validated_data.get('activity')
        capacity = validated_data.get('capacity', 1)
        total_price = validated_data.get('total_price', 0)
        if (not total_price or float(total_price) == 0) and activity and activity.price:
            validated_data['total_price'] = activity.price * capacity

        return super().create(validated_data)


class EventBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=True, help_text="Guest Phone Number (Required)")
    date = serializers.DateField(required=True, help_text="Event Date (YYYY-MM-DD)")
    start_time = serializers.TimeField(required=True, help_text="Event Start Time (HH:MM:SS)")
    end_time = serializers.TimeField(required=True, help_text="Event End Time (HH:MM:SS)")
    guests = serializers.IntegerField(required=True, help_text="Number of guests")

    food_preference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    drink_preference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    music_preference = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = EventBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class SaltRoomBookingSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, help_text="Guest Name (Required)")
    email = serializers.EmailField(required=True, help_text="Guest Email (Required)")
    phone = serializers.CharField(required=False, default="", allow_blank=True, help_text="Guest Phone (Optional)")
    date = serializers.DateField(required=True, help_text="Booking Date (YYYY-MM-DD)")
    start_time = serializers.TimeField(required=True, help_text="Start Time (HH:MM or HH:MM:SS)")
    end_time = serializers.TimeField(required=False, help_text="End Time (Auto-calculated if omitted)")
    capacity = serializers.IntegerField(required=False, default=1, help_text="Number of people (max saltroom capacity)")
    special_request = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    # Membership / Payment mode selection
    payment_mode = serializers.ChoiceField(
        choices=['pass', 'subscription', 'weekly_subscription', 'unlimited_subscription', 'card'],
        required=False,
        default='card',
        write_only=True,
        help_text="Booking payment method: 'card' (single session €25), 'pass' (10 session pass), 'subscription' (auto-detect or specified plan), 'weekly_subscription' (Once a week plan), or 'unlimited_subscription' (Unlimited plan)."
    )
    purchase_id = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
        help_text="Existing active ClientPurchase purchase_id (e.g. PASS-0001 or SUB-0001) to deduct session from."
    )
    plan_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="SubscriptionPlan ID to purchase if user does not already have an active subscription."
    )
    purchase_plan_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Alias for plan_id."
    )
    pass_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="SessionPass ID to purchase if user does not already have an active pass."
    )
    purchase_pass_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Alias for pass_id."
    )
    plan_type = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
        help_text="Optional plan type: 'weekly', 'unlimited', or 'pass'."
    )

    class Meta:
        model = SaltRoomBooking
        fields = '__all__'
        read_only_fields = [
            'id', 'booking_id', 'user', 'is_paid', 'status', 'payment_status',
            'used_pass', 'used_subscription', 'client_purchase', 'total_price',
            'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        from datetime import datetime, timedelta
        from services.models import Saltroom

        # If start_time not in attrs, but provided as 'time' in initial_data
        if not attrs.get('start_time') and self.initial_data.get('time'):
            t_raw = str(self.initial_data.get('time')).strip()
            if len(t_raw.split(':')) == 2:
                t_raw = f"{t_raw}:00"
            try:
                attrs['start_time'] = datetime.strptime(t_raw, "%H:%M:%S").time()
            except Exception:
                pass

        # Auto-calculate end_time if missing
        if not attrs.get('end_time') and attrs.get('start_time') and attrs.get('date'):
            salt_obj = Saltroom.objects.first()
            duration_td = salt_obj.duration if salt_obj and salt_obj.duration else timedelta(minutes=60)
            dt_start = datetime.combine(attrs['date'], attrs['start_time'])
            dt_end = dt_start + duration_td
            attrs['end_time'] = dt_end.time()

        return attrs

    def create(self, validated_data):
        from datetime import datetime, timedelta
        from services.models import Saltroom

        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user

        # Pop write-only non-model fields before creating SaltRoomBooking
        for f in [
            'payment_mode', 'purchase_id', 'plan_id', 'purchase_plan_id',
            'pass_id', 'purchase_pass_id', 'plan_type'
        ]:
            validated_data.pop(f, None)

        if not validated_data.get('end_time'):
            salt_obj = Saltroom.objects.first()
            duration_td = salt_obj.duration if salt_obj and salt_obj.duration else timedelta(minutes=60)
            date_val = validated_data.get('date')
            start_val = validated_data.get('start_time')
            if date_val and start_val:
                dt_start = datetime.combine(date_val, start_val)
                dt_end = dt_start + duration_td
                validated_data['end_time'] = dt_end.time()
            else:
                validated_data['end_time'] = datetime.strptime("12:00:00", "%H:%M:%S").time()

        if 'total_price' not in validated_data or validated_data['total_price'] == 0:
            salt_obj = Saltroom.objects.first()
            price_per_person = salt_obj.price_per_person if salt_obj else 25
            capacity = validated_data.get('capacity', 1)
            validated_data['total_price'] = float(price_per_person) * capacity

        return super().create(validated_data)



from rest_framework import serializers
from .models import SaunaBooking, LunchroomBooking, ActivityBooking, EventBooking, PackageBooking


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

    class Meta:
        model = PackageBooking
        fields = '__all__'
        read_only_fields = ['id', 'booking_id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
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

        # 1. Create Sauna Booking if sauna_data provided
        if sauna_data and isinstance(sauna_data, dict):
            from .serializers import SaunaBookingSerializer
            s_data = dict(sauna_data)
            s_data.setdefault('name', validated_data.get('name'))
            s_data.setdefault('email', validated_data.get('email'))
            s_data.setdefault('phone', validated_data.get('phone'))
            s_data.setdefault('booking_date', str(validated_data.get('date')))
            s_data.setdefault('booking_time', '10:00:00')
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
            a_serializer = ActivityBookingSerializer(data=a_data, context=self.context)
            if a_serializer.is_valid(raise_exception=True):
                a_booking = a_serializer.save()
                booked_services_ids.append({'activity': a_booking.booking_id})

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



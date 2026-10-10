from rest_framework import serializers
from .models import SaunaBooking, LunchroomBooking


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


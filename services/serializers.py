from rest_framework import serializers
from .models import (
    Service, ServiceOpeningHour, ServiceScheduleException, BlockedSlot,
    SaltRoomPricing, AddOnExtra, EventInquiry, ServicePackage, MembershipPlan,
    SaunaSeesion, PrivateSauna, SharedSauna, Activities, ActivitySession,
    ActivitiesFeature, ServiceFeature, ExcludeDate
)


class ServiceOpeningHourSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = ServiceOpeningHour
        fields = ['id', 'day_of_week', 'day_name', 'open_time', 'close_time', 'is_closed']


class ServiceScheduleExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceScheduleException
        fields = '__all__'


class BlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSlot
        fields = '__all__'


class ServiceSerializer(serializers.ModelSerializer):
    opening_hours = ServiceOpeningHourSerializer(many=True, read_only=True)
    schedule_exceptions = ServiceScheduleExceptionSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = '__all__'


class SaltRoomPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaltRoomPricing
        fields = '__all__'


class AddOnExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOnExtra
        fields = '__all__'


class EventInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventInquiry
        fields = '__all__'


class ServicePackageSerializer(serializers.ModelSerializer):
    services_detail = ServiceSerializer(source='services', many=True, read_only=True)

    class Meta:
        model = ServicePackage
        fields = '__all__'


class MembershipPlanSerializer(serializers.ModelSerializer):
    service_detail = ServiceSerializer(source='service', read_only=True)

    class Meta:
        model = MembershipPlan
        fields = '__all__'


# Legacy / Existing Serializers
class SaunaSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaunaSeesion
        exclude = ['created_at', 'updated_at']


class ActivitiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activities
        exclude = ['created_at', 'updated_at']


class ActivitiesFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitiesFeature
        fields = ['id', 'feature']


class ActivitySessionSerializer(serializers.ModelSerializer):
    features = ActivitiesFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ActivitySession
        exclude = ['created_at', 'updated_at']


class AllServicesSerializer(serializers.Serializer):
    sauna_seesion = SaunaSessionSerializer(many=True, required=False)
    activity_session = ActivitiesSerializer(many=True, required=False)


class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        exclude = ['created_at', 'updated_at']


class PrivateSaunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivateSauna
        exclude = ['created_at', 'updated_at']


class SharedSaunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedSauna
        exclude = ['created_at', 'updated_at']


class SaunaServiceSerializer(serializers.Serializer):
    private_sauna = PrivateSaunaSerializer(many=True, required=False)
    shared_sauna = SharedSaunaSerializer(many=True, required=False)

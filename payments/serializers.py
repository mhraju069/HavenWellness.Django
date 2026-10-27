from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import *


class SubscriptionPlanFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlanFeatures
        exclude = ['subscription_plan', 'created_at', 'updated_at']


def _sync_features(model_class, parent_instance, parent_fk_field, feature_list):
    """
    Helper to sync features with multi-language support:
    feature_list can contain:
    - simple strings: "Feature text"
    - dictionaries: {"feature": "...", "feature_en": "...", "feature_nl": "...", "feature_de": "..."}
    """
    if feature_list is None:
        return

    # Delete existing
    getattr(parent_instance, 'features').all().delete()

    for item in feature_list:
        if isinstance(item, str):
            text = item.strip()
            if text:
                kwargs = {parent_fk_field: parent_instance, 'feature': text, 'feature_en': text}
                model_class.objects.create(**kwargs)
        elif isinstance(item, dict):
            base_text = (
                item.get('feature') or
                item.get('feature_en') or
                item.get('feature_nl') or
                item.get('feature_de') or
                ''
            ).strip()
            if base_text:
                kwargs = {
                    parent_fk_field: parent_instance,
                    'feature': base_text,
                    'feature_en': item.get('feature_en') or base_text,
                    'feature_nl': item.get('feature_nl'),
                    'feature_de': item.get('feature_de'),
                }
                model_class.objects.create(**kwargs)


class SubscriptionPlansSerializer(serializers.ModelSerializer):
    features = SubscriptionPlanFeaturesSerializer(many=True, read_only=True)
    feature_list = serializers.ListField(
        child=serializers.JSONField(),
        write_only=True,
        required=False,
        help_text="Optional list of feature strings or multilingual objects (e.g. [{'feature_en':'...', 'feature_nl':'...', 'feature_de':'...'}])"
    )

    class Meta:
        model = SubscriptionPlans
        exclude = ['created_at', 'updated_at']

    def create(self, validated_data):
        feature_list = validated_data.pop('feature_list', None)
        plan = SubscriptionPlans.objects.create(**validated_data)
        _sync_features(SubscriptionPlanFeatures, plan, 'subscription_plan', feature_list)
        return plan

    def update(self, instance, validated_data):
        feature_list = validated_data.pop('feature_list', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        _sync_features(SubscriptionPlanFeatures, instance, 'subscription_plan', feature_list)
        return instance


class SessionPassFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionPassFeatures
        exclude = ['session_pass', 'created_at', 'updated_at']


class SessionPassSerializer(serializers.ModelSerializer):
    features = SessionPassFeaturesSerializer(many=True, read_only=True)
    feature_list = serializers.ListField(
        child=serializers.JSONField(),
        write_only=True,
        required=False,
        help_text="Optional list of feature strings or multilingual objects (e.g. [{'feature_en':'...', 'feature_nl':'...', 'feature_de':'...'}])"
    )

    class Meta:
        model = SessionPass
        exclude = ['created_at', 'updated_at']

    def create(self, validated_data):
        feature_list = validated_data.pop('feature_list', None)
        session_pass = SessionPass.objects.create(**validated_data)
        _sync_features(SessionPassFeatures, session_pass, 'session_pass', feature_list)
        return session_pass

    def update(self, instance, validated_data):
        feature_list = validated_data.pop('feature_list', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        _sync_features(SessionPassFeatures, instance, 'session_pass', feature_list)
        return instance


class PaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = '__all__'


class CreatePaymentIntentRequestSerializer(serializers.Serializer):
    booking_id = serializers.CharField(help_text="Booking identifier, e.g., PS-0001 or SS-0001", required=True)
    currency = serializers.CharField(default="eur", required=False)


class CreatePaymentIntentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    client_secret = serializers.CharField()
    payment_intent_id = serializers.CharField()
    booking_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()


class PaymentMessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class PurchaseRequestSerializer(serializers.Serializer):
    purchase_type = serializers.ChoiceField(
        choices=['session_pass', 'subscription'],
        help_text="Type of purchase: 'session_pass' or 'subscription'"
    )
    pass_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID of the SessionPass (required if purchase_type is 'session_pass')"
    )
    plan_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID of the SubscriptionPlan (required if purchase_type is 'subscription')"
    )
    plan_type = serializers.ChoiceField(
        choices=['weekly', 'unlimited'],
        required=False,
        allow_null=True,
        help_text="Optional filter if selecting by plan type: 'weekly' or 'unlimited'"
    )
    plan_category = serializers.ChoiceField(
        choices=['sauna', 'saltroom'],
        required=False,
        allow_null=True,
        help_text="Optional filter if selecting by category: 'sauna' or 'saltroom'"
    )
    name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, help_text="Client Name (defaults to authenticated user name)")
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True, help_text="Client Email (defaults to authenticated user email)")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True, help_text="Client Phone (defaults to authenticated user phone)")
    currency = serializers.CharField(max_length=10, default="eur", required=False)

    def validate(self, attrs):
        purchase_type = attrs.get('purchase_type')
        if purchase_type == 'session_pass':
            pass_id = attrs.get('pass_id')
            if not pass_id:
                raise serializers.ValidationError({"pass_id": "pass_id is required when purchase_type is 'session_pass'."})
            if not SessionPass.objects.filter(id=pass_id).exists():
                raise serializers.ValidationError({"pass_id": f"SessionPass with id {pass_id} does not exist."})
        elif purchase_type == 'subscription':
            plan_id = attrs.get('plan_id')
            if not plan_id:
                plan_type = attrs.get('plan_type')
                plan_category = attrs.get('plan_category')
                if plan_type:
                    query = {'plan_type': plan_type}
                    if plan_category:
                        query['plan_category'] = plan_category
                    plan = SubscriptionPlans.objects.filter(**query).first()
                    if plan:
                        attrs['plan_id'] = plan.id
                    else:
                        raise serializers.ValidationError({"plan_id": f"No SubscriptionPlan found for type '{plan_type}' and category '{plan_category}'."})
                else:
                    raise serializers.ValidationError({"plan_id": "Either plan_id or plan_type (weekly/unlimited) is required when purchase_type is 'subscription'."})
            else:
                if not SubscriptionPlans.objects.filter(id=plan_id).exists():
                    raise serializers.ValidationError({"plan_id": f"SubscriptionPlan with id {plan_id} does not exist."})
        return attrs


class ClientPurchaseSerializer(serializers.ModelSerializer):
    session_pass_details = SessionPassSerializer(source='session_pass', read_only=True)
    subscription_plan_details = SubscriptionPlansSerializer(source='subscription_plan', read_only=True)

    class Meta:
        model = ClientPurchase
        fields = '__all__'
        read_only_fields = ['id', 'purchase_id', 'status', 'payment_status', 'created_at', 'updated_at']
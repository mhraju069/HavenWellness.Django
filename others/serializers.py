from rest_framework import serializers
from .models import ContactInfo, TermsAndConditions, PrivacyPolicy, FAQ, SupportMessage, SocialMediaLink


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = ['id', 'email', 'phone', 'address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = [
            'id',
            'effective_date',
            'acceptance_of_terms',
            'user_responsibilities',
            'ticket_purchase',
            'refund_policy',
            'limitation_of_liability',
            'changes_to_terms',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = [
            'id',
            'effective_date',
            'info_we_collect',
            'how_we_use_data',
            'child_safety',
            'user_rights',
            'security',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField(read_only=True)
    sender_email = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SupportMessage
        fields = [
            'id',
            'sender',
            'sender_name',
            'sender_email',
            'name',
            'email',
            'phone',
            'subject',
            'message',
            'is_read',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'sender', 'sender_name', 'sender_email', 'created_at', 'updated_at']

    def get_sender_name(self, obj):
        if obj.sender:
            return getattr(obj.sender, 'name', None) or getattr(obj.sender, 'username', '')
        return obj.name or "Anonymous"

    def get_sender_email(self, obj):
        if obj.sender:
            return getattr(obj.sender, 'email', '')
        return obj.email or ""


class SupportMessageCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=50)
    subject = serializers.CharField(required=False, allow_blank=True, max_length=255)
    message = serializers.CharField(required=True, allow_blank=False)


class SocialMediaLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = ['id', 'media_type', 'url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SocialMediaBulkUpdateSerializer(serializers.Serializer):
    facebook = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    instagram = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    twitter = serializers.URLField(required=False, allow_blank=True, allow_null=True)

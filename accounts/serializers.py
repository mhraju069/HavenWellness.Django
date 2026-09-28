from .models import User
from rest_framework import serializers

class UserProfileSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False, help_text="Current password required when updating password")
    password = serializers.CharField(write_only=True, required=False, help_text="New password")

    class Meta:
        model = User
        fields = ['id', 'email', 'uid', 'name', 'bio', 'image', 'phone', 'language', 'role', 'old_password', 'password']
        read_only_fields = ['id', 'email', 'role', 'uid']

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.image = validated_data.get('image', instance.image)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.language = validated_data.get('language', instance.language)

        if validated_data.get('password'):
            if not instance.check_password(validated_data.get('old_password', '')):
                raise serializers.ValidationError({"old_password": "Old password does not match."})
            instance.set_password(validated_data['password'])

        instance.save()
        return instance


class GetOtpRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="User's email address to send OTP")
    task = serializers.CharField(required=False, allow_blank=True, default='', help_text="Optional task label")


class GetOtpResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    log = serializers.CharField()


class OtpVerifyRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="User's email address")
    otp_code = serializers.CharField(max_length=6, required=True, help_text="6-digit OTP code")


class OtpVerifyResponseSerializer(serializers.Serializer):
    user = UserProfileSerializer()
    refresh = serializers.CharField(help_text="JWT Refresh Token")
    access = serializers.CharField(help_text="JWT Access Token")


class FirebaseLoginRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, help_text="User name when oauth is false")


class FirebaseLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT Access Token")
    refresh = serializers.CharField(help_text="JWT Refresh Token")
    user = UserProfileSerializer()
    status = serializers.BooleanField()
    active = serializers.BooleanField()
    log = serializers.CharField()

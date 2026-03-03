from .models import User
from rest_framework import serializers

class UserProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        exclude = ['password','is_staff','is_superuser','is_active','date_joined','block','groups','user_permissions']
        read_only_fields = ['id', 'email', 'role','uid']

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)

        if validated_data.get('password'):
            if not instance.check_password(validated_data['old_password']):
                raise serializers.ValidationError("Old password does not match.")
            instance.set_password(validated_data['password'])

        instance.save()
        return instance

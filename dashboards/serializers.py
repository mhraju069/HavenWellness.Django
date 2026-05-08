from rest_framework import serializers
from services.models import *

class ExcludeDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcludeDate
        fields = '__all__'
from rest_framework import serializers
from services.models import *

class ExceptionServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceptionService
        fields = '__all__'
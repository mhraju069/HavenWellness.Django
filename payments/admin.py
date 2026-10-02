from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

admin.site.register(SessionPass, ModelAdmin)
admin.site.register(SessionPassFeatures, ModelAdmin)
admin.site.register(SubscriptionPlans, ModelAdmin)
admin.site.register(SubscriptionPlanFeatures, ModelAdmin)

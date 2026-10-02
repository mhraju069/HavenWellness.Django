from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin
# Register your models here.

admin.site.register(SaunaSeesion, ModelAdmin)
admin.site.register(PrivateSauna, ModelAdmin)
admin.site.register(PrivateSaunaFeatures, ModelAdmin)
admin.site.register(SharedSauna, ModelAdmin)
admin.site.register(SharedSaunaFeatures, ModelAdmin)


admin.site.register(Activities, ModelAdmin)
admin.site.register(ActivitySession, ModelAdmin)
admin.site.register(ActivitiesFeature, ModelAdmin)

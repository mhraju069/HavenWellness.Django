from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin
from .models import *


class BaseTranslationAdmin(TranslationAdmin, ModelAdmin):
    pass


admin.site.register(Services, BaseTranslationAdmin)
admin.site.register(PrivateSauna, ModelAdmin)
admin.site.register(PrivateSaunaFeatures, BaseTranslationAdmin)

admin.site.register(SharedSauna, ModelAdmin)
admin.site.register(SharedSaunaFeatures, BaseTranslationAdmin)

admin.site.register(Activities, BaseTranslationAdmin)
admin.site.register(ActivitiesFeature, BaseTranslationAdmin)

admin.site.register(Lunchroom, BaseTranslationAdmin)

admin.site.register(Saltroom, BaseTranslationAdmin)
admin.site.register(SaltroomFeatures, BaseTranslationAdmin)

admin.site.register(Packages, BaseTranslationAdmin)
admin.site.register(PackageFeatures, BaseTranslationAdmin)

class ServiceSettingsAdmin(ModelAdmin):
    list_display = ('get_service_name', 'get_week_days_display', 'open_time', 'close_time', 'is_closed')
    list_filter = ('service', 'is_closed')
    search_fields = ('service__title', 'service__type')

    def get_service_name(self, obj):
        return obj.service.title if obj.service else "Global (All Services)"
    get_service_name.short_description = "Service"

    def get_week_days_display(self, obj):
        if not obj.week_days:
            return "All Days"
        return ", ".join(obj.week_days)
    get_week_days_display.short_description = "Days of Week"


admin.site.register(ServiceSettings, ServiceSettingsAdmin)
admin.site.register(BlockDate, ModelAdmin)
admin.site.register(SpecialOpeningDate, ModelAdmin)


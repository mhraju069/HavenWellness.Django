from django.contrib import admin
from .models import (
    Service, ServiceOpeningHour, ServiceScheduleException, BlockedSlot,
    SaltRoomPricing, AddOnExtra, EventInquiry, ServicePackage, MembershipPlan,
    SaunaSeesion, PrivateSauna, SharedSauna, Activities, ActivitySession,
    ActivitiesFeature, ServiceFeature, ExcludeDate
)
from unfold.admin import ModelAdmin

admin.site.register(Service, ModelAdmin)
admin.site.register(ServiceOpeningHour, ModelAdmin)
admin.site.register(ServiceScheduleException, ModelAdmin)
admin.site.register(BlockedSlot, ModelAdmin)
admin.site.register(SaltRoomPricing, ModelAdmin)
admin.site.register(AddOnExtra, ModelAdmin)
admin.site.register(EventInquiry, ModelAdmin)
admin.site.register(ServicePackage, ModelAdmin)
admin.site.register(MembershipPlan, ModelAdmin)

admin.site.register(SaunaSeesion, ModelAdmin)
admin.site.register(PrivateSauna, ModelAdmin)
admin.site.register(SharedSauna, ModelAdmin)
admin.site.register(Activities, ModelAdmin)
admin.site.register(ActivitySession, ModelAdmin)
admin.site.register(ActivitiesFeature, ModelAdmin)
admin.site.register(ServiceFeature, ModelAdmin)
admin.site.register(ExcludeDate, ModelAdmin)

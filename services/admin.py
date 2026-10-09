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

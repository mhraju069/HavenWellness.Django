from modeltranslation.translator import register, TranslationOptions
from .models import (
    Services,
    PrivateSaunaFeatures,
    SharedSaunaFeatures,
    Activities,
    ActivitiesFeature,
    Lunchroom,
    Saltroom,
    SaltroomFeatures,
    Packages,
    PackageFeatures,
    ServiceFeature,
)

@register(Services)
class ServicesTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'description')

@register(PrivateSaunaFeatures)
class PrivateSaunaFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(SharedSaunaFeatures)
class SharedSaunaFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(Activities)
class ActivitiesTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'additional_notes')

@register(ActivitiesFeature)
class ActivitiesFeatureTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(Lunchroom)
class LunchroomTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'description')

@register(Saltroom)
class SaltroomTranslationOptions(TranslationOptions):
    fields = ('title', 'subtitle', 'description')

@register(SaltroomFeatures)
class SaltroomFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(Packages)
class PackagesTranslationOptions(TranslationOptions):
    fields = ('title', 'packages', 'description')

@register(PackageFeatures)
class PackageFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(ServiceFeature)
class ServiceFeatureTranslationOptions(TranslationOptions):
    fields = ('feature',)

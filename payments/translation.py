from modeltranslation.translator import register, TranslationOptions
from .models import SessionPass, SessionPassFeatures, SubscriptionPlans, SubscriptionPlanFeatures

@register(SessionPass)
class SessionPassTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(SessionPassFeatures)
class SessionPassFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

@register(SubscriptionPlans)
class SubscriptionPlansTranslationOptions(TranslationOptions):
    fields = ('name',)

@register(SubscriptionPlanFeatures)
class SubscriptionPlanFeaturesTranslationOptions(TranslationOptions):
    fields = ('feature',)

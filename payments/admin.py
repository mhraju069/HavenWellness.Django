from django.contrib import admin
from .models import (
    SessionPass,
    SessionPassFeatures,
    SubscriptionPlans,
    SubscriptionPlanFeatures,
    Payments,
)
from unfold.admin import ModelAdmin

@admin.register(Payments)
class PaymentsAdmin(ModelAdmin):
    list_display = ('booking_id', 'booking_type', 'client', 'amount', 'currency', 'payment_status', 'stripe_payment_intent_id', 'created_at')
    list_filter = ('booking_type', 'payment_status', 'currency', 'created_at')
    search_fields = ('booking_id', 'stripe_payment_intent_id', 'transaction_id', 'client__email')

admin.site.register(SessionPass, ModelAdmin)
admin.site.register(SessionPassFeatures, ModelAdmin)
admin.site.register(SubscriptionPlans, ModelAdmin)
admin.site.register(SubscriptionPlanFeatures, ModelAdmin)

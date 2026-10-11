from django.contrib import admin
from .models import (
    SessionPass,
    SessionPassFeatures,
    SubscriptionPlans,
    SubscriptionPlanFeatures,
    Payments,
    ClientPurchase,
)
from unfold.admin import ModelAdmin

@admin.register(Payments)
class PaymentsAdmin(ModelAdmin):
    list_display = ('booking_id', 'booking_type', 'client', 'amount', 'currency', 'payment_status', 'stripe_payment_intent_id', 'created_at')
    list_filter = ('booking_type', 'payment_status', 'currency', 'created_at')
    search_fields = ('booking_id', 'stripe_payment_intent_id', 'transaction_id', 'client__email')


@admin.register(ClientPurchase)
class ClientPurchaseAdmin(ModelAdmin):
    list_display = (
        'purchase_id',
        'purchase_type',
        'name',
        'email',
        'amount',
        'currency',
        'start_date',
        'end_date',
        'remaining_sessions',
        'total_sessions',
        'max_active_reservations',
        'payment_status',
        'status',
        'created_at',
    )
    list_filter = ('purchase_type', 'payment_status', 'status', 'created_at')
    search_fields = ('purchase_id', 'name', 'email', 'phone')


@admin.register(SubscriptionPlans)
class SubscriptionPlansAdmin(ModelAdmin):
    list_display = ('name', 'price', 'plan_type', 'plan_category', 'duration_weeks', 'max_reservations', 'created_at')
    list_filter = ('plan_type', 'plan_category')


admin.site.register(SessionPass, ModelAdmin)
admin.site.register(SessionPassFeatures, ModelAdmin)
admin.site.register(SubscriptionPlanFeatures, ModelAdmin)

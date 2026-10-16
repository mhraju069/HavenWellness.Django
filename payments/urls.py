from django.urls import path
from .views import (
    CreatePaymentIntentAPIView,
    ConfirmPaymentAPIView,
    StripeWebhookView,
    PaymentSuccessView,
    PaymentCancelView,
    SessionPassListAPIView,
    SessionPassDetailAPIView,
    SubscriptionPlanListAPIView,
    SubscriptionPlanDetailAPIView,
    AllPlansAndPassesListAPIView,
    PurchasePassOrPlanAPIView,
    UserPurchasesAPIView,
)

urlpatterns = [
    path('my-purchases/', UserPurchasesAPIView.as_view(), name='my_purchases'),
    path('plans-and-passes/', AllPlansAndPassesListAPIView.as_view(), name='all_plans_and_passes_list'),
    path('session-passes/', SessionPassListAPIView.as_view(), name='session_passes_list'),
    path('session-passes/<int:pk>/', SessionPassDetailAPIView.as_view(), name='session_passes_detail'),
    path('subscription-plans/', SubscriptionPlanListAPIView.as_view(), name='subscription_plans_list'),
    path('subscription-plans/<int:pk>/', SubscriptionPlanDetailAPIView.as_view(), name='subscription_plans_detail'),
    path('purchase/', PurchasePassOrPlanAPIView.as_view(), name='purchase_pass_or_plan'),
    path('confirm/', ConfirmPaymentAPIView.as_view(), name='confirm_payment_short'),
    path('confirm-payment/', ConfirmPaymentAPIView.as_view(), name='confirm_payment'),
    path('create-intent/', CreatePaymentIntentAPIView.as_view(), name='create_payment_intent'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('cancel/', PaymentCancelView.as_view(), name='payment_cancel'),
]

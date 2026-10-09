from django.urls import path
from .views import (
    CreatePaymentIntentAPIView,
    StripeWebhookView,
    PaymentSuccessView,
    PaymentCancelView,
)

urlpatterns = [
    path('create-intent/', CreatePaymentIntentAPIView.as_view(), name='create_payment_intent'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('success/', PaymentSuccessView.as_view(), name='payment_success'),
    path('cancel/', PaymentCancelView.as_view(), name='payment_cancel'),
]

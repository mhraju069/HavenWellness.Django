from django.urls import path
from .views import GetPaymentLinkView, StripeWebhookView

urlpatterns = [
    path('get-link/', GetPaymentLinkView.as_view(), name='get_payment_link'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
]

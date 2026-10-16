from django.urls import path
from .views import (
    ContactInfoView,
    PrivacyPolicyView,
    TermsAndConditionsView,
    SupportMessageView,
)

urlpatterns = [
    # Contact Information
    path('contact-info/', ContactInfoView.as_view(), name='contact-info'),
    path('contact/', ContactInfoView.as_view(), name='contact-info-alias'),

    # Privacy Policy
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy-policy'),

    # Terms and Conditions
    path('terms-and-conditions/', TermsAndConditionsView.as_view(), name='terms-and-conditions'),
    path('terms/', TermsAndConditionsView.as_view(), name='terms-alias'),

    # Support / Contact Messages
    path('support-messages/', SupportMessageView.as_view(), name='support-messages-list'),
    path('support-messages/<int:pk>/', SupportMessageView.as_view(), name='support-messages-detail'),
    path('messages/', SupportMessageView.as_view(), name='messages-alias'),
    path('messages/<int:pk>/', SupportMessageView.as_view(), name='messages-detail-alias'),
]

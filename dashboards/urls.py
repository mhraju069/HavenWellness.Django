from django.urls import path
from .views import (
    UserDashboardView,
    AdminServiceDetailView,
    ServiceCRUDView,
    ServiceOpeningHoursView,
    ServiceFeatureManageView,
    AdminBookingsView,
    AdminPaymentsView,
    AdminAccessCodesView,
    AdminDatesOverviewView,
    AdminBlockDateView,
    AdminSpecialOpeningDateView,
    AdminUsersView,
)
from services.views import AllServicesView
from others.views import (
    ContactInfoView,
    PrivacyPolicyView,
    TermsAndConditionsView,
    SupportMessageView,
)

urlpatterns = [
    path('', UserDashboardView.as_view(), name='user-dashboard-root'),
    path('user/', UserDashboardView.as_view(), name='user-dashboard'),
    path('admin/bookings/', AdminBookingsView.as_view(), name='admin-bookings-list'),
    path('admin/bookings/<str:booking_id>/', AdminBookingsView.as_view(), name='admin-booking-detail'),
    # Admin Users Management
    path('admin/users/', AdminUsersView.as_view(), name='admin-users-list'),
    path('admin/users/<int:user_id>/', AdminUsersView.as_view(), name='admin-users-detail'),
    path('admin/payments/', AdminPaymentsView.as_view(), name='admin-payments'),
    path('admin/access-codes/', AdminAccessCodesView.as_view(), name='admin-access-codes-list'),
    path('admin/access-codes/<str:access_code>/', AdminAccessCodesView.as_view(), name='admin-access-code-detail'),
    path('admin/services/', AllServicesView.as_view(), name='service-list'),
    path('admin/services/manage/', ServiceCRUDView.as_view(), name='admin-service-crud'),
    path('admin/services/manage/<int:pk>/', ServiceCRUDView.as_view(), name='admin-service-crud-detail'),
    path('admin/services/settings/', ServiceOpeningHoursView.as_view(), name='admin-service-settings'),
    path('admin/services/settings/<int:setting_id>/', ServiceOpeningHoursView.as_view(), name='admin-service-settings-detail'),
    path('admin/services/features/', ServiceFeatureManageView.as_view(), name='admin-service-features'),
    path('admin/services/features/<int:feature_id>/', ServiceFeatureManageView.as_view(), name='admin-service-features-detail'),
    path('admin/services/details/', AdminServiceDetailView.as_view(), name='admin-service-detail-query'),
    path('admin/services/<str:service_type>/', AdminServiceDetailView.as_view(), name='admin-service-detail'),

    # Admin Dates Management (Overview, Blocked Dates, Special Opening Dates)
    path('admin/dates/', AdminDatesOverviewView.as_view(), name='admin-dates-overview'),
    path('admin/dates/blocked/', AdminBlockDateView.as_view(), name='admin-blocked-dates'),
    path('admin/dates/blocked/<int:pk>/', AdminBlockDateView.as_view(), name='admin-blocked-dates-detail'),
    path('admin/dates/special-openings/', AdminSpecialOpeningDateView.as_view(), name='admin-special-opening-dates'),
    path('admin/dates/special-openings/<int:pk>/', AdminSpecialOpeningDateView.as_view(), name='admin-special-opening-dates-detail'),

    # Aliases under admin/services/dates/
    path('admin/services/dates/', AdminDatesOverviewView.as_view(), name='admin-services-dates-overview'),
    path('admin/services/dates/blocked/', AdminBlockDateView.as_view(), name='admin-services-blocked-dates'),
    path('admin/services/dates/blocked/<int:pk>/', AdminBlockDateView.as_view(), name='admin-services-blocked-dates-detail'),
    path('admin/services/dates/special-openings/', AdminSpecialOpeningDateView.as_view(), name='admin-services-special-opening-dates'),
    path('admin/services/dates/special-openings/<int:pk>/', AdminSpecialOpeningDateView.as_view(), name='admin-services-special-opening-dates-detail'),

    # Admin Contact, Legal & Support Messages
    path('admin/contact-info/', ContactInfoView.as_view(), name='admin-contact-info'),
    path('admin/privacy-policy/', PrivacyPolicyView.as_view(), name='admin-privacy-policy'),
    path('admin/terms-and-conditions/', TermsAndConditionsView.as_view(), name='admin-terms-and-conditions'),
    path('admin/support-messages/', SupportMessageView.as_view(), name='admin-support-messages'),
    path('admin/support-messages/<int:pk>/', SupportMessageView.as_view(), name='admin-support-messages-detail'),
]
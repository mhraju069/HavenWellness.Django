from django.urls import path
from .views import (
    UserDashboardView,
    AdminServiceDetailView,
    ServiceCRUDView,
    ServiceOpeningHoursView,
    ServiceFeatureManageView,
    AdminBookingsView,
    AdminPaymentsView,
)
from services.views import AllServicesView

urlpatterns = [
    path('', UserDashboardView.as_view(), name='user-dashboard-root'),
    path('user/', UserDashboardView.as_view(), name='user-dashboard'),
    path('admin/bookings/', AdminBookingsView.as_view(), name='admin-bookings-list'),
    path('admin/bookings/<str:booking_id>/', AdminBookingsView.as_view(), name='admin-booking-detail'),
    path('admin/payments/', AdminPaymentsView.as_view(), name='admin-payments'),
    path('admin/services/', AllServicesView.as_view(), name='service-list'),
    path('admin/services/manage/', ServiceCRUDView.as_view(), name='admin-service-crud'),
    path('admin/services/manage/<int:pk>/', ServiceCRUDView.as_view(), name='admin-service-crud-detail'),
    path('admin/services/settings/', ServiceOpeningHoursView.as_view(), name='admin-service-settings'),
    path('admin/services/settings/<int:setting_id>/', ServiceOpeningHoursView.as_view(), name='admin-service-settings-detail'),
    path('admin/services/features/', ServiceFeatureManageView.as_view(), name='admin-service-features'),
    path('admin/services/features/<int:feature_id>/', ServiceFeatureManageView.as_view(), name='admin-service-features-detail'),
    path('admin/services/details/', AdminServiceDetailView.as_view(), name='admin-service-detail-query'),
    path('admin/services/<str:service_type>/', AdminServiceDetailView.as_view(), name='admin-service-detail'),
]
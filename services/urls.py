from django.urls import path
from .views import (
    AllServicesView, SaunaServiceView, ActivitiesView, SaltRoomView,
    AddOnExtraView, EventInquiryView, ServicePackageView, MembershipPlanView,
    ServiceScheduleView
)

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('sauna/', SaunaServiceView.as_view()),
    path('activities/', ActivitiesView.as_view()),
    path('salt-room/', SaltRoomView.as_view()),
    path('extras/', AddOnExtraView.as_view()),
    path('events/inquiry/', EventInquiryView.as_view()),
    path('packages/', ServicePackageView.as_view()),
    path('memberships/', MembershipPlanView.as_view()),
    path('schedules/', ServiceScheduleView.as_view()),
]
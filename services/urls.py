from django.urls import path
from .views import *
from dashboards.views import (
    AdminDatesOverviewView,
    AdminBlockDateView,
    AdminSpecialOpeningDateView,
)

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('<int:pk>/', AllServicesView.as_view()),
    path('details/', ServiceDetailView.as_view()),
    path('details/<str:service_type>/', ServiceDetailView.as_view()),
    path('slots/', GetSlotView.as_view()),
    path('slots/<str:service_type>/', GetSlotView.as_view()),
    path('get_slot/', GetSlotView.as_view()),

    # Date Management APIs
    path('dates/', AdminDatesOverviewView.as_view(), name='services-dates-overview'),
    path('dates/blocked/', AdminBlockDateView.as_view(), name='services-blocked-dates'),
    path('dates/blocked/<int:pk>/', AdminBlockDateView.as_view(), name='services-blocked-dates-detail'),
    path('dates/special-openings/', AdminSpecialOpeningDateView.as_view(), name='services-special-opening-dates'),
    path('dates/special-openings/<int:pk>/', AdminSpecialOpeningDateView.as_view(), name='services-special-opening-dates-detail'),
]
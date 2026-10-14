from django.urls import path
from .views import *

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('<int:pk>/', AllServicesView.as_view()),
    path('details/', ServiceDetailView.as_view()),
    path('details/<str:service_type>/', ServiceDetailView.as_view()),
    path('slots/', GetSlotView.as_view()),
    path('slots/<str:service_type>/', GetSlotView.as_view()),
    path('get_slot/', GetSlotView.as_view()),
]
from django.urls import path
from .views import *

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('details/<str:service_type>/', ServiceDetailView.as_view()),
]
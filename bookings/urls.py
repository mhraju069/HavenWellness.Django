from django.urls import path
from .views import *

urlpatterns = [
    path('slots/', TimeSlotAPIView.as_view()),
]       
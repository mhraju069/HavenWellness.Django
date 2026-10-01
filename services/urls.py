from django.urls import path
from .views import *

urlpatterns = [
    path('exclude-date/', ExcludeDateAPIView.as_view()),
    path('exclude-date/<int:pk>/', ExcludeDateDestroyAPIView.as_view()),
]
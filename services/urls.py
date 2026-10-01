from django.urls import path
from .views import *

urlpatterns = [
    path('service/sauna/', SaunaServiceView.as_view()),
    # path('service/sauna/exclude-date/', ExcludeDateAPIView.as_view()),
    # path('service/sauna/exclude-date/<int:pk>/', ExcludeDateDestroyAPIView.as_view()),
]
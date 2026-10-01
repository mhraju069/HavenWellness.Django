from django.urls import path
from .views import *

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('sauna/', SaunaServiceView.as_view()),
]
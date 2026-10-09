from django.urls import path
from .views import *

urlpatterns = [
    path('', AllServicesView.as_view()),
    path('sauna/', SaunaServiceView.as_view()),
    path('activities/', ActivitiesView.as_view()),
    path('saltroom/', SaltroomServiceView.as_view()),
    path('packages/', PackagesView.as_view()),
]
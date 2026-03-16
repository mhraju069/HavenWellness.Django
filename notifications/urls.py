from django.urls import path
from .views import DeviceRegisterView, NotificationView

urlpatterns = [
    path('register-device/', DeviceRegisterView.as_view(), name='device_register'),
    path('', NotificationView.as_view(), name='notification'),
]
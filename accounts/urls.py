from django.urls import path
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    path('user/', UserRetrieveUpdateDestroyView.as_view(), name='user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp/', OtpVerifyView.as_view(), name='verify_otp'),
    path('get-otp/', GetOtpView.as_view(), name='get_otp'),
    path("",FirebaseLoginView.as_view(),name="firebase_login"),
]
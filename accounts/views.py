import requests
import jwt
from .models import *
from .helper import *
from .serializers import *
from django.utils.text import slugify
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


@extend_schema(
    tags=['Accounts'],
    summary="Retrieve, update or delete the authenticated user profile",
    responses={200: UserProfileSerializer}
)
class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return User.objects.filter(email=self.request.user.email).first()


@extend_schema(
    tags=['Accounts'],
    summary="Request OTP email verification code",
    request=GetOtpRequestSerializer,
    responses={
        200: GetOtpResponseSerializer,
        400: GetOtpResponseSerializer,
    }
)
class GetOtpView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = GetOtpRequestSerializer

    def post(self, request):
        serializer = GetOtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        
        if not email:
            return Response(
                {"status": False, "log": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        res = send_otp(email)

        if res['status']:
            return Response({"status": True, "log": res['log']}, status=status.HTTP_200_OK)
        else:
            return Response({"status": False, "log": res['log']}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Accounts'],
    summary="Verify OTP code and receive JWT tokens",
    request=OtpVerifyRequestSerializer,
    responses={
        200: OtpVerifyResponseSerializer,
        400: GetOtpResponseSerializer,
        403: GetOtpResponseSerializer,
        404: GetOtpResponseSerializer,
    }
)
class OtpVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OtpVerifyRequestSerializer

    def post(self, request):
        serializer = OtpVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        otp_code = serializer.validated_data.get('otp_code')

        result = verify_otp(email, otp_code)

        if result['status']:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"status": False, "log": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserProfileSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            status_code = status.HTTP_403_FORBIDDEN if "Too many attempts" in result['log'] else status.HTTP_400_BAD_REQUEST
            return Response({"status": False, "log": result['log']}, status=status_code)


@extend_schema(
    tags=['Accounts'],
    summary="Register a new user",
    request=RegisterSerializer,
    responses={
        201: AuthResponseSerializer,
        400: AuthResponseSerializer,
    }
)
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')
        name = serializer.validated_data.get('name', '')

        if User.objects.filter(email=email).exists():
            return Response(
                {"status": False, "log": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            name=name,
            is_active=False
        )

        send_otp(user.email)

        return Response({
            "status": True,
            "log": "Registration successful. OTP sent to email for account activation.",
            "user": UserProfileSerializer(user, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Accounts'],
    summary="Login user with email and password",
    request=LoginSerializer,
    responses={
        200: AuthResponseSerializer,
        400: AuthResponseSerializer,
        403: AuthResponseSerializer,
    }
)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"status": False, "log": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(password):
            return Response(
                {"status": False, "log": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if getattr(user, 'block', False):
            return Response(
                {"status": False, "log": "User account is suspended."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.is_active:
            send_otp(user.email)
            return Response(
                {"status": False, "log": "Account is inactive. OTP has been sent to your email for verification."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "status": True,
            "log": "Login successful.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user, context={'request': request}).data,
        }, status=status.HTTP_200_OK)

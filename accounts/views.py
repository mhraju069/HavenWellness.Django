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

try:
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None


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


@extend_schema(
    tags=['Accounts'],
    summary="Firebase Social Authentication (Google, Apple, Phone, etc.)",
    description="Accepts Firebase ID token verified on client-side and returns backend JWT access & refresh tokens.",
    request=FirebaseSocialAuthSerializer,
    responses={
        200: AuthResponseSerializer,
        400: AuthResponseSerializer,
        403: AuthResponseSerializer,
        500: AuthResponseSerializer,
    }
)
class FirebaseSocialAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = FirebaseSocialAuthSerializer

    def post(self, request):
        serializer = FirebaseSocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token = serializer.validated_data.get('id_token')
        role = serializer.validated_data.get('role', 'user')

        if not firebase_auth:
            return Response(
                {"status": False, "log": "Firebase SDK is not installed or configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
        except Exception as e:
            return Response(
                {"status": False, "log": f"Invalid or expired Firebase token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        name = decoded_token.get('name') or ''
        picture = decoded_token.get('picture')

        # If email is not present in token (e.g., phone login or hidden Apple ID)
        if not email:
            email = f"{firebase_uid}@firebaseuser.com"

        # Check existing user by email or UID
        user = User.objects.filter(email=email).first()
        created = False

        if not user and firebase_uid:
            user = User.objects.filter(uid=firebase_uid).first()

        if not user:
            user = User.objects.create_user(
                email=email,
                uid=firebase_uid,
                name=name,
                role='user',
                is_active=True
            )
            created = True
        else:
            # Sync UID and activate if not already set
            update_fields = []
            if not user.uid and firebase_uid:
                user.uid = firebase_uid
                update_fields.append('uid')
            if not user.is_active:
                user.is_active = True
                update_fields.append('is_active')
            if not user.name and name:
                user.name = name
                update_fields.append('name')
            if update_fields:
                user.save(update_fields=update_fields)

        # Download profile image if newly created and picture URL exists
        if created and picture and not user.image:
            try:
                img_res = requests.get(picture, timeout=5)
                if img_res.status_code == 200:
                    clean_name = slugify(user.name or email.split('@')[0])
                    user.image.save(f"{clean_name}-firebase.jpg", ContentFile(img_res.content), save=True)
            except Exception:
                pass

        if getattr(user, 'block', False):
            return Response(
                {"status": False, "log": "User account is suspended."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "status": True,
            "log": "Authentication successful.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user, context={'request': request}).data,
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Accounts'],
    summary="Send OTP for Forgot Password",
    description="Sends a 4-digit OTP code to the user's registered email address to verify password reset request.",
    request=ForgotPasswordRequestSerializer,
    responses={
        200: GetOtpResponseSerializer,
        400: GetOtpResponseSerializer,
        404: GetOtpResponseSerializer,
    }
)
class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordRequestSerializer

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"status": False, "log": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        res = send_otp(email)
        if res.get('status'):
            return Response({
                "status": True,
                "log": f"Password reset OTP sent successfully to {email}."
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": False,
                "log": res.get('log', "Failed to send OTP.")
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Accounts'],
    summary="Reset Password with OTP verification",
    description="Verifies the OTP code received via email and updates the user's password.",
    request=ResetPasswordRequestSerializer,
    responses={
        200: GetOtpResponseSerializer,
        400: GetOtpResponseSerializer,
        404: GetOtpResponseSerializer,
    }
)
class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordRequestSerializer

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        otp_code = serializer.validated_data.get('otp_code')
        new_password = serializer.validated_data.get('new_password')

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"status": False, "log": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            otp_obj = OTP.objects.filter(user=user).latest('created_at')
        except OTP.DoesNotExist:
            return Response(
                {"status": False, "log": "No OTP request found for this account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response(
                {"status": False, "log": "OTP has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.otp != otp_code:
            return Response(
                {"status": False, "log": "Invalid OTP code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # OTP is valid: update password, activate user if needed, and delete OTP
        user.set_password(new_password)
        if not user.is_active:
            user.is_active = True
        user.save()

        otp_obj.delete()

        return Response({
            "status": True,
            "log": "Password has been reset successfully. You can now login with your new password."
        }, status=status.HTTP_200_OK)


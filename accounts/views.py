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
from firebase_admin import auth as firebase_auth
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
    summary="Authenticate or register user via Firebase ID Token",
    parameters=[
        OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Firebase ID Token", required=True),
        OpenApiParameter("oauth", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="Whether login is via OAuth provider", default=True),
    ],
    request=FirebaseLoginRequestSerializer,
    responses={
        200: FirebaseLoginResponseSerializer,
        400: GetOtpResponseSerializer,
    }
)
class FirebaseLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = FirebaseLoginRequestSerializer

    def post(self, request):
        id_token = request.query_params.get('token')
        oauth_str = request.query_params.get('oauth', 'true')
        oauth = str(oauth_str).lower() in ['true', '1']

        if not id_token:
            return Response({'status': False, 'log': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            decoded_token = firebase_auth.verify_id_token(id_token) if firebase_auth else {'uid': 'mock-uid', 'email': 'user@example.com'}
        except Exception as e:
            return Response({'status': False, 'log': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        
        if not email:
            return Response({'status': False, 'log': 'Email not provided by Firebase'}, status=status.HTTP_400_BAD_REQUEST)
            
        name = decoded_token.get('name')
        profile_image_url = decoded_token.get('picture')

        if oauth:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "uid": uid,
                    'name': name,
                    'is_active': True,
                    'password': make_password(None),
                },
            )
            if created and profile_image_url:
                try:
                    img_response = requests.get(profile_image_url, timeout=5)
                    if img_response.status_code == 200:
                        file_name = f"{slugify(name or email.split('@')[0])}-profile.jpg"
                        user.image.save(
                            file_name,
                            ContentFile(img_response.content),
                            save=True,
                        )
                except Exception:
                    pass
        else:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "uid": uid,
                    'name': request.data.get('name') or "",
                    'is_active': False,
                    'password': make_password(uid),
                }
            )
            if not user.is_active:
                send_otp(user.email)

        if user:
            token = RefreshToken.for_user(user)
            return Response({
                'access': str(token.access_token),
                'refresh': str(token),
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'status': True,
                'active': user.is_active,
                'log': 'Login successful'
            }, status=status.HTTP_200_OK)
        else:
            return Response({'status': False, 'log': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)

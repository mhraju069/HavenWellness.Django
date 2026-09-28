from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    messaging = None

from .models import Device, Notification
from .serializers import (
    DeviceSerializer,
    NotificationSerializer,
    DeviceRegisterResponseSerializer,
    NotificationListResponseSerializer,
)


@extend_schema(
    tags=['Notifications'],
    summary="Register device token for push notifications",
    parameters=[
        OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY, description="FCM Device token", required=True),
    ],
    responses={
        200: DeviceRegisterResponseSerializer,
        400: OpenApiTypes.OBJECT,
    }
)
class DeviceRegisterView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceSerializer

    def post(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token not found'}, status=status.HTTP_400_BAD_REQUEST)

        Device.objects.get_or_create(user=request.user, token=token)
        return Response({'message': 'Device registered successfully'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Get user notifications list",
    responses={200: NotificationListResponseSerializer}
)
class NotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        return Response({'notifications': NotificationSerializer(notifications, many=True).data})


def send_bulk_notification(tokens, title, body):
    if not messaging:
        return
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )
    response = messaging.send_each_for_multicast(message)
    print(f"✅ Success: {response.success_count}, ❌ Failed: {response.failure_count}")


def send_push_notification(token, title, body, data=None):
    if not messaging:
        return False
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data=data or {},
    )

    try:
        response = messaging.send(message)
        print(f"✅ Notification sent: {response}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def notify_user(user, title, body):
    devices = Device.objects.filter(user=user)
    obj = Notification.objects.create(user=user, title=title, body=body)
    for device in devices:
        send_push_notification(
            token=device.token,
            title=title,
            body=body,
        )
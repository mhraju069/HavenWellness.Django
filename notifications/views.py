import json
from django.utils import timezone
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
    UnreadCountResponseSerializer,
    MarkReadResponseSerializer,
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
        token = request.query_params.get('token') or request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        Device.objects.get_or_create(user=request.user, token=token)
        return Response({'message': 'Device registered successfully'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Get user notifications list",
    parameters=[
        OpenApiParameter("is_read", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="Filter by read status (true/false)", required=False),
        OpenApiParameter("type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by notification_type", required=False),
    ],
    responses={200: NotificationListResponseSerializer}
)
class NotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get(self, request):
        queryset = Notification.objects.filter(user=request.user)

        is_read_param = request.query_params.get('is_read')
        if is_read_param is not None:
            if is_read_param.lower() in ['true', '1']:
                queryset = queryset.filter(is_read=True)
            elif is_read_param.lower() in ['false', '0']:
                queryset = queryset.filter(is_read=False)

        type_param = request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(notification_type=type_param)

        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        total_count = queryset.count()

        return Response({
            'unread_count': unread_count,
            'total_count': total_count,
            'notifications': NotificationSerializer(queryset, many=True).data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Get count of unread notifications",
    responses={200: UnreadCountResponseSerializer}
)
class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Mark single notification as read",
    responses={200: MarkReadResponseSerializer}
)
class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])

        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'message': 'Notification marked as read',
            'unread_count': unread_count
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Mark all notifications as read",
    responses={200: MarkReadResponseSerializer}
)
class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({
            'message': 'All notifications marked as read',
            'updated_count': updated,
            'unread_count': 0
        }, status=status.HTTP_200_OK)


def send_bulk_notification(tokens, title, body):
    if not messaging:
        return
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )
    try:
        response = messaging.send_each_for_multicast(message)
        print(f"✅ FCM Multicast Success: {response.success_count}, ❌ Failed: {response.failure_count}")
    except Exception as e:
        print(f"❌ FCM Multicast Error: {e}")


def send_push_notification(token, title, body, data=None):
    if not messaging:
        return False
    # Ensure data values are strings for FCM payload
    fcm_data = {str(k): str(v) for k, v in (data or {}).items()}
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data=fcm_data,
    )

    try:
        response = messaging.send(message)
        print(f"✅ Notification sent: {response}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def notify_user(user, title, body, notification_type='general', link=None, data=None):
    """
    Central helper to:
    1. Create Notification record in Database
    2. Broadcast real-time message via Django Channels WebSocket (Redis channel layer)
    3. Send mobile FCM push notification to user's registered devices
    """
    if data is None:
        data = {}

    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        notification_type=notification_type,
        link=link,
        data=data,
    )

    unread_count = Notification.objects.filter(user=user, is_read=False).count()

    # 1. Real-time WebSocket dispatch via Channels
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"user_notifications_{user.id}"
            serialized_data = NotificationSerializer(notification).data
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "notification_message",
                    "payload": {
                        "notification": serialized_data,
                        "unread_count": unread_count,
                    }
                }
            )
    except Exception as e:
        print(f"⚠️ WebSocket dispatch failed: {e}")

    # 2. Push Notification via FCM
    devices = Device.objects.filter(user=user)
    fcm_payload = {
        "id": str(notification.id),
        "notification_type": notification_type,
        "link": link or "",
        "unread_count": str(unread_count),
    }
    for device in devices:
        send_push_notification(
            token=device.token,
            title=title,
            body=body,
            data=fcm_payload,
        )

    return notification
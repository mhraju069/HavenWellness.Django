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


from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()



@extend_schema(
    tags=['Notifications'],
    summary="Get user or admin notifications list",
    parameters=[
        OpenApiParameter("is_read", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="Filter by read status (true/false)", required=False),
        OpenApiParameter("type", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by notification_type", required=False),
        OpenApiParameter("scope", OpenApiTypes.STR, OpenApiParameter.QUERY, description="For admins: 'admin' (admin alerts only), 'user' (personal only), or default all visible", required=False),
    ],
    responses={200: NotificationListResponseSerializer}
)
class NotificationView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get(self, request):
        user = request.user
        is_admin = getattr(user, 'role', '') == 'admin' or user.is_staff or user.is_superuser

        scope = request.query_params.get('scope')

        if is_admin:
            if scope == 'admin':
                queryset = Notification.objects.filter(Q(audience='admin') | Q(user=user, audience='user'))
            elif scope == 'user':
                queryset = Notification.objects.filter(user=user, audience='user')
            else:
                # By default, admins see both their direct notifications and admin-broadcast alerts
                queryset = Notification.objects.filter(Q(user=user) | Q(audience='admin') | Q(audience='all'))
        else:
            # Regular users see their own notifications and any universal broadcast
            queryset = Notification.objects.filter(Q(user=user, audience='user') | Q(audience='all'))

        is_read_param = request.query_params.get('is_read')
        if is_read_param is not None:
            if is_read_param.lower() in ['true', '1']:
                queryset = queryset.filter(is_read=True)
            elif is_read_param.lower() in ['false', '0']:
                queryset = queryset.filter(is_read=False)

        type_param = request.query_params.get('type')
        if type_param:
            queryset = queryset.filter(notification_type=type_param)

        unread_count = queryset.filter(is_read=False).count()
        total_count = queryset.count()

        return Response({
            'unread_count': unread_count,
            'total_count': total_count,
            'notifications': NotificationSerializer(queryset, many=True).data
        }, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Get count of unread notifications",
    parameters=[
        OpenApiParameter("scope", OpenApiTypes.STR, OpenApiParameter.QUERY, description="For admins: 'admin', 'user', or all", required=False),
    ],
    responses={200: UnreadCountResponseSerializer}
)
class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_admin = getattr(user, 'role', '') == 'admin' or user.is_staff or user.is_superuser
        scope = request.query_params.get('scope')

        if is_admin:
            if scope == 'admin':
                queryset = Notification.objects.filter(Q(audience='admin') | Q(user=user, audience='user'))
            elif scope == 'user':
                queryset = Notification.objects.filter(user=user, audience='user')
            else:
                queryset = Notification.objects.filter(Q(user=user) | Q(audience='admin') | Q(audience='all'))
        else:
            queryset = Notification.objects.filter(Q(user=user, audience='user') | Q(audience='all'))

        unread_count = queryset.filter(is_read=False).count()
        return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Notifications'],
    summary="Mark single notification as read",
    responses={200: MarkReadResponseSerializer}
)
class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = request.user
        is_admin = getattr(user, 'role', '') == 'admin' or user.is_staff or user.is_superuser

        try:
            if is_admin:
                notification = Notification.objects.get(Q(pk=pk) & (Q(user=user) | Q(audience='admin') | Q(audience='all')))
            else:
                notification = Notification.objects.get(pk=pk, user=user)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])

        if is_admin:
            unread_count = Notification.objects.filter(Q(user=user) | Q(audience='admin') | Q(audience='all'), is_read=False).count()
        else:
            unread_count = Notification.objects.filter(user=user, is_read=False).count()

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
        user = request.user
        is_admin = getattr(user, 'role', '') == 'admin' or user.is_staff or user.is_superuser

        if is_admin:
            updated = Notification.objects.filter(
                Q(user=user) | Q(audience='admin') | Q(audience='all'),
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
        else:
            updated = Notification.objects.filter(
                Q(user=user, audience='user') | Q(audience='all'),
                is_read=False
            ).update(is_read=True, read_at=timezone.now())

        return Response({
            'message': 'All notifications marked as read',
            'updated_count': updated,
            'unread_count': 0
        }, status=status.HTTP_200_OK)


def send_bulk_notification(tokens, title, body):
    if not messaging or not tokens:
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
    if not messaging or not token:
        return False
    # Ensure all data values are strings for FCM payload
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
        print(f"✅ FCM Notification sent: {response}")
        return True
    except Exception as e:
        print(f"❌ FCM Error: {e}")
        return False


def notify_user(user, title, body, notification_type='general', link=None, data=None):
    """
    User-specific notification dispatch:
    1. Creates Notification in DB
    2. Sends real-time WebSocket to user's channel group
    3. Sends FCM push notification to user's devices
    """
    if data is None:
        data = {}

    notification = Notification.objects.create(
        user=user,
        audience='user',
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
        print(f"⚠️ User WebSocket dispatch failed: {e}")

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


def notify_admins(title, body, notification_type='general', link=None, data=None):
    """
    Admin-wide notification dispatch:
    1. Creates an admin Notification record in DB (audience='admin')
    2. Broadcasts real-time WebSocket to 'admin_notifications' channel group
    3. Sends FCM push notification to all admin devices
    """
    if data is None:
        data = {}

    notification = Notification.objects.create(
        user=None,
        audience='admin',
        title=title,
        body=body,
        notification_type=notification_type,
        link=link,
        data=data,
    )

    admin_unread_count = Notification.objects.filter(audience='admin', is_read=False).count()

    # 1. Real-time WebSocket dispatch to admin group
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            serialized_data = NotificationSerializer(notification).data
            async_to_sync(channel_layer.group_send)(
                "admin_notifications",
                {
                    "type": "notification_message",
                    "payload": {
                        "notification": serialized_data,
                        "unread_count": admin_unread_count,
                    }
                }
            )
    except Exception as e:
        print(f"⚠️ Admin WebSocket dispatch failed: {e}")

    # 2. Push Notification to all admin devices
    admin_users = User.objects.filter(Q(role='admin') | Q(is_staff=True) | Q(is_superuser=True))
    admin_devices = Device.objects.filter(user__in=admin_users)
    tokens = list(admin_devices.values_list('token', flat=True))

    if tokens:
        send_bulk_notification(
            tokens=tokens,
            title=title,
            body=body
        )

    return notification
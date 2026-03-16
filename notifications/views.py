import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Device
from rest_framework.views import APIView


class DeviceRegisterView(APIView):
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token not found'}, status=400)

        Device.objects.get_or_create(user=request.user, token=token)
        return Response({'message': 'Device registered successfully'})


def send_bulk_notification(tokens, title, body):
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )
    response = messaging.send_each_for_multicast(message)
    print(f"✅ Success: {response.success_count}, ❌ Failed: {response.failure_count}")


def send_push_notification(token, title, body, data=None):

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
    for device in devices:
        send_push_notification(
            token=device.token,
            title=title,
            body=body,
        )
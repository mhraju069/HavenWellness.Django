import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Connection URL: ws://<host>/ws/notifications/?token=<jwt_token>
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        self.user = user
        self.user_group_name = f"user_notifications_{self.user.id}"

        # Join personal user notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # If user is admin/staff, join the broadcast admin notification group
        is_admin_user = getattr(self.user, 'role', '') == 'admin' or getattr(self.user, 'is_staff', False) or getattr(self.user, 'is_superuser', False)
        if is_admin_user:
            self.admin_group_name = "admin_notifications"
            await self.channel_layer.group_add(
                self.admin_group_name,
                self.channel_name
            )

        await self.accept()

        # Send an initial connection acknowledgement
        await self.send_json({
            "type": "connection_established",
            "message": "Connected to real-time notifications.",
            "user_id": self.user.id,
            "role": getattr(self.user, 'role', 'user'),
        })

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        if hasattr(self, "admin_group_name"):
            await self.channel_layer.group_discard(
                self.admin_group_name,
                self.channel_name
            )


    async def receive_json(self, content):
        """
        Handle incoming client messages if needed (e.g. heartbeat ping/pong).
        """
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})

    async def notification_message(self, event):
        """
        Handler called when group_send is triggered with type 'notification_message'.
        """
        payload = event.get("payload", {})
        await self.send_json({
            "type": "notification",
            "data": payload
        })

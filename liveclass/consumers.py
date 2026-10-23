
import json
from datetime import datetime, timezone
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer


class ClassroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"classroom_{self.room_id}"

        query_params = parse_qs(
            self.scope.get("query_string", b"").decode("utf-8")
        )

        self.peer_id = query_params.get("peer_id", [None])[0]
        self.participant_name = query_params.get(
            "name", ["Participant"]
        )[0]
        self.participant_role = query_params.get(
            "role", ["student"]
        )[0]

        self._announced = False

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        if self.peer_id:
            await self.announce_participant()

    async def announce_participant(self):
        if not self.peer_id or self._announced:
            return

        self._announced = True

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "peer_joined",
                "peer_id": self.peer_id,
                "name": self.participant_name,
                "role": self.participant_role,
            },
        )

    async def disconnect(self, close_code):
        if self.peer_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "peer_left",
                    "peer_id": self.peer_id,
                },
            )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        message_type = data.get("type")

        # JOIN
        if message_type == "join":
            supplied_peer_id = data.get("peer_id")

            if supplied_peer_id:
                self.peer_id = str(supplied_peer_id)

            self.participant_name = data.get(
                "name", self.participant_name
            )
            self.participant_role = data.get(
                "role", self.participant_role
            )

            await self.announce_participant()
            return

        # CLASSROOM CHAT
        if message_type == "chat-message":
            message_text = data.get("message", data.get("text", ""))

            if not isinstance(message_text, str):
                return

            message_text = message_text.strip()

            if not message_text or len(message_text) > 2000:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "peer_id": str(self.peer_id or ""),
                    "name": self.participant_name,
                    "role": self.participant_role,
                    "message": message_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return

        # PARTICIPANT INFORMATION
        if message_type == "participant-info":
            target_peer_id = data.get("target_peer_id")

            if not target_peer_id or not self.peer_id:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "participant_info",
                    "target_peer_id": str(target_peer_id),
                    "peer_id": str(self.peer_id),
                    "name": self.participant_name,
                    "role": self.participant_role,
                },
            )
            return

        # CAMERA AND MICROPHONE STATE
        if message_type == "media-state":
            if not self.peer_id:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "media_state",
                    "peer_id": str(self.peer_id),
                    "name": self.participant_name,
                    "role": self.participant_role,
                    "camera_on": data.get("camera_on", True),
                    "microphone_on": data.get(
                        "microphone_on", True
                    ),
                },
            )
            return

        # WEBRTC SIGNALING
        if message_type in ("offer", "answer", "ice-candidate"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_message",
                    "sender_channel": self.channel_name,
                    "message": data,
                },
            )
            return

        # LEAVE
        if message_type == "leave":
            if self.peer_id:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "peer_left",
                        "peer_id": str(self.peer_id),
                    },
                )

    async def chat_message(self, event):
        # Send to every participant in this room, including the sender.
        await self.send(
            text_data=json.dumps({
                "type": "chat-message",
                "peer_id": event["peer_id"],
                "name": event["name"],
                "role": event["role"],
                "message": event["message"],
                "timestamp": event["timestamp"],
            })
        )

    async def webrtc_message(self, event):
        if event["sender_channel"] == self.channel_name:
            return

        await self.send(text_data=json.dumps(event["message"]))

    async def peer_joined(self, event):
        if str(event["peer_id"]) == str(self.peer_id):
            return

        await self.send(
            text_data=json.dumps({
                "type": "peer-joined",
                "peer_id": event["peer_id"],
                "name": event["name"],
                "role": event["role"],
            })
        )

    async def participant_info(self, event):
        if str(event["target_peer_id"]) != str(self.peer_id):
            return

        await self.send(
            text_data=json.dumps({
                "type": "participant-info",
                "peer_id": event["peer_id"],
                "name": event["name"],
                "role": event["role"],
            })
        )

    async def media_state(self, event):
        if str(event["peer_id"]) == str(self.peer_id):
            return

        await self.send(
            text_data=json.dumps({
                "type": "media-state",
                "peer_id": event["peer_id"],
                "name": event["name"],
                "role": event["role"],
                "camera_on": event["camera_on"],
                "microphone_on": event["microphone_on"],
            })
        )

    async def peer_left(self, event):
        if str(event["peer_id"]) == str(self.peer_id):
            return

        await self.send(
            text_data=json.dumps({
                "type": "peer-left",
                "peer_id": event["peer_id"],
            })
        )

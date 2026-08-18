import asyncio
import json
import logging
import uuid

from fastapi import WebSocket
from redis.exceptions import RedisError

from app.db.redis import redis_client

logger = logging.getLogger(__name__)


class ConnectionManager:

    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = {}
        self.redis = redis_client
        self.broadcast_channel = "websocket:broadcast"
        self.node_id = uuid.uuid4().hex

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        connections = self.active_connections.get(user_id)
        if connections is None:
            return

        connections.discard(websocket)
        if not connections:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        await self._deliver_locally(user_id, message)

        payload = json.dumps({
            "node_id": self.node_id,
            "user_id": user_id,
            "message": message,
        })
        try:
            await self.redis.publish(self.broadcast_channel, payload)
        except RedisError:
            logger.exception(
                "Redis publish failed (channel=%s); message delivered locally only",
                self.broadcast_channel,
            )

    async def _deliver_locally(self, user_id: int, message: dict) -> None:
        connections = self.active_connections.get(user_id)
        if not connections:
            return

        dead_connections: list[WebSocket] = []

        for websocket in set(connections):
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.append(websocket)

        for websocket in dead_connections:
            self.disconnect(user_id, websocket)


    async def start_listener(self) -> None:

        retry_delay = 1.0
        while True:
            pubsub = self.redis.pubsub()
            try:
                await pubsub.subscribe(self.broadcast_channel)
                retry_delay = 1.0
                logger.info(
                    "Subscribed to %s (node=%s)", self.broadcast_channel, self.node_id
                )

                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message is None:
                        continue

                    try:
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode()
                        payload = json.loads(data)
                    except (KeyError, TypeError, json.JSONDecodeError):
                        logger.warning("Dropping malformed pubsub message: %r", message)
                        continue

                    if payload.get("node_id") == self.node_id:
                        continue  

                    target_user_id = payload.get("user_id")
                    actual_message = payload.get("message")
                    if target_user_id is None or actual_message is None:
                        logger.warning(
                            "Dropping pubsub message without user_id/message: %r", payload
                        )
                        continue

                    await self._deliver_locally(target_user_id, actual_message)
            except asyncio.CancelledError:
                raise
            except RedisError:
                logger.exception(
                    "Redis listener error (channel=%s); reconnecting in %.1fs",
                    self.broadcast_channel,
                    retry_delay,
                )
            finally:
                try:
                    await pubsub.aclose()
                except RedisError:
                    pass

            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30.0)


    async def disconnect_all(self) -> None:
        connections = [
            websocket
            for websockets in self.active_connections.values()
            for websocket in set(websockets)
        ]
        for websocket in connections:
            try:
                await websocket.close(code=1001)
            except Exception:
                pass

        self.active_connections.clear()


manager = ConnectionManager()

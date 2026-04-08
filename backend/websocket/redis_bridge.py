"""
Optional Redis pub/sub bridge for cross-instance websocket fanout.

If redis or connectivity is unavailable, the bridge stays disabled and
the app continues to work in single-instance mode.
"""

import asyncio
import json
import logging
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisBridge:
    """Publish/subscribe bridge for websocket room messages."""

    def __init__(self):
        self._client = None
        self._pubsub = None
        self._listener_task: Optional[asyncio.Task] = None
        self.enabled = False

    async def startup(self, manager) -> None:
        """Initialize redis pubsub listener when redis dependency is available."""
        try:
            import redis.asyncio as redis
        except Exception:
            logger.info("redis.asyncio not installed; websocket fanout disabled")
            return

        try:
            self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._client.ping()
            self._pubsub = self._client.pubsub(ignore_subscribe_messages=True)
            await self._pubsub.psubscribe("ws:room:*")
            self._listener_task = asyncio.create_task(self._listen_loop(manager))
            self.enabled = True
            logger.info("Redis websocket fanout enabled")
        except Exception as exc:
            self.enabled = False
            self._client = None
            self._pubsub = None
            logger.warning("Redis websocket fanout disabled: %s", exc)

    async def shutdown(self) -> None:
        """Stop listener and close redis resources."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None

        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

        self.enabled = False

    async def publish_room(self, room_id: str, message: dict) -> None:
        """Publish a room message for other instances."""
        if not self.enabled or not self._client:
            return
        try:
            payload = json.dumps(message)
            await self._client.publish(f"ws:room:{room_id}", payload)
        except Exception as exc:
            logger.warning("Redis publish failed for room %s: %s", room_id, exc)

    async def _listen_loop(self, manager) -> None:
        """Listen to redis fanout messages and rebroadcast locally."""
        if not self._pubsub:
            return

        while True:
            try:
                event = await self._pubsub.get_message(timeout=1.0)
                if not event:
                    await asyncio.sleep(0.05)
                    continue

                channel = event.get("channel", "")
                data = event.get("data")
                if not channel.startswith("ws:room:"):
                    continue

                room_id = channel.replace("ws:room:", "", 1)
                if isinstance(data, str):
                    message = json.loads(data)
                else:
                    message = data

                await manager.broadcast_to_room(room_id, message, publish=False)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(0.2)

"""Notifications service for in-app alerts and optional FCM push delivery."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Set

from sqlalchemy.orm import Session

from backend.models.notification import Notification, NotificationType


class NotificationsService:
    """Service layer for user notifications and device token registration."""

    # MVP in-memory token store; replace with persistent store in a later migration.
    _device_tokens: Dict[str, Set[str]] = {}

    @staticmethod
    def register_device_token(user_id: str, token: str) -> None:
        if not token:
            return
        NotificationsService._device_tokens.setdefault(str(user_id), set()).add(token)

    @staticmethod
    def get_device_tokens(user_id: str) -> List[str]:
        return list(NotificationsService._device_tokens.get(str(user_id), set()))

    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        trip_id: str | None = None,
    ) -> Notification:
        try:
            notif_type = NotificationType(notification_type)
        except ValueError:
            notif_type = NotificationType.SYSTEM

        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=str(user_id),
            trip_id=trip_id,
            type=notif_type,
            title=title,
            message=message,
            is_read=False,
            sent_via_fcm=False,
            created_at=datetime.utcnow(),
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def list_user_notifications(
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.user_id == str(user_id))
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> Notification | None:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == str(user_id))
            .first()
        )
        if not notification:
            return None

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def send_fcm_push(token: str, title: str, message: str, data: dict | None = None) -> tuple[bool, str]:
        try:
            import firebase_admin
            from firebase_admin import messaging

            if not firebase_admin._apps:
                return False, "firebase_not_initialized"

            msg = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=message),
                data={k: str(v) for k, v in (data or {}).items()},
            )
            response = messaging.send(msg)
            return True, response
        except Exception as exc:  # noqa: BLE001 - best-effort push delivery
            return False, str(exc)

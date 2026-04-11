"""Notifications service for in-app alerts and optional FCM push delivery."""

from __future__ import annotations

import uuid
import requests
from datetime import datetime, timezone
from typing import Dict, List, Set

from sqlalchemy.orm import Session

from backend.models.notification import Notification, NotificationType
from backend.config import settings


class NotificationsService:
    """Service layer for user notifications and device token registration."""

    @staticmethod
    def normalize_india_phone(phone: str) -> str:
        raw = ''.join(ch for ch in str(phone or '').strip() if ch.isdigit() or ch == '+')
        digits = ''.join(ch for ch in raw if ch.isdigit())

        if len(digits) == 12 and digits.startswith('91'):
            local = digits[2:]
        elif len(digits) == 10:
            local = digits
        else:
            raise ValueError('Phone must be a valid India mobile number (10 digits).')

        if local[0] not in {'6', '7', '8', '9'}:
            raise ValueError('India mobile number must start with 6/7/8/9.')

        return f'+91{local}'

    @staticmethod
    def normalize_india_phone_digits(phone: str) -> str:
        normalized = NotificationsService.normalize_india_phone(phone)
        return ''.join(ch for ch in normalized if ch.isdigit())

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
            created_at=datetime.now(timezone.utc),
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
        notification.read_at = datetime.now(timezone.utc)
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

    @staticmethod
    def send_sms_update(phone: str, title: str, message: str) -> tuple[bool, str]:
        if not phone:
            return False, "missing_destination_phone"

        provider = str(settings.PHONE_NOTIFICATION_PROVIDER or "auto").strip().lower()

        if provider in {"callmebot", "whatsapp"}:
            return NotificationsService.send_callmebot_whatsapp(phone, title, message)

        if provider in {"twilio", "sms"}:
            return NotificationsService.send_twilio_sms(phone, title, message)

        # auto mode: prefer free WhatsApp route first, then Twilio if configured.
        ok, result = NotificationsService.send_callmebot_whatsapp(phone, title, message)
        if ok:
            return ok, result

        ok_twilio, result_twilio = NotificationsService.send_twilio_sms(phone, title, message)
        if ok_twilio:
            return ok_twilio, result_twilio

        return False, f"phone_notification_unavailable: {result}; {result_twilio}"

    @staticmethod
    def send_callmebot_whatsapp(phone: str, title: str, message: str) -> tuple[bool, str]:
        api_key = settings.CALLMEBOT_API_KEY
        if not api_key:
            return False, "callmebot_not_configured"

        try:
            phone_digits = NotificationsService.normalize_india_phone_digits(phone)
        except ValueError as exc:
            return False, str(exc)

        body = f"{title}\n{message}".strip()
        url = "https://api.callmebot.com/whatsapp.php"
        try:
            response = requests.get(
                url,
                params={
                    "phone": phone_digits,
                    "text": body,
                    "apikey": api_key,
                },
                timeout=15,
            )
            if response.status_code >= 400:
                return False, response.text
            return True, "sent_via_callmebot_whatsapp"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    @staticmethod
    def send_twilio_sms(phone: str, title: str, message: str) -> tuple[bool, str]:
        sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM_NUMBER

        if not sid or not auth_token or not from_number:
            return False, "twilio_not_configured"

        try:
            normalized_phone = NotificationsService.normalize_india_phone(phone)
        except ValueError as exc:
            return False, str(exc)

        sms_body = f"{title}\n{message}".strip()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

        try:
            response = requests.post(
                url,
                data={
                    "To": normalized_phone,
                    "From": from_number,
                    "Body": sms_body,
                },
                auth=(sid, auth_token),
                timeout=15,
            )
            if response.status_code >= 400:
                return False, response.text
            return True, "sent_via_twilio"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

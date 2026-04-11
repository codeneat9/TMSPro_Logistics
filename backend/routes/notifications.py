"""Notifications routes for device token registration and alert delivery."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_user_optional
from backend.models.user import User
from backend.services.notifications import NotificationsService
from backend.websocket.manager import manager


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _serialize_notification(item):
    notif_type = item.type.value if hasattr(item.type, "value") else str(item.type)
    return {
        "id": item.id,
        "user_id": item.user_id,
        "trip_id": item.trip_id,
        "type": notif_type,
        "title": item.title,
        "message": item.message,
        "is_read": item.is_read,
        "read_at": item.read_at.isoformat() if item.read_at else None,
        "sent_via_fcm": item.sent_via_fcm,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


class DeviceTokenRequest(BaseModel):
    token: str = Field(..., min_length=10)
    platform: str = "android"


class SendNotificationRequest(BaseModel):
    user_id: str
    notification_type: str = "system"
    title: str
    message: str
    trip_id: Optional[str] = None
    send_push: bool = True


class SmsUpdateRequest(BaseModel):
    phone: Optional[str] = Field(default=None, min_length=7)
    trip_id: Optional[str] = None
    status: str = "update"
    title: str
    message: str


@router.post("/device-token", response_model=dict)
async def register_device_token(
    request: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
):
    NotificationsService.register_device_token(current_user.id, request.token)
    return {"registered": True, "platform": request.platform}


@router.get("/me", response_model=dict)
async def my_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = NotificationsService.list_user_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    serialized = [_serialize_notification(item) for item in items]
    return {"items": serialized, "total": len(serialized), "limit": limit, "offset": offset}


@router.patch("/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = NotificationsService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"id": updated.id, "is_read": updated.is_read}


@router.post("/send", response_model=dict)
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_value not in ["admin", "company"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    notification = NotificationsService.create_notification(
        db=db,
        user_id=request.user_id,
        notification_type=request.notification_type,
        title=request.title,
        message=request.message,
        trip_id=request.trip_id,
    )

    await manager.broadcast_notification(
        user_id=request.user_id,
        notification_type=request.notification_type,
        title=request.title,
        message=request.message,
        data={"trip_id": request.trip_id or ""},
    )

    push_results = []
    if request.send_push:
        for token in NotificationsService.get_device_tokens(request.user_id):
            ok, result = NotificationsService.send_fcm_push(
                token=token,
                title=request.title,
                message=request.message,
                data={"trip_id": request.trip_id or ""},
            )
            push_results.append({"token": token[-8:], "ok": ok, "result": result})

    return {
        "created": True,
        "notification_id": notification.id,
        "ws_sent": True,
        "push_results": push_results,
    }


@router.post('/sms-update', response_model=dict)
async def send_sms_update(
    request: SmsUpdateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if current_user:
        role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if role_value not in ["admin", "company", "customer", "driver"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    destination_phone = request.phone or getattr(current_user, "phone", None)
    if not destination_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required for SMS delivery")

    ok, result = NotificationsService.send_sms_update(
        phone=destination_phone,
        title=request.title,
        message=f"Trip {request.trip_id or '-'} status {request.status}: {request.message}",
    )

    return {
        "sent": ok,
        "phone": destination_phone,
        "auth_used": bool(current_user),
        "trip_id": request.trip_id,
        "status": request.status,
        "result": result,
    }

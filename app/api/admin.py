from fastapi import APIRouter, HTTPException, Response, Depends, Request, Cookie, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
import os

import asyncio

from app.services.gemini_usage_stream import subscribe_gemini_usage

from sqlalchemy.orm import Session
from sqlalchemy import select
from models import AdminPushSubscription, AdminNotification

from firebase_admin.exceptions import FirebaseError

from app.services.firebase_service import send_push_notification

from database import get_db

from app.core.config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH
from app.services.session_manager import create_session, delete_session, get_session

from app.api.dependencies import require_admin

from app.services.settings_service import update_bot_settings, get_bot_settings

from app.services.redis_service import get_gemini_usage_last_24h

from app.services.login_protection import (
    is_ip_blocked,
    record_failed_attempt,
    get_retry_after,
    reset_ip,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

password_hash = PasswordHash.recommended()


class LoginRequest(BaseModel):
    username: str
    password: str

class BotSettingsUpdate(BaseModel):
    bot_enabled: bool | None = None
    dm_replies_enabled: bool | None = None
    reel_reactions_enabled: bool | None = None

    memory_mode: str | None = None
    conversation_context_enabled: bool | None = None

    gemini_enabled: bool | None = None
    gemini_model: str | None = None
    gemini_key_mode: str | None = None
    gemini_auto_fallback: bool | None = None

    admin_name: str | None = None
    behavior_mode: str | None = None
    custom_behavior: str | None = None

    reply_style: str | None = None
    response_length: str | None = None
    language_mode: str | None = None

class PushRegistrationRequest(BaseModel):
    fid: str = Field(min_length=1, max_length=255)


@router.post("/login")
def admin_login(
    data: LoginRequest,
    request: Request,
    response: Response,
):
    client_ip = request.client.host

    # Check temporary IP block
    if is_ip_blocked(client_ip):
        retry_after = get_retry_after(client_ip)

        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # Username check
    if data.username != ADMIN_USERNAME:
        record_failed_attempt(client_ip)

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    # Password check
    if not password_hash.verify(data.password, ADMIN_PASSWORD_HASH):
        record_failed_attempt(client_ip)

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    # Successful login → clear failed attempts
    reset_ip(client_ip)

    session_id = create_session(data.username)

    is_production = os.getenv("ENVIRONMENT") == "production"

    response.set_cookie(
        key="admin_session",
        value=session_id,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=60 * 60 * 12,
        path="/",
    )

    return {
        "message": "Login successful",
    }

@router.get("/dashboard")
def admin_dashboard(session=Depends(require_admin)):
    return {
        "message": "Welcome to admin dashboard",
        "username": session["username"]
    }



@router.post("/logout")
def admin_logout(
    response: Response,
    admin_session: str | None = Cookie(default=None),
):
    is_production = os.getenv("ENVIRONMENT") == "production"

    delete_session(admin_session)

    response.delete_cookie(
        key="admin_session",
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        path="/",
    )

    return {
        "message": "Logged out successfully"
    }

@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    settings = get_bot_settings(db)

    return {
        "settings": {
            "bot_enabled": settings.bot_enabled,
            "dm_replies_enabled": settings.dm_replies_enabled,
            "reel_reactions_enabled": settings.reel_reactions_enabled,
            "memory_mode": settings.memory_mode,
            "conversation_context_enabled": settings.conversation_context_enabled,
            "gemini_enabled": settings.gemini_enabled,
            "gemini_model": settings.gemini_model,
            "gemini_key_mode": settings.gemini_key_mode,
            "gemini_auto_fallback": settings.gemini_auto_fallback,
            "admin_name": settings.admin_name,
            "behavior_mode": settings.behavior_mode,
            "custom_behavior": settings.custom_behavior,
            "reply_style": settings.reply_style,
            "response_length": settings.response_length,
            "language_mode": settings.language_mode,
        }
    }

@router.patch("/settings")
def update_settings(
    settings_data: BotSettingsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    updates = settings_data.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No settings provided"
        )

    try:
        settings = update_bot_settings(
            db,
            **updates
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    return {
        "message": "Settings updated successfully",
        "settings": {
            "bot_enabled": settings.bot_enabled,
            "dm_replies_enabled": settings.dm_replies_enabled,
            "reel_reactions_enabled": settings.reel_reactions_enabled,
            "memory_mode": settings.memory_mode,
            "conversation_context_enabled": settings.conversation_context_enabled,
            "gemini_enabled": settings.gemini_enabled,
            "gemini_model": settings.gemini_model,
            "gemini_key_mode": settings.gemini_key_mode,
            "gemini_auto_fallback": settings.gemini_auto_fallback,
            "admin_name": settings.admin_name,
            "behavior_mode": settings.behavior_mode,
            "custom_behavior": settings.custom_behavior,
            "reply_style": settings.reply_style,
            "response_length": settings.response_length,
            "language_mode": settings.language_mode,
        }
    }

@router.get("/gemini-usage")
def get_gemini_usage(
    _: None = Depends(require_admin),
):
    return get_gemini_usage_last_24h()

@router.websocket("/ws/gemini-usage")
async def gemini_usage_websocket(websocket: WebSocket):
    session_id = websocket.cookies.get("admin_session")

    if not get_session(session_id):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    async def send_usage_events():
        async for event in subscribe_gemini_usage():
            await websocket.send_text(event)

    async def wait_for_disconnect():
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                return

    event_task = asyncio.create_task(send_usage_events())
    disconnect_task = asyncio.create_task(wait_for_disconnect())

    try:
        done, pending = await asyncio.wait(
            {event_task, disconnect_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            if not task.cancelled():
                error = task.exception()

                if error is not None:
                    raise error

    except WebSocketDisconnect:
        pass

    finally:
        for task in (event_task, disconnect_task):
            if not task.done():
                task.cancel()

        await asyncio.gather(
            event_task,
            disconnect_task,
            return_exceptions=True,
        )

@router.post("/push/register")
def register_push_subscription(
    data: PushRegistrationRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    fid = data.fid.strip()

    if not fid:
        raise HTTPException(
            status_code=400,
            detail="Firebase Installation ID is required",
        )

    subscription = db.scalar(
        select(AdminPushSubscription).where(
            AdminPushSubscription.fid == fid
        )
    )

    if subscription is None:
        subscription = AdminPushSubscription(
            fid=fid,
            is_active=True,
        )
        db.add(subscription)
    else:
        subscription.is_active = True

    db.commit()

    return {
        "message": "Push registration saved successfully",
    }



@router.post("/push/test")
def test_push_notification(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    subscription = db.scalar(
        select(AdminPushSubscription).where(
            AdminPushSubscription.is_active.is_(True)
        )
    )

    if subscription is None:
        raise HTTPException(
            status_code=404,
            detail="No active push subscription found",
        )

    try:
        message_id = send_push_notification(
            fid=subscription.fid,
            title="InstaGemBot Test",
            body="Push notifications are working!",
            url="/admin/dashboard",
        )
    except FirebaseError as exc:
        raise HTTPException(
            status_code=502,
            detail="Firebase could not send the test notification",
        ) from exc

    return {
        "message": "Test notification sent successfully",
        "message_id": message_id,
    }



@router.get("/notifications")
def get_admin_notifications(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative",
        )

    notifications = (
        db.query(AdminNotification)
        .order_by(
            AdminNotification.created_at.desc(),
            AdminNotification.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    unread_count = (
        db.query(AdminNotification)
        .filter(AdminNotification.is_read.is_(False))
        .count()
    )

    return {
        "notifications": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "message_id": item.message_id,
                "type": item.type,
                "title": item.title,
                "message": item.message,
                "is_read": item.is_read,
                "delivery_status": item.delivery_status,
                "created_at": item.created_at,
            }
            for item in notifications
        ],
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    notification = db.get(AdminNotification, notification_id)

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.is_read = True
    db.commit()

    return {
        "message": "Notification marked as read",
        "notification_id": notification.id,
        "is_read": notification.is_read,
    }


@router.patch("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    unread_notifications = (
        db.query(AdminNotification)
        .filter(AdminNotification.is_read.is_(False))
        .all()
    )

    updated_count = len(unread_notifications)

    for notification in unread_notifications:
        notification.is_read = True

    db.commit()

    return {
        "message": "All notifications marked as read",
        "updated_count": updated_count,
    }

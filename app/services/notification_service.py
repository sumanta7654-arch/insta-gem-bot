import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AdminNotification, AdminPushSubscription, Message
from app.services.firebase_service import send_push_notification


logger = logging.getLogger(__name__)


def create_admin_notification(
    db: Session,
    user_id: int,
    message_id: int,
    notification_message: str,
) -> bool:
    """Save an admin request and send a push notification."""

    notification_message = notification_message.strip()

    if not notification_message:
        return False

    try:
        source_message = db.get(Message, message_id)

        if source_message is None or source_message.user_id != user_id:
            logger.warning(
                "Invalid admin notification source: user_id=%s message_id=%s",
                user_id,
                message_id,
            )
            return False

        existing = (
            db.query(AdminNotification)
            .filter(AdminNotification.message_id == message_id)
            .first()
        )

        if existing:
            logger.info(
                "Admin notification already exists for message_id=%s",
                message_id,
            )
            return True

        notification = AdminNotification(
            user_id=user_id,
            message_id=message_id,
            type="user_admin_request",
            title="A user wants to tell you something",
            message=notification_message,
            is_read=False,
            delivery_status="pending",
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

    except IntegrityError:
        db.rollback()

        existing = (
            db.query(AdminNotification.id)
            .filter(AdminNotification.message_id == message_id)
            .first()
        )

        if existing:
            return True

        logger.exception(
            "Admin notification integrity error for message_id=%s",
            message_id,
        )
        return False

    except Exception:
        db.rollback()
        logger.exception(
            "Failed to save admin notification for message_id=%s",
            message_id,
        )
        return False

    subscriptions = (
        db.query(AdminPushSubscription)
        .filter(AdminPushSubscription.is_active.is_(True))
        .all()
    )

    if not subscriptions:
        logger.warning(
            "Notification %s saved, but no active push subscriptions exist",
            notification.id,
        )
        return True

    delivered_to_fcm = False

    for subscription in subscriptions:
        try:
            send_push_notification(
                fid=subscription.fid,
                title=notification.title,
                body=notification.message,
                url="/",
            )
            delivered_to_fcm = True

        except Exception:
            logger.exception(
                "Push notification failed for subscription_id=%s",
                subscription.id,
            )

    try:
        notification.delivery_status = (
            "sent" if delivered_to_fcm else "failed"
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Could not update delivery status for notification_id=%s",
            notification.id,
        )

    return True

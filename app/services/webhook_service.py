import time
import random

import logging

logger = logging.getLogger(__name__)

from database import SessionLocal
from models import User, Message

from app.services.instagram_service import (
    get_instagram_username,
    send_instagram_message,
    react_to_instagram_message,
)

from app.services.settings_service import get_bot_settings

from app.services.gemini_service import generate_response, analyze_reel

from app.services.redis_service import cache_message

from app.services.notification_service import create_admin_notification

from app.services.conversation_service import (
    get_conversation_context,
    get_user_summary,
    get_conversation_summary,
    get_compression_context,
    save_user_summary,
    update_conversation_summary,
    update_compression_checkpoint,
)

def process_webhook(data):
    db = SessionLocal()

    try:
        settings = get_bot_settings(db)

        if not settings.bot_enabled:
            return

        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):

                message = messaging.get("message", {})

                if message.get("is_echo"):
                    continue


                if not message:
                    continue

                sender_id = messaging.get("sender", {}).get("id")

                user = db.query(User).filter(
                    User.instagram_id == sender_id
                ).first()

                is_new_user = False
                username = None

                if not user:
                    username = get_instagram_username(sender_id)

                    user = User(
                        instagram_id=sender_id,
                        name=username
                    )

                    db.add(user)
                    db.commit()
                    db.refresh(user)

                    is_new_user = True

                else:
                    username = user.name

                message_id = message.get("mid")

                if message_id:
                    existing_message = db.query(Message).filter(
                        Message.instagram_message_id == message_id
                    ).first()

                    if existing_message:
                        continue

                text = message.get("text")

                if text:
                    user_message = Message(
                        user_id=user.id,
                        role="user",
                        content=text,
                        instagram_message_id=message_id
                    )

                    db.add(user_message)
                    db.commit()

                    cache_message(
                        user_id=user.id,
                        role="user",
                        content=text,
                        created_at=user_message.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

                    if not settings.dm_replies_enabled:
                        continue

                    if not settings.gemini_enabled:
                        continue

                    if settings.conversation_context_enabled:
                        context = get_conversation_context(
                            db=db,
                            user_id=user.id
                        )

                        conversation_summary = get_conversation_summary(
                            db=db,
                            user_id=user.id
                        )

                        should_compress, old_context, compressed_message_id = (
                            get_compression_context(
                                db=db,
                                user_id=user.id
                            )
                        )
                    else:
                        context = []
                        conversation_summary = None
                        should_compress = False
                        old_context = None
                        compressed_message_id = None


                    if settings.memory_mode == "disabled":
                        user_summary = None
                    else:
                        user_summary = get_user_summary(
                            db=db,
                            user_id=user.id
                        )

                    start_time = time.perf_counter()

                    response = generate_response(
                        model=settings.gemini_model,
                        context=context,
                        user_summary=user_summary,
                        conversation_summary=conversation_summary,
                        old_context=old_context,
                        username=username,
                        is_new_user=is_new_user,
                        key_mode=settings.gemini_key_mode,
                        auto_fallback=settings.gemini_auto_fallback,
                        settings=settings
                    )
                    if should_compress:
                        response.memory_summary = None

                    if not should_compress:
                        response.conversation_summary = None


                    if (
                        settings.memory_mode == "enabled"
                        and response.memory_summary is not None
                    ):
                        save_user_summary(
                            db=db,
                            user_id=user.id,
                            summary=response.memory_summary
                        )

                    if (
                        settings.conversation_context_enabled
                        and should_compress
                    ):
                        if response.conversation_summary is not None:
                            update_conversation_summary(
                                db=db,
                                user_id=user.id,
                                new_summary=response.conversation_summary
                            )

                        if compressed_message_id is not None:
                            update_compression_checkpoint(
                                db=db,
                                user_id=user.id,
                                message_id=compressed_message_id
                            )

                    gemini_time = time.perf_counter() - start_time

                    logger.info(
                        "gemini_res_time: %s",
                        gemini_time
                    )

                    if (
                        response.admin_notification
                        and response.admin_notification.required
                    ):
                        notification_message = response.admin_notification.message

                        if notification_message:
                            saved = create_admin_notification(
                                db=db,
                                user_id=user.id,
                                message_id=user_message.id,
                                notification_message=notification_message,
                            )

                            if not saved:
                                logger.info(
                                    "Admin notification could not be saved"
                                )

                    reply = response.reply

                    bot_message = Message(
                        user_id=user.id,
                        role="assistant",
                        content=reply
                    )

                    db.add(bot_message)
                    db.commit()

                    cache_message(
                        user_id=user.id,
                        role="assistant",
                        content=reply,
                        created_at=bot_message.created_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

                    send_instagram_message(sender_id, reply)

               #attachtments
                attachments = message.get("attachments", [])

                for attachment in attachments:
                    if attachment.get("type") == "ig_reel":

                        if not settings.reel_reactions_enabled:
                            continue

                        if not settings.gemini_enabled:
                            continue

                        payload = attachment.get("payload", {})

                        reel_url = payload.get("url")
                        reel_title = payload.get("title")

                        reaction = analyze_reel(
                            model=settings.gemini_model,
                            reel_title=reel_title,
                            reel_url=reel_url,
                            key_mode=settings.gemini_key_mode,
                            auto_fallback=settings.gemini_auto_fallback
                        )

                        time.sleep(random.randint(28, 90))

                        if message_id:
                            react_to_instagram_message(
                                recipient_id=sender_id,
                                message_id=message_id,
                                reaction=reaction.reaction
                            )

        return

    finally:
        db.close()
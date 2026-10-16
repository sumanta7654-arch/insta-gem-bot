from sqlalchemy.orm import Session

from models import UserContext, Message

from app.services.redis_service import (
    get_recent_messages,
    get_cached_user_summary,
    cache_user_summary,
    get_cached_conversation_summary,
    cache_conversation_summary,
)

def get_user_summary(
    db: Session,
    user_id: int
) -> str:

    cached_summary = get_cached_user_summary(user_id)

    if cached_summary is not None:
        return cached_summary

    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    if not user_context:
        return ""

    summary = user_context.summary

    if summary:
        cache_user_summary(
            user_id=user_id,
            summary=summary
        )

    return summary

def get_conversation_summary(
    db: Session,
    user_id: int
) -> str:

    cached_summary = get_cached_conversation_summary(user_id)

    if cached_summary is not None:
        return cached_summary

    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    if not user_context:
        return ""

    summary = user_context.conversation_summary or ""

    if summary:
        cache_conversation_summary(
            user_id=user_id,
            summary=summary
        )

    return summary

def update_conversation_summary(
    db: Session,
    user_id: int,
    new_summary: str
):
    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    if not user_context:
        user_context = UserContext(
            user_id=user_id,
            summary="",
            conversation_summary=new_summary
        )
        db.add(user_context)
    else:
        user_context.conversation_summary = new_summary

    db.commit()

    cache_conversation_summary(
        user_id=user_id,
        summary=new_summary
    )

def update_compression_checkpoint(
    db: Session,
    user_id: int,
    message_id: int
):
    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    if user_context:
        user_context.last_compressed_message_id = message_id
    else:
        user_context = UserContext(
            user_id=user_id,
            summary="",
            last_compressed_message_id=message_id
        )
        db.add(user_context)

    db.commit()

def get_compression_context(
    db: Session,
    user_id: int,
    recent_limit: int = 6,
    compression_interval: int = 6
) -> tuple[bool, str, int | None]:

    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.id.asc())
        .all()
    )

    if len(messages) < 12:
        return False, "", None

    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    last_compressed_id = (
        user_context.last_compressed_message_id
        if user_context
        else None
    )

    # First compression
    if last_compressed_id is None:

        old_messages = messages[:-recent_limit]

    # Later compressions
    else:

        new_messages = [
            message
            for message in messages
            if message.id > last_compressed_id
        ]

        if len(new_messages) < compression_interval + recent_limit:
            return False, "", None

        old_messages = new_messages[:-recent_limit]

    if not old_messages:
        return False, "", None

    context = []

    for message in old_messages:
        timestamp = message.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if message.role == "user":
            context.append(
                f"[{timestamp}] User: {message.content}"
            )
        else:
            context.append(
                f"[{timestamp}] Assistant: {message.content}"
            )

    last_old_message_id = old_messages[-1].id

    return (
        True,
        "\n".join(context),
        last_old_message_id
    )

def save_user_summary(
    db: Session,
    user_id: int,
    summary: str
):
    user_context = (
        db.query(UserContext)
        .filter(UserContext.user_id == user_id)
        .first()
    )

    if user_context:
        user_context.summary = summary
    else:
        user_context = UserContext(
            user_id=user_id,
            summary=summary
        )
        db.add(user_context)

    db.commit()

    cache_user_summary(
        user_id=user_id,
        summary=summary
    )

def get_conversation_context(
    db: Session,
    user_id: int,
    limit: int = 6
) -> str:

    cached_messages = get_recent_messages(user_id)

    if cached_messages is not None:
        messages = cached_messages[-limit:]

        context = []

        for message in messages:
            if message["role"] == "user":
                context.append(
                    f'[{message["created_at"]}] User: {message["content"]}'
                )
            else:
                context.append(
                    f'[{message["created_at"]}] Assistant: {message["content"]}'
                )

        return "\n".join(context)

    # Redis cache miss → MySQL fallback

    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )

    messages.reverse()

    context = []

    for message in messages:
        timestamp = message.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if message.role == "user":
            context.append(
                f"[{timestamp}] User: {message.content}"
            )
        else:
            context.append(
                f"[{timestamp}] Assistant: {message.content}"
            )

    return "\n".join(context)


def get_old_conversation_context(
    db: Session,
    user_id: int,
    recent_limit: int = 6
) -> str:

    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.id.asc())
        .all()
    )

    if len(messages) <= recent_limit:
        return ""

    old_messages = messages[:-recent_limit]

    context = []

    for message in old_messages:
        timestamp = message.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        if message.role == "user":
            context.append(
                f"[{timestamp}] User: {message.content}"
            )
        else:
            context.append(
                f"[{timestamp}] Assistant: {message.content}"
            )

    return "\n".join(context)
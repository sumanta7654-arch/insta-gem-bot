from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    instagram_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    context: Mapped["UserContext | None"] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
    uselist=False
)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    instagram_message_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship(
        back_populates="messages"
    )

    

class UserContext(Base):
    __tablename__ = "user_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    last_compressed_message_id: Mapped[int | None] = mapped_column(
       nullable=True
    )

    conversation_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    user: Mapped["User"] = relationship(
        back_populates="context"
    )

class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id"),
        nullable=False,
        unique=True,
        index=True
    )

    type: Mapped[str] = mapped_column(
        String(50),
        default="user_admin_request",
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_read: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    delivery_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship()

    source_message: Mapped["Message"] = relationship()

class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Master controls
    bot_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    dm_replies_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    reel_reactions_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    # Context controls
    memory_mode: Mapped[str] = mapped_column(
        String(20),
        default="enabled",
        nullable=False
    )

    conversation_context_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    # Gemini controls
    gemini_enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    gemini_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    gemini_key_mode: Mapped[str] = mapped_column(
        String(20),
        default="auto",
        nullable=False
    )

    gemini_auto_fallback: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    # Bot identity / behavior
    admin_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    behavior_mode: Mapped[str] = mapped_column(
        String(30),
        default="natural_friendly",
        nullable=False
    )

    custom_behavior: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Response controls
    reply_style: Mapped[str] = mapped_column(
        String(30),
        default="friendly",
        nullable=False
    )

    response_length: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        nullable=False
    )

    language_mode: Mapped[str] = mapped_column(
        String(30),
        default="auto",
        nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


class AdminPushSubscription(Base):
    __tablename__ = "admin_push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)

    fid: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

from sqlalchemy.orm import Session

from models import BotSettings

def get_bot_settings(db: Session) -> BotSettings:
    settings = db.query(BotSettings).first()

    if settings:
        return settings

    settings = BotSettings(
        gemini_model="gemini-3.5-flash-lite",
        admin_name="Sumanta",
        behavior_mode="natural_friendly",
        custom_behavior=None,
        reply_style="friendly",
        response_length="normal",
        language_mode="auto",
        memory_mode="enabled",
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return settings


def update_bot_settings(
    db: Session,
    **updates
) -> BotSettings:
    settings = get_bot_settings(db)

    allowed_fields = {
        "bot_enabled",
        "dm_replies_enabled",
        "reel_reactions_enabled",
        "memory_mode",
        "conversation_context_enabled",
        "gemini_enabled",
        "gemini_model",
        "gemini_key_mode",
        "gemini_auto_fallback",
        "admin_name",
        "behavior_mode",
        "custom_behavior",
        "reply_style",
        "response_length",
        "language_mode",
    }
    allowed_values = {
        "memory_mode": {
            "enabled",
            "read_only",
            "disabled",
        },
        "behavior_mode": {
            "natural_friendly",
            "casual_playful",
            "professional",
            "warm_supportive",
            "minimal_direct",
        },
        "gemini_key_mode": {
            "auto",
            "key1",
            "key2",
        },
        "reply_style": {
        "friendly",
        "casual",
        "professional",
        "direct",
        },
        "response_length": {
            "short",
            "normal",
            "detailed",
        },
        "language_mode": {
            "auto",
            "english",
            "banglish",
            "bengali",
            "hindi",
            "hinglish"
        },
        "gemini_model": {
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
        },
    }

    for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Invalid settings field: {field}")

        if field in allowed_values:
            if value not in allowed_values[field]:
                raise ValueError(
                    f"Invalid value for {field}: {value}"
                )

        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    return settings
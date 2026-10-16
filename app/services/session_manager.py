import secrets
from datetime import datetime, timedelta, timezone


SESSION_DURATION = timedelta(hours=12)

sessions: dict[str, dict] = {}


def create_session(username: str) -> str:
    session_id = secrets.token_urlsafe(32)

    sessions[session_id] = {
        "username": username,
        "expires_at": datetime.now(timezone.utc) + SESSION_DURATION,
    }

    return session_id


def get_session(session_id: str | None):
    if not session_id:
        return None

    session = sessions.get(session_id)

    if not session:
        return None

    if session["expires_at"] <= datetime.now(timezone.utc):
        sessions.pop(session_id, None)
        return None

    return session


def delete_session(session_id: str | None):
    if session_id:
        sessions.pop(session_id, None)
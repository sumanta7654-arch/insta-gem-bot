from fastapi import Cookie, HTTPException

from app.services.session_manager import get_session


def require_admin(admin_session: str | None = Cookie(default=None)):
    session = get_session(admin_session)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return session
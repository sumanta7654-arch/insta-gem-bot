
import firebase_admin
from firebase_admin import credentials, messaging


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(cred)


def send_push_notification(
    fid: str,
    title: str,
    body: str,
    url: str = "/",
) -> str:
    app = get_firebase_app()

    message = messaging.Message(
        fid=fid,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={
            "url": url,
        },
    )

    return messaging.send(message, app=app)

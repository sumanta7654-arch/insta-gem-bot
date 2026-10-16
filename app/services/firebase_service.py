import json
import os

import firebase_admin
from firebase_admin import credentials, messaging


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

        if service_account_json:
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
        else:
            cred = credentials.ApplicationDefault()

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        options = {"projectId": project_id} if project_id else None

        return firebase_admin.initialize_app(cred, options)


def send_push_notification(
    fid: str,
    title: str,
    body: str,
    url: str = "/",
) -> str:
    app = get_firebase_app()

    message = messaging.Message(
        token=fid,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={"url": url},
    )

    return messaging.send(message, app=app)

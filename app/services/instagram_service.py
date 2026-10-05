import requests

from app.core.config import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_API_VERSION,
    INSTAGRAM_ACCOUNT_ID,
)

def get_instagram_username(user_id: str) -> str | None:

    url = (
        f"https://graph.instagram.com/"
        f"{INSTAGRAM_API_VERSION}/"
        f"{user_id}"
    )

    params = {
        "fields": "username",
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    response = requests.get(
        url,
        params=params
    )

    print("Instagram Profile API:", response.status_code)
    print(response.json())

    if response.status_code != 200:
        return None

    return response.json().get("username")

def send_instagram_message(recipient_id: str, text: str):

    url = (
        f"https://graph.instagram.com/"
        f"{INSTAGRAM_API_VERSION}/"
        f"{INSTAGRAM_ACCOUNT_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print("Instagram Send API:", response.status_code)
    print(response.json())


# ---------- React logic ----------

def react_to_instagram_message(
    recipient_id: str,
    message_id: str,
    reaction: str = "❤️"
):
    url = (
        f"https://graph.instagram.com/"
        f"{INSTAGRAM_API_VERSION}/"
        f"{INSTAGRAM_ACCOUNT_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {INSTAGRAM_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "sender_action": "react",
        "payload": {
            "message_id": message_id,
            "reaction": reaction
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print("Instagram Reaction API:", response.status_code)
    print(response.json())
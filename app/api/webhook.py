from fastapi import APIRouter, Request, BackgroundTasks, Query, HTTPException
from fastapi.responses import PlainTextResponse

from app.core.config import WEBHOOK_VERIFY_TOKEN, META_APP_SECRET

import hashlib
import hmac
import json

from app.services.webhook_service import process_webhook

router = APIRouter()

VERIFY_TOKEN = WEBHOOK_VERIFY_TOKEN

@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)

    return PlainTextResponse("Verification failed", status_code=403)

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    if not META_APP_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Webhook signature verification is not configured"
        )

    # Read the exact raw request body
    body = await request.body()

    # Read Meta's signature header
    signature = request.headers.get("x-hub-signature-256")

    if not signature or not signature.startswith("sha256="):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    # Calculate expected HMAC-SHA256 signature
    expected_signature = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures safely
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook signature"
        )

    # Parse JSON only after signature verification
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )

    background_tasks.add_task(process_webhook, data)

    return {"status": "ok"}

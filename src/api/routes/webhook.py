"""POST /api/v1/webhook/{source} — receive and validate inbound webhooks (HUB-003)."""

import hashlib
import hmac
import json

from fastapi import APIRouter, HTTPException, Request, status

from src.adapters.onebox.normalizer import OneBoxNormalizer
from src.adapters.baf.adapter import BafAdapter
from src.config.settings import settings
from src.core.dispatcher import dispatcher
from src.core.logger import get_logger
from src.core.models import HubEvent

router = APIRouter(tags=["webhooks"])
logger = get_logger(__name__)


def _verify_hmac_sha256(body: bytes, signature_header: str) -> bool:
    """Compare received HMAC-SHA256 signature against locally computed one.

    OneBox sends:  X-OneBox-Signature: sha256=<hex_digest>
    """
    secret = settings.onebox_webhook_secret.encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


@router.post(
    "/webhook/{source}",
    status_code=status.HTTP_200_OK,
    summary="Receive inbound webhook from any source",
)
async def receive_webhook(source: str, request: Request) -> dict[str, str]:
    """Accept a webhook, validate signature, enqueue for async processing.

    Returns 200 immediately regardless of downstream processing (ADR-005).
    """
    body = await request.body()

    # ── HMAC validation (OneBox only for now) ──────────────────────────────
    if source == "onebox":
        signature = request.headers.get("X-OneBox-Signature", "")
        if not signature or not _verify_hmac_sha256(body, signature):
            logger.warning(
                "webhook_signature_invalid",
                source=source,
                remote=request.client.host if request.client else "unknown",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing HMAC signature",
            )

    # ── Parse payload ──────────────────────────────────────────────────────
    try:
        payload: dict = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be valid JSON",
        )

    if source == "onebox":
        event = OneBoxNormalizer.to_hub_event(payload)
    elif source == "1c":
        # 1. Store in DB immediately
        db_id = BafAdapter.process_webhook(payload)
        # 2. Normalize for dispatcher (other integrations like TG notification)
        event = HubEvent(
            source=source,
            event_id=db_id,
            event_type="receipt_created",
            payload=payload
        )
    else:
        event = HubEvent(
            source=source,
            event_type=payload.get("event_type", "unknown"),
            payload=payload,
        )

    logger.info(
        "webhook_accepted",
        source=source,
        event_id=event.event_id,
        event_type=event.event_type,
    )

    try:
        dispatcher.dispatch(event)
    except Exception as exc:
        logger.error(
            "dispatcher_failed",
            event_id=event.event_id,
            source=event.source,
            event_type=event.event_type,
            error=str(exc),
        )

    return {"status": "accepted", "event_id": event.event_id}

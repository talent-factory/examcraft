"""
SubscribeFlow Outgoing-Webhook-Receiver für ExamCraft AI (TF-764)

Empfängt email.sent/delivered/bounced/complained von SubscribeFlows
Outgoing-Webhook-System (siehe OutgoingWebhookService im SubscribeFlow-
Repo) und schreibt sie in dieselben EmailEvent/EmailSuppressionList-
Modelle, die zuvor von resend_webhooks.py befüllt wurden.

Signaturformat unterscheidet sich von Resend/Svix: SubscribeFlow signiert
mit HMAC-SHA256 über den rohen JSON-Body, Base64-kodiert, im Header
X-SubscribeFlow-Signature -- kein Timestamp-Präfix.

ROLLOUT-VORAUSSETZUNG (vor dem produktiven Rollout zu entfernen, sobald
verifiziert): email.delivered/.bounced/.complained werden auf
SubscribeFlow-Seite -- Stand des SubscribeFlow-Quellcodes zum Zeitpunkt
dieser Migration -- nur emittiert, wenn dessen EMAIL_PROVIDER=brevo
konfiguriert ist; der SES-Pfad emittiert diese Events nicht, und
SubscribeFlows eigener Default ist "resend". Läuft SubscribeFlow-Prod noch
auf einem anderen Provider, laufen Bounce-/Complaint-Tracking und
Suppression-List-Pflege hier klammheimlich ins Leere -- nur email.sent-
Zeilen akkumulieren, ohne jeden Fehler. Vor dem produktiven Rollout
unbedingt gegen SubscribeFlow-Prod verifizieren
(z.B. `fly ssh console -a subscribeflow-api -C "printenv EMAIL_PROVIDER"`).
Dieser Vertrag (welche Events unter welcher Provider-Konfiguration
emittiert werden) liegt in SubscribeFlows eigener Verantwortung und kann
sich unabhängig von ExamCraft ändern -- bei Zweifeln gegen den aktuellen
SubscribeFlow-Quellcode neu verifizieren, nicht gegen diesen Kommentar.
"""

import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.email_event import (
    EmailEvent,
    EmailEventType,
    _utcnow,
    add_to_suppression_list,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Placeholder recipient used by _recipient_email() when SubscribeFlow's
# payload is missing the 'email' field -- never a real address, so it must
# never be written to EmailSuppressionList.
_UNKNOWN_RECIPIENT = "unknown@unknown.com"


def verify_subscribeflow_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify SubscribeFlow's outgoing-webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        signature: X-SubscribeFlow-Signature header value (Base64).
        secret: Webhook endpoint's signing secret.

    Returns:
        bool: True if signature is valid.

    NOTE: SubscribeFlow's own docs/guides/webhooks.md (as of TF-764)
    describes this differently and WRONGLY -- hexdigest() compared against
    an "sha256={digest}"-prefixed string. This implementation was verified
    directly against SubscribeFlow's actual signing code
    (outgoing_webhook_service.py: raw Base64 digest, no prefix) and matches
    it. If a signature check ever starts failing, do not "fix" this toward
    that doc -- re-verify against the SubscribeFlow source first, or every
    real webhook delivery will start failing signature verification.
    """
    if not signature or not secret:
        return False
    try:
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(expected).decode("utf-8")
        return hmac.compare_digest(signature, expected_b64)
    except (TypeError, ValueError) as e:
        # Narrowed from a bare `except Exception` -- these are the only
        # errors this specific computation can raise (e.g. a non-string
        # secret/signature); fail closed either way.
        logger.error(f"Signature verification error: {e}")
        return False


@router.post("/subscribeflow")
async def subscribeflow_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_subscribeflow_signature: Optional[str] = Header(
        None, alias="X-SubscribeFlow-Signature"
    ),
):
    """Handle SubscribeFlow outgoing-webhook events.

    Events (TF-764 Phase A):
    - email.sent: Email wurde an den ESP übergeben
    - email.delivered: Email wurde zugestellt
    - email.bounced: Bounce (data.hard unterscheidet hard/soft)
    - email.complained: Spam-Beschwerde

    opened/clicked sind hier nicht implementiert, weil SubscribeFlow sie
    (Stand Phase A) noch gar nicht als Outgoing-Webhook-Event emittiert
    (kein EMAIL_OPENED/EMAIL_CLICKED in dessen WebhookEventType) -- keine
    bewusste ExamCraft-seitige Auslassung, sondern eine Upstream-Lücke.

    Security:
    - Verifiziert HMAC-SHA256-Signatur, fail-closed in Produktion ohne
      SUBSCRIBEFLOW_WEBHOOK_SECRET. Die Signatur trägt KEINEN Timestamp
      (kein Replay-Fenster) -- Schutz vor Replay eines mitgeschnittenen
      Payloads kommt ausschliesslich aus der Dedupe-Prüfung unten
      (_event_already_recorded), nicht aus der Signaturprüfung selbst.
    - Speichert die vier oben genannten Event-Typen als Best-Effort-
      Zustelltelemetrie; ein unbekannter Typ wird nur geloggt, nicht
      persistiert. Upstream-Emission ist Fire-and-Forget (ein
      Broker-Fehler auf SubscribeFlow-Seite verliert das Event dauerhaft,
      ohne erneuten Zustellversuch) -- diese Tabelle ist daher kein
      lückenloser Audit-Trail, sondern die beste verfügbare Annäherung.
    - Aktualisiert Suppression-Liste bei Hard-Bounce/Complaint
    - Ein Fehler beim Verarbeiten eines bekannten Event-Typs (z.B. DB-Fehler)
      liefert 500 statt 200, damit SubscribeFlows Retry greift, statt den
      Fehler stillschweigend zu bestätigen
    """
    webhook_secret = os.getenv("SUBSCRIBEFLOW_WEBHOOK_SECRET")
    is_development = os.getenv("ENVIRONMENT", "production").lower() in [
        "development",
        "dev",
        "local",
    ]

    payload = await request.body()

    if not webhook_secret:
        if is_development:
            logger.warning(
                "SUBSCRIBEFLOW_WEBHOOK_SECRET not set - skipping signature verification (DEVELOPMENT MODE ONLY)"
            )
        else:
            logger.error(
                "SUBSCRIBEFLOW_WEBHOOK_SECRET not set in production - rejecting webhook"
            )
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
    else:
        if not x_subscribeflow_signature:
            logger.warning("Missing X-SubscribeFlow-Signature header")
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_subscribeflow_signature(
            payload, x_subscribeflow_signature, webhook_secret
        ):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not isinstance(event_data, dict):
        logger.error(
            f"Webhook payload is not a JSON object: {type(event_data).__name__}"
        )
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event_data.get("type")
    event_id = event_data.get("id")
    data = event_data.get("data", {})

    if not isinstance(data, dict):
        logger.error(
            f"Webhook 'data' field is not a JSON object: {type(data).__name__}"
        )
        raise HTTPException(status_code=400, detail="Invalid webhook payload structure")

    logger.info(f"SubscribeFlow webhook received: {event_type}")

    try:
        handler: Optional[Callable[[Session, dict, Optional[str]], Awaitable[None]]] = {
            "email.sent": handle_email_sent,
            "email.delivered": handle_email_delivered,
            "email.bounced": handle_email_bounced,
            "email.complained": handle_email_spam_complaint,
        }.get(event_type)
    except TypeError:
        # event_type is unhashable (e.g. a list/dict) -- a malformed payload
        # no retry could ever fix, not a processing failure.
        logger.error(f"Webhook 'type' field is not a valid scalar: {event_type!r}")
        raise HTTPException(status_code=400, detail="Invalid webhook payload structure")

    if handler is None:
        # Unknown/unimplemented event type -- ack with 200 so SubscribeFlow
        # doesn't retry something we will never be able to handle.
        logger.warning(f"Unknown SubscribeFlow event type: {event_type}")
        return {"status": "ok"}

    try:
        await handler(db, data, event_id)
    except Exception as e:
        # Unlike an unknown event type, this is a real processing failure
        # (e.g. a transient DB error) for an event we do support -- roll
        # back the half-written transaction and answer with 500 so
        # SubscribeFlow's own retry/backoff (it does not disable the
        # endpoint on failure) gets a chance to redeliver it, instead of
        # silently swallowing the event with a false "ok".
        db.rollback()
        logger.error(
            f"Error handling SubscribeFlow webhook event type={event_type} "
            f"id={event_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Webhook event processing failed"
        ) from e

    return {"status": "ok"}


def _recipient_email(data: dict, event_type: str) -> str:
    """Extract the recipient email, logging loudly if it's missing.

    SubscribeFlow's payload contract for this field has already drifted
    once during TF-764 Phase A -> Phase B propagation -- a silent
    placeholder here would otherwise hide a future contract break behind
    rows that just look like garbage data in EmailEvent.
    """
    email = data.get("email")
    if not email:
        logger.warning(
            f"SubscribeFlow {event_type} payload missing 'email' field: {data}"
        )
        return _UNKNOWN_RECIPIENT
    return email


def _correlation_id(data: dict, event_type: str) -> str:
    """Extract the ESP-side correlation id, preferring esp_message_id with
    an email_send_id fallback, and logging loudly if both are absent."""
    correlation_id = data.get("esp_message_id") or data.get("email_send_id")
    if not correlation_id:
        logger.warning(
            f"SubscribeFlow {event_type} payload missing both 'esp_message_id' "
            f"and 'email_send_id': {data}"
        )
        return ""
    return correlation_id


def _event_timestamp(data: dict, event_type: str):
    """Extract the event's own timestamp from the payload, falling back to
    receipt time if it's missing or unparsable.

    SubscribeFlow's envelope carries the event's actual creation time in
    ``created_at`` (see outgoing_webhook_service.py in the SubscribeFlow
    repo -- ISO-8601 with an explicit "+00:00" UTC offset, not a "Z"
    suffix). Using that instead of "whenever this handler happened to run"
    matters for the deliverability analytics this table exists for: on a
    SubscribeFlow-side retry or a queue backlog, receipt time can trail the
    real event by minutes to hours.
    """
    raw = data.get("created_at")
    if not raw:
        return _utcnow()
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        logger.warning(
            f"SubscribeFlow {event_type} payload has an unparsable "
            f"'created_at' ({raw!r}) -- falling back to receipt time"
        )
        return _utcnow()
    if parsed.tzinfo is not None:
        # EmailEvent.event_timestamp is a naive DateTime column (see
        # models/email_event.py's _utcnow) -- normalize the same way.
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _event_already_recorded(
    db: Session, correlation_id: str, event_type: EmailEventType
) -> bool:
    """True if an EmailEvent for this correlation id + event type is
    already stored.

    SubscribeFlow delivers webhooks at-least-once and retries on a non-2xx
    response (this endpoint itself now returns 500 for a real processing
    failure, see the module docstring) -- without this check, a redelivery
    of an event we already recorded would create a duplicate EmailEvent
    row every time. An empty correlation_id (both esp_message_id and
    email_send_id missing from the payload) is never treated as a match,
    since it would otherwise conflate distinct malformed events.

    SECURITY NOTE: this is also the endpoint's only defense against replay
    of a captured payload+signature -- the signature itself has no
    timestamp/nonce (see the module docstring), so a captured request is
    otherwise replayable indefinitely. This function turns a replay into a
    harmless no-op via the correlation-id match. Do not remove or weaken it
    in a future refactor without adding a real replay defense (e.g. a
    signed timestamp) first.
    """
    if not correlation_id:
        return False
    return (
        db.query(EmailEvent)
        .filter(
            EmailEvent.email_id == correlation_id,
            EmailEvent.event_type == event_type,
        )
        .first()
        is not None
    )


async def handle_email_sent(
    db: Session, data: dict, event_id: Optional[str] = None
) -> None:
    """Track email.sent event.

    SubscribeFlow's actual email.sent payload (email_send_tasks.py::_send_email)
    is ``{"email_send_id", "esp_message_id", "email"}`` -- there is no "to" or
    "message_id" field.
    """
    correlation_id = _correlation_id(data, "email.sent")
    if _event_already_recorded(db, correlation_id, EmailEventType.SENT):
        logger.info(
            f"Duplicate SubscribeFlow webhook delivery ignored: {correlation_id}"
        )
        return

    email_event = EmailEvent(
        email_id=correlation_id,
        provider="subscribeflow",
        event_type=EmailEventType.SENT,
        recipient_email=_recipient_email(data, "email.sent"),
        event_timestamp=_event_timestamp(data, "email.sent"),
        event_metadata={**data, "webhook_event_id": event_id},
    )
    db.add(email_event)
    db.commit()
    logger.info(f"Email sent: {email_event.email_id}")


async def handle_email_delivered(
    db: Session, data: dict, event_id: Optional[str] = None
) -> None:
    """Track email.delivered event.

    SubscribeFlow's actual email.delivered payload
    (brevo_webhook_service.py::_queue_emission) is
    ``{"email_send_id", "esp_message_id", "email"}`` -- there is no
    "message_id" field.
    """
    correlation_id = _correlation_id(data, "email.delivered")
    if _event_already_recorded(db, correlation_id, EmailEventType.DELIVERED):
        logger.info(
            f"Duplicate SubscribeFlow webhook delivery ignored: {correlation_id}"
        )
        return

    email_event = EmailEvent(
        email_id=correlation_id,
        provider="subscribeflow",
        event_type=EmailEventType.DELIVERED,
        recipient_email=_recipient_email(data, "email.delivered"),
        event_timestamp=_event_timestamp(data, "email.delivered"),
        event_metadata={**data, "webhook_event_id": event_id},
    )
    db.add(email_event)
    db.commit()
    logger.info(f"Email delivered: {email_event.email_id}")


async def handle_email_bounced(
    db: Session, data: dict, event_id: Optional[str] = None
) -> None:
    """Handle bounce and add to suppression list if hard.

    SubscribeFlow's actual email.bounced payload
    (brevo_webhook_service.py::_queue_emission) is
    ``{"email_send_id", "esp_message_id", "email", "hard"}`` -- there is no
    "message_id" field.

    The EmailEvent write and the (conditional) suppression-list write are
    one atomic transaction -- a single commit at the end -- so a failure in
    either step leaves nothing committed, and a SubscribeFlow retry of the
    same event starts clean instead of risking a duplicate EmailEvent row.
    """
    recipient = _recipient_email(data, "email.bounced")
    hard_raw = data.get("hard", False)
    if hard_raw not in (True, False):
        # SubscribeFlow's payload contract has already drifted once during
        # this migration -- don't trust a non-boolean "hard" field enough
        # to let Python's truthy coercion turn e.g. the string "false" into
        # True and wrongly promote a soft bounce to a hard one.
        logger.warning(
            f"SubscribeFlow email.bounced payload has a non-boolean 'hard' "
            f"field ({hard_raw!r}) -- treating as soft bounce"
        )
    hard = hard_raw is True
    correlation_id = _correlation_id(data, "email.bounced")

    if _event_already_recorded(db, correlation_id, EmailEventType.BOUNCED):
        logger.info(
            f"Duplicate SubscribeFlow webhook delivery ignored: {correlation_id}"
        )
        return

    email_event = EmailEvent(
        email_id=correlation_id,
        provider="subscribeflow",
        event_type=EmailEventType.BOUNCED,
        recipient_email=recipient,
        event_timestamp=_event_timestamp(data, "email.bounced"),
        event_metadata={**data, "webhook_event_id": event_id},
    )
    db.add(email_event)

    if not hard:
        db.commit()
        logger.info(f"Soft bounce (will retry): {recipient}")
        return

    if recipient == _UNKNOWN_RECIPIENT:
        # _recipient_email() already logged loudly that 'email' was missing
        # -- recording the audit row is still worthwhile, but the
        # suppression list must never contain a synthetic placeholder
        # address.
        db.commit()
        logger.warning(
            f"Hard bounce with unknown recipient -- EmailEvent recorded, "
            f"suppression list not updated: {correlation_id}"
        )
        return

    await add_to_suppression_list(
        db=db,
        email=recipient,
        reason=EmailEventType.BOUNCED,
        provider="subscribeflow",
        event_id=correlation_id,
        suppress_transactional=True,
        suppress_marketing=True,
        commit=False,
    )
    db.commit()
    logger.warning(f"Hard bounce - added to suppression list: {recipient}")


async def handle_email_spam_complaint(
    db: Session, data: dict, event_id: Optional[str] = None
) -> None:
    """Handle spam complaint - suppress marketing only.

    SubscribeFlow's actual email.complained payload
    (brevo_webhook_service.py::_queue_emission) is
    ``{"email_send_id", "esp_message_id", "email"}`` -- there is no
    "message_id" field.

    Same atomic single-commit shape as ``handle_email_bounced`` above.
    """
    recipient = _recipient_email(data, "email.complained")
    correlation_id = _correlation_id(data, "email.complained")

    if _event_already_recorded(db, correlation_id, EmailEventType.SPAM_COMPLAINT):
        logger.info(
            f"Duplicate SubscribeFlow webhook delivery ignored: {correlation_id}"
        )
        return

    email_event = EmailEvent(
        email_id=correlation_id,
        provider="subscribeflow",
        event_type=EmailEventType.SPAM_COMPLAINT,
        recipient_email=recipient,
        event_timestamp=_event_timestamp(data, "email.complained"),
        event_metadata={**data, "webhook_event_id": event_id},
    )
    db.add(email_event)

    if recipient == _UNKNOWN_RECIPIENT:
        db.commit()
        logger.warning(
            f"Spam complaint with unknown recipient -- EmailEvent recorded, "
            f"suppression list not updated: {correlation_id}"
        )
        return

    await add_to_suppression_list(
        db=db,
        email=recipient,
        reason=EmailEventType.SPAM_COMPLAINT,
        provider="subscribeflow",
        event_id=correlation_id,
        suppress_transactional=False,
        suppress_marketing=True,
        commit=False,
    )
    db.commit()
    logger.warning(f"Spam complaint - suppressed marketing: {recipient}")

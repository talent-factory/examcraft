"""Tests für den SubscribeFlow-Outgoing-Webhook-Receiver (TF-764).

Ersetzt test_email_webhooks.py (Resend/Svix). SubscribeFlow signiert mit
HMAC-SHA256 über den rohen JSON-Body, Base64-kodiert, im Header
X-SubscribeFlow-Signature (siehe OutgoingWebhookService.deliver_webhook
im SubscribeFlow-Repo) -- kein Svix-Timestamp-Präfix wie bei Resend.

Wie im Vorgänger: Signatur-/Fehlerpfade laufen über den vollen HTTP-Stack
(`client`), die Event-Handling-Logik wird direkt gegen die Handler-
Funktionen mit `test_db` getestet (schneller, kein Signatur-Rechnen nötig).

Fixture-Payloads spiegeln die tatsächliche SubscribeFlow-Phase-A-Emission
wider (verifiziert gegen email_send_tasks.py::_send_email und
brevo_webhook_service.py::_queue_emission im SubscribeFlow-Repo):
``{"email_send_id", "esp_message_id", "email", ["hard" nur bei Bounce]}``
-- kein "to"-Feld, kein "message_id"-Feld.
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


def _sign(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


class TestVerifySubscribeflowSignature:
    def test_valid_signature_passes(self):
        from webhooks.subscribeflow_webhooks import verify_subscribeflow_signature

        payload = b'{"type": "email.delivered"}'
        secret = "whsec_test"  # pragma: allowlist secret
        signature = _sign(payload, secret)

        assert verify_subscribeflow_signature(payload, signature, secret) is True

    def test_invalid_signature_fails(self):
        from webhooks.subscribeflow_webhooks import verify_subscribeflow_signature

        payload = b'{"type": "email.delivered"}'
        assert (
            verify_subscribeflow_signature(
                payload, "bm90YXNpZ25hdHVyZQ==", "whsec_test"
            )
            is False
        )

    def test_missing_signature_or_secret_fails(self):
        from webhooks.subscribeflow_webhooks import verify_subscribeflow_signature

        payload = b'{"type": "email.delivered"}'
        assert verify_subscribeflow_signature(payload, "", "whsec_test") is False
        assert verify_subscribeflow_signature(payload, "sig", "") is False


class TestWebhookEndpoint:
    """Tests für Webhook Endpoint -- Signatur-/Fehlerpfade (Analogie zu
    test_email_webhooks.py::TestWebhookEndpoint, Header-Namen angepasst)."""

    def test_webhook_without_secret_development_mode(self, client):
        """Webhook processes without secret in development mode.

        Uses the plain `client` fixture (real TestClient(app), not the
        savepoint-isolated `test_db`) -- its writes are real commits against
        the shared CI test database and are never rolled back. The
        esp_message_id must therefore be namespaced/unique to this test, or
        it silently pollutes any other test in the suite that queries
        EmailEvent by the same literal id (this exact collision broke CI
        against test_handle_email_sent's "msg_1" -- see PR #236 CI run
        33596699041/job/100141475627).
        """
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={
                    "type": "email.delivered",
                    "data": {
                        "esp_message_id": "msg_devmode_ack",
                        "email": "user@example.com",
                    },
                },
            )

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_webhook_without_secret_production_mode_rejected(self, client):
        """Webhook without secret is rejected in production mode"""
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "production",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={
                    "type": "email.delivered",
                    "data": {
                        "esp_message_id": "msg_prodmode_rejected",
                        "email": "user@example.com",
                    },
                },
            )

            assert response.status_code == 500
            assert "Webhook secret not configured" in response.json()["detail"]

    def test_webhook_with_invalid_signature_rejected(self, client):
        """Webhook with invalid signature is rejected when secret is set"""
        with patch.dict(
            "os.environ",
            {"SUBSCRIBEFLOW_WEBHOOK_SECRET": "secret123"},  # pragma: allowlist secret
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={"type": "email.delivered", "data": {}},
                headers={"X-SubscribeFlow-Signature": "bm90YXZhbGlk"},
            )

            assert response.status_code == 401

    def test_webhook_missing_signature_header_rejected(self, client):
        """A present-but-wrong signature and a missing header are two
        distinct branches (:101-103 vs :104-108) -- both must reject."""
        with patch.dict(
            "os.environ",
            {"SUBSCRIBEFLOW_WEBHOOK_SECRET": "secret123"},  # pragma: allowlist secret
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={"type": "email.delivered", "data": {}},
            )

            assert response.status_code == 401
            assert "Missing signature" in response.json()["detail"]

    def test_webhook_with_valid_signature_accepted(self, client, test_db):
        """The one HTTP-level signature path none of the other tests in
        this class exercise: a genuinely valid signature over the real
        request body must be accepted and the event persisted.

        Every other test here goes through either the dev-mode bypass
        (secret unset) or a deliberately wrong/missing signature -- the
        header alias, `await request.body()` vs. a re-serialized JSON
        body, and the wiring into verify_subscribeflow_signature could all
        be silently broken (e.g. always returning False) and every other
        test in this class would still pass, while production would
        reject 100% of real SubscribeFlow deliveries with 401.
        """
        from models.email_event import EmailEvent

        secret = "whsec_valid_e2e_test"  # pragma: allowlist secret
        body = {
            "type": "email.delivered",
            "id": "evt_valid_sig_e2e",
            "data": {
                "esp_message_id": "msg_valid_sig_e2e",
                "email": "user@example.com",
            },
        }
        payload_bytes = json.dumps(body).encode("utf-8")
        signature = _sign(payload_bytes, secret)

        with patch.dict("os.environ", {"SUBSCRIBEFLOW_WEBHOOK_SECRET": secret}):
            response = client.post(
                "/webhooks/subscribeflow",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-SubscribeFlow-Signature": signature,
                },
            )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "msg_valid_sig_e2e")
            .first()
        )
        assert event is not None, (
            "a genuinely valid signature must reach the handler and persist "
            "the event, not just return 200"
        )

    def test_webhook_unknown_event_type_acked_but_not_persisted(self, client, test_db):
        """An event type we don't handle must still be acked with 200 (so
        SubscribeFlow doesn't retry forever) but must NOT be written to
        EmailEvent -- the audit-trail claim only covers the 4 known types."""
        from models.email_event import EmailEvent

        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={
                    "type": "email.opened",
                    "id": "evt_unknown",
                    "data": {"esp_message_id": "msg_unknown", "email": "u@example.com"},
                },
            )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "msg_unknown")
            .first()
        )
        assert event is None, "unknown event types must not be persisted"

    def test_webhook_handler_failure_returns_500_instead_of_false_ack(self, client):
        """A real processing failure for a *known* event type (e.g. a DB
        error) must surface as 500 so SubscribeFlow's retry gets a chance
        to redeliver it -- not be swallowed behind a false 200 'ok'."""
        with (
            patch(
                "webhooks.subscribeflow_webhooks.os.getenv",
                side_effect=lambda key, default=None: {
                    "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                    "ENVIRONMENT": "development",
                }.get(key, default),
            ),
            patch(
                "webhooks.subscribeflow_webhooks.handle_email_delivered",
                new_callable=AsyncMock,
                side_effect=RuntimeError("db exploded"),
            ),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={
                    "type": "email.delivered",
                    "data": {"esp_message_id": "msg_fail", "email": "u@example.com"},
                },
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Webhook event processing failed"

    def test_webhook_invalid_json_rejected(self, client):
        """Webhook with invalid JSON is rejected"""
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                content="not json",
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400 or response.status_code == 422

    def test_webhook_non_object_json_body_rejected(self, client):
        """A syntactically valid JSON body that isn't an object (e.g. a bare
        array) must be rejected with 400, not crash into a generic 500."""
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json=["not", "an", "object"],
            )

            assert response.status_code == 400

    def test_webhook_null_data_field_rejected(self, client):
        """A syntactically valid envelope with 'data: null' must be
        rejected with 400 -- previously this reached ``data.get(...)`` in
        the handler and raised ``AttributeError``, which surfaced as an
        unbounded-retry 500 for a payload no retry could ever fix."""
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={"type": "email.sent", "id": "evt_null_data", "data": None},
            )

            assert response.status_code == 400

    def test_webhook_non_scalar_event_type_rejected(self, client):
        """A 'type' field that is itself a list/object is unhashable --
        previously this crashed the handler-lookup dict's ``.get()`` with an
        unhandled ``TypeError`` (500, outside the try/except that adds
        rollback + a clean error response)."""
        with patch(
            "webhooks.subscribeflow_webhooks.os.getenv",
            side_effect=lambda key, default=None: {
                "SUBSCRIBEFLOW_WEBHOOK_SECRET": None,
                "ENVIRONMENT": "development",
            }.get(key, default),
        ):
            response = client.post(
                "/webhooks/subscribeflow",
                json={"type": ["email.sent"], "data": {}},
            )

            assert response.status_code == 400


class TestEventTimestamp:
    """_event_timestamp prefers the payload's own 'created_at' over receipt
    time -- on a SubscribeFlow-side retry or queue backlog, receipt time
    can trail the real event by minutes to hours, which would otherwise
    quietly corrupt the deliverability analytics this table exists for."""

    def test_uses_payload_created_at_when_present(self):
        from webhooks.subscribeflow_webhooks import _event_timestamp

        result = _event_timestamp(
            {"created_at": "2026-08-30T10:00:00+00:00"}, "email.delivered"
        )
        assert result == datetime(2026, 8, 30, 10, 0, 0)

    def test_falls_back_to_receipt_time_when_missing(self):
        from webhooks.subscribeflow_webhooks import _event_timestamp

        before = datetime.now(timezone.utc).replace(tzinfo=None)
        result = _event_timestamp({}, "email.delivered")
        after = datetime.now(timezone.utc).replace(tzinfo=None)
        assert before <= result <= after

    def test_falls_back_and_warns_on_unparsable_created_at(self):
        from webhooks.subscribeflow_webhooks import _event_timestamp

        with patch("webhooks.subscribeflow_webhooks.logger") as mock_logger:
            result = _event_timestamp(
                {"created_at": "not-a-timestamp"}, "email.delivered"
            )

        assert isinstance(result, datetime)
        warning_text = "\n".join(
            str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
        )
        assert "unparsable 'created_at'" in warning_text

    @pytest.mark.asyncio
    async def test_handler_persists_payload_created_at_not_receipt_time(self, test_db):
        """End-to-end through a real handler, not just the helper in
        isolation -- confirms the wiring, not just the parsing logic."""
        from webhooks.subscribeflow_webhooks import handle_email_delivered
        from models.email_event import EmailEvent

        await handle_email_delivered(
            test_db,
            {
                "esp_message_id": "msg_created_at",
                "email": "user@example.com",
                "created_at": "2020-01-01T00:00:00+00:00",
            },
            "evt_created_at",
        )

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "msg_created_at")
            .first()
        )
        assert event is not None
        assert event.event_timestamp == datetime(2020, 1, 1, 0, 0, 0)


class TestEmailEventHandlers:
    """Handler-Funktionen direkt mit test_db aufgerufen (kein HTTP-Layer)."""

    @pytest.mark.asyncio
    async def test_handle_email_sent(self, test_db):
        from webhooks.subscribeflow_webhooks import handle_email_sent
        from models.email_event import EmailEvent, EmailEventType

        await handle_email_sent(
            test_db,
            {
                "email_send_id": "es_1",
                "esp_message_id": "msg_1",
                "email": "user@example.com",
            },
            "evt_1",
        )

        event = test_db.query(EmailEvent).filter(EmailEvent.email_id == "msg_1").first()
        assert event is not None
        assert event.event_type == EmailEventType.SENT
        assert event.recipient_email == "user@example.com"
        assert event.provider == "subscribeflow"
        assert event.event_metadata["webhook_event_id"] == "evt_1"

    @pytest.mark.asyncio
    async def test_handle_email_sent_falls_back_to_email_send_id(self, test_db):
        """esp_message_id is preferred, but email_send_id alone must still
        work -- the ``or``-fallback in _correlation_id was itself the
        subject of a payload-contract bugfix earlier in this branch."""
        from webhooks.subscribeflow_webhooks import handle_email_sent
        from models.email_event import EmailEvent

        await handle_email_sent(
            test_db,
            {"email_send_id": "es_fallback", "email": "user@example.com"},
            "evt_fallback",
        )

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "es_fallback")
            .first()
        )
        assert event is not None

    @pytest.mark.asyncio
    async def test_handle_email_sent_missing_email_logs_warning(self, test_db):
        """A payload missing 'email' entirely must be logged loudly, not
        silently written as an unremarkable placeholder row.

        Patches the module logger directly rather than using caplog: caplog
        relies on propagation from the named logger to the root logger,
        which is unreliable across the full backend test suite (some other
        test/module disables propagation depending on run order) -- see
        project_caplog_propagation_full_suite. Patching the logger call is
        immune to that.
        """
        from webhooks.subscribeflow_webhooks import handle_email_sent
        from models.email_event import EmailEvent

        with patch("webhooks.subscribeflow_webhooks.logger") as mock_logger:
            await handle_email_sent(
                test_db, {"esp_message_id": "msg_noemail"}, "evt_noemail"
            )

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "msg_noemail")
            .first()
        )
        assert event is not None
        assert event.recipient_email == "unknown@unknown.com"
        warning_text = "\n".join(
            str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
        )
        assert "missing 'email' field" in warning_text

    @pytest.mark.asyncio
    async def test_handle_email_sent_missing_both_correlation_ids_still_persists(
        self, test_db
    ):
        """Neither 'esp_message_id' nor 'email_send_id' present -->
        _correlation_id falls back to "" and _event_already_recorded treats
        an empty correlation id as never-a-match. The event must still be
        recorded (not silently dropped) and the gap logged loudly -- this
        is exactly the payload shape that broke the migration once already
        (see the module docstring's "the payload contract has already
        drifted once" note)."""
        from webhooks.subscribeflow_webhooks import handle_email_sent
        from models.email_event import EmailEvent

        with patch("webhooks.subscribeflow_webhooks.logger") as mock_logger:
            await handle_email_sent(
                test_db, {"email": "user@example.com"}, "evt_no_correlation"
            )

        event = test_db.query(EmailEvent).filter(EmailEvent.email_id == "").first()
        assert event is not None, (
            "an empty correlation id must still be persisted, not dropped"
        )
        assert event.recipient_email == "user@example.com"
        warning_text = "\n".join(
            str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
        )
        assert "missing both 'esp_message_id' and 'email_send_id'" in warning_text

    @pytest.mark.asyncio
    async def test_handle_email_delivered(self, test_db):
        from webhooks.subscribeflow_webhooks import handle_email_delivered
        from models.email_event import EmailEvent, EmailEventType

        await handle_email_delivered(
            test_db,
            {
                "email_send_id": "es_2",
                "esp_message_id": "msg_2",
                "email": "user@example.com",
            },
            "evt_2",
        )

        event = test_db.query(EmailEvent).filter(EmailEvent.email_id == "msg_2").first()
        assert event is not None
        assert event.event_type == EmailEventType.DELIVERED
        assert event.recipient_email == "user@example.com"
        assert event.event_metadata["webhook_event_id"] == "evt_2"

    @pytest.mark.asyncio
    async def test_handle_email_bounced_hard(self, test_db):
        from webhooks.subscribeflow_webhooks import handle_email_bounced
        from models.email_event import EmailEvent, EmailEventType, EmailSuppressionList

        await handle_email_bounced(
            test_db,
            {
                "email_send_id": "es_3",
                "esp_message_id": "msg_3",
                "email": "bounced@example.com",
                "hard": True,
            },
            "evt_3",
        )

        event = test_db.query(EmailEvent).filter(EmailEvent.email_id == "msg_3").first()
        assert event is not None
        assert event.event_type == EmailEventType.BOUNCED
        assert event.event_metadata["webhook_event_id"] == "evt_3"

        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "bounced@example.com")
            .first()
        )
        assert suppression is not None
        assert suppression.suppress_transactional == 1
        assert suppression.suppress_marketing == 1
        assert suppression.original_event_id == "msg_3"

    @pytest.mark.asyncio
    async def test_handle_email_bounced_soft(self, test_db):
        from webhooks.subscribeflow_webhooks import handle_email_bounced
        from models.email_event import EmailSuppressionList

        await handle_email_bounced(
            test_db,
            {
                "email_send_id": "es_4",
                "esp_message_id": "msg_4",
                "email": "softbounce@example.com",
                "hard": False,
            },
        )

        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "softbounce@example.com")
            .first()
        )
        assert suppression is None

    @pytest.mark.asyncio
    async def test_handle_email_bounced_non_boolean_hard_treated_as_soft_and_warns(
        self, test_db
    ):
        """A non-boolean 'hard' value (e.g. the string "false") must NOT be
        promoted to a hard bounce via Python's truthy coercion
        (bool("false") is True) -- that would wrongly suppress a recipient
        on a payload shape SubscribeFlow never actually sends today, but
        the module docstring already documents that this payload contract
        has drifted once before."""
        from webhooks.subscribeflow_webhooks import handle_email_bounced
        from models.email_event import EmailSuppressionList

        with patch("webhooks.subscribeflow_webhooks.logger") as mock_logger:
            await handle_email_bounced(
                test_db,
                {
                    "esp_message_id": "msg_hard_nonbool",
                    "email": "notreallyhard@example.com",
                    "hard": "false",
                },
                "evt_hard_nonbool",
            )

        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "notreallyhard@example.com")
            .first()
        )
        assert suppression is None, (
            "a non-boolean 'hard' value must never be coerced into a hard bounce"
        )
        warning_text = "\n".join(
            str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
        )
        assert "non-boolean 'hard' field" in warning_text

    @pytest.mark.asyncio
    async def test_handle_email_sent_duplicate_delivery_not_persisted_twice(
        self, test_db
    ):
        """SubscribeFlow delivers at-least-once -- a redelivery of an event
        we already recorded (network blip after our 200, or our own
        500-triggered retry) must not create a second EmailEvent row."""
        from webhooks.subscribeflow_webhooks import handle_email_sent
        from models.email_event import EmailEvent

        payload = {
            "email_send_id": "es_dup",
            "esp_message_id": "msg_dup",
            "email": "user@example.com",
        }
        await handle_email_sent(test_db, payload, "evt_dup_1")
        await handle_email_sent(test_db, payload, "evt_dup_2")

        events = (
            test_db.query(EmailEvent).filter(EmailEvent.email_id == "msg_dup").all()
        )
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_handle_email_bounced_suppression_failure_rolls_back_email_event(
        self, test_db
    ):
        """The EmailEvent write and the suppression-list write must be one
        atomic transaction -- if the suppression-list step fails, the
        EmailEvent must not be left committed either, otherwise a
        SubscribeFlow retry of the same event (now returning 500) creates a
        duplicate EmailEvent row on redelivery."""
        from webhooks.subscribeflow_webhooks import handle_email_bounced
        from models.email_event import EmailEvent

        with patch(
            "webhooks.subscribeflow_webhooks.add_to_suppression_list",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db exploded mid-transaction"),
        ):
            with pytest.raises(RuntimeError, match="db exploded mid-transaction"):
                await handle_email_bounced(
                    test_db,
                    {
                        "email_send_id": "es_atomic",
                        "esp_message_id": "msg_atomic",
                        "email": "bounced@example.com",
                        "hard": True,
                    },
                    "evt_atomic",
                )
        test_db.rollback()

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "msg_atomic")
            .first()
        )
        assert event is None, (
            "EmailEvent must not survive a failed suppression-list write in "
            "the same handler invocation"
        )

    @pytest.mark.asyncio
    async def test_handle_email_bounced_unknown_recipient_skips_suppression_write(
        self, test_db
    ):
        """A bounce payload missing 'email' falls back to a placeholder
        recipient -- that placeholder must never pollute the real
        suppression list, even though the EmailEvent audit row is still
        recorded."""
        from webhooks.subscribeflow_webhooks import handle_email_bounced
        from models.email_event import EmailEvent, EmailSuppressionList

        await handle_email_bounced(
            test_db,
            {"email_send_id": "es_noemail", "hard": True},
            "evt_noemail",
        )

        event = (
            test_db.query(EmailEvent)
            .filter(EmailEvent.email_id == "es_noemail")
            .first()
        )
        assert event is not None, "the audit row must still be recorded"

        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "unknown@unknown.com")
            .first()
        )
        assert suppression is None, (
            "a placeholder recipient must never be written to the suppression list"
        )

    @pytest.mark.asyncio
    async def test_handle_email_spam_complaint(self, test_db):
        from webhooks.subscribeflow_webhooks import handle_email_spam_complaint
        from models.email_event import EmailEvent, EmailEventType, EmailSuppressionList

        await handle_email_spam_complaint(
            test_db,
            {
                "email_send_id": "es_5",
                "esp_message_id": "msg_5",
                "email": "complainer@example.com",
            },
            "evt_5",
        )

        event = test_db.query(EmailEvent).filter(EmailEvent.email_id == "msg_5").first()
        assert event is not None
        assert event.event_type == EmailEventType.SPAM_COMPLAINT
        assert event.event_metadata["webhook_event_id"] == "evt_5"

        suppression = (
            test_db.query(EmailSuppressionList)
            .filter(EmailSuppressionList.email == "complainer@example.com")
            .first()
        )
        assert suppression is not None
        assert suppression.suppress_transactional == 0
        assert suppression.suppress_marketing == 1
        assert suppression.original_event_id == "msg_5"

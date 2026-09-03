"""Provisioning script for TF-764: creates the SubscribeFlow templates,
scoped API key, and outgoing webhook endpoint that ExamCraft's transactional
email sending and delivery-status tracking depend on.

Run manually per environment (dev/staging/prod) with the existing admin
SUBSCRIBEFLOW_API_KEY -- never wired into app startup. Idempotent for
templates (matched by slug, updated in place), the API key (matched by
name via GET /api/v1/api-keys -- an existing key is left untouched, never
re-minted), and the webhook endpoint (matched by URL, reused and its
subscribed events reconciled rather than duplicated). One unavoidable
caveat: SubscribeFlow never returns a key's plaintext value again after
creation, so if a key named "ExamCraft emails:send" already exists but its
value was lost, this script can only report that it exists -- it cannot
recover it. Revoke the orphaned key via the SubscribeFlow admin API first,
then re-run to mint a fresh one.

If any step fails partway through (e.g. the webhook step raises after the
API key was already minted for real), the *fact* that each earlier step
succeeded (id, scopes, "reused" flag) is logged before the exception
propagates -- but any newly minted secret's plaintext is deliberately
REDACTED from that log line (see _redact_secrets below), on purpose: a log
line is far less controlled (terminal scrollback, CI job logs, log
aggregation) than the one deliberate, once-only stdout print() near the
end of _main() that normally shows it. If provision() raises BEFORE
_main() reaches that print() -- exactly the "webhook step raises after
the key was minted" scenario above -- the freshly minted secret is gone
for good: it was logged nowhere in recoverable form. In that case, revoke
the orphaned key via the SubscribeFlow admin API (see the caveat above)
and re-run this script to mint a fresh one; don't expect to recover it
from application logs. (--dry-run previews only the templates portion and
returns before the key/webhook steps run at all, so it can never mint an
unrecoverable secret.)

Usage:
    python -m scripts.provision_subscribeflow_email \
        --admin-key sf_live_... \
        --backend-url https://examcraft-api.fly.dev

Prints the (newly created or reused) scoped API key and webhook secret to
stdout for manual transfer into Fly secrets (SUBSCRIBEFLOW_EMAILS_API_KEY,
SUBSCRIBEFLOW_WEBHOOK_SECRET) -- this script never calls `fly secrets set`.
"""

import argparse
import asyncio
import json
import logging
import os
from typing import Any, Optional

from subscribeflow import SubscribeFlowClient

logger = logging.getLogger(__name__)

API_KEY_NAME = "ExamCraft emails:send"
WEBHOOK_EVENTS = ["email.sent", "email.delivered", "email.bounced", "email.complained"]

TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "verification",
        "subject": "Verify your ExamCraft AI account",
        "variables_schema": {"first_name": "string", "verification_url": "string"},
        "mjml_content": """<mjml>
  <mj-body background-color="#f9f9f9">
    <mj-section background-color="#667eea" padding="30px">
      <mj-column>
        <mj-text align="center" color="#ffffff" font-size="24px" font-weight="bold">
          Welcome to ExamCraft AI! 🎓
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#f9f9f9" padding="30px">
      <mj-column>
        <mj-text font-size="16px">Hi {{ first_name }},</mj-text>
        <mj-text font-size="16px">
          Thank you for signing up for ExamCraft AI! We're excited to have you on board.
        </mj-text>
        <mj-text font-size="16px">
          To get started, please verify your email address by clicking the button below:
        </mj-text>
        <mj-button background-color="#667eea" href="{{ verification_url }}" font-weight="bold">
          Verify Email Address
        </mj-button>
        <mj-text font-size="14px" color="#666666">
          Or copy and paste this link into your browser:<br/>
          <a href="{{ verification_url }}" style="color:#667eea; word-break: break-all;">{{ verification_url }}</a>
        </mj-text>
        <mj-text font-size="14px" color="#666666">
          This link will expire in 24 hours for security reasons.
        </mj-text>
        <mj-text font-size="14px" color="#666666">
          If you didn't create an account with ExamCraft AI, you can safely ignore this email.
        </mj-text>
        <mj-divider border-color="#dddddd" />
        <mj-text align="center" font-size="12px" color="#999999">
          © Talent Factory GmbH. All rights reserved.
        </mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>""",
    },
    {
        "name": "welcome",
        "subject": "Welcome to ExamCraft AI - Let's Get Started! 🚀",
        "variables_schema": {
            "first_name": "string",
            "dashboard_url": "string",
            "docs_url": "string",
        },
        "mjml_content": """<mjml>
  <mj-body background-color="#f9f9f9">
    <mj-section background-color="#667eea" padding="30px">
      <mj-column>
        <mj-text align="center" color="#ffffff" font-size="24px" font-weight="bold">
          You're All Set! 🎉
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#f9f9f9" padding="30px">
      <mj-column>
        <mj-text font-size="16px">Hi {{ first_name }},</mj-text>
        <mj-text font-size="16px">
          Your email has been verified successfully! You're now ready to start creating
          amazing exam questions with AI.
        </mj-text>
        <mj-text font-size="18px" color="#667eea" font-weight="bold">What's Next?</mj-text>
        <mj-text font-size="16px" line-height="2">
          📄 Upload your first document<br/>
          🤖 Generate AI-powered exam questions<br/>
          ✅ Review and refine your questions<br/>
          📝 Export your exam
        </mj-text>
        <mj-button background-color="#667eea" href="{{ dashboard_url }}" font-weight="bold">
          Go to Dashboard
        </mj-button>
        <mj-text font-size="14px" color="#666666">
          Need help? Check out our <a href="{{ docs_url }}" style="color:#667eea;">documentation</a>
          or contact our support team.
        </mj-text>
        <mj-divider border-color="#dddddd" />
        <mj-text align="center" font-size="12px" color="#999999">
          © Talent Factory GmbH. All rights reserved.
        </mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>""",
    },
    {
        "name": "impersonation-started",
        "subject": "An administrator started accessing your ExamCraft AI account",
        "variables_schema": {
            "to_name": "string",
            "admin_name": "string",
            "reason": "string",
            "started_at": "string",
        },
        "mjml_content": """<mjml>
  <mj-body background-color="#f9f9f9">
    <mj-section background-color="#667eea" padding="30px">
      <mj-column>
        <mj-text align="center" color="#ffffff" font-size="24px" font-weight="bold">
          Account Access Notice
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#f9f9f9" padding="30px">
      <mj-column>
        <mj-text font-size="16px">Hi {{ to_name }},</mj-text>
        <mj-text font-size="16px">
          An administrator, <strong>{{ admin_name }}</strong>, has just started accessing
          your ExamCraft AI account on your behalf. The session is active now and expires
          automatically after 30 minutes if it isn't ended sooner.
        </mj-text>
        <mj-table font-size="14px">
          <tr><td style="padding:6px 0;color:#666666;">Administrator</td><td style="padding:6px 0;"><strong>{{ admin_name }}</strong></td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Reason given</td><td style="padding:6px 0;">{{ reason }}</td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Started</td><td style="padding:6px 0;">{{ started_at }}</td></tr>
        </mj-table>
        <mj-text font-size="14px" color="#666666">
          If you did not expect this, or have any concerns, please contact your
          institution's administrator or ExamCraft AI support.
        </mj-text>
        <mj-divider border-color="#dddddd" />
        <mj-text align="center" font-size="12px" color="#999999">
          © Talent Factory GmbH. All rights reserved.
        </mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>""",
    },
    {
        "name": "impersonation-ended",
        "subject": "Your ExamCraft AI account was accessed by an administrator",
        "variables_schema": {
            "to_name": "string",
            "admin_name": "string",
            "reason": "string",
            "started_at": "string",
            "ended_at": "string",
            "duration": "string",
            "ended_how": "string",
        },
        "mjml_content": """<mjml>
  <mj-body background-color="#f9f9f9">
    <mj-section background-color="#667eea" padding="30px">
      <mj-column>
        <mj-text align="center" color="#ffffff" font-size="24px" font-weight="bold">
          Account Access Notice
        </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#f9f9f9" padding="30px">
      <mj-column>
        <mj-text font-size="16px">Hi {{ to_name }},</mj-text>
        <mj-text font-size="16px">
          An administrator, <strong>{{ admin_name }}</strong>, accessed your ExamCraft AI
          account on your behalf. This session has now ended, {{ ended_how }}.
        </mj-text>
        <mj-table font-size="14px">
          <tr><td style="padding:6px 0;color:#666666;">Administrator</td><td style="padding:6px 0;"><strong>{{ admin_name }}</strong></td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Reason given</td><td style="padding:6px 0;">{{ reason }}</td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Started</td><td style="padding:6px 0;">{{ started_at }}</td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Ended</td><td style="padding:6px 0;">{{ ended_at }}</td></tr>
          <tr><td style="padding:6px 0;color:#666666;">Duration</td><td style="padding:6px 0;">{{ duration }}</td></tr>
        </mj-table>
        <mj-text font-size="14px" color="#666666">
          If you did not expect this, or have any concerns, please contact your
          institution's administrator or ExamCraft AI support.
        </mj-text>
        <mj-divider border-color="#dddddd" />
        <mj-text align="center" font-size="12px" color="#999999">
          © Talent Factory GmbH. All rights reserved.
        </mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>""",
    },
]


async def provision(
    admin_api_key: str,
    base_url: str,
    backend_url: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create/update the 4 templates, ensure the scoped emails:send API key
    exists, and create/reuse the outgoing webhook endpoint. Idempotent per
    slug (templates), name (API key -- an existing key is reused, never
    re-minted) and URL (webhook endpoint -- reused, with its subscribed
    events reconciled). See the module docstring for the one caveat: a
    key's plaintext can't be recovered once its value is lost, only its
    existence detected."""
    result: dict[str, Any] = {
        "templates": [],
        "emails_api_key": None,
        "webhook_endpoint": None,
    }

    async with SubscribeFlowClient(
        api_key=admin_api_key, base_url=base_url, timeout=30.0
    ) as client:
        try:
            # list() only returns one page (offset-based: skip/limit) --
            # an account with >100 existing templates would otherwise have
            # its 101st+ template missed and duplicated on every re-run.
            existing_by_slug = {}
            skip = 0
            while True:
                templates_page = await client.templates.list(skip=skip, limit=100)
                existing_by_slug.update({t.slug: t for t in templates_page.items})
                skip += len(templates_page.items)
                if not templates_page.items or skip >= templates_page.total:
                    break

            for tmpl in TEMPLATES:
                slug = tmpl["name"]
                if slug in existing_by_slug:
                    if not dry_run:
                        updated = await client.templates.update(
                            slug=slug,
                            subject=tmpl["subject"],
                            mjml_content=tmpl["mjml_content"],
                            variables_schema=tmpl["variables_schema"],
                        )
                        result["templates"].append(
                            {"slug": updated.slug, "action": "updated"}
                        )
                    else:
                        result["templates"].append({"slug": slug, "action": "updated"})
                else:
                    if not dry_run:
                        created = await client.templates.create(
                            name=tmpl["name"],
                            subject=tmpl["subject"],
                            mjml_content=tmpl["mjml_content"],
                            variables_schema=tmpl["variables_schema"],
                            category="transactional",
                        )
                        result["templates"].append(
                            {"slug": created.slug, "action": "created"}
                        )
                    else:
                        result["templates"].append({"slug": slug, "action": "created"})

            if dry_run:
                return result

            # Check for an existing key of this name before minting a new one --
            # GET /api/v1/api-keys exists and lists names, so re-runs no longer
            # have to blindly mint an orphaned duplicate. It cannot return the
            # plaintext of an existing key though (SubscribeFlow only shows that
            # once, at creation), so a reused key's "key" stays None here.
            #
            # _request() is typed -> dict[str, Any]; every other list endpoint
            # in this SDK wraps its items in a {"items": [...]} envelope, and
            # this endpoint isn't part of the typed SDK surface (no dedicated
            # `client.api_keys` resource), so its actual shape is unverified.
            # Handle both a bare list and a dict envelope defensively rather
            # than assume -- a wrong assumption here would crash exactly at
            # the step that mints a once-only secret.
            existing_keys_response = await client._request("GET", "/api/v1/api-keys")
            existing_keys = (
                existing_keys_response.get("items", [])
                if isinstance(existing_keys_response, dict)
                else existing_keys_response
            )
            existing_key = next(
                (k for k in existing_keys if k.get("name") == API_KEY_NAME), None
            )
            if existing_key:
                key_id = existing_key.get("id")
                if key_id is None:
                    raise RuntimeError(
                        f"GET /api/v1/api-keys returned an existing "
                        f"{API_KEY_NAME!r} key with no 'id' field -- unexpected "
                        f"response shape, refusing to guess: {existing_key!r}"
                    )
                existing_scopes = set(existing_key.get("scopes") or [])
                if existing_scopes != {"emails:send"}:
                    # A same-named key with broader scopes would silently
                    # defeat the least-privilege point of minting a
                    # dedicated emails:send key in the first place --
                    # reused regardless (this script never mutates an
                    # existing key's scopes), but loud enough that an
                    # operator notices and can rotate it deliberately.
                    logger.warning(
                        "Reusing existing API key %r with scopes %s -- expected "
                        "exactly {'emails:send'}. This key may be broader than "
                        "intended; review it via the SubscribeFlow admin API and "
                        "revoke+re-run this script to mint a correctly-scoped "
                        "replacement if it shouldn't be.",
                        API_KEY_NAME,
                        sorted(existing_scopes),
                    )
                result["emails_api_key"] = {
                    "id": key_id,
                    "key": None,
                    "scopes": existing_key.get("scopes"),
                    "reused": True,
                }
            else:
                key_response = await client._request(
                    "POST",
                    "/api/v1/api-keys",
                    json={"name": API_KEY_NAME, "scopes": ["emails:send"]},
                )
                result["emails_api_key"] = {
                    "id": key_response["id"],
                    "key": key_response["key"],
                    "scopes": key_response["scopes"],
                    "reused": False,
                }

            # webhooks.list() is cursor-based -- same >100-item gap as the
            # templates page above, follow next_cursor until exhausted.
            # Page-capped defensively: the SDK derives next_cursor from
            # response.get("cursor") for both this cursor-based endpoint and,
            # via the same code path, the offset-based templates endpoint
            # above -- which suggests the cursor semantics aren't firmly
            # pinned upstream. A cap turns a hypothetical always-truthy-cursor
            # bug into a loud failure instead of an infinite loop.
            webhook_url = f"{backend_url}/webhooks/subscribeflow"
            all_endpoints: list[Any] = []
            cursor: Optional[str] = None
            for _ in range(
                50
            ):  # 50 * 100 = 5000 endpoints, far beyond any real account
                webhooks_page = await client.webhooks.list(cursor=cursor, limit=100)
                all_endpoints.extend(webhooks_page.items)
                cursor = webhooks_page.next_cursor
                if not cursor:
                    break
            else:
                raise RuntimeError(
                    "webhooks.list() pagination did not terminate after 50 "
                    "pages -- aborting rather than looping forever; check "
                    "next_cursor semantics against the SubscribeFlow SDK"
                )
            matching_endpoint = next(
                (e for e in all_endpoints if e.url == webhook_url), None
            )
            if matching_endpoint:
                if set(matching_endpoint.events) != set(WEBHOOK_EVENTS):
                    reconciled = await client.webhooks.update(
                        matching_endpoint.id, events=WEBHOOK_EVENTS
                    )
                    result["webhook_endpoint"] = {
                        "id": reconciled.id,
                        "secret": None,
                        "events_reconciled": True,
                    }
                else:
                    result["webhook_endpoint"] = {
                        "id": matching_endpoint.id,
                        "secret": None,
                        "events_reconciled": False,
                    }
            else:
                endpoint = await client.webhooks.create(
                    url=webhook_url, events=WEBHOOK_EVENTS
                )
                result["webhook_endpoint"] = {
                    "id": endpoint.id,
                    "secret": endpoint.secret,
                    "events_reconciled": False,
                }
        except Exception:
            # Whatever succeeded before the failure (including a freshly minted,
            # only-shown-once API key or webhook secret) must not be lost to a
            # bare traceback -- log it so an operator can still recover it.
            # The plaintext secret itself is redacted: it was already handed
            # to the operator via the deliberate, once-only stdout print() in
            # _main() if that step completed, and a log line is far less
            # controlled (terminal scrollback, CI job logs, log aggregation)
            # than that one intentional print.
            logger.error(
                "provision() failed partway through; steps completed before "
                "the failure (secrets redacted -- see the once-only stdout "
                "print() for any that were actually minted this run): %s",
                json.dumps(_redact_secrets(result), indent=2, default=str),
            )
            raise

    return result


def _redact_secrets(result: dict[str, Any]) -> dict[str, Any]:
    """Copy of ``result`` with any plaintext secret fields blanked out, safe
    to pass to a logger. Used only for the partial-failure log above --
    the deliberate stdout ``print()`` in ``_main()`` still shows the real
    values once, as designed."""
    redacted = dict(result)
    api_key = redacted.get("emails_api_key")
    if api_key and api_key.get("key"):
        redacted["emails_api_key"] = {**api_key, "key": "<redacted>"}
    webhook_endpoint = redacted.get("webhook_endpoint")
    if webhook_endpoint and webhook_endpoint.get("secret"):
        redacted["webhook_endpoint"] = {**webhook_endpoint, "secret": "<redacted>"}
    return redacted


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-key", default=os.getenv("SUBSCRIBEFLOW_API_KEY", ""))
    parser.add_argument(
        "--base-url",
        default=os.getenv("SUBSCRIBEFLOW_BASE_URL", "https://api.subscribeflow.net"),
    )
    parser.add_argument(
        "--backend-url", required=True, help="e.g. https://examcraft-api.fly.dev"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.admin_key:
        raise SystemExit("--admin-key or SUBSCRIBEFLOW_API_KEY required")

    result = asyncio.run(
        provision(args.admin_key, args.base_url, args.backend_url, dry_run=args.dry_run)
    )
    print(json.dumps(result, indent=2, default=str))
    if result["emails_api_key"] and result["emails_api_key"]["key"]:
        print("\n>>> Store as Fly secret SUBSCRIBEFLOW_EMAILS_API_KEY (shown once).")
    elif result["emails_api_key"] and result["emails_api_key"]["reused"]:
        print(
            "\n>>> Key already existed and was reused -- its value was NOT "
            "shown (SubscribeFlow only returns it at creation). If "
            "SUBSCRIBEFLOW_EMAILS_API_KEY is not already set correctly for "
            "this environment, revoke this key via the SubscribeFlow admin "
            "API and re-run this script to mint a fresh one."
        )
    if result["webhook_endpoint"] and result["webhook_endpoint"]["secret"]:
        print(">>> Store as Fly secret SUBSCRIBEFLOW_WEBHOOK_SECRET (shown once).")
    elif result["webhook_endpoint"] and result["webhook_endpoint"].get(
        "events_reconciled"
    ):
        print(">>> Existing webhook endpoint's subscribed events were updated.")


if __name__ == "__main__":
    _main()

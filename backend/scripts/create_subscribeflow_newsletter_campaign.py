"""Creates a DRAFT campaign in SubscribeFlow for an already-provisioned
ExamCraft newsletter template (see provision_subscribeflow_newsletter.py).

This script only calls `client.campaigns.create()` -- it never calls
`client.campaigns.send()` or `.retry()`. Triggering the actual send is a
deliberate, separate step (via the SubscribeFlow admin UI, or a future
dedicated script written only when explicitly asked for) so that a
newsletter is never sent as a side effect of provisioning it.

Recipients are resolved via the existing "examcraft" tag: every
ExamCraft user is subscribed to it automatically on email verification
(see services/subscribeflow_service.py, SubscribeFlowService.subscribe_user).
This script does not create or modify that tag beyond looking it up.

NOTE: this does NOT use `client.tags.get_or_create()`. The server's Tag
model now returns `approval_status` and `created_by_subscriber_id`
(a tag-approval feature), but the latest published SDK (subscribeflow
1.8.0 on PyPI, checked -- there is no newer release) still has
`Tag(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and
neither field declared, so ANY `client.tags.*` call that parses a Tag
response raises a pydantic ValidationError. This is a SubscribeFlow
SDK/server drift bug, not fixable by bumping a version pin -- worth
its own ticket. Workaround here: resolve the tag via raw
`client._request()` calls (same escape hatch already used in
provision_subscribeflow_email.py for endpoints without a typed
wrapper) and read only the `id` field out of the raw dict, skipping
`Tag.model_validate()` entirely.

Idempotent on campaign *name*: if a campaign with the same name already
exists (any status), this script reports it instead of creating a
duplicate draft.

Usage:
    python -m scripts.create_subscribeflow_newsletter_campaign \
        --admin-key sf_live_... \
        [--base-url https://api.subscribeflow.net] \
        [--slug newsletter-2026-issue-01] \
        [--tag examcraft] \
        [--name "ExamCraft Newsletter -- Ausgabe 01 (September 2026)"] \
        [--dry-run]
"""

import argparse
import asyncio
import json
import os
from typing import Any
from urllib.parse import quote

from subscribeflow import SubscribeFlowClient
from subscribeflow.exceptions import NotFoundError

DEFAULT_SLUG = "newsletter-2026-issue-01"
DEFAULT_TAG = "examcraft"
DEFAULT_NAME = "ExamCraft Newsletter -- Ausgabe 01 (September 2026)"


async def _get_or_create_tag_id(
    client: SubscribeFlowClient, name: str
) -> tuple[str, bool]:
    """Resolve a tag's id without going through `Tag.model_validate()`.

    See the module docstring: the server's Tag response carries fields
    the published SDK's Tag model forbids, so any typed `client.tags.*`
    call raises. Reads only `id` off the raw response dict instead.
    """
    try:
        response = await client._request(
            "GET", f"/api/v1/tags/by-name/{quote(name, safe='')}"
        )
        return response["id"], False
    except NotFoundError:
        response = await client._request(
            "POST", "/api/v1/tags", json={"name": name, "is_public": True}
        )
        return response["id"], True


async def create_campaign(
    admin_api_key: str,
    base_url: str,
    *,
    slug: str = DEFAULT_SLUG,
    tag_name: str = DEFAULT_TAG,
    campaign_name: str = DEFAULT_NAME,
    dry_run: bool = False,
) -> dict[str, Any]:
    async with SubscribeFlowClient(
        api_key=admin_api_key, base_url=base_url, timeout=30.0
    ) as client:
        # 1. Resolve the template by slug (no direct get-by-slug in the
        # SDK, same pagination pattern as the provisioning scripts).
        template = None
        skip = 0
        while template is None:
            page = await client.templates.list(skip=skip, limit=100)
            template = next((t for t in page.items if t.slug == slug), None)
            skip += len(page.items)
            if not page.items or skip >= page.total:
                break
        if template is None:
            raise SystemExit(
                f"No template with slug {slug!r} found. Run "
                "provision_subscribeflow_newsletter.py first."
            )

        # 2. Resolve the recipient tag (already exists in practice --
        # see module docstring for why this bypasses client.tags.*).
        tag_id, tag_created = await _get_or_create_tag_id(client, tag_name)

        # 3. Idempotency check on campaign name.
        cursor = None
        for _ in range(50):
            campaigns_page = await client.campaigns.list(cursor=cursor, limit=100)
            existing = next(
                (c for c in campaigns_page.items if c.name == campaign_name), None
            )
            if existing:
                return {
                    "action": "already_exists",
                    "campaign_id": existing.id,
                    "status": existing.status,
                    "name": existing.name,
                }
            cursor = campaigns_page.next_cursor
            if not cursor:
                break
        else:
            raise RuntimeError(
                "campaigns.list() pagination did not terminate after 50 pages"
            )

        if dry_run:
            return {
                "action": "would_create",
                "template_id": template.id,
                "tag_id": tag_id,
                "tag_created": tag_created,
                "name": campaign_name,
            }

        # 4. Create the DRAFT campaign. Never sent from this script.
        campaign = await client.campaigns.create(
            name=campaign_name,
            template_id=template.id,
            tag_filter={"include_tags": [tag_id]},
        )
        return {
            "action": "created",
            "campaign_id": campaign.id,
            "status": campaign.status,
            "name": campaign.name,
            "template_id": campaign.template_id,
            "tag_filter": campaign.tag_filter,
        }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-key", default=os.getenv("SUBSCRIBEFLOW_API_KEY", ""))
    parser.add_argument(
        "--base-url",
        default=os.getenv("SUBSCRIBEFLOW_BASE_URL", "https://api.subscribeflow.net"),
    )
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.admin_key:
        raise SystemExit("--admin-key or SUBSCRIBEFLOW_API_KEY required")

    result = asyncio.run(
        create_campaign(
            args.admin_key,
            args.base_url,
            slug=args.slug,
            tag_name=args.tag,
            campaign_name=args.name,
            dry_run=args.dry_run,
        )
    )
    print(json.dumps(result, indent=2, default=str))
    if result["action"] == "created":
        print(
            "\nCampaign created in DRAFT status -- NOT sent. "
            "Trigger the send explicitly (SubscribeFlow admin UI or "
            "client.campaigns.send()) only when ready."
        )


if __name__ == "__main__":
    _main()

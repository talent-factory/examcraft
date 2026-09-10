"""Provisioning script for the ExamCraft AI customer newsletter: creates/
updates marketing email templates in SubscribeFlow, one entry per issue.

Unlike provision_subscribeflow_email.py (transactional templates), this
script does NOT mint an API key or manage a webhook endpoint -- the
scoped "ExamCraft emails:send" key and the delivery-status webhook
already exist from TF-764 and are shared across transactional and
marketing sends. This script only creates/updates EmailTemplate rows
(category="marketing"), matched by slug and idempotent, same as the
templates loop in the transactional script.

Recipients already exist as SubscribeFlow Subscribers: every user is
subscribed with the "examcraft" tag on email verification (see
services/subscribeflow_service.py, SubscribeFlowService.subscribe_user).
A campaign for a given issue is created separately (not by this script)
via `client.campaigns.create(name=..., template_id=..., tag_filter=
{"include_tags": [<id of the "examcraft" tag>]})` and triggered with
`client.campaigns.send(campaign_id)` -- a deliberate, explicit step,
never run by automation.

IMPORTANT -- compliance footer caveat, tracked as TF-803 (found while
building the "newsletter-2026-09" entry below): every SubscribeFlow
render (transactional AND marketing) unconditionally appends its own
compliance footer after the template's own content
(TemplateRenderingService._append_compliance_footer): an "unsubscribe /
manage preferences" block using formal "Sie" and the *global*
`settings.app_name` / `settings.company_address` -- NOT anything
per-organization. On the `subscribeflow-api` Fly app, neither
`APP_NAME` nor `COMPANY_ADDRESS` is set (checked via `fly secrets list`
and the committed `fly.toml` / `.env.example`), so the code defaults
apply: `app_name="SubscribeFlow"`, `company_address=""`. Every email
already sent through SubscribeFlow -- the 4 existing transactional
templates included -- therefore currently closes with "Sie erhalten
diese E-Mail, weil Sie bei SubscribeFlow registriert sind." (wrong
product name, no address, and a "Sie" that clashes with ExamCraft's
"Du" voice). This script's own templates deliberately do NOT include a
second, redundant footer/unsubscribe block for that reason -- but the
mismatch itself is a SubscribeFlow-side config gap, not something this
script can fix. See TF-803 for the recommended fix (set
`APP_NAME=ExamCraft AI` and `COMPANY_ADDRESS=Talent Factory GmbH,
Hofstattweg 6, 3422 Kirchberg BE, Schweiz` as Fly secrets on
`subscribeflow-api` -- affects every template, not just the
newsletter).

Usage:
    python -m scripts.provision_subscribeflow_newsletter \
        --admin-key sf_live_... \
        [--base-url https://api.subscribeflow.net] \
        [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import os
from typing import Any

from subscribeflow import SubscribeFlowClient

NEWSLETTERS: list[dict[str, Any]] = [
    {
        # One slug per issue -- content differs each time, so each issue
        # gets its own template rather than reusing/overwriting a single
        # "newsletter" slug. Add the next issue as a new list entry.
        #
        # NOT "newsletter-2026-09": that slug is permanently stuck after
        # being archived once in SubscribeFlow -- see TF-804 (archiving
        # soft-deletes via is_active=false, but the DB unique index on
        # `slug` is hard and global, and create()/update()/get_by_slug()
        # all filter on is_active=true, so an archived slug can neither
        # be recreated nor reactivated via the API). Use an
        # "-issue-NN" suffix going forward instead of the calendar
        # month, so a slug never has to be reused across attempts.
        "name": "newsletter-2026-issue-01",
        "subject": "ExamCraft AI Update: mehr Struktur, Sicherheit und Übersicht",
        # No custom variables: CampaignsResource.create() (SDK) only takes
        # name/template_id/tag_filter -- there is no way to pass a
        # per-campaign variable like a release-notes URL at send time, so
        # a Jinja placeholder here would always render empty. Anything
        # that doesn't vary per recipient goes in as a literal below.
        "variables_schema": {},
        "mjml_content": """<mjml>
  <mj-head>
    <mj-preview>Neuerungen aus v1.9 bis v1.11: mehr Struktur, mehr Sicherheit, mehr Übersicht.</mj-preview>
    <mj-font name="Space Grotesk" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&display=swap" />
    <mj-font name="IBM Plex Sans" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" />
    <mj-attributes>
      <mj-all font-family="IBM Plex Sans, Helvetica, Arial, sans-serif" />
      <mj-text color="#3f3f52" line-height="1.6" />
    </mj-attributes>
  </mj-head>
  <mj-body background-color="#f9f9f9" width="640px">
    <mj-section background-color="#667eea" padding="34px 32px 30px 32px">
      <mj-column>
        <mj-text align="left" color="rgba(255,255,255,0.8)" font-size="11.5px" font-weight="700" letter-spacing="1px" padding-bottom="8px">
          AUSGABE NR. 01 &mdash; SEPTEMBER 2026
        </mj-text>
        <mj-text align="left" color="#ffffff" font-family="Space Grotesk, Helvetica, Arial, sans-serif" font-size="26px" line-height="1.3" font-weight="700">
          Was ist neu bei ExamCraft AI
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="28px 32px 6px 32px">
      <mj-column>
        <mj-text font-size="15.5px">
          {% set _first_name = subscriber.first_name | default('', true) %}Hi{% if _first_name %} {{ _first_name }}{% endif %},
        </mj-text>
        <mj-text font-size="15.5px" padding-top="4px">
          Mit den Versionen 1.9, 1.10 und 1.11 haben wir seit August einiges an
          ExamCraft AI weiterentwickelt &mdash; mehr Struktur im Admin-Bereich, mehr
          Transparenz bei Sicherheit und Datenschutz, und einige spürbare
          Verbesserungen bei der Prüfungserstellung. Hier die Highlights im
          Überblick.
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="10px 32px 0 32px">
      <mj-column background-color="#eef0fd" border="1px solid #dfe1f8" border-radius="10px" padding="20px 24px">
        <mj-text color="#667eea" font-size="11px" font-weight="700" letter-spacing="0.6px">🗂&nbsp; ADMINS &amp; TEAMS</mj-text>
        <mj-text font-family="Space Grotesk, Helvetica, Arial, sans-serif" font-size="16px" font-weight="700" color="#1c1c28" padding-top="4px" padding-bottom="8px">Mehr Struktur</mj-text>
        <mj-text font-size="14px">
          <ul style="margin:0; padding-left:18px;">
            <li style="margin-bottom:8px;"><strong>Granulare Sichtbarkeit:</strong> Fragen, Prüfungen, Vorlagen und Kompetenzraster lassen sich neu auf &laquo;privat&raquo;, &laquo;Team&raquo; oder &laquo;Institution&raquo; beschränken.</li>
            <li style="margin-bottom:8px;"><strong>Organisationseinheiten:</strong> Abteilungen und Teams inklusive eigener Mitgliederverwaltung.</li>
            <li><strong>Aufgeräumtes Admin-Panel:</strong> kategorisierte Seitenleiste, Institutions-/Plattform-Switcher, ein Aktionen-Menü pro Person.</li>
          </ul>
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="14px 32px 0 32px">
      <mj-column background-color="#eef0fd" border="1px solid #dfe1f8" border-radius="10px" padding="20px 24px">
        <mj-text color="#667eea" font-size="11px" font-weight="700" letter-spacing="0.6px">🔒&nbsp; SICHERHEIT</mj-text>
        <mj-text font-family="Space Grotesk, Helvetica, Arial, sans-serif" font-size="16px" font-weight="700" color="#1c1c28" padding-top="4px" padding-bottom="8px">Datenschutz im Fokus</mj-text>
        <mj-text font-size="14px">
          <ul style="margin:0; padding-left:18px;">
            <li style="margin-bottom:8px;"><strong>Transparente Zugriffe:</strong> Impersonation bestätigst du neu per Passwort, mit sofortiger E-Mail-Benachrichtigung.</li>
            <li style="margin-bottom:8px;"><strong>DSGVO-Löschautomatik:</strong> abgelaufene Aufbewahrungsfristen werden automatisch vollzogen.</li>
            <li><strong>Vertragsdokumente griffbereit:</strong> AVV, TOM und Subprozessoren neu direkt einsehbar.</li>
          </ul>
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="14px 32px 0 32px">
      <mj-column background-color="#eef0fd" border="1px solid #dfe1f8" border-radius="10px" padding="20px 24px">
        <mj-text color="#667eea" font-size="11px" font-weight="700" letter-spacing="0.6px">📝&nbsp; PRÜFUNGEN</mj-text>
        <mj-text font-family="Space Grotesk, Helvetica, Arial, sans-serif" font-size="16px" font-weight="700" color="#1c1c28" padding-top="4px" padding-bottom="8px">Schneller erstellt</mj-text>
        <mj-text font-size="14px">
          <ul style="margin:0; padding-left:18px;">
            <li style="margin-bottom:8px;"><strong>PDF-Export:</strong> Prüfungen lassen sich neu direkt als druckfertiges PDF exportieren.</li>
            <li style="margin-bottom:8px;"><strong>Freie Navigation im Wizard:</strong> jederzeit zwischen Schritten wechseln, Fortschritt bleibt erhalten.</li>
            <li><strong>Klarere Fehlermeldungen:</strong> einheitlich auf Schweizer Hochdeutsch statt technischem Rohtext.</li>
          </ul>
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="14px 32px 0 32px">
      <mj-column background-color="#eef0fd" border="1px solid #dfe1f8" border-radius="10px" padding="20px 24px">
        <mj-text color="#667eea" font-size="11px" font-weight="700" letter-spacing="0.6px">📊&nbsp; OPS-DASHBOARD</mj-text>
        <mj-text font-family="Space Grotesk, Helvetica, Arial, sans-serif" font-size="16px" font-weight="700" color="#1c1c28" padding-top="4px" padding-bottom="8px">Mehr Übersicht</mj-text>
        <mj-text font-size="14px">
          <ul style="margin:0; padding-left:18px;">
            <li style="margin-bottom:8px;"><strong>Neues Ops-Dashboard:</strong> Institutions-Admins sehen den Systemstatus auf einen Blick, inklusive Chat für Rückfragen.</li>
            <li><strong>Onboarding-Tour:</strong> neue Mitarbeitende finden sich dank vertiefter Tour schneller zurecht.</li>
          </ul>
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="#f9f9f9" padding="26px 32px 30px 32px">
      <mj-column>
        <mj-button background-color="#667eea" border-radius="8px" href="https://docs.examcraft.ch/changelog" font-weight="700" font-size="14.5px">
          Alle Details in den Release Notes
        </mj-button>
        <mj-text align="center" font-size="13px" color="#8f8fa3" padding-top="16px">
          Fragen dazu? Schreib uns an
          <a href="mailto:support@talent-factory.ch" style="color:#667eea;">support@talent-factory.ch</a>
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
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create/update every entry in NEWSLETTERS (matched by slug). Mirrors
    the templates loop in provision_subscribeflow_email.py, including the
    same >100-templates pagination gap."""
    result: dict[str, Any] = {"templates": []}

    async with SubscribeFlowClient(
        api_key=admin_api_key, base_url=base_url, timeout=30.0
    ) as client:
        existing_by_slug = {}
        skip = 0
        while True:
            templates_page = await client.templates.list(skip=skip, limit=100)
            existing_by_slug.update({t.slug: t for t in templates_page.items})
            skip += len(templates_page.items)
            if not templates_page.items or skip >= templates_page.total:
                break

        for tmpl in NEWSLETTERS:
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
                        category="marketing",
                    )
                    result["templates"].append(
                        {"slug": created.slug, "action": "created"}
                    )
                else:
                    result["templates"].append({"slug": slug, "action": "created"})

    return result


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-key", default=os.getenv("SUBSCRIBEFLOW_API_KEY", ""))
    parser.add_argument(
        "--base-url",
        default=os.getenv("SUBSCRIBEFLOW_BASE_URL", "https://api.subscribeflow.net"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.admin_key:
        raise SystemExit("--admin-key or SUBSCRIBEFLOW_API_KEY required")

    result = asyncio.run(provision(args.admin_key, args.base_url, dry_run=args.dry_run))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _main()

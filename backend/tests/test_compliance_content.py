"""Tests for ``services.compliance_content`` (TF-746).

Pure unit tests — the content module has no DB/network dependency, so
these assert structural invariants (required Art. 28/32 elements are
present, subprocessor list is complete) rather than exact wording.
"""

from __future__ import annotations

import re

from services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES
from services.compliance_content import DRAFT_NOTICE, get_compliance_content

REQUIRED_SUBPROCESSORS = {
    "Anthropic",
    "OpenAI",
    "Fly.io",
    "Tigris",
    "Stripe",
    "Resend",
    "Sentry",
    "PostgreSQL",
    "Redis",
    "Google",
    "Microsoft",
    "SubscribeFlow",
    "Brevo",
}

# Art. 28 Abs. 3 DSGVO lit. a-h — every AVV must address each of these.
REQUIRED_AVV_TOPICS = (
    "Gegenstand und Dauer",
    "Weisung",
    "Vertraulichkeit",
    "Art. 32",
    "Unterauftrag",
    "Betroffenenrechte",
    "Löschung",
    "Rückgabe",
    "Nachweis",
)

# Art. 32 DSGVO Schutzziele — every TOM annex must cover each category.
REQUIRED_TOM_CATEGORIES = (
    "Vertraulichkeit",
    "Integrität",
    "Verfügbarkeit",
    "Verfahren",
)


def test_avv_carries_the_draft_notice() -> None:
    content = get_compliance_content()

    assert content.avv.draft_notice == DRAFT_NOTICE


def test_avv_covers_every_required_art_28_topic() -> None:
    content = get_compliance_content()
    full_text = " ".join(
        section.heading + " " + " ".join(section.paragraphs)
        for section in content.avv.sections
    )

    for topic in REQUIRED_AVV_TOPICS:
        assert topic in full_text, f"AVV missing required topic: {topic}"


def test_tom_covers_every_schutzziel_category() -> None:
    content = get_compliance_content()
    headings = [section.heading for section in content.tom.sections]

    for category in REQUIRED_TOM_CATEGORIES:
        assert any(category in heading for heading in headings), (
            f"TOM missing Schutzziel category: {category}"
        )


def test_subprocessor_list_includes_every_required_service() -> None:
    content = get_compliance_content()
    names = {sp.name for sp in content.subprocessors}

    for required in REQUIRED_SUBPROCESSORS:
        assert any(required in name for name in names), (
            f"Subprocessor list missing: {required}"
        )


def test_every_subprocessor_documents_location_and_change_notice() -> None:
    content = get_compliance_content()

    for sp in content.subprocessors:
        assert sp.location, f"{sp.name} missing location"
        assert sp.transfer_mechanism, f"{sp.name} missing transfer mechanism"
        assert sp.change_notice, f"{sp.name} missing change-notice policy"


def test_vvt_text_names_the_processor() -> None:
    content = get_compliance_content()

    assert "ExamCraft" in content.vvt_text
    assert "Talent Factory" in content.vvt_text


def test_state_specific_notes_flag_baden_wuerttemberg_and_hessen() -> None:
    content = get_compliance_content()
    text = content.state_specific_notes.heading + " ".join(
        content.state_specific_notes.paragraphs
    )

    assert "Baden-Württemberg" in text
    assert "Hessen" in text


def test_tom_jwt_lifetime_claim_matches_the_actual_configured_default() -> None:
    """Regression test: the TOM text once claimed "15 Minuten" while the
    code default (``auth_service.ACCESS_TOKEN_EXPIRE_MINUTES``) was 30 —
    a factual drift a reader could not have caught. Derive the expected
    number from the code so the two can never silently diverge again.
    """
    content = get_compliance_content()
    full_text = " ".join(
        section.heading + " " + " ".join(section.paragraphs)
        for section in content.tom.sections
    )

    assert f"({ACCESS_TOKEN_EXPIRE_MINUTES} Minuten)" in full_text


def test_avv_deletion_cross_reference_points_to_an_existing_tom_section() -> None:
    """Regression test: the AVV once referenced "TOM-Anlage Abschnitt 4"
    for the Löschautomatik, but that section actually covered CI/restore
    rehearsal — not deletion periods. Assert the cross-reference names a
    TOM section number that actually exists and whose heading is about
    retention/deletion.
    """
    content = get_compliance_content()
    avv_text = " ".join(
        section.heading + " " + " ".join(section.paragraphs)
        for section in content.avv.sections
    )

    match = re.search(r"TOM-Anlage Abschnitt (\d+)", avv_text)
    assert match, "AVV no longer cross-references a TOM-Anlage section number"

    referenced_number = match.group(1)
    tom_headings = [section.heading for section in content.tom.sections]
    referenced_heading = next(
        (h for h in tom_headings if h.startswith(f"{referenced_number}.")),
        None,
    )
    assert referenced_heading is not None, (
        f"AVV references TOM-Anlage Abschnitt {referenced_number}, "
        f"which does not exist (TOM headings: {tom_headings})"
    )
    assert "Löschfristen" in referenced_heading or "Speicherbegrenzung" in (
        referenced_heading
    ), (
        f"AVV's deletion cross-reference points at an unrelated section: {referenced_heading!r}"
    )

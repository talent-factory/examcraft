"""Consistency between ONBOARDING_MAX_STEPS and help-onboarding-steps.json (TF-625).

If the backend constant and the frontend JSON drift apart, the core tour is
marked complete too early or never — exactly the mechanism that kept TF-604
invisible. The coupling deliberately exists only here in the test: at runtime
the backend must not depend on a frontend asset (separate deployments), but
within the same repository both files always sit side by side.
"""

import json
from pathlib import Path

import pytest

from api.v1.help import (
    MAX_TRACK_STEPS,
    MAX_TRACKS_PER_USER,
    ONBOARDING_MAX_STEPS,
    TRACK_ID_PATTERN,
)

STEPS_FILE = (
    Path(__file__).resolve().parents[3]
    / "core"
    / "frontend"
    / "public"
    / "help-onboarding-steps.json"
)

# The eight routes from TF-625 that appeared in no tour before this ticket,
# each with the role that actually sees the menu entry.
REQUIRED_ROUTES = {
    "/exams/compose": {"teacher", "admin"},
    "/auswertungen": {"teacher", "admin"},
    "/auswertungen/klassen": {"teacher", "admin"},
    "/auswertungen/studierende": {"teacher", "admin"},
    "/settings/tags": {"teacher"},
    "/settings/competency-frameworks": {"teacher"},
    "/aktivitaeten": {"teacher", "admin"},
    "/chat": {"teacher", "admin"},
    "/admin/integrations/moodle": {"admin"},
}


LOCALES_DIR = (
    Path(__file__).resolve().parents[3] / "core" / "frontend" / "src" / "locales"
)

# Steps whose popover title names a control the user has to find on screen.
# Keyed by highlight_selector, valued by the dotted i18n path of the label that
# control actually renders. A tour that says "Rollen" while the tab reads
# "Rollen & Berechtigungen" sends the user looking for something that is not
# there — found manually during TF-625 testing.
TITLE_MUST_MATCH_LABEL = {
    "[data-testid='admin-tab-content-users']": "pages.admin.tabUsers",
    "[data-testid='admin-tab-content-institutions']": "pages.admin.tabInstitutions",
    "[data-testid='admin-tab-content-roles']": "pages.admin.tabRoles",
    "[data-testid='admin-tab-content-audit']": "pages.admin.tabAudit",
    "[data-testid='admin-tab-content-subscription']": "pages.admin.tabSubscription",
    "[data-testid='moodle-connection-content']": "nav.sidebar.moodleConnection",
}


def _resolve(translations: dict, dotted: str) -> str:
    node = translations
    for part in dotted.split("."):
        node = node[part]
    return node


@pytest.fixture(scope="module")
def translations():
    result = {}
    for locale in ("de", "en"):
        path = LOCALES_DIR / locale / "translation.json"
        if not path.exists():  # pragma: no cover - only on a broken checkout
            pytest.skip(f"translation file not found at {path}")
        result[locale] = json.loads(path.read_text(encoding="utf-8"))
    return result


@pytest.fixture(scope="module")
def steps_data():
    if not STEPS_FILE.exists():  # pragma: no cover - only on a broken checkout
        pytest.skip(f"steps file not found at {STEPS_FILE}")
    return json.loads(STEPS_FILE.read_text(encoding="utf-8"))


class TestCoreStepConsistency:
    def test_roles_match_constant(self, steps_data):
        assert set(steps_data.keys()) == set(ONBOARDING_MAX_STEPS.keys())

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_core_length_matches_max_steps(self, steps_data, role):
        """This is the test that would have prevented TF-604."""
        assert len(steps_data[role]["core"]) == ONBOARDING_MAX_STEPS[role], (
            f"ONBOARDING_MAX_STEPS['{role}'] == {ONBOARDING_MAX_STEPS[role]}, "
            f"but the JSON has {len(steps_data[role]['core'])} core steps"
        )

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_core_steps_numbered_contiguously_from_zero(self, steps_data, role):
        numbers = [s["step"] for s in steps_data[role]["core"]]
        assert numbers == list(range(len(numbers)))

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_core_stays_short(self, steps_data, role):
        """Acceptance criterion: the first-login core tour stays at ~8 steps."""
        assert len(steps_data[role]["core"]) <= 8


class TestTrackConsistency:
    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_track_ids_valid_and_unique(self, steps_data, role):
        ids = [tr["id"] for tr in steps_data[role]["tracks"]]
        assert len(ids) == len(set(ids)), f"duplicate track ids in {role}: {ids}"
        for track_id in ids:
            assert TRACK_ID_PATTERN.match(track_id), f"invalid track id: {track_id}"

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_track_count_within_backend_cap(self, steps_data, role):
        assert len(steps_data[role]["tracks"]) <= MAX_TRACKS_PER_USER

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_track_steps_numbered_contiguously_from_zero(self, steps_data, role):
        for track in steps_data[role]["tracks"]:
            numbers = [s["step"] for s in track["steps"]]
            assert numbers == list(range(len(numbers))), (
                f"track {track['id']} ({role}) is not numbered contiguously "
                f"from 0: {numbers}"
            )

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_track_length_within_backend_cap(self, steps_data, role):
        for track in steps_data[role]["tracks"]:
            assert 1 <= len(track["steps"]) <= MAX_TRACK_STEPS

    @pytest.mark.parametrize("role", ["teacher", "admin"])
    def test_every_track_step_has_a_highlight_anchor(self, steps_data, role):
        """Without an anchor the skip path kicks in and the step is never shown."""
        for track in steps_data[role]["tracks"]:
            for step in track["steps"]:
                assert step["highlight_selector"], (
                    f"track {track['id']} ({role}) step {step['step']} "
                    f"({step['route']}) has no highlight_selector"
                )


class TestTitlesMatchVisibleLabels:
    """Popover titles that name a control must use that control's own wording.

    Both sides now live in translation.json, but under different keys: the step
    title under its own `i18n_key`, the control label wherever the component
    reads it. Nothing but this test keeps the two from drifting — the same
    class of gap as ONBOARDING_MAX_STEPS vs. the core array.

    Read `step["title_de"]`/`["title_en"]` until e43b3ed moved the tour texts
    out of help-onboarding-steps.json; the step file now carries only structure
    plus an explicit `i18n_key`.
    """

    @pytest.mark.parametrize("locale", ["de", "en"])
    def test_step_title_equals_rendered_label(self, steps_data, translations, locale):
        checked = 0
        for role in steps_data:
            for track in steps_data[role]["tracks"]:
                for step in track["steps"]:
                    dotted = TITLE_MUST_MATCH_LABEL.get(step["highlight_selector"])
                    if not dotted:
                        continue
                    expected = _resolve(translations[locale], dotted)
                    title = _resolve(translations[locale], f"{step['i18n_key']}.title")
                    assert title == expected, (
                        f"{role}/{track['id']} step {step['step']}: title is "
                        f"{title!r}, but the control reads {expected!r} "
                        f"({dotted})"
                    )
                    checked += 1
        # Guard against the mapping silently matching nothing after a selector
        # rename, which would turn this whole test into a no-op.
        assert checked >= len(TITLE_MUST_MATCH_LABEL)


class TestRouteCoverage:
    @pytest.mark.parametrize("route,roles", sorted(REQUIRED_ROUTES.items()))
    def test_route_is_reachable_in_every_role_that_sees_it(
        self, steps_data, route, roles
    ):
        """Acceptance criterion: all eight routes are reachable in the tour."""
        for role in roles:
            covered = {
                step["route"] for step in steps_data[role]["core"] if step.get("route")
            }
            for track in steps_data[role]["tracks"]:
                covered.update(s["route"] for s in track["steps"] if s.get("route"))
            assert route in covered, f"{route} missing from the tour for role {role}"

    def test_admin_only_routes_absent_for_teacher(self, steps_data):
        """A step the user can never see does not belong in their tour."""
        teacher_routes = set()
        for track in steps_data["teacher"]["tracks"]:
            teacher_routes.update(s["route"] for s in track["steps"] if s.get("route"))
        teacher_routes.update(
            s["route"] for s in steps_data["teacher"]["core"] if s.get("route")
        )
        assert "/admin/integrations/moodle" not in teacher_routes
        assert "/admin" not in teacher_routes

    def test_teacher_only_routes_absent_for_admin(self, steps_data):
        """Admin is excluded from /settings/tags & co. via excludedRoles."""
        admin_routes = set()
        for track in steps_data["admin"]["tracks"]:
            admin_routes.update(s["route"] for s in track["steps"] if s.get("route"))
        admin_routes.update(
            s["route"] for s in steps_data["admin"]["core"] if s.get("route")
        )
        assert "/settings/tags" not in admin_routes
        assert "/settings/competency-frameworks" not in admin_routes

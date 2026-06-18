"""TF-435: probe-based transport selection."""

from unittest.mock import patch

import pytest

from services.moodle_feedback.selection import select_transport
from services.moodle_feedback.transports import (
    GradebookFeedbackTransport,
    PluginFeedbackTransport,
)
from services.moodle_feedback.ws_client import MoodleWsError


def _site_info(functions):
    return {"functions": [{"name": n} for n in functions]}


def test_select_plugin_when_function_present():
    with patch(
        "services.moodle_feedback.selection.call_moodle",
        return_value=_site_info(["local_examcraft_set_quiz_feedback"]),
    ):
        t = select_transport("https://m", "tok")
    assert isinstance(t, PluginFeedbackTransport)


def test_select_gradebook_when_function_absent():
    with patch(
        "services.moodle_feedback.selection.call_moodle",
        return_value=_site_info(["core_webservice_get_site_info"]),
    ):
        t = select_transport("https://m", "tok")
    assert isinstance(t, GradebookFeedbackTransport)


def test_force_override_gradebook():
    with patch(
        "services.moodle_feedback.selection.call_moodle",
        return_value=_site_info(["local_examcraft_set_quiz_feedback"]),
    ):
        t = select_transport("https://m", "tok", force="gradebook")
    assert isinstance(t, GradebookFeedbackTransport)


def test_force_override_plugin_without_probe():
    """force=plugin returns the plugin transport without probing site_info."""
    with patch("services.moodle_feedback.selection.call_moodle") as call:
        t = select_transport("https://m", "tok", force="plugin")
    assert isinstance(t, PluginFeedbackTransport)
    call.assert_not_called()  # forced → no probe


def test_unknown_force_raises_not_silently_gradebook():
    """A typo'd force value must fail loud, not fall through to gradebook."""
    with patch("services.moodle_feedback.selection.call_moodle"):
        with pytest.raises(ValueError):
            select_transport("https://m", "tok", force="Plugin")  # wrong case


def test_probe_failure_raises_and_does_not_fall_back():
    """A bad token / unreachable site raises MoodleWsError — no silent gradebook."""
    with patch(
        "services.moodle_feedback.selection.call_moodle",
        side_effect=MoodleWsError("Token ungültig"),
    ):
        with pytest.raises(MoodleWsError):
            select_transport("https://m", "tok")

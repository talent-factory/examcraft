"""Pick the feedback transport: probe site_info for the plugin function. TF-435."""

from __future__ import annotations

from enums import FeedbackTransportName
from services.moodle_feedback.transports import (
    FeedbackTransport,
    GradebookFeedbackTransport,
    PluginFeedbackTransport,
)
from services.moodle_feedback.ws_client import call_moodle

PLUGIN_FUNCTION = "local_examcraft_set_quiz_feedback"


def select_transport(
    base_url: str, token: str, *, force: FeedbackTransportName | str | None = None
) -> FeedbackTransport:
    """Return the transport to use.

    ``force`` (a ``FeedbackTransportName`` or its string value) overrides the
    probe. An unrecognised force value raises ``ValueError`` rather than
    silently falling through to gradebook — the old ``force == "plugin"``
    literal compare made a typo (``"Plugin"``) pick the wrong transport.
    Otherwise probe core_webservice_get_site_info for the plugin function.

    A failed probe (bad token, unreachable site) raises ``MoodleWsError``;
    selection does NOT fall back to gradebook on probe error (a dead site
    can't accept either transport). The caller classifies that failure.
    """
    if force is not None:
        forced = FeedbackTransportName(force)  # raises ValueError on unknown
        if forced is FeedbackTransportName.PLUGIN:
            return PluginFeedbackTransport(base_url, token)
        return GradebookFeedbackTransport(base_url, token)

    info = call_moodle(base_url, token, "core_webservice_get_site_info", {})
    functions = {f.get("name") for f in (info.get("functions") or [])}
    if PLUGIN_FUNCTION in functions:
        return PluginFeedbackTransport(base_url, token)
    return GradebookFeedbackTransport(base_url, token)

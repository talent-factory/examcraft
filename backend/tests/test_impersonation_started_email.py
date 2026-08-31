"""Tests for TF-759's impersonation-started notification email.

Sibling of ``test_impersonation_ended_email.py`` (TF-742): same
``EmailService`` / Celery-task pattern, this time dispatched when a session
*begins* instead of when it ends, so the target user learns about an
ongoing impersonation without having to wait for it to close.
"""

from unittest.mock import patch

from services.email_service import EmailService


def test_send_impersonation_started_email_builds_expected_content():
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_1"}

        result = EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="Support-Anfrage TICKET-42",
            started_at="2026-08-31T10:00:00+00:00",
        )

        assert result == {"id": "email_1"}
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to"] == "target@example.com"
        assert "Admin Person" in call_kwargs["html"]
        assert "Support-Anfrage TICKET-42" in call_kwargs["html"]
        assert "Target User" in call_kwargs["html"]
        assert "2026-08-31T10:00:00+00:00" in call_kwargs["html"]
        assert "Admin Person" in call_kwargs["text"]
        assert call_kwargs["tags"] == {"type": "impersonation_started"}


def test_send_impersonation_started_email_mentions_auto_expiry():
    """The target should learn the session isn't open-ended -- it dies on
    its own after the TF-741 hard cap even if no one ends it manually."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_2"}

        EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "30" in html or "automatically" in html.lower()


def test_send_impersonation_started_email_handles_missing_started_at():
    """Defensive: must never raise, worst case shows "unknown"."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_3"}

        EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at=None,
        )

        mock_send.assert_called_once()
        assert "unknown" in mock_send.call_args.kwargs["html"]


def test_send_impersonation_started_email_escapes_html_in_admin_supplied_reason():
    """Same TF-742 review fix, applied here: ``reason`` is free text typed
    by the *impersonating admin* and delivered inside a trusted-looking
    ExamCraft security notice to a *different* user (the impersonation
    target) -- must be escaped before interpolation into the HTML body."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_4"}

        malicious_reason = '<a href="https://evil.example/reset">click</a>'

        EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason=malicious_reason,
            started_at="2026-08-31T10:00:00+00:00",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "<a href=" not in html
        assert "&lt;a href=" in html
        assert "&lt;/a&gt;" in html
        text = mock_send.call_args.kwargs["text"]
        assert malicious_reason in text


def test_send_impersonation_started_email_escapes_html_in_names():
    """``to_name``/``admin_name`` are escaped too (``html.escape`` is applied
    to all three interpolated fields in the implementation) -- the sibling
    test above only exercised ``reason``; this covers the other two so a
    regression there wouldn't slip through untested."""
    with patch.object(EmailService, "_send_email") as mock_send:
        mock_send.return_value = {"id": "email_6"}

        EmailService.send_impersonation_started_email(
            to_email="target@example.com",
            to_name="<img src=x onerror=alert(1)>",
            admin_name='"><script>alert(2)</script>',
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
        )

        html = mock_send.call_args.kwargs["html"]
        assert "<img src=x" not in html
        assert "<script>" not in html
        assert "&lt;img src=x" in html
        assert "&lt;script&gt;" in html


def test_impersonation_email_tasks_are_registered_and_routed():
    """Review-fix regression guard (TF-759): both impersonation
    notification tasks were previously unreachable in production --
    ``tasks.notification_tasks`` was missing from ``celery_app``'s
    ``include`` list (so the worker never imported the module and the
    tasks weren't registered at all) and neither task had a
    ``task_routes`` entry (so a message would have landed on the
    unconsumed default ``celery`` queue, which no worker command
    listens on -- see the queue comments in ``celery_app.py``). Both
    gaps are silent: ``.delay()`` still returns normally, the task is
    just never picked up. This test would have caught that.

    ``celery_app.tasks`` only contains tasks whose defining module has
    actually been Python-imported in this process -- merely listing a
    module in ``include`` doesn't populate it until something (a real
    worker at bootstrap, or ``import_default_modules()`` here) imports
    it, so we call that explicitly instead of depending on *other*
    test files having already imported ``tasks.notification_tasks``
    first (which would make this test pass even with a bad
    ``include`` list, depending on pytest's collection order)."""
    from celery_app import celery_app

    assert "tasks.notification_tasks" in celery_app.conf.include, (
        "tasks.notification_tasks is missing from celery_app.py's "
        "`include` list -- the worker never imports it, so none of its "
        "tasks are registered at all"
    )
    celery_app.loader.import_default_modules()

    consumed_queues = {
        "document_processing",
        "rag_embedding",
        "question_generation",
        "notifications",
        "import_processing",
        "maintenance_processing",
    }

    for name in (
        "tasks.notification_tasks.send_impersonation_started_email",
        "tasks.notification_tasks.send_impersonation_ended_email",
    ):
        assert name in celery_app.tasks, (
            f"{name} isn't registered even after import_default_modules() -- "
            "is the @celery_app.task `name=` wrong?"
        )
        route = celery_app.conf.task_routes.get(name)
        assert route is not None, (
            f"{name} has no task_routes entry -- it would land on the "
            "unconsumed default 'celery' queue and never run"
        )
        assert route["queue"] in consumed_queues, (
            f"{name} is routed to queue {route['queue']!r}, which no "
            "worker command actually consumes"
        )


def test_celery_task_delegates_to_email_service():
    from tasks.notification_tasks import send_impersonation_started_email

    with patch.object(EmailService, "send_impersonation_started_email") as mock_send:
        mock_send.return_value = {"id": "email_5"}

        result = send_impersonation_started_email.run(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
        )

        assert result == {"id": "email_5"}
        mock_send.assert_called_once_with(
            to_email="target@example.com",
            to_name="Target User",
            admin_name="Admin Person",
            reason="r",
            started_at="2026-08-31T10:00:00+00:00",
        )

"""Tests for the SubscribeFlow email provisioning script (TF-764)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.provision_subscribeflow_email import API_KEY_NAME, TEMPLATES, provision

WEBHOOK_EVENTS = ["email.sent", "email.delivered", "email.bounced", "email.complained"]


def _request_side_effect(*, existing_keys=None, created_key=None):
    """Build a ``client._request`` side_effect that answers GET (list) and
    POST (create) for /api/v1/api-keys differently, matching the real API."""
    existing_keys = existing_keys if existing_keys is not None else []
    created_key = created_key or {
        "key": "sf_live_test",
        "id": "key-1",
        "scopes": ["emails:send"],
    }

    async def _side_effect(method, path, **kwargs):
        if method == "GET" and path == "/api/v1/api-keys":
            return existing_keys
        if method == "POST" and path == "/api/v1/api-keys":
            return created_key
        raise AssertionError(f"unexpected _request call: {method} {path}")

    return _side_effect


@pytest.mark.asyncio
async def test_provision_creates_missing_templates():
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    assert mock_client.templates.create.call_count == len(TEMPLATES)
    assert result["emails_api_key"]["key"] == "sf_live_test"
    assert result["emails_api_key"]["reused"] is False
    assert (
        result["webhook_endpoint"]["secret"] == "whsec_test"
    )  # pragma: allowlist secret
    mock_client.webhooks.create.assert_called_once_with(
        url="https://examcraft-api.fly.dev/webhooks/subscribeflow",
        events=WEBHOOK_EVENTS,
    )


@pytest.mark.asyncio
async def test_provision_updates_existing_template_instead_of_duplicating():
    existing_template = MagicMock(slug="verification")
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[existing_template], total=1)
    )
    mock_client.templates.update = AsyncMock(return_value=existing_template)
    mock_client.templates.create = AsyncMock()
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    verification_creates = [
        c
        for c in mock_client.templates.create.call_args_list
        if c.kwargs.get("name") == "verification"
    ]
    assert verification_creates == [], (
        "existing 'verification' template must be updated, not re-created"
    )
    mock_client.templates.update.assert_any_call(
        slug="verification",
        subject=TEMPLATES[0]["subject"],
        mjml_content=TEMPLATES[0]["mjml_content"],
        variables_schema=TEMPLATES[0]["variables_schema"],
    )


@pytest.mark.asyncio
async def test_provision_reuses_existing_webhook_endpoint():
    existing_endpoint = MagicMock(
        id="wh-existing",
        url="https://examcraft-api.fly.dev/webhooks/subscribeflow",
        events=WEBHOOK_EVENTS,
    )
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[existing_endpoint], total=1, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock()
    mock_client.webhooks.update = AsyncMock()
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    mock_client.webhooks.create.assert_not_called()
    # events already match WEBHOOK_EVENTS -- no reconciliation needed
    mock_client.webhooks.update.assert_not_called()
    assert result["webhook_endpoint"]["id"] == "wh-existing"
    assert result["webhook_endpoint"]["secret"] is None, (
        "the plaintext secret is only ever returned at creation time -- "
        "reusing an existing endpoint must not fabricate one"
    )


@pytest.mark.asyncio
async def test_provision_reconciles_events_on_existing_webhook_with_stale_subscription():
    """An endpoint created before all 4 event types existed (or edited by
    hand) must have its subscribed events brought back in line, not just be
    silently reused as-is."""
    existing_endpoint = MagicMock(
        id="wh-existing",
        url="https://examcraft-api.fly.dev/webhooks/subscribeflow",
        events=["email.sent"],
    )
    reconciled_endpoint = MagicMock(id="wh-existing")
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[existing_endpoint], total=1, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock()
    mock_client.webhooks.update = AsyncMock(return_value=reconciled_endpoint)
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    mock_client.webhooks.create.assert_not_called()
    mock_client.webhooks.update.assert_called_once_with(
        "wh-existing", events=WEBHOOK_EVENTS
    )
    assert result["webhook_endpoint"]["events_reconciled"] is True


@pytest.mark.asyncio
async def test_provision_reuses_existing_api_key_instead_of_minting_orphan():
    """A key named 'ExamCraft emails:send' already present must be left
    alone -- re-running the script must not mint a second, orphaned key."""
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )
    mock_client._request = AsyncMock(
        side_effect=_request_side_effect(
            existing_keys=[
                {"id": "key-existing", "name": API_KEY_NAME, "scopes": ["emails:send"]}
            ]
        )
    )

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    post_calls = [
        c
        for c in mock_client._request.call_args_list
        if c.args[:2] == ("POST", "/api/v1/api-keys")
    ]
    assert post_calls == [], "an existing key must never be re-minted"
    assert result["emails_api_key"] == {
        "id": "key-existing",
        "key": None,
        "scopes": ["emails:send"],
        "reused": True,
    }


@pytest.mark.asyncio
async def test_provision_warns_but_still_reuses_key_with_unexpected_scopes():
    """A same-named key with scopes broader (or narrower) than the intended
    {'emails:send'} must still be reused as-is (this script never mutates an
    existing key), but must log loudly -- silently trusting a same-named
    key's scopes would defeat the whole point of minting a dedicated,
    least-privilege key.

    Patches the module logger directly rather than using caplog: caplog
    relies on propagation from the named logger to the root logger, which is
    unreliable across the full backend test suite (see
    project_caplog_propagation_full_suite) -- patching the logger call is
    immune to that.
    """
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )
    mock_client._request = AsyncMock(
        side_effect=_request_side_effect(
            existing_keys=[
                {
                    "id": "key-existing",
                    "name": API_KEY_NAME,
                    "scopes": ["emails:send", "subscribers:write"],
                }
            ]
        )
    )

    with (
        patch(
            "scripts.provision_subscribeflow_email.SubscribeFlowClient"
        ) as mock_client_cls,
        patch("scripts.provision_subscribeflow_email.logger") as mock_logger,
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    assert result["emails_api_key"]["reused"] is True
    assert result["emails_api_key"]["scopes"] == ["emails:send", "subscribers:write"]
    warning_text = "\n".join(
        str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
    )
    assert "emails:send" in warning_text, (
        "an unexpectedly-scoped reused key must be logged loudly"
    )


@pytest.mark.asyncio
async def test_provision_reuses_existing_api_key_when_endpoint_returns_paginated_envelope():
    """GET /api/v1/api-keys is driven through the SDK's private ``_request``
    (annotated -> dict[str, Any], not a bare list), and every *other* list
    endpoint in this SDK wraps its items in a {"items": [...]} envelope --
    if /api/v1/api-keys does too, iterating the raw response directly would
    iterate dict keys (strings) and crash on ``k["name"]``. The script must
    handle both response shapes."""
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )

    async def _paginated_request(method, path, **kwargs):
        if method == "GET" and path == "/api/v1/api-keys":
            return {
                "items": [
                    {
                        "id": "key-existing",
                        "name": API_KEY_NAME,
                        "scopes": ["emails:send"],
                    }
                ],
                "total": 1,
            }
        raise AssertionError(f"unexpected _request call: {method} {path}")

    mock_client._request = AsyncMock(side_effect=_paginated_request)

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    assert result["emails_api_key"] == {
        "id": "key-existing",
        "key": None,
        "scopes": ["emails:send"],
        "reused": True,
    }


@pytest.mark.asyncio
async def test_provision_paginates_beyond_first_page_of_templates():
    """An account with >100 templates must not have its 101st+ template
    missed (and consequently duplicated) just because ``list()`` only reads
    the first page."""
    existing_verification = MagicMock(slug="verification")

    async def _templates_list(*, skip: int = 0, limit: int = 100, **kwargs):
        if skip == 0:
            return MagicMock(
                items=[MagicMock(slug=f"other-{i}") for i in range(100)], total=101
            )
        return MagicMock(items=[existing_verification], total=101)

    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(side_effect=_templates_list)
    mock_client.templates.update = AsyncMock(return_value=existing_verification)
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.webhooks.create = AsyncMock(
        return_value=MagicMock(
            id="wh-1", secret="whsec_test"
        )  # pragma: allowlist secret
    )
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
        )

    verification_creates = [
        c
        for c in mock_client.templates.create.call_args_list
        if c.kwargs.get("name") == "verification"
    ]
    assert verification_creates == [], (
        "a template on the 2nd page of results must still be found and "
        "updated, not missed and re-created"
    )
    mock_client.templates.update.assert_any_call(
        slug="verification",
        subject=TEMPLATES[0]["subject"],
        mjml_content=TEMPLATES[0]["mjml_content"],
        variables_schema=TEMPLATES[0]["variables_schema"],
    )


@pytest.mark.asyncio
async def test_provision_dry_run_previews_templates_only():
    """--dry-run must return before the API-key/webhook steps run at all --
    that's the entire point of the flag (avoid minting a live, orphaned key
    during a preview)."""
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )

    with patch(
        "scripts.provision_subscribeflow_email.SubscribeFlowClient"
    ) as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        result = await provision(
            admin_api_key="sf_live_admin",
            base_url="https://api.subscribeflow.net",
            backend_url="https://examcraft-api.fly.dev",
            dry_run=True,
        )

    mock_client.templates.create.assert_not_called()
    mock_client.templates.update.assert_not_called()
    mock_client._request.assert_not_called()
    mock_client.webhooks.list.assert_not_called()
    mock_client.webhooks.create.assert_not_called()
    assert result["emails_api_key"] is None
    assert result["webhook_endpoint"] is None
    assert [t["action"] for t in result["templates"]] == ["created"] * len(TEMPLATES)


@pytest.mark.asyncio
async def test_provision_logs_partial_progress_before_reraising_on_failure():
    """If the webhook step fails after the API key was already minted for
    real, the fact that a key was created must not be lost to a bare
    traceback -- but its plaintext value must never be written to the log
    stream (only the deliberate, once-only stdout ``print()`` in ``_main()``
    is allowed to show it).

    Patches the module logger directly rather than using caplog: caplog
    relies on propagation from the named logger to the root logger, which
    is unreliable across the full backend test suite (some other test/
    module disables propagation depending on run order) -- see
    project_caplog_propagation_full_suite. Patching the logger call is
    immune to that.
    """
    mock_client = AsyncMock()
    mock_client.templates.list = AsyncMock(
        return_value=MagicMock(items=[], total=0, next_cursor=None)
    )
    mock_client.templates.create = AsyncMock(
        side_effect=lambda **kwargs: MagicMock(slug=kwargs["name"].lower())
    )
    mock_client.webhooks.list = AsyncMock(side_effect=RuntimeError("network blip"))
    mock_client._request = AsyncMock(side_effect=_request_side_effect())

    with (
        patch(
            "scripts.provision_subscribeflow_email.SubscribeFlowClient"
        ) as mock_client_cls,
        patch("scripts.provision_subscribeflow_email.logger") as mock_logger,
    ):
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        with pytest.raises(RuntimeError, match="network blip"):
            await provision(
                admin_api_key="sf_live_admin",
                base_url="https://api.subscribeflow.net",
                backend_url="https://examcraft-api.fly.dev",
            )

    logged_text = "\n".join(
        str(arg) for call in mock_logger.error.call_args_list for arg in call.args
    )
    assert "sf_live_test" not in logged_text, (
        "the plaintext API key must never be written to the log stream"
    )
    assert "key-1" in logged_text, (
        "the fact that a key was created (its id) must still be recoverable "
        "from the log, even with the plaintext value redacted"
    )

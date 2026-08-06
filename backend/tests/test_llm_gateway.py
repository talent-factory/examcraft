# core/backend/tests/test_llm_gateway.py
import importlib
import services.llm_gateway as gw


def _reload(monkeypatch, url=None, key=None):
    if url is None:
        monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    else:
        monkeypatch.setenv("LLM_GATEWAY_URL", url)
    if key is None:
        monkeypatch.delenv("LLM_GATEWAY_API_KEY", raising=False)
    else:
        monkeypatch.setenv("LLM_GATEWAY_API_KEY", key)
    return importlib.reload(gw)


def test_disabled_by_default(monkeypatch):
    m = _reload(monkeypatch)
    assert m.gateway_enabled() is False


def test_enabled_when_url_set(monkeypatch):
    m = _reload(monkeypatch, url="http://tf-llm-gateway.internal:4000", key="sk-x")
    assert m.gateway_enabled() is True
    assert m.gateway_base_url() == "http://tf-llm-gateway.internal:4000/v1"
    assert m.gateway_api_key() == "sk-x"


def test_base_url_no_double_slash(monkeypatch):
    m = _reload(monkeypatch, url="http://gw:4000/", key="k")
    assert m.gateway_base_url() == "http://gw:4000/v1"


def test_permanent_status_classification(monkeypatch):
    m = _reload(monkeypatch, url="http://gw:4000", key="k")
    assert m.is_permanent_status(404) is True
    assert m.is_permanent_status(400) is True
    assert m.is_permanent_status(401) is True
    assert m.is_permanent_status(429) is False
    assert m.is_permanent_status(500) is False
    assert m.is_permanent_status(503) is False


def test_base_url_no_double_v1(monkeypatch):
    """LLM_GATEWAY_URL mit abschliessendem /v1 darf kein zweites /v1 erhalten."""
    m = _reload(monkeypatch, url="http://gw:4000/v1", key="k")
    assert m.gateway_base_url() == "http://gw:4000/v1"


def test_alias_constants(monkeypatch):
    m = _reload(monkeypatch, url="http://gw:4000", key="k")
    assert m.ALIAS_GENERATION == "examcraft/generation"
    assert m.ALIAS_GRADING == "examcraft/grading"
    assert m.ALIAS_EMBEDDING == "tf/embedding-small"
    assert m.ALIAS_CHAT == "examcraft/chat"
    assert m.ALIAS_WIZARD == "examcraft/wizard"


def test_gateway_timeout_default_and_override(monkeypatch):
    m = _reload(monkeypatch, url="http://gw:4000", key="k")
    monkeypatch.delenv("LLM_GATEWAY_TIMEOUT", raising=False)
    assert m.gateway_timeout() == 30.0
    monkeypatch.setenv("LLM_GATEWAY_TIMEOUT", "12.5")
    assert m.gateway_timeout() == 12.5


def test_gateway_generation_timeout_default_and_override(monkeypatch):
    """TF-593: dedizierter, grosszügigerer Timeout für die Fragengenerierung
    (lange Custom-Prompts brauchen regelmässig >30s), unabhängig vom
    generischen gateway_timeout()-Default für Grading/Embeddings/Chat/Wizard."""
    m = _reload(monkeypatch, url="http://gw:4000", key="k")
    monkeypatch.delenv("LLM_GATEWAY_GENERATION_TIMEOUT", raising=False)
    assert m.gateway_generation_timeout() == 120.0
    monkeypatch.setenv("LLM_GATEWAY_GENERATION_TIMEOUT", "90.0")
    assert m.gateway_generation_timeout() == 90.0


def test_make_pydantic_model_timeout_override(monkeypatch):
    """make_pydantic_model's `timeout` param must win over gateway_timeout(),
    so gateway_generator._build_agent can request the longer generation
    timeout without changing the shared 30s default for other call sites."""
    m = _reload(monkeypatch, url="http://gw:4000", key="sk-x")
    monkeypatch.setenv("LLM_GATEWAY_TIMEOUT", "30.0")

    default_model = m.make_pydantic_model(m.ALIAS_GENERATION)
    assert default_model.client.timeout == 30.0

    overridden_model = m.make_pydantic_model(m.ALIAS_GENERATION, timeout=120.0)
    assert overridden_model.client.timeout == 120.0


def test_make_client_fails_fast_without_key(monkeypatch):
    """Gateway-URL gesetzt, aber kein Virtual Key ⇒ RuntimeError statt leerem Bearer."""
    import pytest

    m = _reload(monkeypatch, url="http://gw:4000", key=None)
    with pytest.raises(RuntimeError, match="LLM_GATEWAY_API_KEY"):
        m.make_openai_client()
    with pytest.raises(RuntimeError, match="LLM_GATEWAY_API_KEY"):
        m.make_pydantic_model(m.ALIAS_GENERATION)


def test_make_openai_client_sets_timeout(monkeypatch):
    m = _reload(monkeypatch, url="http://gw:4000", key="sk-x")
    monkeypatch.setenv("LLM_GATEWAY_TIMEOUT", "17.0")
    client = m.make_openai_client()
    assert client.timeout == 17.0

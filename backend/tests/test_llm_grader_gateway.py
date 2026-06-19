# core/backend/tests/test_llm_grader_gateway.py
from services.grading.llm_grader import LlmGrader


class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _FakeChat:
    def __init__(self, store):
        self._store = store

    def create(self, **kwargs):
        self._store.update(kwargs)
        return _Resp(
            '{"points_awarded": 8, "confidence": 0.9, "rationale": "gut",'
            ' "matched_aspects": ["a"], "missing_aspects": []}'
        )


class _FakeOpenAI:
    def __init__(self, store):
        self.chat = type("C", (), {"completions": _FakeChat(store)})()


def test_gateway_grading_sends_cache_control(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # ensure no legacy demo-stub path
    captured: dict = {}

    import services.llm_gateway as gw

    # Fix 3: gateway_enabled vor Konstruktion patchen, damit self._gateway korrekt gesetzt wird.
    monkeypatch.setattr(gw, "gateway_enabled", lambda: True)
    monkeypatch.setattr(gw, "make_openai_client", lambda: _FakeOpenAI(captured))

    grader = LlmGrader(model="examcraft/grading")
    outcome = grader.grade(
        question_text="Was ist `x`?",
        correct_answer="x ist ...",
        given_answer="x ist ...",
        points_max=10,
    )

    assert outcome.points_awarded == 8
    assert captured["model"] == "examcraft/grading"
    # System block carries cache_control
    sys_part = captured["messages"][0]["content"][0]
    assert sys_part["cache_control"] == {"type": "ephemeral"}
    # First user (question) block carries cache_control, student block does not
    user_parts = captured["messages"][1]["content"]
    assert user_parts[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in user_parts[1]


def test_gateway_default_model_is_grading_alias(monkeypatch):
    """Fix 1: Kein model-Arg → Gateway-Default ist logischer Grading-Alias, nicht rohe Modell-ID."""
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    captured: dict = {}

    import services.llm_gateway as gw

    monkeypatch.setattr(gw, "gateway_enabled", lambda: True)
    monkeypatch.setattr(gw, "make_openai_client", lambda: _FakeOpenAI(captured))

    # Kein model= Argument — das ist der Produktiv-Default (Institution.llm_model_for_grading = NULL)
    grader = LlmGrader()
    outcome = grader.grade(
        question_text="Was ist `y`?",
        correct_answer="y ist ...",
        given_answer="y ist ...",
        points_max=5,
    )

    assert outcome.points_awarded == 5  # Fake gibt 8, wird auf points_max=5 geclampt
    assert captured["model"] == "examcraft/grading"
    # Timeout muss gesetzt sein (Fix 2)
    assert captured.get("timeout") is not None

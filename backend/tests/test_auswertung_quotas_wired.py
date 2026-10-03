"""TF-970: contract test — every ``assert_*`` tier gate in
``services/auswertung_quotas.py`` must be called from at least one real call
site.

This prevents the gap TF-970 closed: ``assert_review_bulk_allowed`` and
``assert_custom_grading_schemes_allowed`` were fully implemented, unit-tested
and listed in ``QUOTA_ERROR_CODES``, yet no endpoint called them — so the
paid features were open in every tier, and the whole suite stayed green.

The gates are discovered from the module's AST rather than listed here, so a
new ``assert_*`` added without a caller turns this test red on its own.

A call site is an ``ast.Call`` (a bare import or a mention in a comment or
docstring does not count) in the call-site layers of ``core/backend`` plus the
``premium/backend`` and ``enterprise/backend`` sibling tiers (skipped when
absent, e.g. in the core-only mirror). ``auswertung_quotas.py`` itself is
excluded, as are ``tests`` directories: a test that calls a gate directly is
exactly what kept the dead gates looking alive.

Pure filesystem + AST — no DB required.
"""

import ast
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND.parents[1]
_QUOTAS_MODULE = _BACKEND / "services" / "auswertung_quotas.py"
_SCAN_DIRS = ("api", "services", "tasks", "middleware")
_SIBLING_TIERS = ("premium/backend", "enterprise/backend")


def _gate_names() -> set[str]:
    tree = ast.parse(_QUOTAS_MODULE.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("assert_")
    }


def _scan_roots() -> list[Path]:
    roots = [_BACKEND / d for d in _SCAN_DIRS]
    for tier in _SIBLING_TIERS:
        tier_root = _REPO_ROOT / tier
        if tier_root.is_dir():
            roots.extend(tier_root / d for d in _SCAN_DIRS)
    return [r for r in roots if r.is_dir()]


def _scanned_files() -> list[Path]:
    files = []
    for root in _scan_roots():
        for path in root.rglob("*.py"):
            if "tests" in path.parts or path.resolve() == _QUOTAS_MODULE:
                continue
            files.append(path)
    return files


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def test_scan_sees_the_known_call_sites() -> None:
    """Sanity check of the scan roots and the AST walk: an empty or wrong
    root would report every gate as uncalled — or, with a broken walk, every
    gate as called — without saying why."""
    files = _scanned_files()
    assert _BACKEND / "api" / "submissions.py" in files
    assert "assert_driver_allowed" in _called_names(_BACKEND / "api" / "submissions.py")
    assert not any("tests" in f.parts for f in files)


def test_gate_discovery_finds_the_known_gates() -> None:
    """Guards the discovery itself: if the module were renamed or the gates
    moved into a class, ``_gate_names()`` would return nothing and the
    wiring test below would pass vacuously."""
    assert {
        "assert_driver_allowed",
        "assert_class_history_allowed",
        "assert_review_bulk_allowed",
        "assert_custom_grading_schemes_allowed",
    } <= _gate_names()


def test_every_quota_gate_has_a_call_site() -> None:
    called: set[str] = set()
    for path in _scanned_files():
        called |= _called_names(path)

    uncalled = sorted(_gate_names() - called)
    assert not uncalled, (
        f"Tier gate(s) without a caller: {uncalled}. A gate nobody calls "
        "leaves the paid feature open in every tier (TF-970). Call it at the "
        "start of the endpoint that performs the gated action."
    )

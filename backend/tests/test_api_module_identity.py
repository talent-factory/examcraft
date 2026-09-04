"""Guard: every api/ router module exists exactly once (TF-660).

``main.py``'s lifespan loads the core API modules from their file paths. As
long as it does that under the module's canonical dotted name (``api.exams``),
the module object serving requests is the same one a test reaches via
``patch("api.exams....")`` and the same one a sibling module gets from
``from api.exams import ...``.

Loading under a synthetic name instead (the old ``core_api_exams``) produces a
second, independent module object. That has cost real money twice:

* ``from api.question_review import ...`` in exams.py failed to resolve in the
  prod image and crash-looped the backend after v1.8.0 (TF-417, and TF-320
  before it).
* Five ``test_rag_api.py`` tests patched a module the live route did not use,
  passed alone, failed in the full suite, and were silenced with
  a CI-only skip marker — leaving the generate-exam path untested in CI for
  months (TF-660).

Neither failure is visible in a normal test run, which is why this file
asserts the structural property directly.
"""

import sys

from fastapi.testclient import TestClient

from main import app


def _startup():
    """Trigger the lifespan so the routers are actually registered."""
    with TestClient(app):
        pass


def test_no_synthetic_core_api_modules_after_startup():
    """main.py must not register api/ modules under ``core_api_*`` names."""
    _startup()

    synthetic = sorted(n for n in sys.modules if n.startswith("core_api_"))
    assert not synthetic, (
        "api/ modules loaded under synthetic names — a second module object "
        f"that patches and absolute imports cannot reach: {synthetic}"
    )


def test_routes_are_served_by_the_canonically_imported_modules():
    """Each route's endpoint must live in the module ``sys.modules`` holds.

    This is the property the ``patch("api.<module>....")`` idiom depends on.
    """
    _startup()

    mismatches = []
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None:
            continue
        module_name = getattr(endpoint, "__module__", "")
        if not module_name.startswith("api."):
            continue

        registered = sys.modules.get(module_name)
        if registered is None:
            mismatches.append(f"{route.path}: {module_name} not in sys.modules")
        elif endpoint.__globals__ is not registered.__dict__:
            mismatches.append(
                f"{route.path}: {module_name} in sys.modules is a different "
                "object than the one serving this route"
            )

    assert not mismatches, mismatches


def test_repeated_startup_reuses_the_same_module_objects():
    """A second lifespan entry must not re-execute the api/ modules.

    The test suite enters the lifespan many times (every
    ``with TestClient(app):``). Re-executing a module each time would hand
    every subsequent entry a fresh set of module-level globals — new logger
    objects, new singletons, new rate limiters — and reopen exactly the gap
    this file guards against.
    """
    _startup()
    first = {
        name: module for name, module in sys.modules.items() if name.startswith("api.")
    }
    assert first, "no api.* modules registered after startup"

    _startup()

    replaced = [
        name for name, module in first.items() if sys.modules[name] is not module
    ]
    assert not replaced, f"api/ modules re-executed on second startup: {replaced}"

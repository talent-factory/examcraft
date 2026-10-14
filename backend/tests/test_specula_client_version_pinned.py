"""specula-client is pinned in exactly one place (TF-1061).

CI installed v0.1.0 while both Dockerfiles (production included) installed
v0.1.4, so the tests ran against a different library than the one deployed.
Every install site now reads ``core/backend/specula-client.version``; this
guard fails on any hard-coded git ref that deviates from it.
"""

import pathlib
import re
import subprocess

import pytest

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent.parent
VERSION_FILE = BACKEND_ROOT / "specula-client.version"
VERSION_FILE_NAME = VERSION_FILE.name

# Git ref after the repo URL, up to the closing quote or whitespace.
GIT_REF_PATTERN = re.compile(r"specula-client-python\.git@([^\"'\s]+)")
# Install sites read the file into this shell variable.
VERSION_VARIABLE_REFS = {"${SPECULA_CLIENT_VERSION}", "$SPECULA_CLIENT_VERSION"}

# Each of them must actually install from the pinned version -- also the
# sanity check that the scan below saw the repo and not an empty directory.
INSTALL_SITES = {
    ".github/workflows/ci.yml",
    "core/backend/Dockerfile",
    "core/backend/Dockerfile.fly",
    "justfile",
}

# Only the private repo has the install sites; the core/ mirror and the api
# container (only core/backend under /app) do not.
needs_private_repo = pytest.mark.skipif(
    not (REPO_ROOT / ".github/workflows/ci.yml").is_file(),
    reason="TF-1061: core/-Mirror bzw. Container ohne Repo-Root",
)


def _pinned_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def _repo_files() -> list[str]:
    """Tracked plus untracked, not-ignored files (a new file counts too)."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return [name for name in out.decode().split("\0") if name]


def test_version_file_holds_a_release_tag():
    assert re.fullmatch(r"v\d+\.\d+\.\d+", _pinned_version()), (
        f"{VERSION_FILE_NAME} muss genau ein Tag wie v0.1.4 enthalten"
    )


@needs_private_repo
def test_no_install_site_deviates_from_pinned_version():
    pinned = _pinned_version()
    refs: dict[str, list[str]] = {}
    for name in _repo_files():
        path = REPO_ROOT / name
        if not path.is_file():  # deleted but still in the index
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found = GIT_REF_PATTERN.findall(text)
        if found:
            refs[name] = found

    missing = INSTALL_SITES - refs.keys()
    assert not missing, f"Keine specula-client-Installation gefunden in: {missing}"

    deviating = {
        name: ref
        for name, found in refs.items()
        for ref in found
        if ref != pinned and ref not in VERSION_VARIABLE_REFS
    }
    assert not deviating, (
        f"specula-client weicht von {VERSION_FILE_NAME} ({pinned}) ab: {deviating}"
    )

    unread = {
        name
        for name, found in refs.items()
        if set(found) & VERSION_VARIABLE_REFS
        and VERSION_FILE_NAME not in (REPO_ROOT / name).read_text(encoding="utf-8")
    }
    assert not unread, (
        f"$SPECULA_CLIENT_VERSION ohne Bezug auf {VERSION_FILE_NAME}: {unread}"
    )

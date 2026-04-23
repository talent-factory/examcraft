"""Convert internal docs file paths to public docs.examcraft.ch URLs."""

import os

DOCS_SITE_PATH = os.environ.get("DOCS_SITE_PATH", "core/docs-site/docs")
DOCS_BASE_URL = os.environ.get("DOCS_BASE_URL", "https://docs.examcraft.ch")


def convert_docs_path_to_url(
    filepath: str,
    base_url: str = "",
    docs_site_path: str = "",
) -> str:
    """Convert a docs source file path to a public URL.

    Rules:
    1. Strip docs_site_path prefix
    2. Remove .md extension
    3. .en. files get /en/ prefix (MkDocs i18n convention)
    4. index files: use directory path only
    5. Append trailing slash
    """
    base = base_url or DOCS_BASE_URL
    prefix = docs_site_path or DOCS_SITE_PATH

    # Strip prefix if present
    if filepath.startswith(prefix):
        path = filepath[len(prefix) :]
        path = path.lstrip("/")
    else:
        path = filepath

    # Detect English variant
    is_english = ".en.md" in path

    # Remove extension
    path = path.replace(".en.md", "").replace(".md", "")

    # Handle index files — drop the filename, keep directory
    if path.endswith("/index") or path == "index":
        path = path.rsplit("index", 1)[0]
    else:
        path = path + "/"

    # Add /en/ prefix for English files
    if is_english:
        path = "en/" + path

    # Ensure no double slashes
    url = f"{base.rstrip('/')}/{path}"
    return url

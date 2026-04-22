"""Generate per-language sitemap.xml files to silence SEO-tool probes.

The mkdocs-static-i18n plugin emits a single root `sitemap.xml` that lists
every URL across all built languages. SEO crawlers and browser extensions
(Ahrefs, Lighthouse, etc.) commonly probe `/{lang}/sitemap.xml` per hreflang
language, producing 404 warnings in `mkdocs serve` output.

This post-build hook filters the root sitemap per language and writes a
dedicated `site/{lang}/sitemap.xml` plus a matching `.xml.gz`.
"""

from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

LANGUAGES: tuple[str, ...] = ("en", "fr", "it")
SITEMAP_NS: str = "http://www.sitemaps.org/schemas/sitemap/0.9"


def on_post_build(config, **kwargs) -> None:
    site_dir = Path(config["site_dir"])
    root_sitemap = site_dir / "sitemap.xml"
    if not root_sitemap.exists():
        return

    ET.register_namespace("", SITEMAP_NS)
    tree = ET.parse(root_sitemap)
    urls = tree.getroot().findall(f"{{{SITEMAP_NS}}}url")

    for lang in LANGUAGES:
        lang_dir = site_dir / lang
        if not lang_dir.is_dir():
            continue
        _write_lang_sitemap(lang_dir, urls, lang)


def _write_lang_sitemap(lang_dir: Path, urls: list[ET.Element], lang: str) -> None:
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    prefix = f"/{lang}/"

    for url in urls:
        loc = url.find(f"{{{SITEMAP_NS}}}loc")
        if loc is not None and loc.text and prefix in loc.text:
            urlset.append(url)

    xml_bytes = ET.tostring(urlset, encoding="utf-8", xml_declaration=True)
    (lang_dir / "sitemap.xml").write_bytes(xml_bytes)
    (lang_dir / "sitemap.xml.gz").write_bytes(gzip.compress(xml_bytes))

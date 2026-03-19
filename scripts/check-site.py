#!/usr/bin/env python3
"""Minimal project quality checks used locally and in CI."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "index": ROOT / "index.html",
    "404": ROOT / "404.html",
    "layout": ROOT / "_layouts" / "default.html",
    "config": ROOT / "_config.yml",
    "site_js": ROOT / "assets" / "js" / "site.js",
    "site_css": ROOT / "assets" / "css" / "input.css",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    index = FILES["index"].read_text(encoding="utf-8")
    not_found = FILES["404"].read_text(encoding="utf-8")
    layout = FILES["layout"].read_text(encoding="utf-8")
    config = FILES["config"].read_text(encoding="utf-8")

    require("{% include home-hero.html %}" in index, "index.html should be composed from includes", errors)
    require("layout: default" in index, "index.html should use the default layout", errors)
    require("{% seo" in layout, "default layout should render SEO metadata", errors)
    require("href=\"/\"" not in index + not_found, "hardcoded root links should use relative_url", errors)
    require("<script>" not in index + not_found, "inline script blocks should not remain in page templates", errors)
    require("onclick=" not in index + not_found, "inline event handlers should not remain in page templates", errors)
    require("assets/js/site.js" in layout, "default layout should load the shared site.js bundle", errors)
    require("jekyll-seo-tag" in config, "_config.yml must keep jekyll-seo-tag enabled", errors)
    require("jekyll-sitemap" in config, "_config.yml must keep jekyll-sitemap enabled", errors)
    require(re.search(r"app-card|app-repo-link|skip-link", FILES["site_css"].read_text(encoding="utf-8")) is not None,
            "CSS should include accessibility/mobile support classes", errors)
    require("setupCopyButton" in FILES["site_js"].read_text(encoding="utf-8"),
            "site.js should contain shared interaction handlers", errors)

    if errors:
        print("Quality checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

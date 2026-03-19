#!/usr/bin/env python3
"""
Fetch addon metadata from hassos-apps/repository and regenerate _data/apps.yml.

Usage:
    python scripts/sync-apps.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - fallback only used when PyYAML is absent
    yaml = None


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "hassos-apps/repository"
BRANCH = "main"
BASE_RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
BASE_API = f"https://api.github.com/repos/{REPO}/contents"
JSDELIVR_BASE = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}"
EXCLUDE_DIRS = {"example", ".github"}
ICON_MAP = {
    "shelly-manager": "📡",
    "homebox": "📦",
}
DEFAULT_ICON = "📦"
STATUS_MAP: dict[str, str] = {}
TIMEOUT_SECONDS = 15
MAX_RETRIES = 3


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "hassos-apps-website-sync",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def request(url: str, *, method: str = "GET", parse_json: bool = True) -> object:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, method=method, headers=_headers())
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
                if parse_json:
                    return json.loads(body)
                return body.decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == MAX_RETRIES:
                raise
            last_error = exc
        except urllib.error.URLError as exc:
            last_error = exc
        except TimeoutError as exc:
            last_error = exc
        time.sleep(attempt)

    raise RuntimeError(f"Request failed for {url}: {last_error}")


def head_exists(url: str) -> bool:
    try:
        request(url, method="HEAD", parse_json=False)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise
    except Exception:
        return False


def parse_yaml(text: str) -> dict:
    if yaml is not None:
        parsed = yaml.safe_load(text)
        if not isinstance(parsed, dict):
            raise ValueError("config.yaml did not contain a mapping")
        return parsed
    return parse_simple_yaml(text)


def parse_simple_yaml(text: str) -> dict:
    result: dict[str, object] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ": " in line or line.rstrip().endswith(":"):
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest and not rest.startswith("#"):
                if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
                    rest = rest[1:-1]
                result[key] = rest
            else:
                items: list[str] = []
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("- "):
                        items.append(next_line[2:].strip())
                        i += 1
                    elif not next_line or next_line.startswith("#"):
                        i += 1
                    else:
                        break
                result[key] = items if items else None
                continue
        i += 1
    return result


def get_addon_slugs() -> list[str]:
    contents = request(f"{BASE_API}?ref={BRANCH}")
    assert isinstance(contents, list)
    slugs = []
    for item in contents:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if item.get("type") != "dir" or not isinstance(name, str):
            continue
        if name.startswith(".") or name in EXCLUDE_DIRS:
            continue
        slugs.append(name)
    return sorted(slugs)


def fetch_config(slug: str) -> dict | None:
    try:
        text = request(f"{BASE_RAW}/{slug}/config.yaml", parse_json=False)
        assert isinstance(text, str)
        return parse_yaml(text)
    except Exception as exc:
        print(f"Warning: could not fetch config for '{slug}': {exc}", file=sys.stderr)
        return None


def icon_cdn_url(slug: str) -> str | None:
    candidate = f"{JSDELIVR_BASE}/{slug}/icon.png"
    return candidate if head_exists(candidate) else None


def validate_record(record: dict) -> None:
    required_fields = ("slug", "name", "description", "version", "url", "repo_url", "status", "arch", "icon")
    missing = [field for field in required_fields if not record.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if not isinstance(record["arch"], list):
        raise ValueError("'arch' must be a list")


def build_app_record(slug: str, config: dict) -> dict:
    arch = config.get("arch") or ["amd64", "aarch64"]
    if isinstance(arch, str):
        arch = [arch]

    repo_slug = str(config.get("slug") or slug)
    record = {
        "slug": repo_slug,
        "name": str(config.get("name") or slug.replace("-", " ").title()),
        "description": str(config.get("description") or ""),
        "version": str(config.get("version") or "0.0.0"),
        "url": str(config.get("url") or f"https://github.com/hassos-apps/app-{slug}"),
        "repo_url": f"https://github.com/{REPO}/tree/{BRANCH}/{slug}",
        "status": STATUS_MAP.get(slug, "stable"),
        "arch": [str(item) for item in arch],
        "icon": ICON_MAP.get(slug, DEFAULT_ICON),
    }

    icon_url = icon_cdn_url(slug)
    if icon_url:
        record["icon_url"] = icon_url

    validate_record(record)
    return record


def yaml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return "\n" + "\n".join(f"    - {yaml_value(item)}" for item in value)
    text = str(value)
    if any(char in text for char in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", ">", "!", "'", '"', "@", "`", "\n")):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def dict_to_yaml(data: dict, indent: int = 0) -> str:
    lines: list[str] = []
    pad = "  " * indent
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{pad}{key}: []")
            else:
                lines.append(f"{pad}{key}:")
                for item in value:
                    lines.append(f"{pad}  - {yaml_value(item)}")
        else:
            lines.append(f"{pad}{key}: {yaml_value(value)}")
    return "\n".join(lines)


def write_data_file(apps: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Auto-generated by scripts/sync-apps.py - do not edit manually.",
        f"# Source: https://github.com/{REPO}",
        "# To refresh locally: python scripts/sync-apps.py",
        "# Or trigger the 'Sync Apps from Repository' GitHub Actions workflow.",
        "",
    ]

    for app in apps:
        app_yaml_lines = dict_to_yaml(app, indent=1).splitlines()
        lines.append("- " + app_yaml_lines[0].lstrip())
        lines.extend(app_yaml_lines[1:])
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print(f"Fetching addon list from github.com/{REPO} ...")
    slugs = get_addon_slugs()
    print(f"Found {len(slugs)} addon directories: {', '.join(slugs)}")

    apps: list[dict] = []
    for slug in slugs:
        config = fetch_config(slug)
        if config is None:
            continue
        try:
            app = build_app_record(slug, config)
        except Exception as exc:
            print(f"Warning: skipping '{slug}' due to invalid metadata: {exc}", file=sys.stderr)
            continue
        apps.append(app)
        print(f"  - {app['name']} ({app['version']})")

    output_path = Path(__file__).resolve().parent.parent / "_data" / "apps.yml"
    write_data_file(apps, output_path)
    print(f"Wrote {len(apps)} app(s) to {output_path.relative_to(output_path.parent.parent)}")


if __name__ == "__main__":
    main()

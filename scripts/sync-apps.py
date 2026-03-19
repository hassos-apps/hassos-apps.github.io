#!/usr/bin/env python3
"""
sync-apps.py
Fetches config.yaml from each addon in hassos-apps/repository and
regenerates _data/apps.yml for the Jekyll site.

Usage (local):
    python3 scripts/sync-apps.py

Usage (CI — token is set automatically via GITHUB_TOKEN):
    python3 scripts/sync-apps.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
REPO          = "hassos-apps/repository"
BRANCH        = "main"
BASE_RAW      = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
BASE_API      = f"https://api.github.com/repos/{REPO}/contents"
JSDELIVR_BASE = f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}"

# Dirs to skip (not real addons)
EXCLUDE_DIRS  = {"example", ".github"}

# Emoji icons per slug (fallback when icon.png is missing)
ICON_MAP = {
    "shelly-manager": "📡",
    "homebox":        "📦",
    "example":        "🧩",
}
DEFAULT_ICON = "📦"

# Status per slug — override here if you want to mark something beta/deprecated
STATUS_MAP: dict[str, str] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _headers() -> dict:
    h: dict = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"token {GITHUB_TOKEN}"
    return h


def github_get(url: str) -> dict | list:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def raw_get(url: str) -> str:
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def head_exists(url: str) -> bool:
    """Return True if the URL responds with 2xx."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers=_headers())
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


# ── YAML serializer (no external dependencies) ─────────────────────────────────

def _yaml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        if not v:
            return "[]"
        items = "\n".join(f"    - {_yaml_value(i)}" for i in v)
        return f"\n{items}"
    # string
    s = str(v)
    if any(c in s for c in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", ">", "!", "'", '"', "@", "`", "\n")):
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def dict_to_yaml(d: dict, indent: int = 0) -> str:
    lines = []
    pad = "  " * indent
    for k, v in d.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            lines.append(f"{pad}{k}:")
            for item in v:
                lines.append(f"{pad}  -")
                for ik, iv in item.items():
                    lines.append(f"{pad}    {ik}: {_yaml_value(iv)}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{pad}{k}: []")
            else:
                lines.append(f"{pad}{k}:")
                for item in v:
                    lines.append(f"{pad}  - {_yaml_value(item)}")
        else:
            lines.append(f"{pad}{k}: {_yaml_value(v)}")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def get_addon_slugs() -> list[str]:
    """Return sorted list of addon directory names from the repo root."""
    contents = github_get(f"{BASE_API}?ref={BRANCH}")
    return sorted(
        item["name"]
        for item in contents
        if item["type"] == "dir"
        and not item["name"].startswith(".")
        and item["name"] not in EXCLUDE_DIRS
    )


def parse_simple_yaml(text: str) -> dict:
    """
    Minimal YAML parser — handles the flat key: value and key:\n  - item lists
    that appear in HA addon config.yaml files. Does NOT handle nested dicts.
    """
    result: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # skip comments and blanks
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ": " in line or line.rstrip().endswith(":"):
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest and not rest.startswith("#"):
                # inline value — strip surrounding quotes
                if (rest.startswith('"') and rest.endswith('"')) or \
                   (rest.startswith("'") and rest.endswith("'")):
                    rest = rest[1:-1]
                result[key] = rest
            else:
                # might be a list following
                items = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    next_stripped = next_line.strip()
                    if next_stripped.startswith("- "):
                        items.append(next_stripped[2:].strip())
                        i += 1
                    elif not next_stripped or next_stripped.startswith("#"):
                        i += 1
                    else:
                        break
                result[key] = items if items else None
                continue
        i += 1
    return result


def fetch_config(slug: str) -> dict | None:
    url = f"{BASE_RAW}/{slug}/config.yaml"
    try:
        text = raw_get(url)
        return parse_simple_yaml(text)
    except Exception as exc:
        print(f"  ⚠  Could not fetch config for '{slug}': {exc}", file=sys.stderr)
        return None


def icon_cdn_url(slug: str) -> str | None:
    url = f"{JSDELIVR_BASE}/{slug}/icon.png"
    if head_exists(url):
        return url
    return None


def build_app_record(slug: str, config: dict) -> dict:
    version = str(config.get("version", "0.0.0"))
    arch = config.get("arch") or ["amd64", "aarch64"]
    if isinstance(arch, str):
        arch = [arch]

    record: dict = {
        "slug":        config.get("slug", slug),
        "name":        config.get("name", slug.replace("-", " ").title()),
        "description": config.get("description", ""),
        "version":     version,
        "url":         config.get("url", f"https://github.com/hassos-apps/app-{slug}"),
        "repo_url":    f"https://github.com/{REPO}/tree/{BRANCH}/{slug}",
        "status":      STATUS_MAP.get(slug, "stable"),
        "arch":        arch,
        "icon":        ICON_MAP.get(slug, DEFAULT_ICON),
    }

    icon_url = icon_cdn_url(slug)
    if icon_url:
        record["icon_url"] = icon_url

    return record


def write_data_file(apps: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Auto-generated by scripts/sync-apps.py — do not edit manually.",
        f"# Source: https://github.com/{REPO}",
        "# To refresh locally:  python3 scripts/sync-apps.py",
        "# Or trigger the 'Sync Apps from Repository' GitHub Actions workflow.",
        "",
    ]
    for app in apps:
        # Serialize with indent=1 so each key gets "  key: value",
        # then replace the leading spaces on the first line with "- "
        # to produce a valid YAML list entry.
        app_yaml_lines = dict_to_yaml(app, indent=1).splitlines()
        first = "- " + app_yaml_lines[0].lstrip()
        rest = app_yaml_lines[1:]
        lines.append(first)
        lines.extend(rest)
        lines.append("")  # blank line between entries

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print(f"🔍  Fetching addon list from github.com/{REPO} …")
    slugs = get_addon_slugs()
    print(f"    Found: {slugs}")

    apps: list[dict] = []
    for slug in slugs:
        print(f"  → {slug}")
        config = fetch_config(slug)
        if config is None:
            continue
        app = build_app_record(slug, config)
        apps.append(app)
        print(f"     name={app['name']}  version={app['version']}  icon_url={'yes' if app.get('icon_url') else 'no'}")

    output_path = Path(__file__).parent.parent / "_data" / "apps.yml"
    write_data_file(apps, output_path)
    print(f"\n✅  Written {len(apps)} app(s) to {output_path.relative_to(Path(__file__).parent.parent)}")


if __name__ == "__main__":
    main()

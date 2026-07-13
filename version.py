"""Application version helpers."""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "VERSION")

# GitHub repo used for update checks.
GITHUB_OWNER = "kazuu234"
GITHUB_REPO = "auto-telop"


def get_version():
    """Return the current app version string (e.g. '1.0.0')."""
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def _parse(v):
    """Parse 'v1.2.3' → (1, 2, 3). Non-numeric parts become 0."""
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(latest, current):
    """Return True if `latest` is a newer version than `current`."""
    return _parse(latest) > _parse(current)

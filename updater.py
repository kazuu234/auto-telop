"""Check for and download app updates from GitHub Releases."""

import json
import os
import sys
import urllib.request

from version import GITHUB_OWNER, GITHUB_REPO, get_version, is_newer

LATEST_RELEASE_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)


def _platform_key():
    """Rough platform key used to pick the right release asset."""
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "win"
    return "other"


def _pick_asset(assets):
    """Choose the most appropriate release asset for this platform.

    Falls back to the first asset (or None) if nothing matches.
    """
    plat = _platform_key()
    mac_ext = (".dmg", ".app.zip", ".pkg")
    win_ext = (".exe", ".msi")

    def score(name):
        n = name.lower()
        if plat == "mac":
            if n.endswith(mac_ext) or "mac" in n or "darwin" in n:
                return 2
        if plat == "win":
            if n.endswith(win_ext) or "win" in n:
                return 2
        if n.endswith(".zip"):
            return 1
        return 0

    if not assets:
        return None
    best = max(assets, key=lambda a: score(a.get("name", "")))
    return best


def check_update(timeout=10):
    """Query GitHub for the latest release and compare with current version.

    Returns a dict:
        {current, latest, has_update, notes, download_url, asset_name}
    On network/API failure, has_update is False and `error` is set.
    """
    current = get_version()
    result = {
        "current": current,
        "latest": None,
        "has_update": False,
        "notes": "",
        "download_url": None,
        "asset_name": None,
    }
    try:
        req = urllib.request.Request(
            LATEST_RELEASE_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "auto-telop"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - surface any failure to the UI
        result["error"] = str(e)
        return result

    latest = (data.get("tag_name") or "").strip()
    result["latest"] = latest
    result["notes"] = data.get("body") or ""
    result["has_update"] = bool(latest) and is_newer(latest, current)

    asset = _pick_asset(data.get("assets") or [])
    if asset:
        result["download_url"] = asset.get("browser_download_url")
        result["asset_name"] = asset.get("name")
    else:
        # No binary asset attached: fall back to the source zip.
        result["download_url"] = data.get("zipball_url")
        result["asset_name"] = f"{GITHUB_REPO}-{latest}.zip" if latest else None

    return result


def download_update(url, asset_name, dest_dir=None, progress_cb=None):
    """Download the update asset to dest_dir (default ~/Downloads).

    Returns the downloaded file path. Raises on failure.
    """
    if not url:
        raise ValueError("No download URL available")
    if dest_dir is None:
        dest_dir = os.path.expanduser("~/Downloads")
    os.makedirs(dest_dir, exist_ok=True)
    name = asset_name or os.path.basename(url) or "auto-telop-update"
    dest_path = os.path.join(dest_dir, name)

    req = urllib.request.Request(url, headers={"User-Agent": "auto-telop"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded, total)
    return dest_path


if __name__ == "__main__":
    info = check_update()
    print(json.dumps(info, ensure_ascii=False, indent=2))

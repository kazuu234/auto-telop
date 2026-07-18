"""Ensure ffmpeg/ffprobe are findable when launched as a GUI app.

- **macOS**: apps launched from Finder (or a .app bundle) do NOT inherit the
  login shell's PATH, so Homebrew locations like /opt/homebrew/bin are
  missing and subprocess calls to `ffmpeg`/`ffprobe` fail with "No such file
  or directory".
- **Windows**: double-clicking AutoTelop.exe similarly starts the process
  with whatever PATH Explorer had, which often does not include ffmpeg even
  when it was installed via winget/choco/scoop (those add PATH entries that
  only apply to newly-opened shells, not already-running ones like Explorer).

Whisper also shells out to `ffmpeg` internally, so this must run before any
transcription. Import this module early (app.py does) to patch os.environ.
"""

import ntpath
import os
import shutil
import sys

# macOS: common locations where Homebrew / MacPorts / system tools live.
_MAC_CANDIDATE_DIRS = [
    "/opt/homebrew/bin",   # Apple Silicon Homebrew
    "/usr/local/bin",      # Intel Homebrew
    "/opt/local/bin",      # MacPorts
    "/usr/bin",
    "/bin",
]


def _win_candidate_dirs():
    """Likely ffmpeg install locations on Windows.

    Built with expandvars / os.environ so they resolve correctly on a real
    Windows box. Uses ntpath.expandvars (Windows %VAR% syntax) explicitly
    rather than os.path.expandvars, since the latter is posixpath on Linux
    and would silently leave %VAR% unexpanded there — ntpath.expandvars
    still reads from os.environ, so this stays testable headlessly too.
    """
    dirs = []
    # Bundled ffmpeg next to the frozen exe (optional distribution option).
    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(os.path.dirname(sys.executable), "ffmpeg"))
    dirs.append(ntpath.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"))
    dirs.append(r"C:\ProgramData\chocolatey\bin")
    dirs.append(ntpath.expandvars(r"%USERPROFILE%\scoop\shims"))
    dirs.append(r"C:\ffmpeg\bin")
    return dirs


def _candidate_dirs(platform=None):
    """Return the candidate binary dirs to check for the given platform.

    platform defaults to sys.platform. Split out from
    ensure_media_tools_on_path() so it can be exercised headlessly in tests
    without needing to actually run on macOS/Windows.
    """
    if platform is None:
        platform = sys.platform
    if platform == "darwin":
        return _MAC_CANDIDATE_DIRS
    if platform.startswith("win"):
        return _win_candidate_dirs()
    # linux / other: PATH usually suffices already; nothing to add.
    return []


def ensure_media_tools_on_path():
    """Prepend known binary dirs to PATH so ffmpeg/ffprobe resolve.

    Idempotent. Returns True if ffmpeg is resolvable afterwards.
    """
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    changed = False
    for d in _candidate_dirs():
        if os.path.isdir(d) and d not in parts:
            parts.insert(0, d)
            changed = True
    if changed:
        os.environ["PATH"] = os.pathsep.join(parts)
    # On Windows shutil.which() resolves ffmpeg.exe (PATHEXT) automatically.
    return shutil.which("ffmpeg") is not None


# Patch on import so anything imported afterwards (whisper, ffprobe calls)
# sees the corrected PATH.
ensure_media_tools_on_path()

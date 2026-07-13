"""Ensure ffmpeg/ffprobe are findable when launched from Finder.

GUI apps launched from Finder (or a .app bundle) do NOT inherit the login
shell's PATH, so Homebrew locations like /opt/homebrew/bin are missing and
subprocess calls to `ffmpeg`/`ffprobe` fail with "No such file or directory".
Whisper also shells out to `ffmpeg` internally, so this must run before any
transcription. Import this module early (app.py does) to patch os.environ.
"""

import os
import shutil

# Common locations where Homebrew / MacPorts / system tools live.
_CANDIDATE_DIRS = [
    "/opt/homebrew/bin",   # Apple Silicon Homebrew
    "/usr/local/bin",      # Intel Homebrew
    "/opt/local/bin",      # MacPorts
    "/usr/bin",
    "/bin",
]


def ensure_media_tools_on_path():
    """Prepend known binary dirs to PATH so ffmpeg/ffprobe resolve.

    Idempotent. Returns True if ffmpeg is resolvable afterwards.
    """
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    changed = False
    for d in _CANDIDATE_DIRS:
        if os.path.isdir(d) and d not in parts:
            parts.insert(0, d)
            changed = True
    if changed:
        os.environ["PATH"] = os.pathsep.join(parts)
    return shutil.which("ffmpeg") is not None


# Patch on import so anything imported afterwards (whisper, ffprobe calls)
# sees the corrected PATH.
ensure_media_tools_on_path()

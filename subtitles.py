"""Generate SRT / WebVTT subtitle files from segments.

Both formats carry only text + timing (no font/outline styling) — the look
is applied on the editor side (Premiere caption settings, Filmora, etc.).
WebVTT can additionally carry a rough vertical position derived from the
telop style; some players/NLEs honour it, others ignore it.

Note: for FCP-level embedded styling, use fcpxml.py instead. SRT/VTT are for
Premiere / Filmora and other editors that import caption files.
"""


def _fmt_timestamp(seconds, sep):
    """Format seconds as HH:MM:SS<sep>mmm (sep is ',' for SRT, '.' for VTT)."""
    if seconds is None or seconds < 0:
        seconds = 0
    total_ms = int(round(seconds * 1000))
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def _cue_times(seg, sep):
    start = seg.get("start", 0) or 0
    end = seg.get("end", 0) or 0
    # 終了は開始以上を保証（0長・逆転を防ぐ）
    if end < start:
        end = start
    return _fmt_timestamp(start, sep), _fmt_timestamp(end, sep)


def generate_srt(segments, output_path):
    """Write segments as a SubRip (.srt) file. Returns output_path."""
    blocks = []
    for i, seg in enumerate(segments, 1):
        start, end = _cue_times(seg, ",")
        text = (seg.get("text") or "").strip()
        blocks.append(f"{i}\n{start} --> {end}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))
    return output_path


def _vtt_escape(text):
    """Escape characters that are special in a WebVTT cue payload."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _vtt_cue_settings(style):
    """Derive best-effort WebVTT cue settings from the telop style.

    Maps the FCP-style vertical position (position_y: 0=center, negative=down)
    to a WebVTT `line` percentage (0%=top, 100%=bottom). Calibrated against
    fcpxml position semantics (y=-45 ≒ 画面下から約10% ≒ line 90%).
    """
    if not style:
        return ""
    pos_y = style.get("position_y", -40)
    # center(0) -> 50% from top; -45 -> ~90% from top.
    line_pct = round(50 - pos_y * (40 / 45))
    line_pct = max(0, min(100, line_pct))
    return f" line:{line_pct}% align:center"


def generate_vtt(segments, output_path, style=None):
    """Write segments as a WebVTT (.vtt) file. Returns output_path.

    style: optional telop style dict; used to add a rough vertical position.
    """
    settings = _vtt_cue_settings(style)
    parts = ["WEBVTT\n"]
    for seg in segments:
        start, end = _cue_times(seg, ".")
        text = _vtt_escape((seg.get("text") or "").strip())
        parts.append(f"{start} --> {end}{settings}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return output_path

"""Generate SRT / WebVTT subtitle files from segments.

Both formats carry only text + timing (no font/outline styling) — the look
is applied on the editor side (Premiere caption settings, Filmora, etc.).
WebVTT can additionally carry a rough vertical position derived from the
telop style; some players/NLEs honour it, others ignore it.

Note: for FCP-level embedded styling, use fcpxml.py instead. SRT/VTT are for
Premiere / Filmora and other editors that import caption files.
"""


MIN_CUE_DURATION = 0.1  # NLEはゼロ長キューを黙って破棄するため最低表示時間を保証
# (FCPXML側の max(dur, 1/fps) に相当。Whisperのword_timestampsは最終単語で
# start==endを出すことがある)


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
    # 最低表示時間を保証（ゼロ長・極短キューをNLEが黙って破棄するのを防ぐ）
    end = max(end, start + MIN_CUE_DURATION)
    return _fmt_timestamp(start, sep), _fmt_timestamp(end, sep)


def generate_srt(segments, output_path):
    """Write segments as a SubRip (.srt) file. Returns output_path."""
    blocks = []
    i = 0
    for seg in segments:
        text = (seg.get("text") or "").strip()
        # 空行＝そのテロップを出さない（エディタで行を消した意図に一致）
        if not text:
            continue
        i += 1
        start, end = _cue_times(seg, ",")
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
    to a WebVTT `line` percentage (0%=top, 100%=bottom). This mapping matches
    the editor's style preview (v1.0.5, device-calibrated):
    position_y=-40 → line 90%（画面下から10%）。
    """
    if not style:
        return ""
    pos_y = style.get("position_y")
    if pos_y is None:
        pos_y = -40
    line_pct = round(50 - pos_y)
    line_pct = max(0, min(100, line_pct))
    return f" line:{line_pct}% align:center"


def generate_vtt(segments, output_path, style=None):
    """Write segments as a WebVTT (.vtt) file. Returns output_path.

    style: optional telop style dict; used to add a rough vertical position.
    """
    settings = _vtt_cue_settings(style)
    parts = ["WEBVTT\n"]
    for seg in segments:
        text = _vtt_escape((seg.get("text") or "").strip())
        # 空行＝そのテロップを出さない（エディタで行を消した意図に一致）
        if not text:
            continue
        start, end = _cue_times(seg, ".")
        parts.append(f"{start} --> {end}{settings}\n{text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return output_path

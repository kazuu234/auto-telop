"""Generate telop-embedded FCPXML with font styling → export to Desktop."""

import json
import os
import sys
from datetime import datetime

from fcpxml import generate_styled_fcpxml

# 出力フォーマットのレジストリ（拡張子・保存ダイアログのラベルの単一情報源）。
# 新しい形式を追加する場合はここに1エントリ追加し、_WRITERS に書き出し関数を
# 登録するだけでよい。
FORMATS = {
    "fcpxml": {"ext": ".fcpxml", "dialog_label": "Final Cut Pro XML (*.fcpxml)"},
    "srt":    {"ext": ".srt",    "dialog_label": "SubRip字幕 (*.srt)"},
    "vtt":    {"ext": ".vtt",    "dialog_label": "WebVTT字幕 (*.vtt)"},
}
FORMAT_EXT = {k: v["ext"] for k, v in FORMATS.items()}  # 後方互換


def default_output_path(base_name, output_dir=None, output_format="fcpxml"):
    """Build the default export path (Desktop by default, timestamped)."""
    timestamp = datetime.now().strftime("%m%d_%H%M")
    if output_dir is None:
        output_dir = os.path.expanduser("~/Desktop")
    ext = FORMAT_EXT.get(output_format, ".fcpxml")
    return os.path.join(output_dir, f"{base_name}_テロップ付き_{timestamp}{ext}")


def _export_srt(segments, output_path, style, hook):
    from subtitles import generate_srt
    generate_srt(segments, output_path)


def _export_vtt(segments, output_path, style, hook):
    from subtitles import generate_vtt
    generate_vtt(segments, output_path, style)


def _export_fcpxml(segments, output_path, style, hook):
    generate_styled_fcpxml(segments, hook["video_path"], output_path, style)


# fmt → callable(segments, output_path, style, hook)
_WRITERS = {
    "srt": _export_srt,
    "vtt": _export_vtt,
    "fcpxml": _export_fcpxml,
}


def embed_telop(project_dir, base_name, output_path=None, output_format="fcpxml",
                 config=None, segments=None):
    """Generate the telop export in the requested format.

    output_format: "fcpxml" (Final Cut Pro, styled), "srt" (SubRip captions)
        or "vtt" (WebVTT captions). SRT/VTT carry text + timing only; the look
        is applied in the target editor (Premiere / Filmora).
    output_path: full destination path. When None, defaults to
        ~/Desktop/<base>_テロップ付き_<MMDD_HHMM>.<ext> (backward compatible).
        An existing directory path is also accepted; a timestamped filename is
        generated inside it.
    config: 事前にロード済みのconfig dict。app.py の /api/save から渡され、
        二重ロードを避ける。None ならCLI互換で自前ロードする。
    segments: メモリ上の最終セグメント（app.py がエディタの最終テキストを
        渡す）。指定時は segments.json / 校閲済みテキストの再読込をスキップ
        する。None なら今まで通りファイルから読み込む（CLI互換）。
    """
    # _WRITERS が実際のディスパッチ先の正本。FORMATSにだけ追加されて
    # _WRITERSに書き出し関数が無いエントリだと、ここのチェックを通過して
    # 後段が _export_fcpxml + hook=None にフォールバックし、
    # fcpxmlライター内で分かりにくい TypeError になってしまう。
    if output_format not in _WRITERS:
        output_format = "fcpxml"

    if config is None:
        from transcribe import load_config
        config = load_config()
    style = config.get("style", {})

    if segments is None:
        segments_path = os.path.join(project_dir, f"{base_name}_segments.json")
        with open(segments_path, encoding="utf-8") as f:
            segments = json.load(f)

        review_path = os.path.join(project_dir, f"{base_name}_校閲済みテキスト.txt")
        if os.path.exists(review_path):
            with open(review_path, encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f.readlines()]
            for i, seg in enumerate(segments):
                if i < len(lines) and lines[i]:
                    seg["text"] = lines[i]

    if not output_path:
        output_path = default_output_path(base_name, output_format=output_format)
    else:
        output_path = os.path.expanduser(output_path)
        if os.path.isdir(output_path):
            output_path = default_output_path(base_name, output_path, output_format)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    hook = None
    if output_format == "fcpxml":
        # fcpxml だけが hook["video_path"] を必要とする。SRT/VTT書き出しは
        # .telop_post_hook.json が無いプロジェクトdirでも動く必要がある。
        hook_path = os.path.join(project_dir, ".telop_post_hook.json")
        with open(hook_path, encoding="utf-8") as f:
            hook = json.load(f)

    writer = _WRITERS[output_format]
    writer(segments, output_path, style, hook)

    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python embed_te.py <project_dir> <base_name>")
        sys.exit(1)
    embed_telop(sys.argv[1], sys.argv[2])

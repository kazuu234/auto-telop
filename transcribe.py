"""Whisper transcription + segment processing pipeline."""

import csv
import json
import os
from datetime import datetime

import yaml


def load_config(path="config.yaml"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, path)
    default_path = os.path.join(base_dir, "config.default.yaml")
    if not os.path.exists(config_path):
        import shutil
        shutil.copy(default_path, config_path)
        print(f"Created {path} from config.default.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    # 空ファイル・裸のセクションキー（例: `output:` に値が無い）をNoneではなく
    # {} に正規化する。呼び出し側全体（/editor, _remember_output_prefs,
    # /api/last-save-dir 等）が config["section"] を安全に .get() できるようにする。
    if config is None:
        config = {}
    for key in ("style", "whisper", "segment", "output"):
        if key in config and config[key] is None:
            config[key] = {}
    return config


def transcribe(video_path, config):
    """Run Whisper on a video file and return raw segments."""
    import whisper  # 遅延import: エディタ(app.py)起動時に読み込まないため
    wcfg = config["whisper"]
    model = whisper.load_model(wcfg["model"])
    result = model.transcribe(
        video_path,
        language=wcfg["language"],
        word_timestamps=True,
    )
    return result["segments"]


def refine_segments(raw_segments, config):
    """Split long segments and detect silence gaps.

    Takes Whisper's raw segments (often few, long) and produces
    shorter subtitle-friendly segments with proper timing.
    """
    scfg = config["segment"]
    max_chars = scfg["max_chars"]
    max_dur = scfg["max_duration"]
    min_dur = scfg["min_duration"]
    silence_thresh = scfg["silence_threshold"]

    refined = []
    silence_count = 0

    for seg in raw_segments:
        words = seg.get("words", [])
        if not words:
            refined.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
            })
            continue

        current_words = []
        current_start = words[0]["start"]

        for i, w in enumerate(words):
            current_words.append(w)
            current_text = "".join(cw["word"] for cw in current_words).strip()
            current_end = w["end"]
            duration = current_end - current_start

            next_start = words[i + 1]["start"] if i + 1 < len(words) else None
            gap = (next_start - current_end) if next_start else 0

            should_split = (
                len(current_text) >= max_chars
                or duration >= max_dur
                or gap >= silence_thresh
                or next_start is None
            )

            if should_split and current_text:
                # min_dur 未満でも捨てずに次のチャンクへ持ち越す（最後の単語なら必ず出力）
                if duration >= min_dur or next_start is None:
                    refined.append({
                        "start": round(current_start, 3),
                        "end": round(current_end, 3),
                        "text": current_text,
                    })
                    current_words = []
                    if next_start is not None:
                        current_start = next_start
                if gap >= silence_thresh:
                    silence_count += 1

    return refined, silence_count


def save_raw_tsv(segments, output_path):
    """Save raw transcription as TSV."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["index", "start", "end", "text"])
        for i, seg in enumerate(segments):
            writer.writerow([i + 1, seg["start"], seg["end"], seg["text"]])


def save_review_text(segments, output_path):
    """Save editable text file (one line per segment)."""
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg["text"] + "\n")


def run_pipeline(video_path, project_dir, progress_cb=None):
    """Full transcription pipeline: video → segments + files.

    progress_cb: optional callable(stage_message) for GUI progress updates.
    """
    def report(stage):
        if progress_cb:
            try:
                progress_cb(stage)
            except Exception:
                pass

    config = load_config()
    base = os.path.splitext(os.path.basename(video_path))[0]

    os.makedirs(project_dir, exist_ok=True)

    print(f"Transcribing with Whisper ({config['whisper']['model']})...")
    report(f"Whisper文字起こし中 ({config['whisper']['model']})")
    raw_segments = transcribe(video_path, config)
    print(f"Raw segments: {len(raw_segments)}")

    report("セグメント整形中")
    refined, silence_count = refine_segments(raw_segments, config)
    print(f"Refined segments: {len(refined)} (silence gaps: {silence_count})")

    avg_chars = sum(len(s["text"]) for s in refined) / len(refined) if refined else 0
    avg_dur = sum(s["end"] - s["start"] for s in refined) / len(refined) if refined else 0
    print(f"Average: {avg_chars:.0f} chars / {avg_dur:.1f}s per segment")

    tsv_path = os.path.join(project_dir, f"{base}_raw_text.tsv")
    save_raw_tsv(refined, tsv_path)

    review_path = os.path.join(project_dir, f"{base}_校閲済みテキスト.txt")
    save_review_text(refined, review_path)

    segments_path = os.path.join(project_dir, f"{base}_segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(refined, f, ensure_ascii=False, indent=2)

    # Video duration (for the library entry display). Best-effort via ffprobe.
    try:
        from fcpxml import _get_video_info
        video_duration = _get_video_info(video_path)[0]
    except Exception:
        video_duration = refined[-1]["end"] if refined else 0

    meta = {
        "video_path": os.path.abspath(video_path),
        "base_name": base,
        "raw_count": len(raw_segments),
        "refined_count": len(refined),
        "silence_count": silence_count,
        "avg_chars": round(avg_chars, 1),
        "avg_duration": round(avg_dur, 1),
        "video_duration": round(video_duration, 1),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    meta_path = os.path.join(project_dir, f"{base}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    report("FCPXML生成中")
    from fcpxml import generate_pipeline_fcpxml
    fcpxml_path = os.path.join(project_dir, f"{base}_pipeline.fcpxml")
    # スタイル(Noto Sans JP 60px等・位置)を必ず適用する。未指定だと
    # Helvetica 48px・位置なしのフォールバックになり、FCPでサイズが
    # 反映されず(6pt扱い)テロップが見えなくなる。
    generate_pipeline_fcpxml(refined, video_path, fcpxml_path,
                             style_config=config.get("style", {}))

    hook_path = os.path.join(project_dir, ".telop_post_hook.json")
    with open(hook_path, "w", encoding="utf-8") as f:
        json.dump({
            "base_name": base,
            "project_dir": os.path.abspath(project_dir),
            "video_path": os.path.abspath(video_path),
            "on_save": [
                {"script": "reapply.py", "output": f"{base}_校閲済み.fcpxml"},
                {"script": "embed_te.py", "output": f"~/Desktop/{base}_テロップ付き_{{MMDD_HHMM}}.fcpxml"},
            ],
        }, f, ensure_ascii=False, indent=2)

    print(f"\nProject ready: {project_dir}")
    print(f"Open http://localhost:5050 to edit")

    return meta


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <video_file>")
        sys.exit(1)
    video = sys.argv[1]
    base = os.path.splitext(os.path.basename(video))[0]
    proj = os.path.join("projects", base)
    run_pipeline(video, proj)

"""Reapply edited text onto segment timings → generate 校閲済み FCPXML."""

import json
import os
import sys

from fcpxml import generate_pipeline_fcpxml


def reapply(project_dir, base_name, config=None):
    review_path = os.path.join(project_dir, f"{base_name}_校閲済みテキスト.txt")
    segments_path = os.path.join(project_dir, f"{base_name}_segments.json")

    with open(segments_path, encoding="utf-8") as f:
        segments = json.load(f)

    with open(review_path, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f.readlines()]

    if len(lines) != len(segments):
        print(f"Warning: text lines ({len(lines)}) != segments ({len(segments)})")

    for i, seg in enumerate(segments):
        if i < len(lines):
            seg["text"] = lines[i]

    output_path = os.path.join(project_dir, f"{base_name}_校閲済み.fcpxml")

    hook_path = os.path.join(project_dir, ".telop_post_hook.json")
    with open(hook_path, encoding="utf-8") as f:
        hook = json.load(f)

    if config is None:
        from transcribe import load_config
        config = load_config()
    style = config.get("style", {})

    generate_pipeline_fcpxml(segments, hook["video_path"], output_path, style_config=style)
    print(f"Generated: {output_path}")
    return output_path, segments


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reapply.py <project_dir> <base_name>")
        sys.exit(1)
    reapply(sys.argv[1], sys.argv[2])

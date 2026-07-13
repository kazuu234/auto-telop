"""Generate telop-embedded FCPXML with font styling → export to Desktop."""

import json
import os
import sys
from datetime import datetime

from fcpxml import generate_styled_fcpxml


def embed_telop(project_dir, base_name):
    from transcribe import load_config
    config = load_config()
    style = config["style"]

    segments_path = os.path.join(project_dir, f"{base_name}_segments.json")
    with open(segments_path, encoding="utf-8") as f:
        segments = json.load(f)

    review_path = os.path.join(project_dir, f"{base_name}_校閲済みテキスト.txt")
    if os.path.exists(review_path):
        with open(review_path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
        for i, seg in enumerate(segments):
            if i < len(lines):
                seg["text"] = lines[i]

    hook_path = os.path.join(project_dir, ".telop_post_hook.json")
    with open(hook_path, encoding="utf-8") as f:
        hook = json.load(f)

    timestamp = datetime.now().strftime("%m%d_%H%M")
    desktop = os.path.expanduser("~/Desktop")
    output_path = os.path.join(desktop, f"{base_name}_テロップ付き_{timestamp}.fcpxml")

    generate_styled_fcpxml(segments, hook["video_path"], output_path, style)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python embed_te.py <project_dir> <base_name>")
        sys.exit(1)
    embed_telop(sys.argv[1], sys.argv[2])

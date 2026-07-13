"""Generate telop-embedded FCPXML with font styling → export to Desktop."""

import json
import os
import sys
from datetime import datetime

from fcpxml import generate_styled_fcpxml


def default_output_path(base_name, output_dir=None):
    """Build the default export path (Desktop by default, timestamped)."""
    timestamp = datetime.now().strftime("%m%d_%H%M")
    if output_dir is None:
        output_dir = os.path.expanduser("~/Desktop")
    return os.path.join(output_dir, f"{base_name}_テロップ付き_{timestamp}.fcpxml")


def embed_telop(project_dir, base_name, output_path=None):
    """Generate the styled telop FCPXML.

    output_path: full destination path. When None, defaults to
    ~/Desktop/<base>_テロップ付き_<MMDD_HHMM>.fcpxml (backward compatible).
    An existing directory path is also accepted; a timestamped filename is
    generated inside it.
    """
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

    if not output_path:
        output_path = default_output_path(base_name)
    else:
        output_path = os.path.expanduser(output_path)
        if os.path.isdir(output_path):
            output_path = default_output_path(base_name, output_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    generate_styled_fcpxml(segments, hook["video_path"], output_path, style)
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python embed_te.py <project_dir> <base_name>")
        sys.exit(1)
    embed_telop(sys.argv[1], sys.argv[2])

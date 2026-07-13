"""FCPXML generation for Final Cut Pro."""

import os
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET


def _get_video_info(video_path):
    """Get video duration and frame rate via ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", video_path,
            ],
            capture_output=True, text=True,
        )
        import json
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
        for stream in info["streams"]:
            if stream["codec_type"] == "video":
                r_parts = stream.get("r_frame_rate", "30/1").split("/")
                fps = int(r_parts[0]) / int(r_parts[1]) if len(r_parts) == 2 else 30
                width = stream.get("width", 1920)
                height = stream.get("height", 1080)
                return duration, fps, width, height
    except Exception:
        pass
    return 60.0, 30.0, 1920, 1080


def _seconds_to_fcpxml_time(seconds, fps=30):
    """Convert seconds to FCPXML rational time snapped to frame boundaries."""
    frames = round(seconds * fps)
    fps_rounded = round(fps)
    # 許容誤差は 0.01: 整数fps (30.0) をNTSC (29.97) と誤判定しないよう十分小さく
    if abs(fps - 30000 / 1001) < 0.01:
        return f"{frames * 1001}/30000s"
    if abs(fps - 60000 / 1001) < 0.01:
        return f"{frames * 1001}/60000s"
    if abs(fps - 24000 / 1001) < 0.01:
        return f"{frames * 1001}/24000s"
    return f"{frames * 100}/{fps_rounded * 100}s"


def _split_text_runs(text):
    """Split text into (is_ascii, chunk) runs for dual-font rendering."""
    runs = []
    for match in re.finditer(r'[A-Za-z0-9\s\.\,\!\?\-\:\;\'\"\(\)\[\]\/\@\#\$\%\&\*\+\=]+|[^A-Za-z0-9\s\.\,\!\?\-\:\;\'\"\(\)\[\]\/\@\#\$\%\&\*\+\=]+', text):
        chunk = match.group()
        # 判定はチャンク内に英数字を含むかで行う（先頭が空白でも英語扱いにする）
        is_ascii = bool(re.search(r'[A-Za-z0-9]', chunk))
        runs.append((is_ascii, chunk))
    return runs if runs else [(False, text)]


def _write_fcpxml(root, output_path):
    """Serialize WITHOUT any pretty-printing.

    Pretty-printers (minidom.toprettyxml / ET.indent) inject whitespace
    around text nodes, which shows up as literal spaces and newlines in
    the telop text once imported into FCP. Compact output is safe.
    """
    body = ET.tostring(root, encoding="unicode")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE fcpxml>\n')
        f.write(body + "\n")
    return output_path


def _build_text_style_attrs(font, font_size, bold_val, outline):
    """Build text-style attributes dict for FCPXML."""
    attrs = {
        "font": font,
        "fontSize": str(font_size),
        "fontColor": "1 1 1 1",
        "bold": bold_val,
        "alignment": "center",
    }
    outline_val = int(outline)
    if outline_val > 0:
        attrs["strokeColor"] = "0 0 0 1"
        attrs["strokeWidth"] = str(-outline_val)
    return attrs


def _add_text_with_dual_font(title_el, seg_text, idx, style_config):
    """Add text and text-style-def elements (DTD order: text*, text-style-def*)."""
    font_ja = style_config.get("font_name", "Noto Sans JP")
    font_en = style_config.get("font_name_en", font_ja)
    size_ja = style_config.get("font_size", 60)
    size_en = style_config.get("font_size_en", size_ja)
    bold_ja = "1" if style_config.get("bold", True) else "0"
    bold_en = "1" if style_config.get("bold_en", style_config.get("bold", True)) else "0"
    outline_ja = style_config.get("outline_width", 6)
    outline_en = style_config.get("outline_width_en", outline_ja)

    text_el = ET.SubElement(title_el, "text")

    if font_en == font_ja and size_ja == size_en:
        ts = ET.SubElement(text_el, "text-style", ref=f"ts{idx}_ja")
        ts.text = seg_text
        tsd = ET.SubElement(title_el, "text-style-def", id=f"ts{idx}_ja")
        attrs = _build_text_style_attrs(font_ja, size_ja, bold_ja, outline_ja)
        ET.SubElement(tsd, "text-style", **attrs)
        return

    runs = _split_text_runs(seg_text)
    style_defs = []
    for r_idx, (is_ascii, chunk) in enumerate(runs):
        ref_id = f"ts{idx}_{'en' if is_ascii else 'ja'}_{r_idx}"
        ts = ET.SubElement(text_el, "text-style", ref=ref_id)
        ts.text = chunk
        if is_ascii:
            style_defs.append((ref_id, font_en, size_en, bold_en, outline_en))
        else:
            style_defs.append((ref_id, font_ja, size_ja, bold_ja, outline_ja))

    for ref_id, font, size, bold, outline in style_defs:
        tsd = ET.SubElement(title_el, "text-style-def", id=ref_id)
        attrs = _build_text_style_attrs(font, size, bold, outline)
        ET.SubElement(tsd, "text-style", **attrs)


def _add_position(title_el, style_config, width=1920, height=1080):
    """Add position via adjust-transform.

    Converts percentage values (-100~100) to pixel coordinates from center.
    """
    pos_x_pct = style_config.get("position_x", 0)
    pos_y_pct = style_config.get("position_y", -85)
    pos_x_px = round(pos_x_pct / 100 * (width / 2))
    pos_y_px = round(pos_y_pct / 100 * (height / 2))
    ET.SubElement(title_el, "adjust-transform",
                  position=f"{pos_x_px} {pos_y_px}")


def generate_pipeline_fcpxml(segments, video_path, output_path, style_config=None):
    """Generate FCPXML with subtitle timing markers."""
    duration, fps, width, height = _get_video_info(video_path)
    abs_video = os.path.abspath(video_path)
    video_url = "file://" + urllib.parse.quote(abs_video)

    total_dur = _seconds_to_fcpxml_time(duration, fps)

    root = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(root, "resources")

    ET.SubElement(resources, "format", id="r1",
                  name=f"FFVideoFormat{height}p{int(fps)}",
                  frameDuration=_seconds_to_fcpxml_time(1 / fps, fps),
                  width=str(width), height=str(height))

    asset = ET.SubElement(resources, "asset", id="r2", name=os.path.basename(video_path),
                          start="0/1s", duration=total_dur,
                          hasVideo="1", hasAudio="1", format="r1")
    ET.SubElement(asset, "media-rep", kind="original-media", src=video_url)

    ET.SubElement(resources, "effect", id="r3",
                  name="Basic Title",
                  uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti")

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="Auto Telop")
    project = ET.SubElement(event, "project", name=os.path.splitext(os.path.basename(video_path))[0])
    sequence = ET.SubElement(project, "sequence", format="r1",
                             duration=total_dur, tcStart="0/1s")
    spine = ET.SubElement(sequence, "spine")

    clip = ET.SubElement(spine, "asset-clip", ref="r2", name=os.path.basename(video_path),
                         duration=total_dur, start="0/1s", offset="0/1s")

    for i, seg in enumerate(segments):
        offset = _seconds_to_fcpxml_time(seg["start"], fps)
        # 0フレーム duration は DTD 的に不正になるため最低1フレーム確保
        seg_dur = _seconds_to_fcpxml_time(max(seg["end"] - seg["start"], 1 / fps), fps)
        title = ET.SubElement(clip, "title", ref="r3", lane="1",
                              name=f"Telop {i + 1}", offset=offset, duration=seg_dur)
        if style_config:
            _add_text_with_dual_font(title, seg["text"], i + 1, style_config)
            _add_position(title, style_config, width, height)
        else:
            text = ET.SubElement(title, "text")
            ts = ET.SubElement(text, "text-style", ref=f"ts{i + 1}")
            ts.text = seg["text"]
            tsd = ET.SubElement(title, "text-style-def", id=f"ts{i + 1}")
            ET.SubElement(tsd, "text-style",
                          font="Helvetica", fontSize="48",
                          fontColor="1 1 1 1", bold="1",
                          strokeColor="0 0 0 1", strokeWidth="-2",
                          alignment="center")

    return _write_fcpxml(root, output_path)


def generate_styled_fcpxml(segments, video_path, output_path, style_config):
    """Generate FCPXML with embedded telop styling."""
    duration, fps, width, height = _get_video_info(video_path)
    abs_video = os.path.abspath(video_path)
    video_url = "file://" + urllib.parse.quote(abs_video)

    total_dur = _seconds_to_fcpxml_time(duration, fps)

    root = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(root, "resources")

    ET.SubElement(resources, "format", id="r1",
                  name=f"FFVideoFormat{height}p{int(fps)}",
                  frameDuration=_seconds_to_fcpxml_time(1 / fps, fps),
                  width=str(width), height=str(height))

    asset = ET.SubElement(resources, "asset", id="r2", name=os.path.basename(video_path),
                          start="0/1s", duration=total_dur,
                          hasVideo="1", hasAudio="1", format="r1")
    ET.SubElement(asset, "media-rep", kind="original-media", src=video_url)

    ET.SubElement(resources, "effect", id="r3",
                  name="Basic Title",
                  uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti")

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="Auto Telop")
    project = ET.SubElement(event, "project", name=os.path.splitext(os.path.basename(video_path))[0])
    sequence = ET.SubElement(project, "sequence", format="r1",
                             duration=total_dur, tcStart="0/1s")
    spine = ET.SubElement(sequence, "spine")

    clip = ET.SubElement(spine, "asset-clip", ref="r2", name=os.path.basename(video_path),
                         duration=total_dur, start="0/1s", offset="0/1s")

    for i, seg in enumerate(segments):
        offset = _seconds_to_fcpxml_time(seg["start"], fps)
        # 0フレーム duration は DTD 的に不正になるため最低1フレーム確保
        seg_dur = _seconds_to_fcpxml_time(max(seg["end"] - seg["start"], 1 / fps), fps)
        title = ET.SubElement(clip, "title", ref="r3", lane="1",
                              name=f"Telop {i + 1}", offset=offset, duration=seg_dur)
        _add_text_with_dual_font(title, seg["text"], i + 1, style_config)
        _add_position(title, style_config, width, height)

    return _write_fcpxml(root, output_path)

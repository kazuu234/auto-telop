"""FCPXML generation for Final Cut Pro."""

import os
import subprocess
import xml.etree.ElementTree as ET
from xml.dom import minidom


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
    if abs(fps - 29.97) < 0.1 or abs(fps - 30000 / 1001) < 0.01:
        return f"{frames * 1001}/30000s"
    if abs(fps - 59.94) < 0.1 or abs(fps - 60000 / 1001) < 0.01:
        return f"{frames * 1001}/60000s"
    if abs(fps - 23.976) < 0.1 or abs(fps - 24000 / 1001) < 0.01:
        return f"{frames * 1001}/24000s"
    return f"{frames * 100}/{fps_rounded * 100}s"


def _add_position_param(title_el, style_config):
    """Add position parameter to a title element."""
    pos_x = style_config.get("position_x", 0)
    pos_y = style_config.get("position_y", -85)
    if pos_x != 0 or pos_y != 0:
        ET.SubElement(title_el, "param",
                      name="Position", key="9999/999166631/999166633/1/100/101",
                      value=f"{pos_x} {pos_y}")


def generate_pipeline_fcpxml(segments, video_path, output_path, style_config=None):
    """Generate FCPXML with subtitle timing markers."""
    duration, fps, width, height = _get_video_info(video_path)
    abs_video = os.path.abspath(video_path)
    video_url = "file://" + abs_video.replace(" ", "%20")

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
        seg_dur = _seconds_to_fcpxml_time(seg["end"] - seg["start"], fps)
        title = ET.SubElement(clip, "title", ref="r3", lane="1",
                              name=f"Telop {i + 1}", offset=offset, duration=seg_dur)
        if style_config:
            _add_position_param(title, style_config)
        text = ET.SubElement(title, "text")
        text_style = ET.SubElement(text, "text-style", ref=f"ts{i + 1}")
        text_style.text = seg["text"]
        text_style_def = ET.SubElement(title, "text-style-def", id=f"ts{i + 1}")
        ET.SubElement(text_style_def, "text-style",
                      font="Helvetica", fontSize="48",
                      fontColor="1 1 1 1", bold="1",
                      strokeColor="0 0 0 1", strokeWidth="2",
                      alignment="center")

    xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    lines = [l for l in xml_str.split("\n") if l.strip()]
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    lines.insert(1, '<!DOCTYPE fcpxml>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return output_path


def generate_styled_fcpxml(segments, video_path, output_path, style_config):
    """Generate FCPXML with embedded telop styling."""
    duration, fps, width, height = _get_video_info(video_path)
    abs_video = os.path.abspath(video_path)
    video_url = "file://" + abs_video.replace(" ", "%20")

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

    font = style_config.get("font_name", "A P-OTF A1Gothic StdN")
    font_size = style_config.get("font_size", 35)

    for i, seg in enumerate(segments):
        offset = _seconds_to_fcpxml_time(seg["start"], fps)
        seg_dur = _seconds_to_fcpxml_time(seg["end"] - seg["start"], fps)
        title = ET.SubElement(clip, "title", ref="r3", lane="1",
                              name=f"Telop {i + 1}", offset=offset, duration=seg_dur)
        _add_position_param(title, style_config)
        text = ET.SubElement(title, "text")
        text_style = ET.SubElement(text, "text-style", ref=f"ts{i + 1}")
        text_style.text = seg["text"]
        text_style_def = ET.SubElement(title, "text-style-def", id=f"ts{i + 1}")
        bold_val = "1" if style_config.get("bold", True) else "0"
        ET.SubElement(text_style_def, "text-style",
                      font=font, fontSize=str(font_size),
                      fontColor="1 1 1 1", bold=bold_val,
                      strokeColor="0 0 0 1",
                      strokeWidth=str(style_config.get("outline_width", 3)),
                      alignment="center")

    xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    lines = [l for l in xml_str.split("\n") if l.strip()]
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    lines.insert(1, '<!DOCTYPE fcpxml>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return output_path

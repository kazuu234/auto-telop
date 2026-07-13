"""Web editor for subtitle review and correction."""

import json
import os
import subprocess
import glob

import yaml
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")


def _find_projects():
    projects = []
    for meta_file in sorted(glob.glob(os.path.join(PROJECTS_DIR, "*", "*_meta.json"))):
        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)
        meta["project_dir"] = os.path.dirname(meta_file)
        projects.append(meta)
    return projects


@app.route("/")
def index():
    projects = _find_projects()
    if not projects:
        return render_template("editor.html", project=None, segments=[], meta={})

    name = request.args.get("project")
    if name:
        project = next((p for p in projects if p["base_name"] == name), projects[0])
    else:
        project = projects[0]

    segments_path = os.path.join(project["project_dir"], f"{project['base_name']}_segments.json")
    with open(segments_path, encoding="utf-8") as f:
        segments = json.load(f)

    review_path = os.path.join(project["project_dir"], f"{project['base_name']}_校閲済みテキスト.txt")
    if os.path.exists(review_path):
        with open(review_path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
        for i, seg in enumerate(segments):
            if i < len(lines) and lines[i]:
                seg["text"] = lines[i]

    config = yaml.safe_load(open(os.path.join(BASE_DIR, "config.yaml")))
    style = config.get("style", {})

    return render_template("editor.html", project=project, segments=segments,
                           meta=project, projects=projects, style=style)


@app.route("/video/<path:project_name>")
def serve_video(project_name):
    projects = _find_projects()
    project = next((p for p in projects if p["base_name"] == project_name), None)
    if not project:
        return "Not found", 404
    return send_file(project["video_path"], mimetype="video/mp4")


@app.route("/api/save", methods=["POST"])
def save():
    data = request.json
    project_name = data["project"]
    segments = data["segments"]

    projects = _find_projects()
    project = next((p for p in projects if p["base_name"] == project_name), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    project_dir = project["project_dir"]

    segments_path = os.path.join(project_dir, f"{project_name}_segments.json")
    with open(segments_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    review_path = os.path.join(project_dir, f"{project_name}_校閲済みテキスト.txt")
    with open(review_path, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg["text"] + "\n")

    from reapply import reapply
    reapply(project_dir, project_name)

    from embed_te import embed_telop
    output = embed_telop(project_dir, project_name)

    return jsonify({"ok": True, "output": output, "count": len(segments)})


@app.route("/api/merge", methods=["POST"])
def merge_segments():
    data = request.json
    segments = data["segments"]
    indices = sorted(data["indices"])

    if len(indices) < 2:
        return jsonify({"error": "Need at least 2 segments to merge"}), 400

    merged = {
        "start": segments[indices[0]]["start"],
        "end": segments[indices[-1]]["end"],
        "text": "".join(segments[i]["text"] for i in indices),
    }

    new_segments = []
    skip = set(indices[1:])
    for i, seg in enumerate(segments):
        if i == indices[0]:
            new_segments.append(merged)
        elif i not in skip:
            new_segments.append(seg)

    return jsonify({"segments": new_segments})


@app.route("/api/split", methods=["POST"])
def split_segment():
    data = request.json
    segments = data["segments"]
    idx = data["index"]
    pos = data["position"]

    seg = segments[idx]
    text = seg["text"]

    if pos <= 0 or pos >= len(text):
        return jsonify({"error": "Invalid split position"}), 400

    ratio = pos / len(text)
    mid = seg["start"] + (seg["end"] - seg["start"]) * ratio

    seg1 = {"start": seg["start"], "end": round(mid, 3), "text": text[:pos]}
    seg2 = {"start": round(mid, 3), "end": seg["end"], "text": text[pos:]}

    new_segments = segments[:idx] + [seg1, seg2] + segments[idx + 1:]
    return jsonify({"segments": new_segments})


@app.route("/api/style", methods=["GET"])
def get_style():
    config = yaml.safe_load(open(os.path.join(BASE_DIR, "config.yaml")))
    return jsonify(config.get("style", {}))


@app.route("/api/style", methods=["POST"])
def update_style():
    new_style = request.json
    config_path = os.path.join(BASE_DIR, "config.yaml")
    config = yaml.safe_load(open(config_path))
    config["style"] = new_style
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

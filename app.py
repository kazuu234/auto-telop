"""Flask backend: library home + subtitle editor + APIs.

Runs standalone in a browser (python app.py) or embedded inside the native
desktop window (desktop.py). All state lives on disk under projects/, so the
library persists across restarts with no database.
"""

import json
import os
import glob
import shutil

import media_env  # noqa: F401 — patches PATH so ffmpeg/ffprobe resolve from Finder

import yaml
from flask import Flask, render_template, request, jsonify, send_file

from jobs import manager as job_manager

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

os.makedirs(PROJECTS_DIR, exist_ok=True)
job_manager.configure(PROJECTS_DIR)


def _find_projects():
    projects = []
    for meta_file in glob.glob(os.path.join(PROJECTS_DIR, "*", "*_meta.json")):
        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            continue
        meta["project_dir"] = os.path.dirname(meta_file)
        meta["_mtime"] = os.path.getmtime(meta_file)
        projects.append(meta)
    # Newest first.
    projects.sort(key=lambda m: m.get("_mtime", 0), reverse=True)
    return projects


def _load_segments(project):
    segments_path = os.path.join(
        project["project_dir"], f"{project['base_name']}_segments.json"
    )
    with open(segments_path, encoding="utf-8") as f:
        segments = json.load(f)

    review_path = os.path.join(
        project["project_dir"], f"{project['base_name']}_校閲済みテキスト.txt"
    )
    if os.path.exists(review_path):
        with open(review_path, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
        for i, seg in enumerate(segments):
            if i < len(lines) and lines[i]:
                seg["text"] = lines[i]
    return segments


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """Library home: list of extracted projects + extraction queue."""
    from version import get_version
    return render_template("home.html", version=get_version())


@app.route("/editor")
def editor():
    projects = _find_projects()
    if not projects:
        return render_template("editor.html", project=None, segments=[], meta={})

    name = request.args.get("project")
    if name:
        project = next((p for p in projects if p["base_name"] == name), projects[0])
    else:
        project = projects[0]

    segments = _load_segments(project)

    from transcribe import load_config
    config = load_config()
    style = config.get("style", {})
    default_format = config.get("output", {}).get("default_format", "fcpxml")

    return render_template("editor.html", project=project, segments=segments,
                           meta=project, projects=projects, style=style,
                           default_format=default_format)


@app.route("/video/<path:project_name>")
def serve_video(project_name):
    project = next((p for p in _find_projects() if p["base_name"] == project_name), None)
    if not project:
        return "Not found", 404
    return send_file(project["video_path"], mimetype="video/mp4")


# ---------------------------------------------------------------------------
# Library / extraction APIs
# ---------------------------------------------------------------------------

@app.route("/api/projects")
def api_projects():
    """Return library entries (finished projects) + active jobs."""
    projects = []
    for p in _find_projects():
        projects.append({
            "base_name": p.get("base_name"),
            "refined_count": p.get("refined_count"),
            "video_duration": p.get("video_duration"),
            "avg_chars": p.get("avg_chars"),
            "created_at": p.get("created_at"),
        })
    return jsonify({"projects": projects, "jobs": job_manager.list_jobs()})


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Enqueue one or more videos for transcription."""
    data = request.json or {}
    paths = data.get("paths") or []
    if isinstance(paths, str):
        paths = [paths]

    accepted, rejected = [], []
    for p in paths:
        expanded = os.path.abspath(os.path.expanduser(p))
        if os.path.isfile(expanded):
            accepted.append(job_manager.submit(expanded))
        else:
            rejected.append(p)
    return jsonify({"jobs": accepted, "rejected": rejected})


@app.route("/api/jobs")
def api_jobs():
    return jsonify({"jobs": job_manager.list_jobs()})


@app.route("/api/jobs/clear", methods=["POST"])
def api_jobs_clear():
    job_manager.clear_finished()
    return jsonify({"ok": True})


@app.route("/api/project/<path:project_name>", methods=["DELETE"])
def api_delete_project(project_name):
    project = next((p for p in _find_projects() if p["base_name"] == project_name), None)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    shutil.rmtree(project["project_dir"], ignore_errors=True)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Editor APIs
# ---------------------------------------------------------------------------

@app.route("/api/save", methods=["POST"])
def save():
    data = request.json
    project_name = data["project"]
    segments = data["segments"]
    output_path = data.get("output_path")  # optional custom destination

    from embed_te import FORMAT_EXT
    output_format = data.get("output_format") or "fcpxml"  # fcpxml / srt / vtt
    if output_format not in FORMAT_EXT:
        output_format = "fcpxml"

    project = next((p for p in _find_projects() if p["base_name"] == project_name), None)
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

    from transcribe import load_config
    config = load_config()

    # 校閲済み.fcpxml はFCP専用の中間成果物。SRT/VTT保存では再生成をスキップする
    # （校閲済みテキストは直前に書き込み済みなので失われるものはない）。
    if output_format == "fcpxml":
        from reapply import reapply
        reapply(project_dir, project_name, config=config)

    from embed_te import embed_telop
    output = embed_telop(project_dir, project_name,
                         output_path=output_path, output_format=output_format,
                         config=config, segments=segments)

    # 保存先/形式を記憶するのはエクスポート成功後のみ（失敗時にprefsを汚さない）。
    out_dir = None
    if output_path:
        # 拡張子なしの裸ファイル名（例: "out.srt"）だと dirname が "" になり、
        # "" is not None で skip-check の out_dir is None 分岐を素通りしてしまう
        # ため None に正規化する。
        out_dir = (output_path if os.path.isdir(output_path)
                  else os.path.dirname(output_path)) or None
    _remember_output_prefs(out_dir, output_format)

    return jsonify({"ok": True, "output": output, "count": len(segments)})


def _remember_output_prefs(out_dir, output_format=None):
    from transcribe import load_config
    config = load_config()
    out_cfg = config.setdefault("output", {})
    # 変更が無ければ書き込まない（yaml.dumpはコメントを消すため書き込みを最小化）
    if (out_dir is None or out_cfg.get("last_save_dir") == out_dir) \
            and out_cfg.get("default_format") == output_format:
        return
    if out_dir:
        out_cfg["last_save_dir"] = out_dir
    if output_format:
        out_cfg["default_format"] = output_format
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


@app.route("/api/last-save-dir")
def api_last_save_dir():
    from transcribe import load_config
    config = load_config()
    return jsonify({"dir": config.get("output", {}).get("last_save_dir")})


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
    from transcribe import load_config
    return jsonify(load_config().get("style", {}))


@app.route("/api/style", methods=["POST"])
def update_style():
    new_style = request.json
    from transcribe import load_config
    config = load_config()
    # マージ（UIにないキーを消さない）
    config.setdefault("style", {}).update(new_style)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Version / update APIs
# ---------------------------------------------------------------------------

@app.route("/api/version")
def api_version():
    from version import get_version
    return jsonify({"version": get_version()})


@app.route("/api/update/check")
def api_update_check():
    from updater import check_update
    return jsonify(check_update())


@app.route("/api/update/download", methods=["POST"])
def api_update_download():
    from updater import download_update
    data = request.json or {}
    url = data.get("download_url")
    name = data.get("asset_name")
    if not url:
        return jsonify({"error": "download_url required"}), 400
    try:
        path = download_update(url, name)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "path": path})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)

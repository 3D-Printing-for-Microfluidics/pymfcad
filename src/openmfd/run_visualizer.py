import json
import importlib.util
import re
import tempfile
import uuid
import subprocess
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, abort, request, send_file, after_this_request

PORT = 8000
CWD = Path.cwd().resolve()


def get_openmfd_env_dir():
    """Return the absolute path to the openmfd package directory."""
    spec = importlib.util.find_spec("openmfd")
    if spec and spec.origin:
        package_path = Path(spec.origin).parent
        # print(f"\tFound openmfd package at: {package_path.relative_to(CWD)}")
        return package_path.relative_to(CWD)
    print("\topenmfd package not found in sys.path")
    return None

def start_server():
    env_dir = get_openmfd_env_dir()
    visualizer_dir = (env_dir / "visualizer").resolve()
    static_dir = visualizer_dir / "static"
    docs_dir = (env_dir / "docs_site").resolve()

    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")

    selected_preview_dir = None
    render_sessions = {}

    if not visualizer_dir.is_dir():
        raise RuntimeError("Cannot find visualizer directory!")

    def get_glb_dir():
        if selected_preview_dir and selected_preview_dir.is_dir():
            return selected_preview_dir
        cwd_preview = CWD / "preview"
        if cwd_preview.is_dir():
            return cwd_preview

        default_dir = visualizer_dir / "demo_device"
        if default_dir.is_dir():
            return default_dir

        return None

    def list_glb_files(preview_dir):
        glb_list = []
        for path in sorted(preview_dir.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file() and path.suffix.lower() == ".glb":
                stem = path.stem
                version = "v0"
                base_name = stem
                match = re.match(r"^(.*)__v(\d+)$", stem, re.IGNORECASE)
                if match:
                    base_name = match.group(1)
                    version = f"v{match.group(2)}"

                name_key = base_name.lower()
                name = base_name
                type_str = "unknown"

                if name_key.startswith("bulk_"):
                    name = name_key[5:].capitalize()
                    type_str = "bulk"
                elif name_key.startswith("void_"):
                    name = name_key[5:].capitalize()
                    type_str = "void"
                elif name_key.startswith("regional_"):
                    name = name_key[9:]
                    if name.startswith("membrane_settings_"):
                        name = name[18:].capitalize()
                        type_str = "regional membrane settings"
                    elif name.startswith("position_settings_"):
                        name = name[18:].capitalize()
                        type_str = "regional position settings"
                    elif name.startswith("exposure_settings_"):
                        name = name[18:].capitalize()
                        type_str = "regional exposure settings"
                    elif name.startswith("secondary_dose_settings_"):
                        name = name[24:].capitalize()
                        type_str = "regional secondary dose"
                    else:
                        name = name.capitalize()
                        type_str = "regional"
                elif name_key == "ports":
                    name = "Unconnected Ports"
                    type_str = "ports"
                elif name_key == "device":
                    name = "Device"
                    type_str = "device"
                elif name_key == "bounding_box":
                    name = "Bounding Box"
                    type_str = "bounding box"

                # remove CWD from path for JSON
                path = path.resolve().relative_to(CWD)

                glb_list.append(
                    {
                        "name": name,
                        "type": type_str,
                        "file": path.as_posix(),
                        "version": version,
                        "base_name": base_name,
                    }
                )

        return glb_list

    def list_settings_files(preview_dir):
        candidates = ["openmfd-settings.json", "settings.json"]
        files = []
        for name in candidates:
            path = preview_dir / name
            if path.is_file():
                stat = path.stat()
                files.append(
                    {
                        "name": path.name,
                        "path": str(path.resolve().relative_to(CWD)),
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                    }
                )
        return files

    @app.route("/")
    def index():
        return send_from_directory(str(visualizer_dir), "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(str(visualizer_dir), "favicon.ico")

    @app.route("/docs")
    @app.route("/docs/")
    def docs_index():
        if not docs_dir.is_dir():
            return abort(404)
        return send_from_directory(str(docs_dir), "index.html")

    @app.route("/docs/<path:subpath>")
    def docs_assets(subpath):
        if not docs_dir.is_dir():
            return abort(404)
        # if subpath is directory, serve index.html
        target_path = docs_dir / subpath
        if target_path.is_dir():
            subpath = str(Path(subpath) / "index.html")
        return send_from_directory(str(docs_dir), subpath)

    @app.route("/main.js")
    def main_js():
        return send_from_directory(str(visualizer_dir), "main.js")

    @app.route("/visualizer/<path:subpath>")
    def visualizer_assets(subpath):
        return send_from_directory(str(visualizer_dir), subpath)

    @app.route("/glb_list.json")
    def glb_list():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"error": "No valid .glb directory found."}), 404
        return jsonify(list_glb_files(preview_dir))

    @app.route("/cwd.json")
    def cwd_info():
        return jsonify({"cwd": str(CWD)})

    @app.route("/preview_info.json")
    def preview_info():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"cwd": str(CWD), "source": "none", "preview_dir": ""})
        if selected_preview_dir and preview_dir == selected_preview_dir:
            source = "custom"
        elif preview_dir == (CWD / "preview"):
            source = "cwd/preview"
        else:
            source = "demo"
        return jsonify(
            {
                "cwd": str(CWD),
                "source": source,
                "preview_dir": str(preview_dir),
            }
        )

    @app.route("/preview_settings_list.json")
    def preview_settings_list():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"preview_dir": "", "files": [], "signature": ""})
        files = list_settings_files(preview_dir)
        signature = "|".join(
            f"{item['path']}:{item['mtime']}:{item['size']}" for item in files
        )
        return jsonify(
            {
                "preview_dir": str(preview_dir),
                "files": files,
                "signature": signature,
            }
        )

    @app.route("/preview_settings_file")
    def preview_settings_file():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"error": "No preview directory"}), 404
        rel_path = (request.args.get("path") or "").strip()
        if not rel_path:
            return jsonify({"error": "path required"}), 400
        candidate = (CWD / rel_path).resolve()
        try:
            candidate.relative_to(preview_dir)
        except ValueError:
            return jsonify({"error": "Path must be inside preview folder"}), 400
        if not candidate.is_file() or candidate.suffix.lower() != ".json":
            return jsonify({"error": "File not found"}), 404
        try:
            data = json.loads(candidate.read_text())
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400
        return jsonify(data)

    @app.route("/pathtracing_animation/start", methods=["POST"])
    def start_pathtracing_animation():
        session_id = uuid.uuid4().hex
        tmp_dir = Path(tempfile.mkdtemp(prefix="openmfd_pt_"))
        render_sessions[session_id] = {
            "dir": tmp_dir,
            "count": 0,
        }
        return jsonify({"session_id": session_id})

    @app.route("/pathtracing_animation/frame", methods=["POST"])
    def upload_pathtracing_frame():
        session_id = (request.form.get("session_id") or "").strip()
        if not session_id or session_id not in render_sessions:
            return jsonify({"error": "Invalid session"}), 400
        frame_index = request.form.get("index")
        try:
            frame_num = int(frame_index)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid frame index"}), 400
        file = request.files.get("frame")
        if file is None:
            return jsonify({"error": "Missing frame file"}), 400
        session = render_sessions[session_id]
        out_path = session["dir"] / f"frame_{frame_num:04d}.png"
        file.save(out_path)
        session["count"] = max(session["count"], frame_num + 1)
        return jsonify({"ok": True})

    @app.route("/pathtracing_animation/finish", methods=["POST"])
    def finish_pathtracing_animation():
        data = request.get_json(silent=True) or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id or session_id not in render_sessions:
            return jsonify({"error": "Invalid session"}), 400
        session = render_sessions.pop(session_id, None)
        if not session:
            return jsonify({"error": "Missing session"}), 400

        tmp_dir = session["dir"]
        fps = int(data.get("fps") or 30)
        fps = max(1, min(60, fps))
        file_type = (data.get("type") or "webm").lower()
        quality = (data.get("quality") or "medium").lower()
        filename = (data.get("filename") or "openmfd-animation").strip()
        filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)

        if file_type not in {"webm", "mp4", "avi"}:
            file_type = "webm"

        output_path = tmp_dir / f"{filename}.{file_type}"

        if quality == "low":
            bitrate = "4M"
        elif quality == "high":
            bitrate = "30M"
        elif quality == "lossless":
            bitrate = "80M"
        else:
            bitrate = "12M"

        if file_type == "mp4":
            codec = "libx264"
            extra = ["-pix_fmt", "yuv420p"]
        elif file_type == "avi":
            codec = "mpeg4"
            extra = []
        else:
            codec = "libvpx-vp9"
            extra = ["-pix_fmt", "yuv420p"]

        cmd = [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(tmp_dir / "frame_%04d.png"),
            "-c:v",
            codec,
            "-b:v",
            bitrate,
            *extra,
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return jsonify({"error": "Encoding failed. Ensure ffmpeg is installed."}), 500

        @after_this_request
        def cleanup(response):
            try:
                for item in tmp_dir.iterdir():
                    item.unlink(missing_ok=True)
                tmp_dir.rmdir()
            except Exception:
                pass
            return response

        return send_file(str(output_path), as_attachment=True, download_name=output_path.name)

    @app.route("/set_preview_dir", methods=["POST"])
    def set_preview_dir():
        nonlocal selected_preview_dir
        data = request.get_json(silent=True) or {}
        raw_path = (data.get("path") or "").strip()
        if not raw_path:
            selected_preview_dir = None
            return jsonify({"ok": True, "preview_dir": ""})

        candidate = (CWD / raw_path).resolve()
        try:
            candidate.relative_to(CWD)
        except ValueError:
            return jsonify({"ok": False, "error": "Path must be inside CWD"}), 400

        if not candidate.is_dir():
            return jsonify({"ok": False, "error": "Folder does not exist"}), 400

        if not any(candidate.glob("*.glb")):
            return jsonify({"ok": False, "error": "No .glb files in folder"}), 400

        selected_preview_dir = candidate
        return jsonify({"ok": True, "preview_dir": str(selected_preview_dir)})

    @app.route("/<path:filename>")
    def serve_glb(filename):
        if filename.endswith(".glb"):
            return send_from_directory(str(CWD), filename)
        abort(404)

    print(f"Serving at http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT)


def main():
    start_server()


if __name__ == "__main__":
    main()

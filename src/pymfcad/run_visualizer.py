import json
import importlib.util
import re
import tempfile
import uuid
import subprocess
from pathlib import Path
from urllib.parse import quote

from flask import Flask, jsonify, send_from_directory, abort, request, send_file, after_this_request

PORT = 8000
CWD = Path.cwd().resolve()

def start_server():
    env_dir = Path(__file__).resolve().parent
    site_root = (env_dir / "site").resolve()
    visualizer_root = (site_root / "visualizer").resolve()
    build_dir = (site_root / "dist").resolve()
    visualizer_dist_dir = (build_dir / "visualizer").resolve()
    serve_dir = visualizer_dist_dir if visualizer_dist_dir.is_dir() else visualizer_root
    static_dir = visualizer_root / "static"
    docs_dir = (site_root / "docs").resolve()

    app = Flask(__name__, static_folder=str(static_dir), static_url_path="/static")

    selected_preview_dir = None
    render_sessions = {}

    if not visualizer_root.is_dir():
        raise RuntimeError("Cannot find visualizer directory!")

    def get_glb_dir():
        if selected_preview_dir and selected_preview_dir.is_dir():
            return selected_preview_dir
        cwd_preview = CWD / "_visualization"
        if cwd_preview.is_dir():
            return cwd_preview

        default_dir = visualizer_root / "demo_device"
        if default_dir.is_dir():
            return default_dir

        return None

    def list_glb_files(preview_dir):
        glb_list = []
        for path in sorted(preview_dir.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file() and path.suffix.lower() == ".glb":
                stat = path.stat()
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
                    elif name.startswith("default_exposure_settings_"):
                        name = name[26:].capitalize()
                        name = name.replace("._default_", "").replace("_default_", "")
                        if name == "":
                            name = "Top-level"
                        type_str = "regional default exposure settings"
                    elif name.startswith("default_position_settings_"):
                        name = name[26:].capitalize()
                        name = name.replace("._default_", "").replace("_default_", "")
                        if name == "":
                            name = "Top-level"
                        type_str = "regional default position settings"
                    elif name.startswith("burnin_"):
                        name = name[7:].capitalize()
                        name = name.replace("._default_", "").replace("_default_", "")
                        if name == "":
                            name = "Top-level"
                        type_str = "regional burn-in settings"
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

                rel_path = path.resolve().relative_to(preview_dir).as_posix()
                file_url = f"/preview_file?path={quote(rel_path)}"

                glb_list.append(
                    {
                        "name": name,
                        "type": type_str,
                        "file": file_url,
                        "version": version,
                        "base_name": base_name,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                    }
                )

        return glb_list

    def list_settings_files(preview_dir):
        candidates = ["pymfcad-settings.json", "settings.json"]
        files = []
        for name in candidates:
            path = preview_dir / name
            if path.is_file():
                stat = path.stat()
                rel_path = path.resolve().relative_to(preview_dir).as_posix()
                files.append(
                    {
                        "name": path.name,
                        "path": rel_path,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                    }
                )
        return files

    @app.route("/")
    def index():
        return send_from_directory(str(serve_dir), "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(str(site_root), "static/favicon.ico")

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
        return send_from_directory(str(serve_dir), "main.js")

    @app.route("/assets/<path:subpath>")
    def visualizer_assets_dist(subpath):
        assets_dir = build_dir / "assets"
        if not assets_dir.is_dir():
            return abort(404)
        return send_from_directory(str(assets_dir), subpath)

    @app.route("/visualizer/<path:subpath>")
    def visualizer_assets(subpath):
        return send_from_directory(str(serve_dir), subpath)

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
        elif preview_dir == (CWD / "_visualization"):
            source = "cwd/_visualization"
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
        candidate = (preview_dir / rel_path).resolve()
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

    @app.route("/save_preview_settings", methods=["POST"])
    def save_preview_settings():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"error": "No preview directory"}), 404

        demo_dir = (visualizer_root / "demo_device").resolve()
        if preview_dir.resolve() == demo_dir:
            return jsonify({"error": "Demo device is read-only"}), 400

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid settings payload"}), 400

        output_path = preview_dir / "pymfcad-settings.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return jsonify({"ok": True, "path": str(output_path.resolve())})

    @app.route("/preview_file")
    def preview_file():
        preview_dir = get_glb_dir()
        if not preview_dir:
            return jsonify({"error": "No preview directory"}), 404
        rel_path = (request.args.get("path") or "").strip()
        if not rel_path:
            return jsonify({"error": "path required"}), 400
        candidate = (preview_dir / rel_path).resolve()
        try:
            candidate.relative_to(preview_dir)
        except ValueError:
            return jsonify({"error": "Path must be inside preview folder"}), 400
        if not candidate.is_file():
            return jsonify({"error": "File not found"}), 404
        return send_from_directory(str(preview_dir), rel_path)

    @app.route("/preview_dir_list")
    def preview_dir_list():
        raw_path = (request.args.get("path") or "").strip()
        if not raw_path:
            return jsonify({"error": "path required"}), 400

        base_dir = (Path(raw_path) if Path(raw_path).is_absolute() else (CWD / raw_path)).resolve()
        if not base_dir.is_dir():
            return jsonify({"error": "Folder does not exist"}), 400

        folders = []
        for entry in sorted(base_dir.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir():
                continue
            if any(entry.glob("*.glb")):
                folders.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                })

        return jsonify({"base": str(base_dir), "folders": folders})

    @app.route("/set_preview_dir", methods=["POST"])
    def set_preview_dir():
        nonlocal selected_preview_dir
        data = request.get_json(silent=True) or {}
        raw_path = (data.get("path") or "").strip()
        if not raw_path:
            selected_preview_dir = None
            return jsonify({"ok": True, "preview_dir": ""})

        candidate = (Path(raw_path) if Path(raw_path).is_absolute() else (CWD / raw_path)).resolve()

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

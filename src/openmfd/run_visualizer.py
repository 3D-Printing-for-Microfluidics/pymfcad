import json
import importlib.util
import re
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, abort, request

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
        for path in preview_dir.iterdir():
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

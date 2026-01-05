import http.server
import socketserver
import webbrowser
import os
import threading

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

import json


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/glb_list.json":
            # Directory containing .glb files
            glb_dir = os.path.join(DIRECTORY, "pymfd", "viewer", "device")
            try:
                files = [f for f in os.listdir(glb_dir) if f.lower().endswith(".glb")]
                # Return relative paths from the web root
                glb_list = []
                for f in files:
                    name = os.path.splitext(f)[0]
                    if name.startswith("bulk_"):
                        name = name[5:].capitalize()
                        type_str = "bulk"
                    elif name.startswith("void_"):
                        name = name[5:].capitalize()
                        type_str = "void"
                    elif name.startswith("regional_"):
                        name = name[9:]
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
                    elif name == "ports":
                        name = "Unconnected Ports"
                        type_str = "ports"
                    elif name == "device":
                        name = "Device"
                        type_str = "device"
                    elif name == "bounding_box":
                        name = "Bounding Box"
                        type_str = "bounding box"
                    glb_list.append(
                        {"name": name, "type": type_str, "file": f"./device/{f}"}
                    )

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(glb_list).encode("utf-8"))
        else:
            super().do_GET()


def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()


def open_browser():
    url = f"http://localhost:{PORT}/pymfd/viewer/index.html"
    webbrowser.open(url)


if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    open_browser()
    input("Press Enter to stop the server...\n")

#!/usr/bin/env python3
"""☽ Saint Charon — Drive Recovery Dashboard Server
Serves the recovery dashboard and provides action API endpoints
that SSH to a remote recovery server to control ddrescue/foremost/classify.

Configuration:
  SSH_HOST  — env var for the recovery server SSH host (default: zima)
  HTML_DIR  — env var for dashboard HTML directory (default: ~/Projects/narwal)
  PORT      — env var for HTTP port (default: 8765)
"""
import http.server, os, json, subprocess, shlex, urllib.parse

SSH_HOST  = os.environ.get("SSH_HOST", "zima")
HTML_DIR  = os.environ.get("HTML_DIR", os.path.expanduser("~/Projects/narwal"))
STATUS_FILE = "/tmp/status.json"
PORT = int(os.environ.get("PORT", "8765"))

def ssh_zima(cmd, timeout=15):
    result = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=5", SSH_HOST, cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HTML_DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == "/status.json" or self.path.startswith("/status.json?"):
            try:
                with open(STATUS_FILE) as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(data.encode())
            except FileNotFoundError:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(b'{"generated_at":"no data yet"}')
        elif self.path == "/api/classify-status":
            code, out, err = ssh_zima("bash /srv/photos/classify_status.sh")
            data = {}
            for line in out.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k] = v
            if data:
                self.json_response({"ok": True, "status": data})
            else:
                self.json_response({"ok": False, "error": f"No data: {err}"}, 500)
        elif self.path == "/" or self.path == "":
            self.send_response(302)
            self.send_header("Location", "/immich_jellyfin_migration_plan.html")
            self.end_headers()
        else:
            super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        try:    params = urllib.parse.parse_qs(body) if body else {}
        except: params = {}

        if self.path == "/api/start-migration":
            code1, dd_pid, _ = ssh_zima("pgrep -x ddrescue || echo none")
            code2, mg_pid, _ = ssh_zima("pgrep -f auto_migrate || echo none")
            acts = []
            if dd_pid and dd_pid != "none":
                c, o, e = ssh_zima(f"kill {dd_pid.strip()}")
                acts.append(f"Killed ddrescue PID {dd_pid.strip()}" if c == 0 else f"Kill failed: {e}")
            if not mg_pid or mg_pid == "none":
                c, o, e = ssh_zima("nohup bash /srv/photos/auto_migrate.sh >> /srv/photos/migration_output.log 2>&1 & echo PID:$!")
                acts.append(f"Started migration PID {o.replace('PID:','').strip()}" if c == 0 else f"Start failed: {e}")
            else:
                acts.append(f"Migration already running PID {mg_pid.strip()}")
            self.json_response({"ok": True, "actions": acts})

        elif self.path == "/api/new-drive":
            dev = params.get("device", [""])[0].strip()
            label = params.get("label", ["unknown"])[0].strip()
            if not dev or not dev.startswith("/dev/"):
                self.json_response({"ok": False, "error": "Invalid device path"}, 400); return
            code, out, _ = ssh_zima(f"test -b {shlex.quote(dev)} && echo OK || echo NO")
            if "OK" not in out:
                self.json_response({"ok": False, "error": f"Device {dev} not found"}, 400); return
            code, ex, _ = ssh_zima("pgrep -x ddrescue || echo none")
            if ex and ex != "none":
                self.json_response({"ok": False, "error": f"ddrescue already running PID {ex}"}, 409); return
            safe = label.replace(" ","_").replace("/","_")
            img = f"/srv/photos/{safe}_recovery.img"
            log = f"/srv/photos/{safe}_recovery.log"
            c, o, e = ssh_zima(f"nohup ddrescue -f -n {shlex.quote(dev)} {shlex.quote(img)} {shlex.quote(log)} > /dev/null 2>&1 & echo PID:$!")
            if c == 0 and "PID:" in o:
                self.json_response({"ok": True, "pid": o.replace("PID:","").strip(), "device": dev, "image": img, "log": log})
            else:
                self.json_response({"ok": False, "error": f"Failed: {o} {e}"}, 500)

        elif self.path == "/api/start-classify":
            src = params.get("source", ["/srv/photos/foremost_out"])[0]
            photo = params.get("photo", ["/srv/photos/external"])[0]
            review = params.get("review", ["/srv/photos/_review"])[0]
            # Check for exiftool (the actual worker) to avoid pgrep matching itself in fish
            code, ex, _ = ssh_zima("pgrep -x exiftool || echo none")
            if ex and ex != "none":
                self.json_response({"ok": False, "error": f"Classify already running (exiftool PID {ex})"}, 409)
                return
            safe_src = src.replace("'", "'\\''")
            safe_photo = photo.replace("'", "'\\''")
            safe_review = review.replace("'", "'\\''")
            c, o, e = ssh_zima(
                f"bash -c 'nohup bash /srv/photos/classify_media.sh "
                f"{safe_src} {safe_photo} {safe_review} "
                f">> /tmp/classify_nohup.log 2>&1 & echo PID:$!'"
            )
            if c == 0 and "PID:" in o:
                self.json_response({"ok": True, "pid": o.replace("PID:","").strip(),
                    "source": src, "photo_dest": photo, "review_dest": review})
            else:
                self.json_response({"ok": False, "error": f"Failed: {o} {e}"}, 500)

        elif self.path == "/api/classify-status":
            code, out, err = ssh_zima("bash /srv/photos/classify_status.sh")
            data = {}
            for line in out.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k] = v
            if data:
                self.json_response({"ok": True, "status": data})
            else:
                self.json_response({"ok": False, "error": f"No data: {err}"}, 500)

        elif self.path == "/api/status-check":
            _, d, _ = ssh_zima("pgrep -x ddrescue || echo none")
            _, m, _ = ssh_zima("pgrep -f auto_migrate || echo none")
            self.json_response({"ddrescue_running": d != "none", "migration_running": m != "none"})

        else:
            self.json_response({"error": "unknown endpoint"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

if __name__ == "__main__":
    os.system("fuser -k 8765/tcp 2>/dev/null || true")
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"✅ Recovery dashboard + API: http://localhost:{PORT}", flush=True)
    server.serve_forever()

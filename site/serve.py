"""Serve the Atlas Loan Lab UI in a browser, with live progress.

    python site/serve.py            # http://127.0.0.1:8765
    python site/serve.py --port 9000
    python site/serve.py --no-browser   # don't open a browser tab

Edit a file in atlas/ and save: the tests re-run and the page updates by itself.
"""
import argparse
import errno
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import labmodel
import progress

ROOT = labmodel.ROOT
WEB = Path(__file__).resolve().parent / "web"
WATCH = ["atlas", "prompts", "docs", "scripts", "CLAUDE.md", ".claude", ".mcp.json"]
TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}

# Editors that can jump to a line, in the order we look for them. ATLAS_EDITOR=cursor (etc.) picks one first.
EDITORS = {
    "code": ("VS Code", lambda f, n: ["-g", f"{f}:{n}"]),
    "cursor": ("Cursor", lambda f, n: ["-g", f"{f}:{n}"]),
    "subl": ("Sublime Text", lambda f, n: [f"{f}:{n}"]),
    "charm": ("PyCharm", lambda f, n: ["--line", str(n), f]),
}
TODO_RE = re.compile(r"TODO \(Lab \d|NotImplementedError")

MODEL = labmodel.build_model()
subscribers: list[queue.Queue] = []
lock = threading.Lock()
busy = threading.Lock()
pending = threading.Event()


def statuses(state: dict) -> dict:
    return {(n, lid): e["status"] for n, lab in state.get("labs", {}).items() for lid, e in lab["lessons"].items()} | \
           {(n, None): lab["status"] for n, lab in state.get("labs", {}).items()}


def changes(old: dict, new: dict) -> list[dict]:
    a, b = statuses(old), statuses(new)
    return [{"lab": int(n), "lesson": lid, "from": a.get((n, lid), "todo"), "to": s}
            for (n, lid), s in b.items() if a.get((n, lid), "todo") != s]


def publish(event: str, payload: dict) -> None:
    msg = f"event: {event}\ndata: {json.dumps(payload)}\n\n"
    with lock:
        for q in subscribers:
            q.put(msg)


def recheck(labs: list[int] | None = None) -> None:
    if not busy.acquire(blocking=False):
        pending.set()  # a run is in flight: re-check everything once it finishes, so no click is lost
        return
    try:
        old = progress.load_state()
        publish("running", {"labs": labs or [l["n"] for l in MODEL["labs"]]})
        new = progress.update(labs)
        publish("progress", {"progress": new, "changed": changes(old, new)})
    finally:
        publish("running", {"labs": []})
        busy.release()
    if pending.is_set():
        pending.clear()
        recheck()


def open_file(rel: str, line: int) -> dict:
    """Open a repo file in the learner's editor, at `line` or else at the first TODO."""
    target = (ROOT / rel).resolve()
    if ROOT not in target.parents or not target.is_file():
        return {"error": f"{rel} is not a file in this repo"}
    if not line:
        lines = target.read_text(errors="replace").splitlines()
        line = next((i for i, text in enumerate(lines, 1) if TODO_RE.search(text)), 1)
    where = f"{rel}:{line}"
    order = [os.environ.get("ATLAS_EDITOR", "")] + list(EDITORS)
    for exe in order:
        if exe in EDITORS and shutil.which(exe):
            name, args = EDITORS[exe]
            subprocess.Popen([exe, *args(str(target), line)])
            return {"opened": where, "app": name}
    opener = {"darwin": ["open"], "win32": ["cmd", "/c", "start", ""]}.get(sys.platform, ["xdg-open"])
    if shutil.which(opener[0]):
        subprocess.Popen([*opener, str(target)])
        return {"opened": rel, "app": "your default app", "hint": f"go to line {line}"}
    return {"error": f"No editor found. Open {where} yourself."}


def snapshot() -> dict:
    stamp = {}
    for name in WATCH:
        p = ROOT / name
        for f in ([p] if p.is_file() else p.rglob("*") if p.is_dir() else []):
            if f.is_file() and f.suffix in {".py", ".md", ".json", ".txt", ".yaml"} and "__pycache__" not in f.parts:
                stamp[str(f)] = f.stat().st_mtime
    return stamp


def watcher() -> None:
    before = snapshot()
    while True:
        time.sleep(1)
        now = snapshot()
        if now != before:
            time.sleep(0.8)  # let a burst of saves settle
            before = snapshot()
            recheck()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def trusted(self) -> bool:
        """Only this page may talk to the server: blocks other websites (Origin) and DNS rebinding (Host)."""
        port = self.server.server_address[1]
        ours = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        if self.headers.get("Host") not in ours or (origin and origin.removeprefix("http://") not in ours):
            self.send(b"forbidden", "text/plain", 403)
            return False
        return True

    def send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.trusted():
            return
        path = self.path.split("?")[0]
        if path == "/api/model":
            self.send(json.dumps(MODEL).encode(), "application/json")
        elif path == "/api/progress":
            self.send(json.dumps(progress.load_state()).encode(), "application/json")
        elif path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            q: queue.Queue = queue.Queue()
            with lock:
                subscribers.append(q)
            try:
                while True:
                    try:
                        self.wfile.write(q.get(timeout=15).encode())
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with lock:
                    subscribers.remove(q)
        else:
            name = "index.html" if path == "/" else path.removeprefix("/web/")
            f = (WEB / name).resolve()
            if WEB in f.parents and f.is_file():
                self.send(f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))
            else:
                self.send(b"not found", "text/plain", 404)

    def do_POST(self):
        if not self.trusted():
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        reply = {}
        if self.path == "/api/run":
            labs = [body["lab"]] if body.get("lab") and body.get("scope") != "all" else None
            threading.Thread(target=recheck, args=(labs,), daemon=True).start()
        elif self.path == "/api/open":
            reply = open_file(str(body.get("file", "")), int(body.get("line") or 0))
        self.send(json.dumps(reply).encode(), "application/json")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true", help="don't open the page in a browser")
    a = p.parse_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        sys.exit(f"Port {a.port} is already in use. The lab UI may already be running: open http://127.0.0.1:{a.port}\n"
                 f"Or start it on another port: python site/serve.py --port {a.port + 1}")
    url = f"http://127.0.0.1:{a.port}"
    print(f"Atlas Loan Lab UI: {url}  (Ctrl+C to stop)")
    if not progress.STATE.exists():
        print("First run: checking all labs (the page shows progress as they finish)...")
        threading.Thread(target=recheck, daemon=True).start()
    threading.Thread(target=watcher, daemon=True).start()
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

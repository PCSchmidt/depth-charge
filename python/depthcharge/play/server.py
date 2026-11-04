"""Local web server for the Depth Charge client (standard library only, bound to 127.0.0.1).

    python -m depthcharge.play.server [--port 8765]

    GET  /               the client
    GET  /api/state      current state
    POST /api/new        {"guided"?: bool, "archetype"?, "discipline"?: CWT|FIM|CNF|DYN, "depth"?, "distance"?, "lead"?, "seed"?}  -> state + ghost path
    POST /api/step       {"n": ticks, "change": {controls and pulses}}
    GET  /api/replay     controls log and digest (only after the dive has ended)
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .session import Session, new_session

STATIC = Path(__file__).parent / "static"


class App:
    def __init__(self):
        self.session: Session | None = None
        self.lock = threading.Lock()

    def handle(self, method: str, path: str, body: dict):
        with self.lock:
            if method == "GET" and path in ("/", "/index.html"):
                return 200, (STATIC / "index.html").read_text(encoding="utf-8"), "text/html; charset=utf-8"
            if method == "POST" and path == "/api/new":
                try:
                    self.session = new_session(str(body.get("archetype", "trained")), body.get("depth", 20.0), body.get("lead", 1.2),
                                               body.get("seed"), bool(body.get("guided", False)), str(body.get("discipline", "CWT")), body.get("distance", 75.0))
                except (ValueError, TypeError) as e:
                    return 400, {"error": str(e)}, "application/json"
                return 200, {**self.session.state(), "ghost": self.session.ghost}, "application/json"
            if self.session is None:
                return 409, {"error": "no dive: POST /api/new first"}, "application/json"
            s = self.session
            if method == "GET" and path == "/api/state":
                return 200, s.state(), "application/json"
            if method == "POST" and path == "/api/step":
                change = body.get("change")
                if change is not None and not isinstance(change, dict):
                    return 400, {"error": "change must be an object"}, "application/json"
                try:
                    s.step(int(body.get("n", 1)), change)
                except (ValueError, TypeError) as e:
                    return 400, {"error": str(e)}, "application/json"
                return 200, s.state(), "application/json"
            if method == "GET" and path == "/api/replay":
                try:
                    return 200, s.replay_json(), "application/json"
                except PermissionError as e:
                    return 403, {"error": str(e)}, "application/json"
            return 404, {"error": "not found"}, "application/json"


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _run(self, method: str) -> None:
            body: dict = {}
            if method == "POST":
                n = int(self.headers.get("Content-Length") or 0)
                if n > 100_000:
                    return self._send(413, {"error": "body too large"}, "application/json")
                try:
                    body = json.loads(self.rfile.read(n) or b"{}")
                except json.JSONDecodeError:
                    return self._send(400, {"error": "invalid JSON"}, "application/json")
                if not isinstance(body, dict):
                    return self._send(400, {"error": "body must be an object"}, "application/json")
            try:
                status, payload, ctype = app.handle(method, self.path.split("?")[0], body)
            except Exception as e:      # keep the server alive; report the failure
                status, payload, ctype = 500, {"error": f"{type(e).__name__}: {e}"}, "application/json"
            self._send(status, payload, ctype)

        def _send(self, status, payload, ctype) -> None:
            data = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            self._run("GET")

        def do_POST(self):  # noqa: N802
            self._run("POST")

        def log_message(self, *args):
            pass

    return Handler


def serve(port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(App()))


def main() -> None:
    ap = argparse.ArgumentParser(description="Depth Charge dive client (local)")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    srv = serve(args.port)
    print(f"Depth Charge client: http://127.0.0.1:{args.port}/  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

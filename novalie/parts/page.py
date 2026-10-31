# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's page server, in a process of its own."""
import http.server
import json
import os
import socket
import sys
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(os.path.dirname(HERE), "ui")
UI_TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
            ".json": "application/json"}
JSON = "application/json"
_UI = {}


def ui_file(name):
    """A file of its page (the folder ui), read again whenever it changes."""
    if not name or "/" in name or "\\" in name or name.startswith(".") or os.path.splitext(name)[1] not in UI_TYPES:
        return None
    path = os.path.join(UI_DIR, name)
    try:
        mtime = os.path.getmtime(path)
        if _UI.get(name, (None,))[0] != mtime:
            with open(path, encoding="utf-8") as f:
                _UI[name] = (mtime, f.read())
    except OSError:
        return None
    return _UI[name][1], UI_TYPES[os.path.splitext(name)[1]]


class Server(http.server.ThreadingHTTPServer):
    """Its page's server. One copy per port."""
    allow_reuse_address = False
    daemon_threads = True
    backend = None

    def handle_error(self, request, client_address):
        """A page closed or reloaded while it was answering."""
        e = sys.exc_info()[1]
        if isinstance(e, (ConnectionError, TimeoutError)):
            return
        print(f"[Novalie] its page server: {type(e).__name__}: {e}"[:200], flush=True)

    def server_bind(self):
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(http.server.BaseHTTPRequestHandler):
    """Its page and what the page asks for."""

    def log_message(self, *args):
        pass

    def guarded(self):
        """No other site may show its page inside theirs."""
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")

    def send(self, code, data, kind=JSON, extra=None):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.guarded()
        self.end_headers()
        self.wfile.write(data)

    def ours(self, action):
        bound = self.server.server_address[1]
        local = {f"127.0.0.1:{bound}", f"localhost:{bound}"}
        if self.server.server_address[0] == "127.0.0.1" and self.headers.get("Host", "") not in local:
            return False
        if not action:
            return True
        origin = self.headers.get("Origin")
        return self.headers.get("X-Novalie") == "1" and (origin is None or origin.split("//")[-1] in local)

    def where(self):
        u = urllib.parse.urlsplit(self.path)
        return u.path, {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

    def do_GET(self):
        if not self.ours(False):
            return self.send(403, "{}")
        path, query = self.where()
        if path in ("/", "/brain") or path.startswith("/ui/"):
            got = ui_file("index.html" if path in ("/", "/brain") else path[4:])
            if got is None:
                return self.send(404, "not found", "text/plain")
            return self.send(200, got[0], got[1])
        try:
            code, kind, data, extra = self.server.backend.get(path, query)
        except ConnectionError:
            return
        except Exception:
            return self.send(503, "{}")
        self.send(code, data, kind, extra)

    def do_POST(self):
        try:
            return self.post()
        except ConnectionError:
            return
        except Exception:
            try:
                return self.send(500, "{}")
            except OSError:
                return

    def post(self):
        try:
            size = max(0, int(self.headers.get("Content-Length", 0) or 0))
        except ValueError:
            return self.send(400, "{}")
        if not self.ours(True):
            self.rfile.read(min(size, 1_000_000))
            return self.send(403, "{}")
        if size > 64_000_000:
            return self.send(413, "{}")
        raw = self.rfile.read(size)
        path, query = self.where()
        code, kind, data, extra = self.server.backend.post(path, query, {"X-Name": self.headers.get("X-Name", "")}, raw)
        self.send(code, data, kind, extra)


def make_server(port, backend, host="127.0.0.1"):
    server = Server((host, port), Handler)
    server.backend = backend
    return server


class RemoteBackend:
    """The page's side of the bridge to its model."""
    ASKED_AHEAD = {"/graph", "/reading", "/worlds", "/knowledge", "/history", "/history?day"}

    def __init__(self, conn, on_end=None):
        self.conn = conn
        self.on_end = on_end or self.end
        self.send_lock = threading.Lock()
        self.waiting, self.next_id = {}, 0
        self.snap, self.live, self.talk = {}, None, None

    def start(self):
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        while True:
            try:
                msg = self.conn.recv()
            except (EOFError, OSError):
                return self.on_end()
            if msg[0] == "snap":
                key, reply = msg[1], msg[2]
                if reply[0] != 200:
                    continue
                if key in ("/live", "/poll"):
                    try:
                        value = json.loads(reply[2])
                    except ValueError:
                        continue
                    if key == "/live":
                        self.live = value
                    else:
                        self.talk = value
                else:
                    self.snap[key] = reply
            elif msg[0] == "reply":
                slot = self.waiting.pop(msg[1], None)
                if slot:
                    slot[1] = msg[2]
                    slot[0].set()

    @staticmethod
    def end():
        time.sleep(1)
        os._exit(0)

    def ask(self, method, path, query, headers, raw, timeout=30):
        slot = [threading.Event(), None]
        with self.send_lock:
            self.next_id += 1
            rid = self.next_id
            self.waiting[rid] = slot
            self.conn.send(("ask", rid, method, path, query, headers, raw))
        if not slot[0].wait(timeout):
            self.waiting.pop(rid, None)
            return 503, JSON, b"{}", {}
        return slot[1]

    @staticmethod
    def js(obj):
        return 200, JSON, json.dumps(obj, ensure_ascii=False).encode("utf-8"), {}

    def get(self, path, query):
        try:
            if path == "/live" and self.live is not None:
                since = int(query.get("since", "0") or 0)
                if self.live:
                    return self.js(dict(self.live, events=[e for e in self.live.get("events", ()) if e["id"] > since]))
                return self.js({})
            if path == "/poll" and self.talk is not None:
                since = max(0, int(query.get("since", "0") or 0))
                t = self.talk
                if not t:
                    return self.js({})
                msgs, count = t["messages"], t["count"]
                first = msgs[0]["id"] if msgs else count
                if since == 0:
                    since = max(0, count - 200)
                if since >= first or since >= count:
                    shown = [m for m in msgs if m["id"] >= since]
                    return self.js({"messages": shown, "next": since + len(shown), "count": count,
                                    "status": t["status"], "inbox": t["inbox"]})
        except ValueError:
            return 400, JSON, b"{}", {}
        key = path + ("?day" if path == "/history" and query.get("span") == "day" else "")
        if key in self.ASKED_AHEAD and key in self.snap:
            return self.snap[key]
        return self.ask("GET", path, query, {}, b"")

    def post(self, path, query, headers, raw):
        return self.ask("POST", path, query, headers, raw)


def page_main():
    """In its own process: connect to the model."""
    from multiprocessing.connection import Client
    bridge_port, first, last = (int(x) for x in sys.argv[1:4])
    host = sys.argv[4] if len(sys.argv) > 4 else "127.0.0.1"
    key = bytes.fromhex(sys.stdin.readline().strip())
    conn = Client(("127.0.0.1", bridge_port), authkey=key)
    backend = RemoteBackend(conn)
    server = None
    for port in range(first, last + 1):
        try:
            server = make_server(port, backend, host)
            break
        except OSError:
            continue
    conn.send(("port", server.server_address[1] if server else None))
    if server is None:
        return
    backend.start()
    server.serve_forever()


if __name__ == "__main__":
    page_main()

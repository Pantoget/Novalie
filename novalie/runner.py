# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its life, its page, and the program's start (python -m novalie)."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import webbrowser

from . import app, config, worlds
from .body import memory_load, memory_status
from .config import HERE, JSON
from .inventing import card_room_gb, free_memory_gb, stop_inventor
from .memory import erase_memory, load_memory
from .parts import council, inventor, workshop
from .parts.page import make_server
from .web import OFFLINE, READ_GATE


class Runner:
    def __init__(self):
        self.stop = threading.Event()
        self.switch_to = None
        self.erasing, self.erased = False, threading.Event()
        self.paused = threading.Event()
        self.offline = OFFLINE
        OFFLINE.clear()
        self.gentle = threading.Event()
        if os.path.exists(pace_file()):
            self.gentle.set()
        self.worked = 0.0
        self.model = load_memory()
        self.thread = threading.Thread(target=self.live, daemon=True)
        self.reader = threading.Thread(target=self.look, daemon=True)
        self.surfer = threading.Thread(target=self.surf, daemon=True)
        self.minds = threading.Thread(target=self.with_brains, daemon=True)
        self.council = None
        self.workshop = None
        self.last_browse = 0.0
        self.last_save = self.last_record = time.time()
        self.save_every = 60.0

    def quiet_trouble(self, where, e):
        """Something went wrong while answering its page."""
        now = time.time()
        if now - getattr(self, "_quiet_at", 0.0) > 60:
            self._quiet_at = now
            print(f"[Novalie] its {where}: {type(e).__name__}: {e}"[:200], flush=True)

    def trouble(self, where, e):
        """Something went wrong."""
        what = f"{type(e).__name__}: {e}"[:200]
        key, now = (where, what), time.time()
        seen = getattr(self, "_troubles", None)
        if seen is None:
            seen = self._troubles = {}
        last, quiet = seen.get(key, (0.0, 0))
        if now - last < 60:
            seen[key] = (last, quiet + 1)
            return
        seen[key] = (now, 0)
        more = f" (and {quiet} more times)" if quiet else ""
        tb = e.__traceback__
        while tb is not None and tb.tb_next is not None:
            tb = tb.tb_next
        at = f" [{os.path.basename(tb.tb_frame.f_code.co_filename)}:{tb.tb_lineno}]" if tb is not None else ""
        print(f"[Novalie] something went wrong in its {where}: {what}{more}{at}", flush=True)
        if self.model is not None:
            self.model.emit("trouble", where=where, what=what + more)

    def title(self, m):
        """Its window's title, seen in the taskbar."""
        if os.name != "nt" or not getattr(self, "show_title", False):
            return
        try:
            import ctypes
            h = m.history[-1] if m.history else {}
            state = " (paused)" if self.paused.is_set() else " (gentle)" if self.gentle.is_set() else ""
            ctypes.windll.kernel32.SetConsoleTitleW(
                f"Novalie{state} · {h.get('ideas', 0)} cells · {h.get('worlds', 0)} worlds · {h.get('words', 0)} words"
                f" · {h.get('meanings', 0)} meanings · {self.port_url}")
        except Exception:
            pass

    def pause(self, on):
        """Pause both of its lives."""
        if self.workshop is not None:
            self.workshop.mark("paused", on)
        if on and not self.paused.is_set():
            self.paused.set()
            if self.model is not None:
                try:
                    self.model.save()
                except Exception as e:
                    self.trouble("memory", e)
                self.last_save = time.time()
                self.model.emit("paused", on=True)
        elif not on and self.paused.is_set():
            self.paused.clear()
            if self.model is not None:
                self.model.emit("paused", on=False)

    def set_gentle(self, on):
        """Gently (about 60% of one processor core instead of all of it, learning more slowly) or at full speed."""
        (self.gentle.set if on else self.gentle.clear)()
        if self.workshop is not None:
            self.workshop.mark("gentle", on)
        try:
            if on:
                os.makedirs(config.STATE_DIR, exist_ok=True)
                with open(pace_file(), "w", encoding="utf-8") as f:
                    f.write("gentle\n")
            elif os.path.exists(pace_file()):
                os.remove(pace_file())
        except OSError:
            pass
        if self.model is not None:
            self.model.emit("gentle", on=on)

    def move(self, m, name):
        """Into the world chosen on its page: the real one, or one of the worlds folder."""
        self.switch_to = None
        try:
            if name == "real":
                m.go_real()
            else:
                READ_GATE.set()                       # (its reading goes on while it lives a world of the folder)
                m.enter(world=worlds.make(name, seed=int(time.time()) % 100_000))
            m.emit("moved", world=name)
        except Exception as e:
            self.trouble("world", e)

    def live(self):
        while not self.stop.is_set():
            m = self.model
            if m is None:
                return
            if self.paused.is_set():
                self.stop.wait(0.25)
                continue
            if self.switch_to is not None:            # (a world chosen on its page: it moves there now)
                self.move(m, self.switch_to)
            t0 = time.perf_counter()
            try:
                m.step()
            except Exception as e:
                self.trouble("world", e)
                try:
                    m.enter()
                except Exception as e2:
                    self.trouble("world", e2)
                    time.sleep(1)
            if self.gentle.is_set() and not getattr(m, "real", False):
                self.worked += time.perf_counter() - t0
                if self.worked > 0.05:
                    self.stop.wait(self.worked)
                    self.worked = 0.0
            now = time.time()
            if now - self.last_record > 10:
                self.last_record = now
                try:
                    m.record()
                except Exception as e:
                    self.trouble("world", e)
                if self.workshop is not None:
                    try:
                        self.workshop.take_in(m)
                        m.workshop_view = self.workshop.status
                    except Exception as e:
                        self.trouble("workshop", e)
                self.title(m)
            if now - self.last_save > self.save_every:
                try:
                    m.save()
                except Exception as e:
                    self.trouble("memory", e)
                self.last_save = time.time()
                try:
                    self.save_every = max(60.0, 15.0 * os.path.getsize(config.STATE_FILE) / 1e6)
                except OSError:
                    pass

    def look(self):
        """Its reading, in its own thread."""
        while not self.stop.is_set():
            m = self.model
            if m is None:
                return
            try:
                if self.paused.is_set():
                    self.stop.wait(0.5)
                    continue
                word, given = None, None
                online = not self.offline.is_set()
                with m.lock:
                    now = time.time()
                    for w in (m.queue if online else ()):
                        if m.retry_at.get(w, 0.0) <= now:
                            word = w
                            m.queue.remove(w)
                            break
                    if word is None and m.given:
                        given = m.given.pop(0)
                if word:
                    m.lookup(word)
                elif given:
                    with m.lock:
                        m.reading_now = given[0]
                    m.emit("reading", title=given[0], source="you")
                    m.read_any(given[1], allow=("pixels", "frames", "sound"), source="you · " + given[0], seeds=True)
                elif not m.look_inbox() and online:
                    if not READ_GATE.is_set():
                        self.stop.wait(0.25)
                    elif not m.browse():
                        self.stop.wait(5.0)
                elif not online:
                    with m.lock:
                        m.reading_now = ""
                    self.stop.wait(1.0)
            except Exception as e:
                self.trouble("reading", e)
                self.stop.wait(2.0)
            self.stop.wait(0.2)

    def surf(self):
        """Its reading of the open web, in its own thread beside its reading of the encyclopedia."""
        while not self.stop.is_set():
            m = self.model
            if m is None:
                return
            if self.paused.is_set() or self.offline.is_set() or not READ_GATE.is_set():
                self.stop.wait(0.25)
                continue
            try:
                read = m.read_web()
            except Exception as e:
                self.trouble("reading", e)
                self.stop.wait(2.0)
                continue
            self.stop.wait(0.2 if read else 0.5)

    def with_brains(self):
        """Its council, in a thread of its own."""
        told = 0.0
        while not self.stop.is_set():
            m = self.model
            link = getattr(m, "link", None) if m is not None else None
            if link is None:
                return
            try:
                if not link.place() and link.name != "Nova(1)":
                    self.stop.set()
                    m.save()
                    stop_inventor()
                    os._exit(0)
                lines = link.hear()
                if self.council is not None:
                    for line in lines:
                        if line.get("kind") == "status":
                            self.council.hear_status(line)
                m.learn_from_brains([x for x in lines if x.get("kind") != "status"])
                if time.time() - told >= 60:
                    told = time.time()
                    m.share_counts()
                    if self.council is not None:
                        self.council.tick(m)
                        m.council_view = self.council.view()
                    else:
                        link.tell("status", **m.brain_status())
            except Exception as e:
                self.trouble("brains", e)
            self.stop.wait(5.0)

    def sleep_and_exit(self):
        """Turned off from its page, keeping everything it learned."""
        time.sleep(0.3)
        self.stop.set()
        for t in (self.thread, self.reader):
            if t.is_alive() and t is not threading.current_thread():
                t.join(timeout=8)
        if self.council is not None:
            self.council.stop_all()
        if self.workshop is not None:
            self.workshop.stop(save=True)
        stop_inventor()
        if self.model is not None:
            try:
                self.model.save()
            except Exception as e:
                print(f"[Novalie] its memory could not be saved: {type(e).__name__}: {e}", flush=True)
        print("[Novalie] turned off from its page; it remembers everything it learned.", flush=True)
        os._exit(0)

    def wipe(self):
        """Stop completely and erase everything it learned."""
        self.erasing = True
        if self.council is not None:
            self.council.stop_all()
        if self.workshop is not None:
            self.workshop.stop()
        self.stop.set()
        m = self.model
        if m is not None:
            m.wiping = True
        for t in (self.thread, self.reader):
            if t.is_alive() and t is not threading.current_thread():
                t.join(timeout=8)
        self.model = None
        stop_inventor()
        gone = erase_memory()
        self.erased.set()
        return gone


def named(req):
    """A symbol and a word from its page."""
    sym, word = req.get("symbol"), req.get("word")
    sym = str(sym) if isinstance(sym, (str, int)) and not isinstance(sym, bool) else ""
    word = word.strip()[:80] if isinstance(word, str) else ""
    return sym[:40], word


def asked(raw):
    """What its page asked, as it sends it."""
    try:
        req = json.loads(raw.decode("utf-8") or "{}")
    except ValueError:
        return None
    return req if isinstance(req, dict) else None


def answer(runner, method, path, query, headers, raw):
    """All that its page asks of the model."""
    def js(code, obj):
        return code, JSON, json.dumps(obj, ensure_ascii=False).encode("utf-8"), {}

    m = runner.model
    try:
        if method == "GET":
            if m is None:
                return js(200, {})
            if path == "/graph":
                return js(200, m.graph())
            if path == "/reading":
                return js(200, m.reading_report())
            if path == "/history":
                return js(200, list(m.history_day) if query.get("span") == "day" else m.history[-720:])
            if path == "/worlds":
                return js(200, m.worlds())
            if path == "/find":
                return js(200, m.find(query.get("q", "")[:80]))
            if path == "/knowledge":
                return js(200, m.proven())
            if path in ("/knowledge.csv", "/history.csv"):
                what = "knowledge" if path == "/knowledge.csv" else "growth"
                data = (m.table() if what == "knowledge" else m.growth_table(query.get("span") == "day")).encode("utf-8")
                return 200, "text/csv", data, {
                    "Content-Disposition": f'attachment; filename="novalie-{what}-{time.strftime("%Y%m%d-%H%M%S")}.csv"'}
            if path == "/cell":
                return js(200, m.cell_info(query.get("id", "")))
            if path == "/world-list":
                return js(200, {"worlds": worlds.listing(), "now": getattr(m.world, "name", "real")})
            if path == "/live":
                since = int(query.get("since", "0") or 0)
                out = m.live(since)
                try:
                    size = os.path.getsize(config.STATE_FILE)
                except OSError:
                    size = 0
                out.update(paused=runner.paused.is_set(), offline=runner.offline.is_set(), memory=size,
                           gentle=runner.gentle.is_set(), saved=round(runner.last_save))
                return js(200, out)
            if path == "/poll":
                since = max(0, int(query.get("since", "0") or 0))
                with m.lock:
                    count = len(m.messages)
                    if since == 0:
                        since = max(0, count - 200)
                    msgs = m.messages[since:]
                return js(200, {"messages": msgs, "next": since + len(msgs), "count": count,
                                "status": m.status(), "inbox": config.INBOX})
            return js(404, {})
        if path == "/stop":
            gone = runner.wipe()
            print("[Novalie] stopped and erased everything it learned." if gone else
                  f"[Novalie] stopped; its memory folder could not be fully deleted: {config.STATE_DIR}", flush=True)
            threading.Thread(target=lambda: (time.sleep(0.5), erase_memory(), os._exit(0)), daemon=True).start()
            return js(200, {"erased": gone})
        if path == "/quit":
            threading.Thread(target=runner.sleep_and_exit, daemon=False, name="turning off").start()
            return js(200, {"saved": True})
        if m is None:
            return js(409, {})
        if path == "/say":
            text = raw.decode("utf-8", errors="replace").strip()[:2000]
            if text:
                m.say(text, who="me")
                m.hear(text)
            return js(200, {})
        req = asked(raw) if path in ("/name", "/unname", "/forget", "/pause", "/offline", "/gentle", "/world") else {}
        if req is None:
            return js(400, {})
        if path == "/name":
            sym, word = named(req)
            if sym and word:
                m.say(f"{sym} = {word}", who="me")
                m.name(sym, word)
            return js(200, {})
        if path == "/forget":
            sym, word = named(req)
            return js(200, {"done": bool(sym and word and m.forget_meaning(word, sym))})
        if path == "/unname":
            sym, word = named(req)
            return js(200, {"done": bool(sym and word and m.unname(sym, word))})
        if path == "/give":
            name = urllib.parse.unquote(headers.get("X-Name") or "file")[:120]
            with m.lock:
                if len(m.given) >= 20 or sum(len(d) for _, d in m.given) + len(raw) > 256_000_000:
                    return js(429, {})
                m.given.append((name, raw))
            m.emit("given", name=name, size=len(raw))
            return js(200, {})
        if path == "/world":                          # a world chosen on its page
            name = str((req or {}).get("name") or "")
            if name != "real" and name not in worlds.names():
                return js(400, {})
            runner.switch_to = name
            return js(200, {"world": name})
        if path in ("/pause", "/offline", "/gentle"):
            on = req.get("on") is True
            if path == "/pause":
                runner.pause(on)
            elif path == "/gentle":
                runner.set_gentle(on)
            else:
                (runner.offline.set if on else runner.offline.clear)()
                m.emit("offline", on=on)
            return js(200, {"on": on})
        if path == "/open-inbox":
            try:
                if os.name == "nt":
                    os.startfile(config.INBOX)
                else:
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", config.INBOX])
            except OSError:
                return js(500, {})
            return js(200, {})
        return js(404, {})
    except ValueError:
        return js(400, {})
    except Exception as e:
        runner.quiet_trouble("page", e)
        return js(503 if method == "GET" else 500, {})


class LocalBackend:
    """Its page served from the model's own process."""

    def __init__(self, runner):
        self.runner = runner

    def get(self, path, query):
        return answer(self.runner, "GET", path, query, {}, b"")

    def post(self, path, query, headers, raw):
        return answer(self.runner, "POST", path, query, headers, raw)


def serve(runner, port):
    """Its page, served from this process."""
    return make_server(port, LocalBackend(runner), config.PAGE_HOST)


def start_page(first, last):
    """Its page in a process of its own."""
    from multiprocessing.connection import Listener
    key = os.urandom(32)
    try:
        listener = Listener(("127.0.0.1", 0), authkey=key)
    except OSError:
        return None
    box = {}

    def accept():
        try:
            box["conn"] = listener.accept()
        except Exception:
            pass

    waiter = threading.Thread(target=accept, daemon=True)
    waiter.start()
    try:
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "parts", "page.py"), str(listener.address[1]),
                                 str(first), str(last), config.PAGE_HOST], stdin=subprocess.PIPE, cwd=HERE)
        proc.stdin.write(key.hex().encode("ascii") + b"\n")
        proc.stdin.close()
    except OSError:
        listener.close()
        return None
    waiter.join(20)
    conn, port = box.get("conn"), None
    try:
        if conn is not None and conn.poll(20):
            tag, port = conn.recv()
    except (EOFError, OSError, ValueError):
        port = None
    listener.close()
    if not port:
        try:
            proc.kill()
        except OSError:
            pass
        return None
    return proc, conn, port


def bridge(runner, conn):
    """The model's side of the bridge to its page's own process."""
    lock = threading.Lock()
    every = {"/live": 0.4, "/poll": 0.4, "/graph": 1.5, "/reading": 4.0, "/worlds": 4.0, "/knowledge": 6.0,
             "/history": 10.0, "/history?day": 60.0}
    last = dict.fromkeys(every, 0.0)

    def send(msg):
        with lock:
            conn.send(msg)

    def publish(key):
        last[key] = time.time()
        path, query = ("/history", {"span": "day"}) if key == "/history?day" else (key, {})
        try:
            send(("snap", key, answer(runner, "GET", path, query, {}, b"")))
        except (OSError, EOFError, ValueError):
            pass

    def handle(rid, method, path, query, headers, raw):
        reply = answer(runner, method, path, query, headers, raw)
        try:
            send(("reply", rid, reply))
        except (OSError, EOFError, ValueError):
            return
        if method == "POST":
            publish("/live")
            publish("/poll")

    while not runner.stop.is_set():
        try:
            if conn.poll(0.05):
                msg = conn.recv()
                if msg and msg[0] == "ask":
                    threading.Thread(target=handle, args=msg[1:], daemon=True).start()
        except (EOFError, OSError):
            return False
        now = time.time()
        for key, gap in every.items():
            if now - last[key] >= gap:
                publish(key)
    return True


def claim_memory():
    """Only one copy of it may live with one memory."""
    key = hashlib.sha1(os.path.abspath(config.STATE_DIR).lower().encode("utf-8")).hexdigest()[:16]
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.CreateMutexW.restype = ctypes.c_void_p
        handle = k32.CreateMutexW(None, False, "Local\\Novalie-" + key)
        if not handle or k32.GetLastError() == 183:
            if handle:
                k32.CloseHandle(ctypes.c_void_p(handle))
            return None
        return handle
    import fcntl
    path = os.path.join(tempfile.gettempdir(), f"novalie-{key}.lock")
    f = open(path, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def address_file():
    return os.path.join(config.STATE_DIR, "address.txt")


def pace_file():
    return os.path.join(config.STATE_DIR, "gentle.txt")


def already_running(port):
    """Is Novalie already answering on this port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/history", timeout=2) as r:
            return r.status == 200 and r.read(1) == b"["
    except Exception:
        return False


def on_close(runner):
    """When its window is closed, it saves what it knows first."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    handler_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    def handler(kind):
        if kind in (2, 5, 6) and runner.model is not None:
            runner.stop.set()
            stop_inventor()
            if runner.council is not None:
                runner.council.stop_all()
            if runner.workshop is not None:
                runner.workshop.mark("quit", True)
            try:
                runner.model.save()
            except Exception:
                pass
        return False

    runner.close_handler = handler_type(handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(runner.close_handler, True)


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print("python -m novalie [options]   (Start Novalie.bat passes its options on)\n"
              "  --port N          its page on port N (8765)\n"
              "  --state DIR       its memory folder (novalie_state, beside it)\n"
              "  --inbox DIR       the folder of files it reads (novalie_inbox, beside it)\n"
              "  --memory-gb G     the most memory it may hold (no ceiling)\n"
              "  --brains N        the most brains of its council at once (one per core)\n"
              "  --no-browser      no page opened\n"
              "  --headless S      run S seconds without a page\n"
              "  --host H          its page reachable at H (0.0.0.0: from other computers)\n"
              "  --gap S, --ignore-robots, --private-network, --page-mb M   how it reads the web")
        return
    if "--inbox" in sys.argv:
        config.INBOX = os.path.abspath(sys.argv[sys.argv.index("--inbox") + 1])
    if "--state" in sys.argv:
        config.STATE_DIR = os.path.abspath(sys.argv[sys.argv.index("--state") + 1])
        config.STATE_FILE = os.path.join(config.STATE_DIR, "brain.pkl")
    if "--workshop" in sys.argv:
        config.STATE_DIR = os.path.abspath(sys.argv[sys.argv.index("--workshop") + 1])
        config.STATE_FILE = os.path.join(config.STATE_DIR, "brain.pkl")
    if "--port" in sys.argv:
        config.PORT = int(sys.argv[sys.argv.index("--port") + 1])
    flag = lambda name, kind: kind(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else None
    got = memory_status()
    ceiling = flag("--memory-gb", float)
    if ceiling:
        inventor.limit_memory(ceiling)
        config.CEILING_GB = ceiling
    config.KEEP = max(1.0, (ceiling or (got[0] if got else 4.0)) / 2.0)
    config.GAP_FLOOR = flag("--gap", float) if "--gap" in sys.argv else config.GAP_FLOOR
    config.PAGE_BYTES = int(flag("--page-mb", float) * 1_000_000) if "--page-mb" in sys.argv else config.PAGE_BYTES
    config.PAGE_HOST = flag("--host", str) or config.PAGE_HOST
    config.OBEY_ROBOTS = "--ignore-robots" not in sys.argv
    config.PRIVATE_NETWORK = "--private-network" in sys.argv
    os.makedirs(config.INBOX, exist_ok=True)
    claim = claim_memory()
    if claim is None:
        url = None
        for _ in range(40):
            try:
                with open(address_file(), encoding="utf-8") as f:
                    url = f.read().strip()
                break
            except OSError:
                time.sleep(0.25)
        print(f"Novalie is already running with this memory: {url or config.STATE_DIR}")
        if url and "--no-browser" not in sys.argv and "--headless" not in sys.argv and "--workshop" not in sys.argv:
            webbrowser.open(url)
        return
    if "--workshop" in sys.argv:
        workshop.run(app)
        return
    if "--brain" in sys.argv:
        config.BRAIN = {"name": sys.argv[sys.argv.index("--brain") + 1],
                 "council": os.path.abspath(sys.argv[sys.argv.index("--council") + 1])}
        runner = Runner()
        runner.model.go_real()
        runner.model.link = council.Link(os.path.abspath(sys.argv[sys.argv.index("--council") + 1]),
                                         sys.argv[sys.argv.index("--brain") + 1])
        for t in (runner.thread, runner.reader, runner.surfer, runner.minds):
            t.start()
        try:
            while not runner.stop.is_set():
                runner.stop.wait(1.0)
        finally:
            runner.stop.set()
            stop_inventor()
            runner.model.save()
        return
    if "--headless" not in sys.argv and "--state" not in sys.argv and already_running(config.PORT):
        print(f"Novalie is already running: http://127.0.0.1:{config.PORT}")
        if "--no-browser" not in sys.argv:
            webbrowser.open(f"http://127.0.0.1:{config.PORT}")
        return
    runner = Runner()
    if runner.model is not None:
        runner.model.go_real()
    most = sys.argv[sys.argv.index("--brains") + 1] if "--brains" in sys.argv else "auto"
    most = max(1, os.cpu_count() or 1) if most == "auto" else max(1, int(most))
    promised = inventor.commit_gb()
    budget = ceiling or (promised[0] - inventor.reserve_gb(promised[0]) if promised else None)
    if most > 1 and runner.model is not None:
        folder = os.path.join(config.STATE_DIR, "council")
        runner.model.link = council.Link(folder, "Nova(1)")
        runner.council = council.Council(folder, config.PROGRAM, most,
                                         round(0.6 * budget, 2) if budget else None,
                                         memory_load, free_memory_gb, card_room_gb)
        runner.council.wake()
    if (runner.model is not None and "--no-workshop" not in sys.argv
            and ("--headless" not in sys.argv or "--with-workshop" in sys.argv)):
        passed = ["--memory-gb", f"{0.2 * budget:.2f}"] if budget else []
        runner.workshop = workshop.Workshop(config.PROGRAM, config.STATE_DIR, passed)
        runner.workshop.mark("paused", False)
        runner.workshop.mark("gentle", runner.gentle.is_set())
        runner.workshop.start()
    if "--headless" in sys.argv:
        seconds = float(sys.argv[sys.argv.index("--headless") + 1])
        runner.thread.start()
        runner.reader.start()
        runner.surfer.start()
        runner.minds.start()
        shown, t0 = 0, time.time()
        while time.time() - t0 < seconds:
            time.sleep(0.5)
            with runner.model.lock:
                new = runner.model.messages[shown:]
            for m in new:
                print(("> " if m["who"] == "me" else "< ") + m["text"], flush=True)
            shown += len(new)
        runner.stop.set()
        runner.thread.join(timeout=10)
        if runner.council is not None:
            runner.council.stop_all()
        if runner.workshop is not None:
            runner.workshop.stop()
        runner.model.save()
        print("status:", json.dumps(runner.model.status(), ensure_ascii=False))
        return
    server, page = None, None
    if "--one-process" not in sys.argv:
        page = start_page(config.PORT, config.PORT + 9)
    if page:
        port = page[2]
    else:
        for port in range(config.PORT, config.PORT + 10):
            try:
                server = serve(runner, port)
                break
            except OSError:
                continue
        if server is None:
            print("No free port between", config.PORT, "and", config.PORT + 9)
            return
    url = f"http://{'127.0.0.1' if config.PAGE_HOST in ('0.0.0.0', '::') else config.PAGE_HOST}:{port}"
    runner.show_title, runner.port_url = True, url
    try:
        os.makedirs(config.STATE_DIR, exist_ok=True)
        with open(address_file(), "w", encoding="utf-8") as f:
            f.write(url)
    except OSError:
        pass
    runner.thread.start()
    runner.reader.start()
    runner.surfer.start()
    runner.minds.start()
    on_close(runner)
    print(f"""
  Novalie is running:  {url}

  - To turn it off and keep everything it learned: the Turn off button on its page, or close this window.
  - The red Erase everything button on its page stops it and erases everything it learned.
  - Put any file here for it to read (a file of links is where its reading on the web begins):
    {config.INBOX}
""", flush=True)
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    try:
        if page and bridge(runner, page[1]) and runner.erasing:
            runner.erased.wait(60)
            time.sleep(1.0)
            os._exit(0)
        if page and not runner.stop.is_set():
            print("[Novalie] its page's own process ended; its page is served from this window now.", flush=True)
            for _ in range(20):
                try:
                    server = serve(runner, port)
                    break
                except OSError:
                    time.sleep(0.25)
        if server is not None:
            server.serve_forever()
    except KeyboardInterrupt:
        runner.stop.set()
        runner.thread.join(timeout=10)
        stop_inventor()
        if runner.council is not None:
            runner.council.stop_all()
        if runner.workshop is not None:
            runner.workshop.stop()
        if runner.model is not None:
            runner.model.save()

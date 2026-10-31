# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's council: more than one brain, when it wants them, named Nova(1), Nova(2), and so on."""
import json
import os
import subprocess
import sys
import threading
import time
import zlib

TEACH = ("way_trusted", "meaning")
BRAIN_GB = 2.0
BRAIN_CARD_GB = 0.25
PASSED = ("--ignore-robots", "--private-network")
PASSED_VALUE = ("--gap", "--page-mb")


def owner(host, living):
    """The brain whose share of the web a site is."""
    if not living:
        return None
    h = (host or "").encode("utf-8")
    return max(living, key=lambda name: (zlib.crc32(name.encode("utf-8") + b"|" + h), name))


def page_key(url):
    """A page as the council remembers that one of its brains read it."""
    return zlib.crc32((url or "").encode("utf-8"))


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    """Written beside the old one first, then put in its place."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    for _ in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.1)


def read_new(path, offset):
    """The lines of a book written since offset."""
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return [], offset
    end = data.rfind(b"\n") + 1
    lines = []
    for raw in data[:end].split(b"\n"):
        if raw.strip():
            try:
                lines.append(json.loads(raw.decode("utf-8")))
            except ValueError:
                pass
    return lines, offset + end


class Link:
    """A brain's place in its council."""

    def __init__(self, folder, name):
        self.folder, self.name = folder, name
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, f"{name}.jsonl")
        self.lock = threading.Lock()
        self.offsets, self.living = {}, [name]
        self.counts, self.counts_at = {}, {}
        self.place()

    def place(self):
        """Where it stands now: the brains alive."""
        living = read_json(os.path.join(self.folder, "council.json"), {}).get("living") or [self.name]
        if self.name in living:
            self.living = list(living)
            return True
        return False

    @property
    def n(self):
        return len(self.living)

    def mine(self, host):
        return len(self.living) <= 1 or owner(host, self.living) == self.name

    def tell(self, kind, **data):
        line = dict(data, kind=kind, by=self.name, t=round(time.time(), 1))
        with self.lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")

    def hear(self):
        """What the other brains said since it last looked."""
        out = []
        try:
            names = sorted(os.listdir(self.folder))
        except OSError:
            return out
        for f in names:
            if f.endswith(".jsonl") and f != os.path.basename(self.path):
                lines, self.offsets[f] = read_new(os.path.join(self.folder, f), self.offsets.get(f, 0))
                out += lines
        return out

    def publish(self, counts):
        """Its own counts, for the others to weigh with theirs."""
        write_json(os.path.join(self.folder, f"{self.name}.counts.json"), counts)

    def pooled(self):
        """The counts of every other brain, alive or gone."""
        changed = set()
        try:
            names = os.listdir(self.folder)
        except OSError:
            return self.counts, changed
        mine = f"{self.name}.counts.json"
        for f in names:
            if not f.endswith(".counts.json") or f == mine:
                continue
            path = os.path.join(self.folder, f)
            try:
                at = os.path.getmtime(path)
            except OSError:
                continue
            if self.counts_at.get(f) == at:
                continue
            data = read_json(path, None)
            if not isinstance(data, dict):
                continue
            brain = f[:-len(".counts.json")]
            old, new = self.counts.get(brain, {}), data.get("met") or {}
            changed |= {w for w in set(old) | set(new) if old.get(w) != new.get(w)}
            self.counts[brain], self.counts_at[f] = new, at
        return self.counts, changed


class Council:
    """Nova(1)'s council (see the top of this file)."""

    def __init__(self, folder, program, most, memory_gb, memory_load, free_memory_gb, card_room_gb=None):
        self.folder, self.program, self.most, self.memory_gb = folder, program, most, memory_gb
        self.memory_load, self.free_memory_gb = memory_load, free_memory_gb
        self.card_room_gb = card_room_gb or (lambda: None)
        os.makedirs(folder, exist_ok=True)
        self.file = os.path.join(folder, "council.json")
        self.state = read_json(self.file, {"made": 1, "living": ["Nova(1)"], "born": {}, "gone": []})
        self.state.setdefault("born", {})
        self.state.setdefault("waiting_then", 0)
        self.state["born"].setdefault("Nova(1)", round(time.time()))
        self.status, self.heard, self.procs, self.lock = {}, {}, {}, threading.Lock()
        write_json(self.file, self.state)

    def hear_status(self, line):
        """What a brain said of itself."""
        name = line.get("by")
        self.status[name], self.heard[name] = line, self.heard.get(name, 0) + 1

    def share_gb(self):
        """The memory each brain may hold."""
        return max(0.5, self.memory_gb / max(1, self.most)) if self.memory_gb else None

    def start(self, name):
        """A brain's process, started."""
        args = sys.argv[1:]
        cmd = [sys.executable, self.program, "--brain", name, "--council", self.folder,
               "--state", os.path.join(self.folder, name), "--no-browser"] + [a for a in args if a in PASSED]
        cmd += [x for i, a in enumerate(args[:-1]) if a in PASSED_VALUE for x in (a, args[i + 1])]
        if self.share_gb():
            cmd += ["--memory-gb", f"{self.share_gb():.2f}"]
        log = open(os.path.join(self.folder, f"{name}.log"), "a", encoding="utf-8")
        env = dict(os.environ, NOVALIE_GPU="0")
        self.procs[name] = subprocess.Popen(cmd, stdout=log, stderr=log, stdin=subprocess.DEVNULL, env=env,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def wake(self):
        """Nova(1) starts again."""
        for name in self.state["living"]:
            if name != "Nova(1)" and name not in self.procs:
                self.start(name)

    def make(self, model, why):
        with self.lock:
            self.state["made"] += 1
            name = f"Nova({self.state['made']})"
            self.state["living"].append(name)
            self.state["born"][name] = round(time.time())
            write_json(self.file, self.state)
        self.start(name)
        model.emit("brain_made", name=name, why=why, living=len(self.state["living"]))
        model.decide("brain_made", name, dict(why, living=list(self.state["living"])))
        return name

    def cancel(self, model, name, why):
        with self.lock:
            if name not in self.state["living"] or name == "Nova(1)":
                return
            self.state["living"].remove(name)
            self.state["gone"].append({"name": name, "at": round(time.time()), "why": why})
            write_json(self.file, self.state)
        p = self.procs.pop(name, None)
        if p is not None:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        model.emit("brain_gone", name=name, why=why, living=len(self.state["living"]))
        model.decide("brain_gone", name, dict(why, living=list(self.state["living"])))

    def stop_all(self):
        """Every brain but Nova(1) stops."""
        for name, p in list(self.procs.items()):
            p.terminate()
        for name, p in list(self.procs.items()):
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        self.procs.clear()

    def tick(self, model):
        """Once a minute, in Nova(1)."""
        now = time.time()
        for name, p in list(self.procs.items()):
            if p.poll() is not None and name in self.state["living"]:
                self.procs.pop(name)
                self.cancel(model, name, {"code": "ended", "exit": p.returncode})
        self.status["Nova(1)"] = model.brain_status()
        living = list(self.state["living"])
        free, card = self.free_memory_gb(), self.card_room_gb()
        short_card = card is not None and card < -BRAIN_CARD_GB
        if (self.memory_load() >= 90 or free < 0 or short_card) and len(living) > 1:
            self.cancel(model, living[-1], {"code": "memory", "load": self.memory_load(),
                                            "room_gb": round(free, 1),
                                            "card_gb": None if card is None else round(card, 2)})
            return
        first = (self.status["Nova(1)"].get("first_page") or 0) - self.state["born"]["Nova(1)"]
        trial = 2 * first if first > 0 else None
        for name in living[1:]:
            st = self.status.get(name) or {}
            if trial is not None and st.get("up", 0) > trial and self.heard.get(name, 0) >= 2 and not st.get("pages", 0):
                self.cancel(model, name, {"code": "idle", "age": round(st.get("up", 0)), "trial": round(trial)})
                return
        waiting = sum((self.status.get(n) or {}).get("waiting", 0) for n in living)
        last = living[-1]
        st = self.status.get(last) or {}
        useful = last == "Nova(1)" or (st.get("pages", 0) > 0 and st.get("proved", 0) > 0)
        room = (len(living) < self.most and self.memory_load() < 80 and free >= BRAIN_GB
                and (card is None or card >= BRAIN_CARD_GB)
                and (self.share_gb() is None or free > self.share_gb()))
        if room and useful and trial is not None and waiting > self.state.get("waiting_then", 0):
            then = self.state.get("waiting_then", 0)
            self.state["waiting_then"] = waiting
            self.make(model, {"code": "work", "waiting": waiting, "then": then, "who": last})

    def view(self):
        """For its page: the brains, alive and gone, and what each said of itself."""
        out = []
        for name in self.state["living"]:
            st = self.status.get(name) or {}
            out.append({"name": name, "born": self.state["born"].get(name), "alive": True,
                        **{k: st.get(k) for k in ("pages", "sites", "ways", "trusted", "meanings", "words", "proved",
                                                  "waiting", "pooled", "code", "at")}})
        return out + [{"name": g["name"], "alive": False, "gone": g["at"], "why": g["why"]} for g in self.state["gone"][-10:]]

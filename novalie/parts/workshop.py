# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's workshop: a place of its own where it works as fast as its computer allows, not at the pace of its clock."""
import json
import os
import pickle
import random
import subprocess
import sys
import threading
import time

from . import invent as invent

SYMBOLS = [chr(c) for c in list(range(0x0391, 0x03AA)) + list(range(0x0410, 0x0430)) + list(range(0x05D0, 0x05EB))]
WAIT_AT_MOST = 180


class MadeWorld:
    """A world of its own making."""

    def __init__(self, k, level):
        rng = random.Random(f"novalie workshop {k}")
        self.k, self.level, self.name, self.jumped = k, level, f"workshop {k}", False
        self.factors, self.dims, self.machine = [], [], None
        parts = min(6, 1 + (level - 1) // 4)
        top = 4 + 3 * level
        kinds = []
        for i in range(parts):
            pick = rng.random()
            if level >= 10 and pick < 0.12:
                kinds.append(("free",))
            elif level >= 6 and pick < 0.3:
                kinds.append(("bit",))
            elif level >= 4 and pick < 0.55:
                kinds.append(("walls", rng.randint(3, max(3, min(top, 24)))))
            else:
                kinds.append(("cycle", rng.randint(3, max(3, min(top, 60)))))
        self.kinds, self.pile_on = tuple(kinds), level >= 8 and rng.random() < 0.3
        ops = []
        for i, kd in enumerate(kinds):
            if kd[0] == "bit":
                ops.append(("flip", i))
            elif kd[0] == "walls":
                ops += [("add", i, 1), ("add", i, -1)]
            else:
                ops.append(("add", i, 1))
                if level >= 3 and rng.random() < 0.5:
                    ops.append(("add", i, -1 if rng.random() < 0.6 else rng.randint(2, 4)))
        cyc = [i for i, kd in enumerate(kinds) if kd[0] == "cycle"]
        if level >= 5 and len(cyc) >= 2 and rng.random() < 0.5:
            a, b = cyc[0], cyc[1]
            ops[ops.index(("add", a, 1))] = ("carry", a, b, 1)
        if self.pile_on:
            ops += [("put", "a"), ("put", "b"), ("take",)]
        self.ops = ops
        self.buttons = [(f"b{i}", 1, i) for i in range(len(ops))]
        self.views = [("value", i) for i in range(parts)]
        if self.pile_on:
            self.views.append(("top",))
        self.tables = []
        for v in self.views:
            n = self.kinds[v[1]][1] if v[0] == "value" and len(self.kinds[v[1]]) > 1 else 3
            letters = rng.sample(SYMBOLS, min(len(SYMBOLS), max(2, n)))
            alias = level >= 7 and rng.random() < 0.3 and n >= 6
            self.tables.append([letters[(x % (n // 2)) if alias else x % len(letters)] for x in range(max(2, n))])
        self.chance = level >= 3 and rng.random() < 0.35
        self.sensors = [("view", str(v[0]), None) for v in self.views] + ([("chance", "lamp", None)] if self.chance else [])
        size = 1
        for kd in kinds:
            size *= kd[1] if len(kd) > 1 else (2 if kd[0] == "bit" else 64)
        self.size = size * (8 if self.pile_on else 1)
        self.regs = tuple(rng.randrange(kd[1]) if len(kd) > 1 else 0 for kd in kinds)
        self.pile, self.lamp, self.draw = (), 0, random.Random(f"novalie workshop chance {k}")
        more = random.Random(f"novalie workshop new parts {k}")
        nums = [i for i, kd in enumerate(kinds) if kd[0] != "bit"]
        if level >= 6 and len(nums) >= 2:
            a, b = nums[0], nums[1]
            if kinds[a] == kinds[b] and more.random() < 0.4:
                self.ops.append(("swap", a, b))
                self.buttons = [(f"b{i}", 1, i) for i in range(len(self.ops))]
            if more.random() < 0.4:
                self.views.append(("cmp", a, b))
                self.tables.append(more.sample(SYMBOLS, 3))
                self.sensors.insert(len(self.views) - 1, ("view", "cmp", None))

    @property
    def state(self):
        return [self.regs, self.pile, self.lamp]

    def press(self, a):
        self.regs, self.pile = invent.act(self.ops[a], self.kinds, self.regs, self.pile)
        if len(self.pile) > 12:
            self.pile = self.pile[-12:]
        self.lamp = int(self.draw.random() < 0.3)

    def observe(self):
        out = []
        for v, table in zip(self.views, self.tables):
            if v[0] == "top":
                out.append(table[0] if not self.pile else table[1 + (self.pile[-1] == "b")])
            elif v[0] == "cmp":
                out.append(table[invent.see(v, self.regs, self.pile) + 1])
            else:
                x = self.regs[v[1]]
                out.append(table[x % len(table)] if x is not None else table[0])
        if self.chance:
            out.append(self.lamp)
        return tuple(out)

    def describe(self):
        """What this world is made of, for its page."""
        return {"kinds": [list(k) for k in self.kinds], "pile": self.pile_on, "ops": [list(map(str, o)) for o in self.ops],
                "chance": self.chance, "size": self.size, "level": self.level}


def budget(world):
    """How many acts it gives a world before it moves on."""
    return int(min(200_000, max(2000, 40 * min(world.size, 5000))))


TRIAL_EVERY = 4


class Stop(Exception):
    """Its life ended, or it is turned off keeping everything."""


def run(app):
    """The workshop's own life."""
    folder = app.STATE_DIR
    os.makedirs(folder, exist_ok=True)
    parent = int(os.environ.get("NOVALIE_PARENT", "0") or 0)
    m = app.load_memory() or app.Novalie()
    ws = m.__dict__.setdefault("workshop", {"k": 0, "level": 1, "worlds": [], "acts": 0, "understood": 0})
    m.real = False
    clock = {"save": time.time(), "teach": time.time()}
    ws["begun"] = (time.time(), m.steps)
    try:
        while True:
            ws["k"] += 1
            trial = ws["k"] % TRIAL_EVERY == 0
            before = None
            if trial:
                with m.lock:
                    held = {k: m.__dict__.pop(k) for k in ("learners", "concepts", "trap_log") if k in m.__dict__}
                    try:
                        before = pickle.dumps(m)
                    finally:
                        m.__dict__.update(held)
            world = MadeWorld(ws["k"], ws["level"])
            m.enter(world=world)
            m.decide("workshop", world.name, world.describe())
            limit, t0, acts0 = budget(world), time.time(), m.steps
            ok, acts, waited = live_world(m, world, limit, folder, parent, clock, t0, acts0, own=True)
            quick = ok and acts < limit / 4
            ws["acts"] += acts
            ws["understood"] += ok
            ws["worlds"] = (ws["worlds"] + [{"k": world.k, "level": world.level, "ok": ok, "acts": acts,
                                             "s": round(time.time() - t0, 1), "thought": round(waited, 1),
                                             "made": world.describe()}])[-40:]
            ws["level"] = ws["level"] + 1 if quick else ws["level"] if ok else max(1, ws["level"] - 1)
            m.judge_ways(ok)
            if trial:
                lab(app, m, before, world, ok, acts, limit, folder, parent, clock)
            teach(m, folder, world, t0, acts0)
    except Stop:
        m.save()


def live_world(m, world, limit, folder, parent, clock, t0, acts0, own):
    """One world lived until it is understood or its acts are spent."""
    end, thinking, waited = limit, None, 0.0
    while not m.__dict__.get("_understood_here"):
        job = m.__dict__.get("_inventing")
        if job is not None and thinking is None:
            thinking = time.time()
        elif job is None and thinking is not None:
            waited += time.time() - thinking
            thinking, end = None, max(end, m.world_steps + limit // 2)
        settle = m.__dict__.get("_settle")
        if settle and settle[2] == m.k:
            end = max(end, min(2 * settle[0] + 1, 4 * limit))
        if m.world_steps >= end and (job is None or time.time() - thinking > WAIT_AT_MOST):
            break
        if os.path.exists(os.path.join(folder, "paused")):
            if os.path.exists(os.path.join(folder, "quit")):
                raise Stop()
            time.sleep(0.5)
            continue
        m.step()
        if m.world_steps % 200 == 0:
            if (parent and not alive(parent)) or os.path.exists(os.path.join(folder, "quit")):
                raise Stop()
            if os.path.exists(os.path.join(folder, "gentle")):
                time.sleep(0.02)
            if own and time.time() - clock["teach"] > 5:
                clock["teach"] = time.time()
                teach(m, folder, world, t0, acts0)
            if own and time.time() - clock["save"] > 60:
                clock["save"] = time.time()
                m.save()
    return bool(m.__dict__.get("_understood_here")), m.world_steps, waited


def lab(app, m, before, world, ok, acts, limit, folder, parent, clock):
    """Its laboratory of itself."""
    changes = [(g, v) for g, values in app.GENES.items() for v in values if v != m.gene(g)]
    if not changes or before is None:
        return
    trials = m.__dict__.get("gene_trials") or {}
    tried = lambda gv: (trials.get(f"{gv[0]}={gv[1]}") or [0, 0, 0])[-1]
    gene, value = min(changes, key=lambda gv: (tried(gv), changes.index(gv)))
    twin = pickle.loads(before)
    twin.real = False
    twin._gene_trial = {gene: value}
    again = MadeWorld(world.k, world.level)
    twin.enter(world=again)
    t0 = time.time()
    ok2, acts2, _ = live_world(twin, again, limit, folder, parent, clock, t0, twin.steps, own=False)
    better = (ok2 and not ok) or (ok2 and ok and acts2 < 0.8 * acts)
    worse = (ok and not ok2) or (ok and ok2 and acts < 0.8 * acts2)
    m.gene_result(gene, value, better, worse)
    m.__dict__.setdefault("lab_log", []).append({"k": world.k, "gene": gene, "value": str(value), "as_is": acts,
                                                "ok": ok, "changed": acts2, "ok2": ok2, "s": round(time.time() - t0, 1)})
    del m.lab_log[:-40]


def alive(pid):
    """Is the process pid still alive."""
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def teach(m, folder, world, t0, acts0):
    """What its workshop learned, written for its life in the real world to take in."""
    ws = m.__dict__.get("workshop") or {}
    secs = max(1e-6, time.time() - t0)
    begun = ws.get("begun") or (t0, acts0)
    card = None
    gpu = sys.modules.get("novalie_gpu")
    if gpu is not None:
        card = gpu.describe(ask=False)
    inventor_card = m.__dict__.get("inventor_card")
    data = {"t": round(time.time(), 1),
            "library": [{"d": e["d"], "T": [str(x) for x in e["T"]], "S": list(e["S"])} for e in m.library],
            "lengths": sorted({x for k in m.kinds_seen for x in set(k[1]) | {k_prod(k)}}),
            "kinds": [[k[0], list(k[1]), n] for k, n in m.kinds_seen.items()],
            "inventions": [e.get("name") for e in m.inventions],
            "shapes": [[repr(s), sorted(v.get("worlds", ())), v.get("n", 0)] for s, v in (m.__dict__.get("law_shapes") or {}).items()],
            "eps": m.eps,
            "status": {"world": world.k, "level": world.level, "made": world.describe(), "worlds": ws.get("k", 0),
                       "understood": ws.get("understood", 0), "acts": ws.get("acts", 0) + m.world_steps,
                       "now": m.world_steps, "per_second": round((m.steps - acts0) / secs, 1),
                       "pace": round((m.steps - begun[1]) / max(1e-6, time.time() - begun[0]), 1),
                       "recent": ws.get("worlds", [])[-8:], "card": card, "inventor_card": inventor_card,
                       "space": space_of(m)},
            "genome": {g: v for g, v in (m.__dict__.get("genome") or {}).items()},
            "gene_changes": list(m.__dict__.get("gene_changes") or ())[-20:],
            "gene_trials": dict(m.__dict__.get("gene_trials") or {}),
            "lab": list(m.__dict__.get("lab_log") or ())[-12:]}
    path = os.path.join(folder, "teach.json")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        os.replace(tmp, path)
    except OSError:
        pass


def space_of(m):
    """The space of the world it is in, as its laws see it."""
    try:
        return m.space()
    except Exception:
        return None


def k_prod(kind):
    p = 1
    for x in kind[1]:
        p *= x
    return p


class Workshop:
    """Its workshop seen from its life in the real world."""

    def __init__(self, program, state_dir, passed=()):
        self.folder = os.path.join(state_dir, "workshop")
        self.program, self.passed, self.proc, self.seen_at = program, list(passed), None, 0.0
        self.status = None

    def start(self):
        os.makedirs(self.folder, exist_ok=True)
        self.mark("quit", False)
        env = dict(os.environ, NOVALIE_PARENT=str(os.getpid()))
        self.log = open(os.path.join(self.folder, "workshop.log"), "a", encoding="utf-8")
        self.proc = subprocess.Popen([sys.executable, self.program, "--workshop", self.folder] + self.passed,
                                     stdout=self.log, stderr=self.log, stdin=subprocess.DEVNULL, env=env,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def stop(self, save=False):
        """Its workshop stopped."""
        p, self.proc = self.proc, None
        if p is not None and save:
            self.mark("quit", True)
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                pass
            self.mark("quit", False)
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=10)
        log, self.log = getattr(self, "log", None), None
        if log is not None:
            log.close()

    def mark(self, name, on):
        """Its pace as its life's."""
        path = os.path.join(self.folder, name)
        try:
            if on:
                os.makedirs(self.folder, exist_ok=True)
                open(path, "w").close()
            elif os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    def take_in(self, m):
        """What its workshop learned since it last looked, taken in by its life in the real world."""
        path = os.path.join(self.folder, "teach.json")
        try:
            at = os.path.getmtime(path)
        except OSError:
            return False
        if at == self.seen_at:
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        self.seen_at, self.status = at, data.get("status")
        got = 0
        with m.lock:
            have = {(e["d"], tuple(map(str, e["T"])), tuple(e["S"])) for e in m.library}
            for e in data.get("library") or ():
                key = (e["d"], tuple(e["T"]), tuple(e["S"]))
                if key not in have:
                    m.library.append({"d": e["d"], "T": tuple(e["T"]), "S": tuple(e["S"])})
                    got += 1
            for kind, cycles, n in data.get("kinds") or ():
                key = (kind, tuple(cycles))
                if key not in m.kinds_seen:
                    m.kinds_seen[key] = 0
                    got += 1
            m.__dict__.setdefault("from_workshop", {})["kinds"] = len(data.get("kinds") or ())
            genome = data.get("genome") or {}
            if genome and genome != (m.__dict__.get("genome") or {}):
                m.genome = dict(genome)
                m.emit("self_adopted", genome={g: str(v) for g, v in genome.items()})
            m.lab_view = {"genome": genome, "changes": data.get("gene_changes") or [], "trials": data.get("gene_trials") or {},
                          "lab": data.get("lab") or []}
        if got:
            m.emit("workshop_taught", kinds=got)
        return bool(got)

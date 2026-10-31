# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie: kinds of things it has never met, and the mechanisms it invents for them."""
import collections
import copy
import itertools
import math
import os
import sys
import time

from . import prime as prime

EVIDENCE = 6.0
NEW_AT_MOST = 0.02
KEEP = 200
MISSING = object()
NOTHING = [("keep",)]
OPS_USED = {}
MADE = {}
WITHOUT = set()
CARD = [None]
LAST = [None]
CARD_FACTOR = 100


def on_card():
    """Its search on its graphics card."""
    if CARD[0] is None:
        CARD[0] = False
        if os.environ.get("NOVALIE_GPU", "1") != "0" and os.environ.get("NOVALIE_CARD_INVENT", "1") != "0":
            try:
                from . import gpu_invent as gi
                if gi.ready() is not None:
                    CARD[0] = gi
            except Exception:
                pass
    return CARD[0] or None


def alive(pid):
    """Whether the process pid is still running."""
    if os.name != "nt":
        return os.getppid() == pid
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k32.OpenProcess(0x00100000, False, pid)
    if not h:
        return False
    try:
        return k32.WaitForSingleObject(h, 0) == 0x102
    finally:
        k32.CloseHandle(h)


def worker_start(gb, parent):
    """In its inventor's own process."""
    import threading
    limit_memory(gb)

    def watch():
        beat = 0
        while True:
            time.sleep(1)
            beat += 1
            got = commit_gb()
            if got and got[1] < reserve_gb(got[0]) / 2:
                os._exit(0)
            if beat % 5 == 0 and not alive(parent):
                os._exit(0)
    threading.Thread(target=watch, daemon=True).start()


def commit_gb():
    """What its computer may promise in all."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Info(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
            "commit", "limit", "peak", "phys", "avail", "cache", "kernel", "paged", "nonpaged", "page")] + [
            (n, wintypes.DWORD) for n in ("handles", "processes", "threads")]
    i = Info()
    i.cb = ctypes.sizeof(Info)
    try:
        if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(i), i.cb):
            return None
    except (AttributeError, OSError):
        return None
    g = i.page / 2 ** 30
    return i.limit * g, max(0, i.limit - i.commit) * g


def reserve_gb(limit):
    """What all its processes together leave free of what its computer may promise."""
    return 0.15 * limit


def limit_memory(gb):
    """This process may hold at most gb of memory, enforced by the system."""
    if os.name != "nt":
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (int(gb * 2 ** 30),) * 2)
            return True
        except (ImportError, ValueError, OSError):
            return False
    import ctypes
    from ctypes import wintypes

    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    job = k32.CreateJobObjectW(None, None)
    info = Extended()
    info.Basic.LimitFlags = 0x100
    info.ProcessMemoryLimit = int(gb * 2 ** 30)
    ok = k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
    return bool(ok and k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()))


# -- its alphabet ---------------------------------------------------------------------------------------
def moved(kind, v, d):
    if kind[0] == "free":
        return v + d
    if kind[0] == "cycle":
        return (v + d) % kind[1]
    return min(max(v + d, 0), kind[1] - 1)


def put(regs, i, v):
    return regs[:i] + (v,) + regs[i + 1:]


def act(ins, kinds, regs, pile):
    """One operation on its hidden numbers and its pile."""
    op = ins[0]
    if op == "keep":
        return regs, pile
    if op == "add":
        return put(regs, ins[1], moved(kinds[ins[1]], regs[ins[1]], ins[2])), pile
    if op == "zero":
        return put(regs, ins[1], 0), pile
    if op == "flip":
        return put(regs, ins[1], 1 - regs[ins[1]]), pile
    if op == "pass":
        a, b = ins[1], ins[2]
        if regs[a] > 0 and moved(kinds[b], regs[b], 1) != regs[b]:
            regs = put(put(regs, a, regs[a] - 1), b, regs[b] + 1)
        return regs, pile
    if op == "put":
        return regs, pile + (ins[1],)
    if op == "take":
        return regs, pile[:-1]
    if op == "if":
        return act(ins[2] if regs[ins[1]] == 0 else ins[3], kinds, regs, pile)
    if op == "push":
        return regs, pile + (regs[ins[1]],)
    if op == "pop":
        return (put(regs, ins[1], pile[-1]), pile[:-1]) if pile else (regs, pile)
    if op == "copy":
        return put(regs, ins[2], regs[ins[1]]), pile
    if op == "carry":
        a, b, d = ins[1], ins[2], ins[3]
        old, new = regs[a], moved(kinds[a], regs[a], d)
        regs = put(regs, a, new)
        if (d > 0 and new < old) or (d < 0 and new > old):
            regs = put(regs, b, moved(kinds[b], regs[b], 1 if d > 0 else -1))
        return regs, pile
    if op == "go":
        v = regs[ins[1]]
        return put(regs, ins[1], None if v is None else ins[2][v]), pile
    if op == "swap":
        a, b = ins[1], ins[2]
        return put(put(regs, a, regs[b]), b, regs[a]), pile
    raise ValueError(op)


def see(f, regs, pile):
    """What a sensor could show of its hidden numbers and pile."""
    k = f[0]
    if k == "value":
        return regs[f[1]]
    if k == "at zero":
        return regs[f[1]] == 0
    if k == "sign":
        return (regs[f[1]] > 0) - (regs[f[1]] < 0)
    if k == "mod":
        return regs[f[1]] % f[2]
    if k == "top":
        return pile[-1] if pile else None
    if k == "empty":
        return not pile
    if k == "height":
        return len(pile)
    if k == "cmp":
        d = regs[f[1]] - regs[f[2]]
        return (d > 0) - (d < 0)
    raise ValueError(k)


def cost(x):
    """How much an operation, a sight or a hidden part says."""
    if x[0] == "if":
        return 1 + cost(x[2]) + cost(x[3])
    if x[0] == "go":
        return max(1, len(x[3]))
    if x[0].startswith("made"):
        return 1
    return {"keep": 0, "add": 1, "zero": 1, "flip": 1, "put": 1, "take": 1, "pass": 2,
            "push": 1, "pop": 1, "copy": 2, "carry": 2, "swap": 2,
            "value": 1, "at zero": 1, "top": 1, "empty": 1, "height": 1, "sign": 2, "mod": 2, "cmp": 2,
            "free": 1, "bit": 1, "cycle": 2, "walls": 2, "made": 1}[x[0]]


def code(x):
    """Its own short name for an operation or a sight."""
    k = x[0]
    if k == "keep":
        return "."
    if k == "add":
        return f"{x[2]:+d}" + (f"@{x[1]}" if x[1] else "")
    if k == "zero":
        return "0" + (f"@{x[1]}" if x[1] else "")
    if k == "flip":
        return "~"
    if k == "pass":
        return f"{x[1]}>{x[2]}"
    if k == "put":
        return f"^{x[1]}"
    if k == "take":
        return "v"
    if k == "if":
        return f"?({code(x[2])},{code(x[3])})"
    if k == "push":
        return f"^#{x[1] or ''}"
    if k == "pop":
        return f"v#{x[1] or ''}"
    if k == "copy":
        return f"{x[1]}:{x[2]}"
    if k == "carry":
        return f"{x[1]}{x[3]:+d}>>{x[2]}"
    if k == "go":
        return x[3]
    if k == "mod":
        return f"%{x[2]}"
    if k == "swap":
        return f"{x[1]}<>{x[2]}"
    return {"value": "=", "at zero": "=0", "sign": "+-", "top": "top", "empty": "none", "height": "h",
            "cmp": "<=>"}[k]


def shape_cost(shape):
    kinds, pile = shape
    return sum(cost(k) for k in kinds) + pile


def shape_code(shape):
    kinds, pile = shape
    parts = ["m" + k[3] if k[0] == "made" else
             {"free": "n", "bit": "b", "cycle": "c", "walls": "w"}[k[0]] + (str(k[1]) if len(k) > 1 else "")
             for k in kinds]
    return "".join(parts + (["p"] if pile else []))


def nature(shape):
    """What kind it is, whatever its sizes."""
    kinds, pile = shape
    return tuple("made:" + k[3] if k[0] == "made" else k[0] for k in kinds), pile


def shapes(sizes, prior=None, seen=()):
    """Every hidden part it can imagine."""
    one = [("free",)] + [(k, n) for k in ("walls", "cycle") for n in sizes]
    out = [((("made", d["n"], d["key"], name),), False) for name, d in MADE.items()]
    out += [((), True)]
    for k in one:
        out += [((k,), False), ((k,), True), ((k, ("bit",)), False)]
    near = set(seen) | {n + 1 for n in seen}
    alike = os.environ.get("NOVALIE_ALIKE", "1") != "0"
    out += [((a, b), False) for a in one for b in one if a[0] == b[0]
            and (a[0] == "free" or (a[1] in near and b[1] in near) or (alike and a == b))]
    served = prior or {}

    def plain(sh):
        names = list(nature(sh)[0]) + (["pile"] if sh[1] else [])
        sized = sum(1 for k in sh[0] if len(k) > 1 and k[1] in seen)
        return (shape_cost(sh) - 0.5 * sized
                - 0.5 * sum(math.log2(1 + served.get(n, 0)) for n in names) / max(1, len(names)))
    return sorted(out, key=plain)


def alphabet(shape, ops=None):
    """Every operation it can give a button, for this shape, simplest first."""
    kinds, pile = shape
    nums = [r for r, k in enumerate(kinds) if k[0] not in ("bit", "made")]
    bits = [r for r, k in enumerate(kinds) if k[0] == "bit"]
    out = [("keep",)]
    for r, k in enumerate(kinds):
        if k[0] == "made" and k[3] in MADE:
            out += [("go", r, f, w) for w, f in MADE[k[3]]["moves"]]
    for r in nums:
        out += [("add", r, d) for d in (1, -1, 2, -2)] + [("zero", r)]
    out += [("flip", b) for b in bits]
    if len(nums) == 2 and all(kinds[r][0] in ("free", "walls") for r in nums):
        out += [("pass", 0, 1), ("pass", 1, 0)]
    if pile:
        out += [("put", s) for s in range(3)] + [("take",)]
        out += [("push", r) for r in nums] + [("pop", r) for r in nums]
    for a in nums:
        for b in nums:
            if a != b:
                out.append(("copy", a, b))
                if kinds[a][0] == "cycle":
                    out += [("carry", a, b, 1), ("carry", a, b, -1)]
    if len(nums) == 2 and kinds[nums[0]] == kinds[nums[1]]:
        out.append(("swap", nums[0], nums[1]))
    for b in bits:
        adds = [x for x in out if x[0] == "add"]
        out += [("if", b, x, y) for x in adds for y in adds if x != y and x[1] == y[1]]
    if ops is not None:
        out = [x for x in out if x[0] in ops]
    out = [x for x in out if x[0] not in WITHOUT]
    used = OPS_USED
    return sorted(out, key=lambda x: cost(x) - 0.3 * math.log2(1 + used.get(x[0], 0)))


def sights(shape, sizes):
    kinds, pile = shape
    out = []
    for r, k in enumerate(kinds):
        out.append(("value", r))
        if k[0] in ("free", "walls", "cycle"):
            out.append(("at zero", r))
        if k[0] == "free":
            out += [("sign", r)] + [("mod", r, n) for n in sizes]
    nums = [r for r, k in enumerate(kinds) if k[0] not in ("bit", "made")]
    if len(nums) == 2 and "cmp" not in WITHOUT:
        out.append(("cmp", nums[0], nums[1]))
    if pile:
        out += [("top",), ("empty",), ("height",)]
    return sorted(out, key=cost)


def starts(shape):
    """Where its hidden part may have been when it began to watch."""
    kinds, _ = shape
    values = []
    for k in kinds:
        if k[0] == "free":
            values.append([0] + [s * v for v in range(1, 9) for s in (1, -1)])
        elif k[0] == "bit":
            values.append([0, 1])
        else:
            values.append(list(range(min(k[1], 12))))
    return [(tuple(v), ()) for v in sorted(itertools.product(*values), key=lambda v: sum(abs(x) for x in v))]


# -- inventing ------------------------------------------------------------------------------------------
class Mechanism:
    """A kind it invented (or reused)."""
    late = 0

    def __init__(self, shape, assign, looks, maps, state, evidence, tried, said, late=0):
        self.shape, self.assign, self.looks, self.maps = shape, assign, looks, maps
        self.state, self.evidence, self.tried, self.said = state, evidence, tried, said
        self.late = late
        ops = " | ".join(code(x) if x else "?" for x in assign)
        self.name = f"{shape_code(shape)}[{ops}]{'/'.join(code(f) for f in looks)}"

    def step(self, a):
        ins = self.assign[a]
        if ins is not None:
            self.state = act(ins, self.shape[0], *self.state)

    def guess(self):
        """What it expects each sensor to show now."""
        return tuple(self.maps[j].get(see(f, *self.state)) for j, f in enumerate(self.looks))

    def learn(self, seen):
        """A value it had not met yet gets the symbol it shows."""
        for j, f in enumerate(self.looks):
            self.maps[j].setdefault(see(f, *self.state), seen[j])

    def holds(self):
        """What holds however it presses, in words of its own symbols."""
        out = []
        by_number = collections.defaultdict(list)
        for j, f in enumerate(self.looks):
            if len(f) > 1 and f[0] != "cmp":
                by_number[f[1]].append(j)
        for r, js in by_number.items():
            if len(js) > 1:
                parts = []
                for j in js:
                    groups = collections.defaultdict(list)
                    for v, s in sorted(self.maps[j].items(), key=lambda kv: str(kv[0])):
                        groups[s].append(v)
                    parts.append(f"sensor {j + 1}: " + ", ".join(f"{s} at {vs}" for s, vs in groups.items()))
                out.append(f"sensors {' and '.join(str(j + 1) for j in js)} show one hidden number "
                           f"({shape_code(((self.shape[0][r],), False))}): " + "; ".join(parts))
        return out


def invent(stream, first, m, library=(), budget=2_000_000, seconds=240, enough=False, machines=True):
    """The simplest mechanism that explains what it saw."""
    if on_card() is not None:
        budget *= CARD_FACTOR
    MADE.clear()
    for e in library:
        if e.get("machine"):
            MADE[e["machine"]["name"]] = e["machine"]
    shown = {len({o[j] for _, o in stream} | {first[j]}) + d for j in range(len(first)) for d in (0, 1)}
    sizes = [n for n in sorted(shown | set(range(2, 9))) if 2 <= n <= 64]
    natures, ops = collections.Counter(), collections.Counter()
    for e in library:
        served = max(1, len(e.get("uses", ())))
        for k in e["nature"][0] + (("pile",) if e["nature"][1] else ()):
            natures[k] += served
        for o in e["ops"]:
            ops[o] += served
    OPS_USED.clear()
    OPS_USED.update(ops)
    seen = {len({o[j] for _, o in stream} | {first[j]}) for j in range(len(first))}
    every = shapes(sizes, natures, seen)
    before = [first] + [o for _, o in stream]
    movers = sorted({a for (a, o), prev in zip(stream, before) if o != prev})
    others = suspects(stream, first, movers, m)
    extras = [()] + [(b,) for b in others] + list(itertools.combinations(others, 2))
    least = sum(seen) + len(movers)
    tried, end, best, reused = 0, time.time() + seconds, None, False
    last = end
    if machines:
        end = time.time() + 0.67 * seconds
    kinds = sorted(library, key=lambda e: shape_cost((tuple((k,) for k in e["nature"][0]), e["nature"][1])))
    for i, entry in enumerate(kinds):
        mine = [s for s in every if nature(s) == entry["nature"]]
        share = (budget - tried) // (len(kinds) - i + 1)
        secs = (end - time.time()) / (len(kinds) - i + 1)
        mech, tried = sweep(stream, first, m, mine, sizes, entry["ops"], movers, extras, tried + share,
                            time.time() + secs, enough, tried, least, best)
        if mech is not None and (best is None or mech.said < best.said):
            best, reused = mech, True
    mech, tried = sweep(stream, first, m, every, sizes, None, movers, extras, budget, end, enough, tried, least, best)
    if mech is not None and (best is None or mech.said < best.said):
        best, reused = mech, False
    if machines and (best is None or best.late > 0):
        mine, tried = learned(stream, first, m, tried, last)
        if mine is not None and (best is None or (mine.late, mine.said) < (best.late, best.said)):
            best, reused = mine, False
    if best is not None:
        best.tried = tried
        for k in best.shape[0]:
            if k[0] == "made" and k[3] in MADE:
                best.made = MADE[k[3]]
    return best, tried, reused


def learned(stream, first, m, tried, end):
    """No mechanism of its alphabet explains what it saw."""
    before = [first] + [o for _, o in stream]
    movers = sorted({a for (a, o), prev in zip(stream, before) if o != prev})
    if not movers:
        return None, tried
    seen = [(movers.index(a), o) for a, o in stream if a in movers]
    fit, tried = prime.learn(seen, first, len(movers), seconds=max(1.0, min(30.0, end - time.time())), tried=tried)
    if fit is None:
        return None, tried
    mach = prime.machine_of(fit, len(movers))
    pressed = {a for a, _ in stream}
    mach["assign"] = [mach["assign"][movers.index(a)] if a in movers else "" if a in pressed else None
                      for a in range(m)]
    if mach["evidence"] < EVIDENCE + math.log10(max(1, tried)) or not mach["complete"] or not mach["gens"]:
        return None, tried
    n, gens = mach["n"], mach["gens"]
    if prime.old_part(gens, n):
        return None, tried
    key = prime.canonical(gens, n)
    name = next((x for x, d in MADE.items() if d["key"] == key), None)
    if name is None:
        name = prime.label_for(MADE)
        _, word, _, _ = prime.monoid(gens, n, most=400)
        moves = sorted(((w, f) for f, w in word.items() if 1 <= len(w) <= 2), key=lambda wf: (len(wf[0]), wf[0]))
        MADE[name] = {"name": name, "n": n, "key": key, "gens": gens, "moves": moves,
                      "nature": prime.nature_of(gens, n), "old": prime.old_part(gens, n)}
    kind = ("made", n, key, name)
    assign = [None if x is None else ("keep",) if x == "" else ("go", 0, gens[prime.LETTERS.index(x)], x)
              for x in mach["assign"]]
    k = len(first)
    maps = [{q: mach["out"][q][j] for q in range(n)} for j in range(k)]
    said = n + sum(len(g) for g in gens) + k + n * k
    mech = Mechanism(((kind,), False), assign, [("value", 0)] * k, maps, ((mach["state"],), ()),
                     mach["evidence"], tried, said, mach["late"])
    return mech, tried


def suspects(stream, first, movers, m):
    """The buttons that never changed what it saw, the most suspect first."""
    seen = [first] + [o for _, o in stream]
    others = [b for b in range(m) if b not in movers]
    odd = {b: [0] for b in others}
    for a, _ in stream:
        for b in others:
            odd[b].append(odd[b][-1] ^ (a == b))
    last, score = {}, collections.Counter()
    for t, (a, o) in enumerate(stream):
        if a not in movers:
            continue
        key = (a, seen[t])
        if key in last:
            t0, o0 = last[key]
            for b in others:
                if odd[b][t] != odd[b][t0]:
                    score[b] += 1 if o != o0 else -1
        last[key] = (t, o)
    return sorted(others, key=lambda b: -score[b])


def sweep(stream, first, m, shapes_, sizes, ops, movers, extras, budget, end, enough, tried, least=0, best=None):
    """Its hidden part and the buttons free to do something, the plainest together first."""
    order = sorted((i + len(shapes_) * len(x) / 2, i, j) for i in range(len(shapes_)) for j, x in enumerate(extras))
    found = None
    for second in (False, True):
        short = []
        for _, i, j in order:
            if tried >= budget or time.time() >= end:
                break
            known = min((x for x in (best, found) if x is not None), key=lambda x: x.said, default=None)
            if known is not None and shape_cost(shapes_[i]) + len(extras[j]) + least >= known.said:
                continue
            left, start = budget - tried, tried
            cap = left if second else max(20_000, left // 8)
            secs = (end - time.time()) if second else (end - time.time()) / 8
            mech, tried = search(stream, first, m, [shapes_[i]], sizes, ops, tried + cap, secs, enough,
                                 set(movers) | set(extras[j]), tried)
            if mech is not None and (found is None or mech.said < found.said):
                found = mech
            elif mech is None and (tried - start >= cap if LAST[0] is None else not LAST[0]):
                short.append((0, i, j))
        if found is not None or not short:
            break
        order = short
    return found, tried


def work(acts, cols, groups, m, library, budget=1_500_000, seconds=60):
    """What its live model asks, in a process of its own."""
    found, done, end = Found(), set(), time.time() + seconds
    found.began = time.time()
    for g in groups:
        if done & set(g) or time.time() >= end:
            continue
        stream = [(a, tuple(cols[j][t + 1] for j in g)) for t, a in enumerate(acts)]
        first = tuple(cols[j][0] for j in g)
        mech, tried, _ = invent(stream, first, m, library, budget, max(1.0, end - time.time()), enough=True)
        if mech is not None:
            mech.evidence_each = evidence_each(mech, stream, first)
            if mech.evidence_each is None or min(mech.evidence_each) < EVIDENCE + math.log10(max(1, tried)):
                continue
            found.append((g, mech, tried))
            done |= set(g)
    found.card = card_use()
    found.ended = time.time()
    return found


def own_worth(stream, first):
    """For each sensor, what foreseeing its value at each act is worth against what it does by itself, as its
    life weighs it."""
    out = []
    for j in range(len(first)):
        freq, stays, n, last, row = collections.Counter([first[j]]), 0, 1, first[j], []
        for _, o in stream:
            v = o[j]
            q = (freq[v] + 1) / (n + 1)
            if v == last:
                q = max(q, (stays + 1) / (n + 1))
                stays += 1
            row.append(-math.log10(min(1.0, q)))
            freq[v] += 1
            n += 1
            last = v
        out.append(row)
    return out


def evidence_each(mech, stream, first):
    """What a mechanism's foresight is worth for each of its sensors alone."""
    kinds = mech.shape[0]
    if getattr(mech, "begin", None) is not None:
        begins = [mech.begin]
    elif len(kinds) == 1 and kinds[0][0] == "made":
        begins = [((q,), ()) for q in range(kinds[0][1])]
    else:
        begins = starts(mech.shape)
    worth = own_worth(stream, first)
    for regs, pile in begins:
        maps = [{see(f, regs, pile): first[j]} for j, f in enumerate(mech.looks)]
        ev, ok = [0.0] * len(first), True
        for t, (a, o) in enumerate(stream):
            ins = mech.assign[a] if a < len(mech.assign) else None
            if ins is not None:
                regs, pile = act(ins, kinds, regs, pile)
            for j, f in enumerate(mech.looks):
                v = see(f, regs, pile)
                s = maps[j].get(v, MISSING)
                if s is MISSING:
                    maps[j][v] = o[j]
                elif s != o[j]:
                    ok = False
                    break
                else:
                    ev[j] += worth[j][t]
            if not ok:
                break
        if ok:
            return ev
    return None


class Found(list):
    """What its inventor found, and what it did on its card."""
    card = began = ended = None


def card_use():
    """What its inventor's process did on its card so far, or None."""
    card = CARD[0] or None
    if card is None:
        return None
    from . import gpu as gpu
    use = dict(card.USE)
    use.update(gpu.describe(ask=False) or {})
    return use


def search(stream, first, m, shapes_, sizes, ops, budget, seconds, enough=False, free=None, tried=0):
    """Every mechanism of these shapes."""
    LAST[0] = None
    card = on_card()
    if card is not None and len(shapes_) == 1:
        got = card.search(sys.modules[__name__], stream, first, m, shapes_[0], sizes, ops, budget, seconds, enough,
                          free, tried)
        if got is not None:
            LAST[0] = got[2]
            return got[0], got[1]
    acts, obs, k = [a for a, _ in stream], [o for _, o in stream], len(first)
    half = len(acts) // 2
    every = [first] + obs
    gain = []
    for j in range(k):
        c = collections.Counter(o[j] for o in every)
        gain.append({s: -math.log10(n / len(every)) for s, n in c.items()})
    allowed_new = max(2, int(NEW_AT_MOST * (len(acts) - half)))
    passed, deadline, cut = [], time.time() + max(0.0, seconds), [False]
    begin = [None]

    def run(t, assign, regs, pile, maps, ev, new_late, looks, shape, alpha):
        nonlocal tried
        kinds = shape[0]
        while t < len(acts):
            a = acts[t]
            ins = assign[a]
            if ins is None:
                for cand in (alpha if free is None or a in free else NOTHING):
                    tried += 1
                    if tried > budget or (tried & 1023 == 0 and time.time() > deadline):
                        cut[0] = True
                    if cut[0]:
                        return
                    run(t, assign[:a] + [cand] + assign[a + 1:], regs, pile, [dict(x) for x in maps], ev, new_late,
                        looks, shape, alpha)
                return
            regs, pile = act(ins, kinds, regs, pile)
            o = obs[t]
            for j, f in enumerate(looks):
                v = see(f, regs, pile)
                s = maps[j].get(v, MISSING)
                if s is MISSING:
                    maps[j][v] = o[j]
                    if t >= half:
                        new_late += 1
                        if new_late > allowed_new:
                            return
                elif s != o[j]:
                    return
                else:
                    ev += gain[j][o[j]]
            t += 1
        if ev >= EVIDENCE:
            said = (sum(cost(x) for x in kinds) + shape[1] + sum(cost(x) for x in assign if x)
                    + sum(cost(f) for f in looks) + sum(len(x) for x in maps))
            passed.append((said, -ev, shape, assign, looks, maps, (regs, pile), ev, new_late, begin[0]))
            if len(passed) > 4 * KEEP:
                passed.sort(key=lambda p: (p[0], p[1]))
                del passed[KEEP:]

    for shape in shapes_:
        alpha = alphabet(shape, ops)
        options = sights(shape, sizes)
        for looks in sorted(itertools.product(options, repeat=k), key=lambda ls: sum(cost(f) for f in ls)):
            for regs, pile in starts(shape):
                begin[0] = (regs, pile)
                maps = [{see(f, regs, pile): first[j]} for j, f in enumerate(looks)]
                tried += 1
                run(0, [None] * m, regs, pile, maps, 0.0, 0, list(looks), shape, alpha)
                if cut[0]:
                    break
                if enough and any(p[7] >= EVIDENCE + math.log10(max(1, tried)) for p in passed):
                    cut[0] = True
                    break
            if cut[0]:
                break
        if cut[0] or any(p[7] >= EVIDENCE + math.log10(max(1, tried)) for p in passed):
            break
    need = EVIDENCE + math.log10(max(1, tried))
    ok = [p for p in passed if p[7] >= need]
    if not ok:
        return None, tried
    said, _, shape, assign, looks, maps, state, ev, late, start = min(ok, key=lambda p: (p[0], p[1]))
    mech = Mechanism(shape, list(assign), list(looks), maps, state, ev, tried, said, late)
    mech.begin = start
    return mech, tried


def keep(library, mech, where):
    """Its library: what it invented, never forgotten: the nature of its hidden part and the kinds of operation."""
    ops = {x[0] for x in mech.assign if x} | {"keep"}
    for entry in library:
        if entry["nature"] == nature(mech.shape) and entry["ops"] == ops:
            entry["uses"].append(where)
            return entry
    entry = {"name": mech.name, "nature": nature(mech.shape), "ops": ops, "uses": [where]}
    made = getattr(mech, "made", None)
    if made:
        entry["machine"] = dict(made)
    library.append(entry)
    return entry


# -- reasoning with a mechanism ----------------------------------------------------------------------------


def plan(mech, m, goal, sensor=0, depth=40, most=50_000):
    """The fewest presses that bring the symbol it wants to see on a sensor."""
    want = {v for v, s in mech.maps[sensor].items() if s == goal}
    look, kinds, start = mech.looks[sensor], mech.shape[0], mech.state
    if see(look, *start) in want:
        return []
    came, frontier = {start: None}, [start]
    for _ in range(depth):
        nxt = []
        for st in frontier:
            for a in range(m):
                ins = mech.assign[a]
                if ins is None:
                    continue
                s2 = act(ins, kinds, *st)
                if s2 in came:
                    continue
                came[s2] = (st, a)
                if see(look, *s2) in want:
                    path = []
                    while came[s2] is not None:
                        s2, a2 = came[s2]
                        path.append(a2)
                    return path[::-1]
                if len(came) >= most:
                    return None
                nxt.append(s2)
        frontier = nxt
    return None


def invariants(mech, presses, most=2):
    """Sums that never change however it presses."""
    kinds = mech.shape[0]
    nums = [r for r, k in enumerate(kinds) if k[0] not in ("bit", "made")]
    if len(nums) < 2:
        return []
    m, trace = copy.copy(mech), []
    for a in presses:
        m.step(a)
        trace.append(m.state[0])
    out = []
    for c in itertools.product(range(-most, most + 1), repeat=len(nums)):
        if all(x == 0 for x in c) or next(x for x in c if x) < 0 or math.gcd(*c) != 1:
            continue
        values = {sum(ci * st[r] for ci, r in zip(c, nums)) for st in trace}
        moving = all(len({st[r] for st in trace}) > 1 for r, ci in zip(nums, c) if ci)
        if len(values) == 1 and moving:
            full = [0] * len(kinds)
            for ci, r in zip(c, nums):
                full[r] = ci
            out.append((tuple(full), values.pop()))
    return out


def laws(mech, presses=2000):
    """What holds however it presses, as data for its page."""
    out, by_number = [], collections.defaultdict(list)
    for j, f in enumerate(mech.looks):
        if len(f) > 1 and f[0] != "cmp":
            by_number[f[1]].append(j)
    for r, js in sorted(by_number.items()):
        if len(js) > 1:
            out.append({"law": "one", "sensors": [j + 1 for j in js],
                        "number": shape_code(((mech.shape[0][r],), False))})
    m = len(mech.assign)
    walk = visiting(mech, m, presses)
    for c, v in invariants(mech, walk):
        out.append({"law": "sum", "c": list(c), "total": v, "proved": proved(mech, c)})
    kinds = mech.shape[0]
    links = set()
    for ins in mech.assign:
        if not ins:
            continue
        if ins[0] == "carry":
            links.add(("carry", ins[1], ins[2]))
        elif ins[0] == "pass":
            links.add(("pass", ins[1], ins[2]))
        elif ins[0] in ("copy", "swap"):
            links.add((ins[0], ins[1], ins[2]))
        elif ins[0] in ("push", "pop"):
            links.add(("memory", ins[1], None))
        elif ins[0] == "if":
            links.add(("steers", ins[1], ins[2][1]))
    for kind, a, b in sorted(links, key=str):
        out.append({"law": kind, "from": shape_code(((kinds[a],), False)),
                    "to": shape_code(((kinds[b],), False)) if b is not None else "p"})
    made = getattr(mech, "made", None)
    if made:
        for lhs, rhs in made["nature"]["laws"][:8]:
            out.append({"law": "rel", "part": "m" + made["name"], "lhs": lhs, "rhs": rhs})
    return out


def visiting(mech, m, most=2000):
    """Presses that go through the states its mechanism can reach, one after another."""
    probe, seen, walk = copy.copy(mech), {mech.state}, []
    while len(walk) < most:
        path = None
        came, frontier = {probe.state: None}, [probe.state]
        while frontier and path is None and len(came) < 5000:
            nxt = []
            for st in frontier:
                for a in range(m):
                    ins = probe.assign[a]
                    if ins is None:
                        continue
                    s2 = act(ins, probe.shape[0], *st)
                    if s2 in came:
                        continue
                    came[s2] = (st, a)
                    if s2 not in seen:
                        path, s3 = [], s2
                        while came[s3] is not None:
                            s3, a3 = came[s3]
                            path.append(a3)
                        path = path[::-1]
                        break
                    nxt.append(s2)
                if path is not None:
                    break
            frontier = nxt
        if not path:
            break
        for a in path:
            probe.step(a)
            seen.add(probe.state)
            walk.append(a)
    return walk


def keeps(ins, c):
    """Does this operation leave the sum c."""
    op = ins[0]
    if op in ("keep", "put", "take", "flip"):
        return True
    if op in ("add", "zero", "go"):
        return c[ins[1]] == 0
    if op in ("pass", "swap"):
        return c[ins[1]] == c[ins[2]]
    if op == "if":
        return keeps(ins[2], c) and keeps(ins[3], c)
    return False


def proved(mech, c):
    """A law c . numbers = k proved."""
    return all(keeps(ins, c) for ins in mech.assign if ins is not None)



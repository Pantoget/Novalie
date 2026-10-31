# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its real world: the clock, its body (busy, load), and the print of its code."""

import hashlib
import os
import threading
import time

from .config import HERE
from .web import READ_GATE


def memory_status():
    """Its computer's memory now."""
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (n, ctypes.c_ulonglong) for n in ("total", "avail", "ptotal", "pavail", "vtotal", "vavail", "ext")]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return m.total / 2 ** 30, m.avail / 2 ** 30
        with open("/proc/meminfo") as f:
            got = {line.split(":")[0]: int(line.split()[1]) for line in f if line.split()[1:2]}
        return got["MemTotal"] / 2 ** 20, got.get("MemAvailable", got.get("MemFree", 0)) / 2 ** 20
    except Exception:
        return None


def memory_load():
    """How full its computer's memory is now, in hundredths."""
    got = memory_status()
    return 0 if not got or not got[0] else int(round(100 * (1 - got[1] / got[0])))


def code_print():
    """Its code's fingerprint."""
    h = hashlib.sha256()
    ui = os.path.join(HERE, "ui")
    try:
        files = sorted(os.path.join(d, n) for d, _, ns in os.walk(HERE) for n in ns if n.endswith(".py"))
        if os.path.isdir(ui):
            files += [os.path.join(ui, n) for n in sorted(os.listdir(ui)) if n.endswith((".js", ".html", ".css", ".json"))]
        for path in files:
            with open(path, "rb") as f:
                h.update(os.path.relpath(path, HERE).encode("utf-8") + b"\0" + f.read() + b"\0")
    except OSError:
        return None
    return h.hexdigest()[:16]


CODE = {"print": code_print(), "began": round(time.time())}


def code_now():
    """Which code it runs, for its page."""
    now = time.time()
    if now - CODE.get("looked", 0) >= 60:
        CODE["disk"], CODE["looked"] = code_print(), now
    return {"print": CODE["print"], "disk": CODE["disk"], "began": CODE["began"],
            "changed": CODE["disk"] is not None and CODE["disk"] != CODE["print"]}


_CYCLES = {}


def thread_cycles():
    """The cycles its processor gave the thread that asks."""
    import ctypes
    k32 = _CYCLES.get("k32")
    if k32 is None:
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentThread.restype = wintypes.HANDLE
        k32.QueryThreadCycleTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ulonglong)]
        _CYCLES["k32"] = k32
    c = ctypes.c_ulonglong()
    return c.value if k32.QueryThreadCycleTime(k32.GetCurrentThread(), ctypes.byref(c)) else None


def cycle_hz():
    """Its processor's cycles in a second, measured once."""
    hz = 0.0
    for _ in range(3):
        t0, c0 = time.perf_counter(), thread_cycles()
        while time.perf_counter() - t0 < 0.01:
            pass
        t1, c1 = time.perf_counter(), thread_cycles()
        if c0 is not None and c1 is not None and t1 > t0:
            hz = max(hz, (c1 - c0) / (t1 - t0))
    return hz


def thread_seconds():
    """The time the thread that asks spent on its processor, in seconds, as finely as its computer counts it."""
    if os.name == "nt" and _CYCLES.get("hz", 1.0) > 0:
        try:
            hz = _CYCLES.get("hz")
            if hz is None:
                hz = _CYCLES["hz"] = cycle_hz()
            n = thread_cycles() if hz > 0 else None
            if n is not None:
                return n / hz
        except Exception:
            _CYCLES["hz"] = 0.0
    return time.thread_time()


def sense_key(sensor):
    """A sense as its memory knows it across its starts."""
    name, version = sensor[1], sensor[2]
    return name if version in (None, 1) else f"{name}@{version}"


OLD_SENSES = ("second", "minute", "hour", "busy", "load")


class RealWorld:
    """The one world it lives in, the real one."""
    def __init__(self, k=0, body=True):
        self.k, self.name, self.jumped, self.body = k, "real", False, body
        self.factors, self.dims, self.machine = [], [], None
        self.buttons = [("time", 1, 0), ("think", 1, 1), ("read", 1, 2)] if body else [("time", 1, 0)]
        self.sensors = [("clock", "second", None), ("clock", "minute", None), ("clock", "hour", None)]
        if body:
            self.sensors += [("body", "busy", 2), ("body", "load", None), ("self", "inventing", None),
                             ("self", "workshop", None), ("self", "learned", 2), ("self", "reading", None),
                             ("control", "control", None)]
        self.size = 86400
        self.private = set(range(3, len(self.sensors)))
        self.named = set(range(min(5, len(self.sensors))))
        self.me = None
        self.t, self.thought = int(time.time()), False
        self.cpu, self.busy, self.cpu_thread = thread_seconds(), 0.0, threading.get_ident()

    def __deepcopy__(self, memo):
        other = RealWorld(self.k, self.body)
        other.t, other.thought = self.t, True
        return other

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.__dict__.pop("fast", None)
        self.__dict__.setdefault("body", False)
        self.__dict__.setdefault("private", {3, 4} if self.body else set())
        self.__dict__.setdefault("cpu_thread", None)
        self.__dict__.setdefault("named", set(range(len(self.__dict__.get("sensors") or ()))))
        self.__dict__.setdefault("me", None)

    def press(self, a):
        if a == 1 and not self.thought:
            end, x = thread_seconds() + 0.05, 1
            while thread_seconds() < end:
                x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        if self.body and not self.thought:
            (READ_GATE.set if a == 2 else READ_GATE.clear)()
            if a == 2 and self.me is not None:
                self.me.read_by_act(max(0.3, self.t + 3.0 - time.time()))
        now_cpu = thread_seconds()
        if self.cpu_thread != threading.get_ident():
            self.cpu_thread, self.cpu = threading.get_ident(), now_cpu
        self.busy, self.cpu = (0.0 if self.thought else round((now_cpu - self.cpu) * 1000, 1)), now_cpu
        if self.thought:
            self.t += 1
            return
        now = time.time()
        if now < self.t - 2 or now - self.t > 172_800:
            self.t, self.jumped = int(now), True
            return
        self.t += 1
        time.sleep(max(0.0, self.t - now))

    @property
    def state(self):
        return list(self.observe())

    def observe(self):
        lt = time.localtime(self.t)
        if not self.body:
            return (lt.tm_sec, lt.tm_min, lt.tm_hour)
        rest = (0,) * (len(self.sensors) - 5)
        if self.thought:
            return (lt.tm_sec, lt.tm_min, lt.tm_hour, 0.0, 0) + rest
        me = self.me
        return (lt.tm_sec, lt.tm_min, lt.tm_hour, self.busy, memory_load()) + (me.self_senses() if me else rest)


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its inventor's process: one budget for all its processes."""

import os
import re

from . import config
from .body import memory_status
from .parts import inventor


def free_memory_gb():
    """What its processes may still take now."""
    got, promised = memory_status(), inventor.commit_gb()
    room = 1.0 if not got else got[1] - 2.0
    if promised:
        room = min(room, promised[1] - inventor.reserve_gb(promised[0]))
    return room


def card_room_gb():
    """What one more of its processes may take on its card now."""
    try:
        import novalie_gpu
        c = novalie_gpu.card()
        return None if c is None else c.spare() / 2 / 2 ** 30
    except Exception:
        return None


INVENTING = []
def inventor_process():
    """Its inventor, in a process of its own."""
    if not INVENTING:
        import concurrent.futures, multiprocessing
        gb = max(0.5, free_memory_gb() / 2)
        if config.CEILING_GB:
            gb = min(gb, config.CEILING_GB)
        INVENTING.append(concurrent.futures.ProcessPoolExecutor(max_workers=1, initializer=inventor.worker_start,
                                                                initargs=(gb, os.getpid()),
                                                                mp_context=multiprocessing.get_context("spawn")))
    return INVENTING[0]


def stop_inventor():
    """Its inventor's process, stopped at once."""
    while INVENTING:
        pool = INVENTING.pop()
        procs = list((getattr(pool, "_processes", None) or {}).values())
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.join(timeout=1.0)
            except Exception:
                pass
        pool.shutdown(wait=False)


def beyond_counts(mech):
    """A mechanism no law of counts could hold."""
    kinds, pile = mech.shape
    if any(k[0] == "made" for k in kinds):
        nat = (getattr(mech, "made", None) or {}).get("nature") or {}
        return not (nat.get("group") and nat.get("commute"))
    return bool(pile or any(k[0] in ("walls", "bit") for k in kinds)
                or any(ins and ins[0] in ("pass", "zero", "if", "flip", "put", "take") for ins in mech.assign)
                or (len(mech.looks) >= 2 and any(ins and ins[0] in ("carry", "copy") for ins in mech.assign)))


def kind_name(entry):
    """Its name for a kind it invented, whatever sizes it met it with and whatever other buttons its world had."""
    head, _, rest = entry["name"].replace(" ", "").partition("[")
    ops, _, looks = rest.partition("]")
    ops = "|".join(sorted({x for x in ops.split("|") if x not in (".", "?")}))
    return re.sub(r"\d+", "", head) + "[" + ops + "]" + re.sub(r"%\d+", "%", looks)


def nature_text(shape_or_nature):
    """What its hidden part is made of, in its own words."""
    if not shape_or_nature:
        return ""
    kinds, pile = shape_or_nature
    names = [("made:" + k[3] if k[0] == "made" else k[0]) if isinstance(k, tuple) else k for k in kinds]
    return "+".join(names + (["pile"] if pile else []))

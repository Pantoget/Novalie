# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its concepts by an anytime-valid test."""
import collections
import math
import os
import sys
import time

from . import eproc as E
from . import gpu_concepts as GC

CFG = {"search": int(os.environ.get("EPROC_SEARCH", "20")), "top": int(os.environ.get("EPROC_TOP", "8")),
       "keep": int(os.environ.get("EPROC_KEEP", "12")), "select": float(os.environ.get("EPROC_SELECT", "2")),
       "since": os.environ.get("EPROC_SINCE", "1") == "1", "card": os.environ.get("EPROC_CARD", "1") == "1",
       "regrain": int(os.environ.get("EPROC_REGRAIN", "50")), "book": os.environ.get("EPROC_BOOK", "0") == "1",
       "book_every": int(os.environ.get("EPROC_BOOK_EVERY", "5"))}
STATS = collections.Counter()
LOG = []


def groups_of(key):
    return key[1] if E.is_book_key(key) else key


def install(app):
    E.SELECT_MIN = CFG["select"]
    N = app.Novalie
    real_see, real_enter = N.see_concepts, N.enter
    from . import typebook as TB

    def enter(self, world=None):
        ep = self.__dict__.get("_eproc")
        if CFG["book"] and ep is not None and world is not None and world is not self.__dict__.get("world"):
            book = self.__dict__.setdefault("type_book", {})
            for m, b in sorted(ep["belief"].items()):
                T = ep["tests"].get(m)
                if T is None:
                    continue
                entry = book.get(m)
                if entry is None or entry.n != ep["n"]:
                    entry = book[m] = TB.Entry(ep["n"])
                classes = [list(g) for g in groups_of(b["key"])]
                for kind in TB.kinds_of_world(self, m, T, classes):
                    entry.add(kind)
                LOG.append((id(self), ep["acts"], m, "into the book", len(entry.classes), classes))
        real_enter(self, world)
        if not getattr(self, "real", False):
            self.__dict__.pop("_eproc", None)

    def state(self, n):
        ep = self.__dict__.get("_eproc")
        if ep is None or ep["n"] != n:
            ep = self._eproc = {"n": n, "tests": {}, "belief": {}, "acts": 0, "virtual": {}}
        return ep

    def see_concepts(self, before, a, o):
        t0 = time.perf_counter()
        room = self.concept_room()
        ages = room.get("ages") or []
        if len(ages) != len(before):
            ages = [0] * len(before)
        agesb = [E.age_of(x) for x in ages]
        ep = state(self, len(before))
        for j, v in enumerate(before):
            if E.is_symbol(v) and j not in ep["tests"]:
                entry = (self.__dict__.get("type_book") or {}).get(j) if CFG["book"] else None
                if entry is not None and (entry.n != len(before) or not entry.classes):
                    entry = None
                ep["tests"][j] = E.ConceptTest(j, len(before), null_grain="withany", since=CFG["since"], book=entry)
        for T in ep["tests"].values():
            T.see(tuple(before), a, tuple(o), agesb)
        ep["acts"] += 1
        STATS["see_s"] += time.perf_counter() - t0
        real_see(self, before, a, o)
        t1 = time.perf_counter()
        for j in sorted(ep["tests"]):
            judge(self, ep, j)
        STATS["judge_s"] += time.perf_counter() - t1

    def judge(self, ep, j):
        T = ep["tests"][j]
        nxt = ep.setdefault("next", {})
        if ep["acts"] >= nxt.get(j, CFG["search"]):
            nxt[j] = ep["acts"] + max(CFG["search"], ep["acts"] // 20)
            vals = T.values(cap=GC.MAX_N)
            if len(vals) >= 2:
                t0 = time.perf_counter()
                found = GC.best_groupings(T, vals, top=CFG["top"], use_card=CFG["card"])
                STATS["search_s"] += time.perf_counter() - t0
                STATS["searches"] += 1
                t0 = time.perf_counter()
                for _, G in found:
                    if E.canon(G) not in T.tracked:
                        T.track(G)
                        STATS["replays"] += 1
                    if T.book is not None:
                        bk = E.book_key(G, TB.kinds_of_groups(T, G))
                        if bk not in T.tracked:
                            T.track(bk)
                            STATS["replays"] += 1
                STATS["replay_s"] += time.perf_counter() - t0
        reading = ep["acts"] % (CFG["book_every"] if ep["acts"] < 200 else 10 * CFG["book_every"]) == 0
        if T.book is not None and reading and len(T.seen) >= 2:
            G, kinds = TB.read_by_book(T, T.values(cap=GC.MAX_N))
            bk = E.book_key(G, kinds)
            if bk not in T.tracked and any(k >= 0 for k in bk[2]):
                T.track(bk)
                STATS["book_reads"] += 1
        if not T.tracked:
            return
        bounds = {key: T.bound(key) for key in T.tracked}
        b = ep["belief"].get(j)
        keep = sorted(bounds, key=lambda k: (-bounds[k], repr(k)))[:CFG["keep"]]
        if b is not None and b["key"] in T.tracked and b["key"] not in keep:
            keep.append(b["key"])
        for key in list(T.tracked):
            if key not in keep:
                T.park(key)
        passing = [k for k in keep if len(groups_of(k)) >= 2 and bounds[k] >= app.EVIDENCE]
        T.best = (bounds[keep[0]], keep[0], T.t)
        if not passing:
            return
        top = max(passing, key=lambda k: (bounds[k], repr(k)))
        if b is None or b["key"] != top:
            ep["belief"][j] = {"key": top, "digits": bounds[top], "at": ep["acts"], "predictor": T.tracked[top]}
            LOG.append((id(self), ep["acts"], j, ("believed" if b is None else "changed") +
                        (" (book)" if E.is_book_key(top) else ""), round(bounds[top], 1),
                        [list(g) for g in groups_of(top)]))
            install_classes(self, j, ep["belief"][j], finer=False)
        else:
            b["digits"] = bounds[top]
            b["predictor"] = T.tracked.get(top, b.get("predictor"))
            if ep["acts"] % CFG["regrain"] == 0:
                install_classes(self, j, b, finer=False)

    def install_classes(self, m, belief, finer=True):
        """What form_classes puts, for the classes its e-process believes."""
        room = self.concept_room()
        coarse = room["stats"].get(m, {})
        ep = self.__dict__.get("_eproc") or {}
        virtual = (ep.get("virtual") or {}).get(m) or set()
        seen = {v: sum(sum(c.values()) for c in cells.values()) for v, cells in coarse.items() if v not in virtual}
        values = sorted((v for v in seen if seen[v]), key=lambda v: (-seen[v], repr(v)))[:12]
        if len(values) < 2:
            room["classes"][m] = None
            return
        if finer:
            self.test_finer(m, values)
        proven = (room.get("proven") or {}).get(m) or {}
        grains = ["fine", "own"] + [f"with {k}" for k in sorted(room.get("with") or {}) if k != m] + \
            [f"since {k}" for k in sorted(room.get("since") or {})] + \
            [f"both {k}" for k in sorted({k for ks in proven.values() for k in ks})] + ["stats"]
        datas = {g: self.grain_room(g, m) for g in grains}
        datas = {g: d for g, d in datas.items() if all(v in d for v in values)}
        pooled = {}
        for g, data in datas.items():
            for v in values:
                for key, counts in data[v].items():
                    pooled.setdefault((g, key[:2]), {}).setdefault(key, collections.Counter()).update(counts)
        cells = sorted({cell for v in values for cell in coarse.get(v, {})}, key=repr)
        chosen = {}
        P = belief.get("predictor")
        for cell in cells:
            lw = (P.logw.get(cell) if P is not None else None) or {}
            if lw and not proven.get(cell):
                g = max(lw, key=lambda g: (lw[g], g == "own", g))
                if g in datas and (g, cell) in pooled:
                    chosen[cell] = g
                    continue
            best = None
            for g in grains:
                got = pooled.get((g, cell))
                if got is None or (g.startswith("both ") and int(g[5:]) not in proven.get(cell, ())):
                    continue
                said = sum(self.kt_digits(c, len(c)) for c in got.values())
                if best is None or said < best[0] - 1e-9:
                    best = (said, g)
            if best is not None:
                chosen[cell] = best[1]
        data = {v: {(chosen[key[:2]], key): counts for g in set(chosen.values()) for key, counts in datas[g][v].items()
                    if chosen.get(key[:2]) == g} for v in values}
        order = {v: k for k, v in enumerate(values)}
        vs = set(values)
        groups = [sorted((v for v in g if v in vs), key=order.get) for g in groups_of(belief["key"])]
        groups = [g for g in groups if g]
        groups.sort(key=lambda g: order[g[0]])
        kinds = {}
        if E.is_book_key(belief["key"]):
            for g, k in zip(belief["key"][1], belief["key"][2]):
                for v in g:
                    kinds[v] = k
        tells = set()
        if len(groups) >= 2:
            for cell in cells:
                per = [collections.Counter() for _ in groups]
                for g, c in zip(groups, per):
                    for v in g:
                        c.update(coarse.get(v, {}).get(cell, {}))
                allc = sum(per, collections.Counter())
                k = len(allc)
                if self.kt_digits(allc, k) - sum(self.kt_digits(c, k) for c in per if c) >= app.EVIDENCE:
                    tells.add(cell)
        concept = len(groups) >= 2
        used = collections.Counter(chosen.values())
        grain = min(used, key=lambda g: (-used[g], g)) if used else "stats"
        room.setdefault("weighed", {})[m] = {"groups": [list(g) for g in groups], "digits": round(belief["digits"], 1),
                                             "bar": app.EVIDENCE, "at": room["steps"], "grain": grain,
                                             "grains": dict(used), "eproc_at": belief["at"]}
        classes = [{"rep": g[0], "members": list(g)} for g in groups]
        T = (ep.get("tests") or {}).get(m)
        if kinds and T is not None and T.book is not None:
            for c in classes:
                k = kinds.get(c["rep"], -1)
                if k >= 0:
                    name = f"kind:{m}.{k}"
                    remember_kind(self, m, name, T.book.classes[k], T.roles)
                    ep.setdefault("virtual", {}).setdefault(m, set()).add(name)
                    c["members"].append(name)
        old = room["classes"].get(m)
        room["classes"][m] = {"classes": classes, "concept": concept, "tells": sorted(tells, key=repr),
                              "digits": round(belief["digits"], 1), "grain": grain, "cells": chosen} if concept else None
        self.__dict__.pop("_class_cache", None)
        if concept:
            self.start_finer(m, groups, data)
        if concept and (old is None or [c["members"] for c in old["classes"]] != [c["members"] for c in classes]):
            shown = [[self.display(x) if isinstance(x, str) else x for x in c["members"]][:8] for c in classes]
            self.emit("concept", sensor=m + 1, classes=shown, tells=len(tells), digits=round(belief["digits"], 1),
                      grain=grain)
            self.decide("concept", m + 1, {"classes": shown, "tells": len(tells), "digits": round(belief["digits"], 1),
                                           "grain": grain})

    def remember_kind(self, m, name, kind, roles):
        """A book kind's changes written in this world's symbols."""
        room = self.concept_room()
        inv = {k: {r: s for s, r in rs.items()} for k, rs in roles.items()}

        def val(k, xr):
            if isinstance(xr, tuple) and len(xr) == 2 and xr[0] == "r":
                return inv.get(k, {}).get(xr[1])
            return xr

        def change(k, yr):
            if yr == ("same",):
                return None, True
            if isinstance(yr, tuple) and len(yr) == 2 and yr[0] == "to":
                s = val(k, yr[1])
                return ("to", s), s is not None
            return yr, True
        stats, own, withs = {}, {}, {}
        for (a, i, xr), c in kind["own"].items():
            x = val(i, xr)
            if x is None:
                continue
            for yr, n in c.items():
                y, ok = change(i, yr)
                if ok:
                    own.setdefault((a, i, x), {})
                    own[(a, i, x)][y] = own[(a, i, x)].get(y, 0) + n
                    stats.setdefault((a, i), {})
                    stats[(a, i)][y] = stats[(a, i)].get(y, 0) + n
        for (a, i, xr, k, xkr), c in kind["with"].items():
            x, xk = val(i, xr), val(k, xkr)
            if x is None or xk is None:
                continue
            for yr, n in c.items():
                y, ok = change(i, yr)
                if ok:
                    d = withs.setdefault(k, {}).setdefault((a, i, x, xk), {})
                    d[y] = d.get(y, 0) + n
        room["stats"].setdefault(m, {})[name] = stats
        room.setdefault("own", {}).setdefault(m, {})[name] = own
        for k in (room.get("with") or {}):
            if k != m:
                room["with"][k].setdefault(m, {})[name] = withs.get(k, {})

    def form_classes(self, m):
        """At its old looks (each time what it saw doubled)."""
        ep = self.__dict__.get("_eproc") or {}
        b = (ep.get("belief") or {}).get(m)
        if b is not None:
            install_classes(self, m, b, finer=True)
            return
        room = self.concept_room()
        room["classes"][m] = None
        T = (ep.get("tests") or {}).get(m)
        best = T.best if T is not None else None
        room.setdefault("weighed", {})[m] = {"groups": [list(g) for g in groups_of(best[1])] if best else [],
                                             "digits": round(best[0], 1) if best else 0.0, "bar": app.EVIDENCE,
                                             "at": room["steps"], "grain": "e-process", "grains": {}}

    N.enter = enter
    N.see_concepts = see_concepts
    N.form_classes = form_classes
    app._eproc_install_classes = install_classes

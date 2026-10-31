# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Entering a world, recall, its starts and its forecasts of itself."""

import collections
import math
import os
import time

from .. import config
from ..body import CODE, OLD_SENSES, RealWorld, sense_key
from ..config import EVIDENCE, INVENT_SECONDS, ODDS_LAGS
from ..evidence import moment_trusted
from ..laws import recalled_moment
from ..learner import Learner
from ..parts import council


class Life:
    # -- living ----------------------------------------------------------------
    def enter(self, world=None):
        if self.__dict__.get("journal"):
            self.journal_close_world()
        if world is not None and world is not self.__dict__.get("world"):
            self.k += 1
        if isinstance(self.__dict__.get("world"), RealWorld) and world is not None:
            self.real_grains = dict(self.__dict__.get("grains") or {})
        elif world is None and self.__dict__.get("real_grains") and not isinstance(self.__dict__.get("world"), RealWorld):
            self.grains = self.__dict__.pop("real_grains")
        self.world = world or RealWorld(self.k, body=config.BRAIN is None)
        self.real = isinstance(self.world, RealWorld)
        self.__dict__.pop("_twins", None)
        self._control, self._watch_searched = None, 0
        if self.real:
            self.world.me = self
            keys = [sense_key(s) for s in self.world.sensors]
            had = self.__dict__.get("grain_keys") or list(OLD_SENSES)
            self.grains = {j: g for j, g in (self.__dict__.get("grains") or {}).items()
                           if j < len(keys) and j < len(had) and had[j] == keys[j]}
            self.grain_keys = keys
            self._control = next((j for j, s in enumerate(self.world.sensors) if s[0] == "control"), None)
        if not isinstance(self.world, RealWorld):
            self.grains = {}
            self.__dict__.pop("concepts", None)
            self.__dict__.pop("_class_cache", None)
        self.raw = {}
        o = self.as_levels(self.world.observe())
        self.learners = [Learner(self.world.buttons, o[j], self.eps) for j in range(len(o))]
        self.pressed = collections.Counter()
        self.tried_from, self.seen_now = collections.Counter(), o
        self.world_steps = 0
        self.mechs = []
        self.plan = self.aim = None
        self.trial, self.tried_alone = None, collections.Counter()
        self._reinvent_at, self._broke_at = None, 0
        self.real_sure, self.real_known = {}, {}
        self.foretold = []
        self.past = collections.deque(maxlen=ODDS_LAGS[-1] + 1)
        self.made, self.made_at = {}, 0
        self.clocks, self.since_change = set(), None
        self.pair_names = []
        for k in ("trap_log", "_traps", "_traps_believed", "_trap_report", "trap_next", "trap_looks", "traps_said",
                  "trap_room"):
            self.__dict__.pop(k, None)
        self._understood_here = False
        if self.real and self.gene("recall"):
            self.recall_senses()
        for f in list(self.__dict__.get("self_foretold") or ()):
            if not f.get("closed") and f.get("right") is None:
                self.self_close(f, None)
        self.__dict__.pop("last_search", None)
        self.choose_ways()
        self.emit("world", world=self.k, sensors=len(o), size=self.world.size, real=isinstance(self.world, RealWorld))

    def recall_of_senses(self):
        """What it learned of each of its real senses, kept across its starts."""
        out = {k: dict(v) for k, v in (self.__dict__.get("real_recall") or {}).items()}
        world = self.__dict__.get("world")
        if not isinstance(world, RealWorld):
            return out
        try:
            for j, L in enumerate(list(self.__dict__.get("learners") or ())):
                if j >= len(world.sensors):
                    break
                name = sense_key(world.sensors[j])
                rec = out.get(name, {})
                m = L.__dict__.get("moment")
                cell = L.moment_cell() if moment_trusted(m) else None
                if cell is not None:
                    tested = m.get("tested")
                    rec["moment"] = {"cond": {k: v for k, v in m["cond"].items() if tested is None or k in tested},
                                     "d": m["d"], "M": m["M"], "attrs": m["attrs"], "P": cell[0],
                                     "values": sorted(list(m["values"]), key=repr)[:4096]}
                if L.__dict__.get("invent_failed"):
                    rec["invent_failed"] = max(L.invent_failed, rec.get("invent_failed", 0))
                if rec:
                    out[name] = rec
        except RuntimeError:
            return {k: dict(v) for k, v in (self.__dict__.get("real_recall") or {}).items()}
        self.real_recall = out
        return out

    def recall_senses(self):
        """At each start in the real world, what it learned of its senses before."""
        keys = {sense_key(s) for s in self.world.sensors}
        names = {s[1] for s in self.world.sensors}
        rr = self.__dict__.get("real_recall") or {}
        for k in [k for k in rr if k not in keys and k.split("@")[0] in names]:
            del rr[k]
        got = dict(rr)
        if config.BRAIN is not None:
            shared = council.read_json(os.path.join(config.BRAIN["council"], "real_recall.json"), {})
            for name, rec in (shared if isinstance(shared, dict) else {}).items():
                got.setdefault(name, rec)
        recalled = []
        for j, L in enumerate(self.learners):
            if j >= len(self.world.sensors):
                break
            name = sense_key(self.world.sensors[j])
            rec = got.get(name)
            if not rec:
                continue
            mo = rec.get("moment")
            if mo:
                L.moment = recalled_moment(mo)
                recalled.append(name)
            if rec.get("invent_failed"):
                L.invent_failed = min(1, rec["invent_failed"])
        self.recalled_now = list(recalled)
        if recalled:
            self.emit("recalled", senses=recalled)
            self.decide("recall", recalled, {"laws": len(recalled)})

    def start_record(self):
        """A new start of its program in the real world."""
        for f in list(self.__dict__.get("self_foretold") or ()):
            if not f.get("closed") and f.get("right") is None:
                self.self_close(f, None)
        log = self.__dict__.setdefault("starts_log", [])
        prev = self.__dict__.get("this_start")
        if prev and (prev.get("sure") or prev.get("born") or prev.get("acts") or time.time() - prev["at"] > 60):
            log.append(prev)
            self.__dict__.setdefault("first_start", log[0])
            del log[:-10]
        self.this_start = {"at": round(time.time()), "steps": self.steps, "acts": 0, "code": CODE["print"],
                           "recalled": list(self.__dict__.get("recalled_now") or ()), "sure": {}, "born": {},
                           "foresaw": {}, "control": {"laws": 0, "moments": 0, "counts": 0, "made": 0, "machines": 0},
                           "ws": [(self.__dict__.get("workshop_view") or {}).get(k) or 0 for k in ("worlds", "understood")]}
        self.self_foretold = []
        self.__dict__.pop("_since", None)
        self.__dict__.pop("_self_pause", None)

    def start_seen(self):
        """This start, seen alive."""
        this = self.__dict__.get("this_start")
        if this is not None:
            this["acts"] = self.steps - this.get("steps", self.steps)

    def moment_eta(self, L):
        """When its law of moments for this sense will be trusted by its own rule."""
        m = L.__dict__.get("moment")
        if not m or m.get("cond") is None or moment_trusted(m) or m.get("d") is None or not m.get("times"):
            return None
        gaps = {b - a for a, b in zip(m["times"], m["times"][1:])}
        P = m.get("recalled")
        if not (P and gaps <= {P}):
            P = gaps.pop() if len(m["times"]) >= 3 and len(gaps) == 1 else None
        v = L.colors[-1]
        if not P or type(v) is not int or type(m["d"]) is not int:
            return None
        bar = EVIDENCE + math.log10(1 + m["revised"]) + 0.30103 * m["attrs"]
        proof, steps, held, values, M = m["proof"], m["steps"], m["held"], set(m["values"]), m.get("M")
        now, at = len(L.colors) - 1, m["times"][-1]
        for k in range(1, 65):
            nxt = at + P
            steps += max(0, nxt - max(at, now) - 1)
            proof += -math.log10(min(1.0, (held + 1) / (steps + 1))) + math.log10(max(2, len(values)))
            steps, held, at = steps + 1, held + 1, nxt
            v = (v + m["d"]) % M if M else v + m["d"]
            values.add(v)
            if proof >= bar:
                return k, at
        return None

    def self_make(self, what, j, sure, due, due_at, **more):
        """A forecast about itself made."""
        n = self.__dict__.get("self_n", 0) + 1
        self.self_n = n
        sensors = getattr(self.__dict__.get("world"), "sensors", None) or ()
        name = sense_key(sensors[j]) if 0 <= j < len(sensors) else what
        f = dict(more, id=n, what=what, j=j, made=self.world_steps, due=due, due_at=round(due_at), name=name,
                 sure=sure, right=None)
        self.self_foretold.append(f)
        self.journal_begin("self", ("self", n), forecast=what, sensor=j + 1 if j >= 0 else None, name=name, sure=sure,
                           due=f["due_at"])
        return f

    def self_close(self, f, right):
        """A forecast about itself checked."""
        f["closed"], f["right"] = True, right
        if f.get("id") is not None:
            self.journal_end(("self", f["id"]), "not checked" if right is None else "came true" if right else "wrong")
        self.note("self", bool(f.get("sure")), None if right is None else True, right)
        if right is None:
            return
        this = self.__dict__.get("this_start")
        if this is not None:
            row = this.setdefault("foresaw", {}).setdefault("sure" if f.get("sure") else "guess", [0, 0])
            row[0 if right else 1] += 1
        if f.get("what") == "moment" and not right:
            self.__dict__.setdefault("_self_pause", set()).add(f.get("j"))
        self.emit("foresaw_" + str(f.get("what")), sensor=(f.get("j") if f.get("j") is not None else -1) + 1,
                  due=f.get("due_at"), right=right, sure=bool(f.get("sure")), mark="✓" if right else "✗")

    def foresee_self(self):
        """Its forecasts about itself, made by its own rules, in the real world, each with the time it falls due,
        kept in its journal."""
        fl = self.__dict__.get("self_foretold")
        if fl is None:
            fl = self.self_foretold = []
        now, clock = self.world_steps, time.time()
        job, ws = self.__dict__.get("_inventing"), self.__dict__.get("workshop_view") or {}
        last = self.__dict__.get("last_search") or {}
        this = self.__dict__.get("this_start") or {}
        pause = self.__dict__.setdefault("_self_pause", set())
        for f in [f for f in fl if not f.get("closed")]:
            right = "wait"
            if f["what"] == "moment" and f["due"] is not None and f["due"] <= now:
                L = self.learners[f["j"]] if f["j"] < len(self.learners) else None
                right = bool(L is not None and moment_trusted(L.__dict__.get("moment")))
            elif f["what"] == "control" and f["due"] is not None and f["due"] <= now:
                right = not any((this.get("control") or {}).values())
            elif f["what"] in ("inventor", "gate"):
                if last.get("job") == f.get("job"):
                    if last.get("error") or last.get("world") != self.k:
                        right = None
                    elif f["what"] == "inventor":
                        b, e = last.get("began"), last.get("ended")
                        right = None if b is None or e is None else e - b <= INVENT_SECONDS + 2
                    else:
                        L = self.learners[f["j"]]
                        right = None if L.__dict__.get("invented") is not None else bool(L.__dict__.get("odds_gate"))
                elif clock >= f["due_at"] + (f["due_at"] - f.get("made_at", f["due_at"])):
                    right = False if f["what"] == "inventor" else None
            elif f["what"] == "workshop":
                if (ws.get("t") or 0) >= f["due_at"]:
                    right = (ws.get("world") or 0) > f.get("world", 0)
                elif clock >= f["due_at"] + (f["due_at"] - f.get("made_at", f["due_at"])):
                    right = False
            if right != "wait":
                self.self_close(f, right)
        have = {(f["what"], f["j"]) for f in fl if not f.get("closed")}
        control = self.__dict__.get("_control")
        for j, L in enumerate(self.learners):
            m = L.__dict__.get("moment") or {}
            if j in pause:
                if moment_trusted(m):
                    pause.discard(j)
                continue
            if (j == control or ("moment", j) in have or m.get("proof", 0) <= 0
                    or any(f["what"] == "moment" and f["j"] == j and f.get("rev") == m.get("revised") for f in fl)):
                continue
            got = self.moment_eta(L)
            if got is None or got[1] - m["times"][-1] < 2 * got[0]:
                continue
            self.self_make("moment", j, False, got[1], clock + (got[1] - now), rev=m["revised"], changes=got[0])
        if control is not None and ("control", control) not in have:
            at = 64
            while at <= now:
                at *= 2
            self.self_make("control", control, True, at, clock + (at - now))
        if job is not None and not job.get("foreseen") and job.get("world") == self.k:
            job["foreseen"] = True
            due_at = clock + INVENT_SECONDS + 2
            self.self_make("inventor", -1, False, None, due_at, job=id(job), made_at=clock)
            for j in job.get("unsure", ()):
                L = self.learners[j]
                if L.__dict__.get("invent_failed", 0) == 1 and not L.__dict__.get("odds_gate"):
                    self.self_make("gate", j, True, None, due_at, job=id(job), made_at=clock)
        t_ws = ws.get("t")
        if t_ws and t_ws != self.__dict__.get("_ws_last"):
            gap, self._ws_last = (t_ws - self._ws_last) if self.__dict__.get("_ws_last") else None, t_ws
            if ("workshop", -1) not in have and ws.get("world") != self.__dict__.get("_ws_seen"):
                self._ws_seen = ws.get("world")
                pace, left = ws.get("per_second") or 0, (ws.get("limit") or 0) - (ws.get("now") or 0)
                if gap and pace > 0 and left > 0 and left / pace >= 2 * gap:
                    self.self_make("workshop", -1, False, None, t_ws + left / pace, world=ws.get("world") or 0,
                                   made_at=clock, pace=round(pace))
        done = collections.Counter()
        keep = []
        for f in reversed(fl):
            if f.get("closed"):
                done[(f["what"], f["j"])] += 1
                if done[(f["what"], f["j"])] > 4:
                    continue
            keep.append(f)
        fl[:] = keep[::-1]

    def since(self, t=None):
        """What changed since its start before."""
        log = list(self.__dict__.get("starts_log") or ())
        this = self.__dict__.get("this_start") or {}
        if t is None:
            t = log[-1]["at"] if log else self.born
        laws = {"born": 0, "held": 0, "gone": 0, "top": []}
        for rec in reversed(self.__dict__.get("journal") or ()):
            if rec["t"] < t:
                break
            if rec["kind"] not in ("odds", "moment"):
                continue
            end = rec["end"]
            held = end is None or end.get("how") == "world ended"
            laws["born"] += 1
            laws["held" if held else "gone"] += 1
            laws["top"].append([rec["kind"], rec["facts"].get("name") or rec["facts"].get("sensor"),
                                rec["facts"].get("digits"), rec["t"], held])
        laws["top"] = sorted(laws["top"], key=lambda x: -(x[2] or 0))[:6]
        machines = sorted([n, round(lf["born"])] for n, lf in (self.__dict__.get("invented_life") or {}).items()
                          if lf.get("born", 0) >= t)[-6:]
        day = [p for p in (self.__dict__.get("history_day") or ()) if p.get("t", 0) >= t]
        growth = None
        if day:
            last = (self.__dict__.get("history") or day)[-1]
            growth = {k: [day[0].get(k, 0), last.get(k, 0)] for k in ("meanings", "words", "ideas", "read")}
        starts = [s for s in log if s.get("at", 0) >= t] + ([this] if this else [])
        ws = self.__dict__.get("workshop_view") or {}
        base = next((s["ws"] for s in starts if s.get("ws")), None)
        workshop = None if ws.get("worlds") is None or base is None else {
            "worlds": [base[0], ws.get("worlds")], "understood": [base[1], ws.get("understood")]}
        council = self.__dict__.get("council_view") or ()
        brains = {"born": [[b["name"], b.get("born")] for b in council if b.get("alive") and b.get("name") != "Nova(1)"
                           and (b.get("born") or 0) >= t][-6:],
                  "gone": [[b["name"], b.get("gone"), (b.get("why") or {}).get("code")] for b in council
                           if not b.get("alive") and (b.get("gone") or 0) >= t][-6:]}
        genes = [[c.get("gene"), str(c.get("from")), str(c.get("to")), c.get("t")]
                 for c in ((self.__dict__.get("lab_view") or {}).get("changes") or ()) if (c.get("t") or 0) >= t][-4:]
        control = None
        if self.__dict__.get("_control") is not None:
            control = {"now": dict(this.get("control") or {}), "starts": len(starts),
                       "clean": sum(1 for s in starts if s.get("control") is not None and not any(s["control"].values()))}
        return {"t": round(t), "laws": laws, "machines": machines, "growth": growth, "workshop": workshop,
                "brains": brains, "genes": genes, "control": control}

    def since_view(self):
        """What changed since it last started, for its first screen."""
        this = self.__dict__.get("this_start")
        if not this:
            return None
        got = self.__dict__.get("_since")
        if got is None or time.time() - got[0] >= 30:
            try:
                got = self._since = (time.time(), self.since())
            except (RuntimeError, KeyError, TypeError):
                got = got or (0.0, None)
        return {"this": dict(this, sure=dict(this.get("sure") or {}), born=dict(this.get("born") or {}),
                             foresaw={k: list(v) for k, v in (this.get("foresaw") or {}).items()}),
                "before": [dict(s) for s in (self.__dict__.get("starts_log") or [])[-9:]],
                "first": dict(self.__dict__.get("first_start") or {}),
                "changed": got[1],
                "forecasts": [{k: v for k, v in f.items() if k != "job"}
                              for f in (self.__dict__.get("self_foretold") or [])][-16:]}

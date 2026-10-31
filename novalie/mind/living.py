# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""One act of its life, and its inventor."""

import collections
import copy
import math
import threading
import time

from .. import config
from ..body import RealWorld, sense_key
from ..config import EVIDENCE, INVENT_SECONDS, ODDS_LAGS
from ..evidence import moment_trusted, trusted
from ..inventing import INVENTING, beyond_counts, free_memory_gb, inventor_process, kind_name, nature_text
from ..laws import seen_with, since_level
from ..parts import inventor


class Living:
    def metered(self, part, t0):
        """What one of its parts just cost."""
        dt = time.perf_counter() - t0
        use = self.__dict__.get("parts_use")
        if use is None:
            use = self.parts_use = {}
        u = use.get(part)
        if u is None:
            u = use[part] = [0, 0.0, 0.0]
        u[0] += 1
        u[1] += dt
        if dt > u[2]:
            u[2] = dt

    def step(self):
        tt = time.perf_counter
        t0 = tt()
        a = self.choose()
        self.metered("choose", t0)
        if getattr(self, "pressed", None) is None:
            self.pressed = collections.Counter()
        self.pressed[a] += 1
        if getattr(self, "tried_from", None) is None:
            self.tried_from = collections.Counter()
        self.tried_from[(getattr(self, "seen_now", None), a)] += 1
        t0 = tt()
        was = self.__dict__.get("seen_now")
        ep_key = self.episode_key(was, a) if was is not None and self.gene("episodes") else None
        ep_cell = self.episodes_room()["cells"].get(ep_key) if ep_key is not None else None
        ep_fore = self.foresee_next(a, episodes=False) if ep_cell is not None else None
        self.metered("episodes", t0)
        self.world.press(a)
        if getattr(self.world, "jumped", False):
            self.decide("rebase", self.world.t, {"steps": self.world_steps})
            self.enter()
            return
        o = self.as_levels(self.world.observe())
        if ep_key is not None:
            t0 = tt()
            self.see_episode(ep_key, ep_cell, ep_fore, o)
            self.metered("episodes", t0)
        if isinstance(self.world, RealWorld) and self.world.body and config.BRAIN is None:
            t0 = tt()
            self.twins_see(a, o)
            self.metered("twins", t0)
        if isinstance(self.world, RealWorld) and self.world.body:
            self.effect_count(a, o)
        seen, self.seen_now = getattr(self, "seen_now", None), o
        named = self.named_senses()
        if getattr(self, "foretold", None):
            for f in [f for f in self.foretold if f["due"] <= self.world_steps + 1]:
                self.foretold.remove(f)
                right = all(o[j] == v for j, v in f["values"].items()) if f["values"] else None
                for j, v in f["values"].items():
                    self.note("answer", True, v, o[j])
                if right is not None:
                    self.emit("foretold", asked=f["text"], right=right, values={str(j + 1): v for j, v in f["values"].items()},
                              saw={str(j + 1): o[j] for j in f["values"]})
        self._worth = {j: L.worth(x) for j, (L, x) in enumerate(zip(self.learners, o))}
        t0 = tt()
        for j, (L, x) in enumerate(zip(self.learners, o)):
            if getattr(L, "invented", None) is None and j in named:
                r = getattr(L, "recognized", None)
                if r is None and L.odds_cell() is not None:
                    g, pr = self.odds_next(j, a)
                    self.note("odds", False, g, x)
                    row = L.odds["cal"].setdefault(min(9, int(10 * pr)), [0, 0])
                    row[0] += 1
                    row[1] += g == x
                else:
                    try:
                        g = r["T"][(r["p"] + r["eff"].get(a, 0)) % r["d"]] if r is not None else L.table.get(L.model.step(L.key, a))
                    except Exception:
                        g = None
                    self.note("kind" if r is not None else "counts", trusted(r) if r is not None else L.counts_closed(), g, x)
            revised = L.revisions
            L.observe(a, x)
            if L.revisions > revised and j in named:
                with self.lock:
                    self.urge += 0.3
            if not getattr(L, "noted", False) and L.counts_closed() and j in named:
                L.noted = True
                if getattr(L, "invented", None) is None and getattr(L, "recognized", None) is None:
                    self.sure_at.append(self.world_steps)
                    del self.sure_at[:-400]
                    self._invent_at = None
        self.metered("counts", t0)
        t0 = tt()
        for j, L in enumerate(self.learners):
            if len(L.colors) >= 2:
                state = {f"s{i}": x for i, x in enumerate(o) if i != j and i in named}
                state["act"] = a
                L.see_moment(L.colors[-2], o[j], state)
                m = L.moment
                if moment_trusted(m) and not m["announced"]:
                    m["announced"] = True
                    cond = {k: v for k, v in m["cond"].items() if k != "act" or len(self.world.buttons) > 1}
                    self.emit("moment", sensor=j + 1, cond=cond, d=m["d"], M=m["M"], proof=round(m["proof"], 1))
                    self.decide("moment", j + 1, {"cond": cond, "d": m["d"], "proof": round(m["proof"], 1)})
                    bar = EVIDENCE + math.log10(1 + m["revised"]) + 0.30103 * m["attrs"]
                    self.journal_begin("moment", ("moment", self.k, j), sensor=j + 1,
                                       name=sense_key(self.world.sensors[j]) if j < len(getattr(self.world, "sensors", ()))
                                       else None, digits=round(m["proof"], 1), margin=round(m["proof"] - bar, 1),
                                       recalled=bool(m.get("recalled")))
                elif not moment_trusted(m) and m["announced"]:
                    m["announced"] = False
                    self.journal_end(("moment", self.k, j), "refuted")
        self.metered("moments", t0)
        past = self.__dict__.get("past")
        if past is None:
            past = self.past = collections.deque(maxlen=ODDS_LAGS[-1] + 1)
        prev = past[-1] if past else None
        ordinal = {i for i, L in enumerate(self.learners) if len(L.__dict__.get("seen_freq") or ()) > 2}
        before = None if prev is None or seen is None else list(seen)
        entry = seen_with(o, before, a, ordinal, named)
        t0 = tt()
        since = self.__dict__.get("since_change")
        if since is None or len(since) != len(o):
            since = self.since_change = [0] * len(o)
        for i in range(len(o)):
            since[i] = 0 if seen is None or i >= len(seen) or o[i] != seen[i] else since[i] + 1
        for i in self.__dict__.get("clocks") or ():
            if i < len(o):
                entry[f"t{i}"] = since_level(since[i])
        entry.update(self.made_seen(o))
        self.pairs_seen(entry, past)
        self.metered("seeing", t0)
        if before is not None:
            t0 = tt()
            self.see_concepts(before, a, o)
            self.metered("concepts", t0)
        past.append(entry)
        if before is not None:
            t0 = tt()
            self.see_traps(before, a, o)
            self.metered("imagine", t0)
        t0 = tt()
        for j, L in enumerate(self.learners):
            if len(L.colors) >= 2 and not L.held():
                L.see_odds(j, past, L.colors[-2], o[j])
                if L.odds["steps"] >= L.odds["next"]:
                    self.judge_odds(j)
        self.metered("odds", t0)
        t0 = tt()
        self.see_made()
        self.metered("made", t0)
        self.steps += 1
        self.world_steps += 1
        if self.world_steps - getattr(self, "episode_at", 0) in self.recognize_times():
            t0 = tt()
            for L in self.learners:
                if getattr(L, "recognized", None) is None and not L.sure():
                    self.recognize(L)
            self.metered("recognize", t0)
        t0 = tt()
        if self.mechs:
            self.follow(a, o)
        self.plan_watch(o)
        if self.mechs and getattr(self, "plan", None) is None and self.world_steps % 25 == 0:
            self.make_plan()
        self.metered("machines", t0)
        t0 = tt()
        if (self.world_steps - getattr(self, "episode_at", 0) in self.invent_times()
                or self.world_steps == getattr(self, "_reinvent_at", None)):
            self.invent_for()
        job = getattr(self, "_inventing", None)
        if job is not None and (job["done"] or job["future"] is not None and job["future"].done()):
            self.adopt(job)
        self.metered("invent", t0)
        t0 = tt()
        if isinstance(self.world, RealWorld):
            this = self.__dict__.get("this_start")
            named, control = self.named_senses(), self.__dict__.get("_control")
            for j, L in enumerate(self.learners):
                sure = L.sure()
                how = ("exact" if L.exact() else "odds") if sure else False
                if (sure and j in named
                        and (not self.real_sure.get(j) or (how == "exact" and self.real_sure.get(j) == "odds"))):
                    self.understood(only=j)
                self.real_sure[j] = how
                if sure and this is not None and j < len(self.world.sensors):
                    this["sure"].setdefault(sense_key(self.world.sensors[j]), self.world_steps)
                if j == control and this is not None and L.counts_closed() and not this.get("control_counts"):
                    this["control_counts"] = True
                    self.control_mark("counts")
            self.foresee_self()
        elif (not self.__dict__.get("_understood_here") and all(L.sure() for L in self.learners)
              and self.settled()):
            self._understood_here = True
            self.understood()
        self.metered("understand", t0)
        if self.world_steps >= 172_800:
            self.enter(None if isinstance(self.world, RealWorld) else self.world)
        if self.steps % 500 == 0:
            t0 = tt()
            self.reorganize()
            self.metered("reorganize", t0)
        if self.urge > 3.0:
            self.urge = 3.0
        if self.urge >= 1.0 and self.steps - self.last_step_said >= 25 and time.time() - self.last_time_said >= 15:
            t0 = tt()
            self.speak()
            self.metered("talk", t0)

    def settled(self):
        """A world it is given, all of its senses sure."""
        if not any(L.odds_cell() is not None and not L.exact() for L in self.learners):
            return True
        now = self.ties()
        mark = self.__dict__.get("_settle")
        if mark is None or mark[2] != self.k:
            self._settle = (self.world_steps, now, self.k, 0)
            return False
        if self.world_steps < 2 * mark[0]:
            return False
        if now <= mark[1] or mark[3] >= 2:
            return True
        self._settle = (self.world_steps, now, self.k, mark[3] + 1)
        return False

    def ties(self):
        """Which of its senses its laws of odds join."""
        out = set()
        for j, L in enumerate(self.learners):
            od = L.__dict__.get("odds")
            if not od:
                continue
            for d, rules in od["laws"].items():
                for law in rules:
                    for (l, attr, v) in [law["cond"]] + [tuple(x[1]) for x in law["unless"] + law["especially"]]:
                        if not isinstance(attr, str):
                            continue
                        if attr.startswith("cmp:"):
                            out.update((j, int(x)) for x in attr.split(":")[1:] if x.isdigit() and int(x) != j)
                        elif attr[:1] in ("c", "s") and attr[1:].isdigit() and int(attr[1:]) != j:
                            out.add((j, int(attr[1:])))
        return frozenset(out)

    def invent_times(self):
        """When it tries to invent."""
        if getattr(self, "_invent_at", None) is None:
            chosen = self.way("invent_at", "learned")
            got = sorted(self.sure_at)
            if chosen != "learned":
                t = int(chosen)
            else:
                t = 1600 if len(got) < 40 else int(min(1600, max(300, 1.25 * got[int(0.95 * (len(got) - 1))])))
            self._invent_at = tuple(t * 2 ** k for k in range(40))
        return self._invent_at

    def recognize_times(self):
        """When it tries its library in a world."""
        s = self.way("recognize", 1.0)
        return {max(10, int(x * s)) for x in (60, 150, 300, 600) + tuple(1200 * 2 ** k for k in range(30))}

    def note(self, tool, sure, guess, seen):
        """Its ledger: what one of its tools foresaw for one sensor, against what it saw."""
        row = self.ledger.setdefault(f"{tool}:{'sure' if sure else 'unsure'}", [0, 0, 0])
        row[2 if guess is None else 0 if guess == seen else 1] += 1
        if sure and guess is not None and guess != seen:
            last = getattr(self, "_surprised", {})
            if time.time() - last.get(tool, 0) > 60:
                last[tool] = time.time()
                self._surprised = last
                self.emit("surprise", tool=tool, expected=str(guess), saw=str(seen), world=self.k)
        if sum(row) > 200_000:
            for k in self.ledger:
                self.ledger[k] = [x // 2 for x in self.ledger[k]]

    def make_plan(self):
        """A plan with a machine it holds here."""
        if getattr(self, "plan", None) or not self.mechs:
            return
        rec = self.mechs[0]
        mech, j = rec["mech"], rec["sensors"][0]
        seen = collections.Counter(self.learners[j].colors)
        goals = sorted(set(mech.maps[0].values()), key=lambda s: (seen[s], str(s)))
        for goal in goals[:2]:
            path = inventor.plan(copy.copy(mech), len(self.world.buttons), goal, sensor=0, depth=30)
            if path:
                self.plan = {"presses": list(path), "goal": goal, "sensor": j, "name": rec["name"]}
                self.plans["made"] += 1
                self.decide("plan", str(goal), {"presses": len(path), "seen": seen[goal], "machine": rec["name"]})
                self.emit("plan", s=rec["name"], goal=str(goal), presses=len(path), world=self.k)
                return

    def plan_watch(self, o):
        """Its plan, watched: reached when its last press brings what it planned."""
        plan = getattr(self, "plan", None)
        if plan is None:
            return
        if not any(rec["name"] == plan["name"] for rec in self.mechs):
            self.plans["dropped"] += 1
            self.emit("plan_dropped", s=plan["name"], world=self.k)
            self.plan = None
        elif not plan["presses"]:
            self.plans["reached" if o[plan["sensor"]] == plan["goal"] else "missed"] += 1
            self.plan = None

    def follow(self, a, o):
        """Its invented mechanisms here, one press at a time."""
        for rec in list(self.mechs):
            mech = rec["mech"]
            mech.step(a)
            ok = True
            for i, j in enumerate(rec["sensors"]):
                v = inventor.see(mech.looks[i], *mech.state)
                had = mech.maps[i].get(v, inventor.MISSING)
                self.note("machine", trusted(rec), None if had is inventor.MISSING else had, o[j])
                if mech.maps[i].setdefault(v, o[j]) != o[j]:
                    ok = False
            if ok:
                rec["calm"] += 1
                rec["proof"] = rec.get("proof", 0.0) + sum(getattr(self, "_worth", {}).get(j, 0.0) for j in rec["sensors"])
                continue
            self.mechs.remove(rec)
            for j in rec["sensors"]:
                self.learners[j].invented = None
            self.emit("invention_failed", s=rec["name"], world=self.k)
            self._reinvent_at = self.world_steps + 600
            self._broke_at = self.world_steps
            self.decide("adapt", rec["name"], {"steps": self.world_steps})

    def invent_for(self):
        """Sensors its laws of counts could not close."""
        job = getattr(self, "_inventing", None)
        if job is not None and not job["done"]:
            return
        if config.BRAIN is not None:
            return
        if free_memory_gb() < 1.0:
            return
        named = self.named_senses()
        unsure = sorted((j for j, L in enumerate(self.learners)
                         if not L.sure() and getattr(L, "recognized", None) is None
                         and getattr(L, "invented", None) is None
                         and (j in named or L.__dict__.get("invent_failed", 0) < 2)), key=lambda j: (j not in named, j))
        if not unsure or not any(j in named for j in unsure) and self.__dict__.get("_watch_searched", 0) >= 2:
            return
        start = max(0, len(self.learners[unsure[0]].actions) - 2400, getattr(self, "_broke_at", 0) or 0)
        acts = list(self.learners[unsure[0]].actions)[start:start + 2400]
        n = len(acts)
        cols = {j: list(L.colors[start:start + n + 1]) for j, L in enumerate(self.learners)}
        moved = {j: [c[t + 1] != c[t] for t in range(n)] for j, c in cols.items()}
        pairs = []
        for j in unsure:
            if j in named and sum(moved[j]) >= 5:
                pairs += [[i, j] for i in cols if i != j and i in named and sum(moved[i]) > sum(moved[j])
                          and all(moved[i][t] for t in range(n) if moved[j][t])]
        both = [j for j in unsure if j in named][:2]
        groups = pairs[:2] + ([both] if len(both) == 2 and len([j for j in unsure if j in named]) == 2 else []) \
            + [[j] for j in unsure]
        if not any(j in named for j in unsure):
            self._watch_searched = self.__dict__.get("_watch_searched", 0) + 1
        cols = {j: cols[j] for g in groups for j in g}
        job = {"world": self.k, "n": n, "start": start, "done": False, "found": [], "error": None, "future": None,
               "unsure": list(unsure)}
        self.decide("invent", unsure, {"steps": self.world_steps, "way": str(self.way("invent_at", "learned"))})
        library = [dict(e) for e in self.inventions]
        args = (acts, cols, groups, len(self.world.buttons), library)
        self.emit("inventing", world=self.k, sensors=len(unsure))
        self._inventing = job
        try:
            job["future"] = inventor_process().submit(inventor.work, *args, int(4_000_000 * self.gene("think")),
                                                      INVENT_SECONDS)
            return
        except Exception:
            pass

        def work():
            try:
                job["found"] = inventor.work(*args, int(4_000_000 * self.gene("think")), INVENT_SECONDS)
            except Exception as e:
                job["error"] = f"{type(e).__name__}: {e}"[:200]
            job["done"] = True

        threading.Thread(target=work, daemon=True, name="inventing").start()

    def adopt(self, job):
        """What its thread invented."""
        self._inventing = None
        if job["future"] is not None:
            try:
                job["found"] = job["future"].result()
                if getattr(job["found"], "card", None):
                    self.inventor_card = dict(job["found"].card, at=round(time.time()))
            except Exception as e:
                job["error"] = f"{type(e).__name__}: {e}"[:200]
                while INVENTING:
                    INVENTING.pop().shutdown(wait=False)
        found = job.get("found")
        self.last_search = {"job": id(job), "world": job["world"], "error": job["error"],
                            "began": getattr(found, "began", None), "ended": getattr(found, "ended", None)}
        if job["error"]:
            self.emit("trouble", where="inventing", what=job["error"])
        if job["world"] != self.k:
            return
        for g, mech, tried in job["found"]:
            stuck = any(0 in getattr(self.learners[j].model, "mods", ()) for j in g)
            if not beyond_counts(mech) and not stuck:
                continue
            if any(getattr(self.learners[j], "invented", None) is not None for j in g):
                continue
            L0, ok = self.learners[g[0]], True
            for t in range(job.get("start", 0) + job["n"], len(L0.actions)):
                mech.step(L0.actions[t])
                for i, j in enumerate(g):
                    want = self.learners[j].colors[t + 1]
                    if mech.maps[i].setdefault(inventor.see(mech.looks[i], *mech.state), want) != want:
                        ok = False
            if not ok:
                self.emit("invention_failed", s=mech.name.replace(" ", ""), world=self.k)
                continue
            if self.__dict__.get("_control") in g:
                self.control_mark("machines")
            if any(j not in self.named_senses() for j in g):
                rec = {"mech": mech, "sensors": list(g), "calm": 0, "name": mech.name.replace(" ", ""),
                       "proof": 0.0, "tests": max(1, tried or 1), "nature": nature_text(mech.shape)}
                self.mechs.append(rec)
                for j in g:
                    self.learners[j].invented = rec
                continue
            with self.lock:
                had = len(self.inventions)
                entry = inventor.keep(self.inventions, mech, self.k)
                del entry["uses"][:-20]
                new = len(self.inventions) > had
                name = kind_name(entry)
                entry["symbol"] = name
                entry["last"] = {"mechanism": mech.name.replace(" ", ""), "evidence": round(mech.evidence),
                                 "tried": tried, "world": self.k, "sensors": len(g),
                                 "laws": inventor.laws(mech)}
                self.salient[name] += 1.5 if new else 0.5
                self.urge += 0.8 if new else 0.3
            rec = {"mech": mech, "sensors": list(g), "calm": 0, "name": name, "proof": 0.0,
                   "tests": max(1, tried or 1),
                   "nature": nature_text(mech.shape)}
            self.mechs.append(rec)
            for j in g:
                self.learners[j].invented = rec
            self.emit("invented", s=name, new=new, sensors=len(g), tried=tried, evidence=round(mech.evidence),
                      world=self.k)
        if not job["error"]:
            for j in job.get("unsure", ()):
                if j < len(self.learners) and getattr(self.learners[j], "invented", None) is None:
                    L = self.learners[j]
                    L.invent_failed = L.__dict__.get("invent_failed", 0) + 1
                    if L.invent_failed >= 2:
                        L.odds_gate = True

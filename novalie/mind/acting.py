# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Acting: imagination, traps, the law of effect, experiments."""

import collections
import math

from ..body import RealWorld, sense_key
from ..config import EVIDENCE, room
from ..evidence import low_tail, paid, trusted, two_rates_digits
from ..laws import PAIRS, causal, is_pair
from ..parts import nm


class Acting:
    def choose(self):
        """Its act, imagined before it is done."""
        a = self.choose_plain()
        traps = self.traps() if self.__dict__.get("imagine", True) and self.gene("imagine") and self.learners else {}
        if not traps:
            return a
        believed = self.__dict__.get("_traps_believed") or {}
        now = [L.colors[-1] if L.colors else None for L in self.learners]

        def risk(b):
            worst, total = None, 0.0
            for (j, v), x in believed.items():
                if (j, now[j]) in believed:
                    continue
                p = (self.odds_of(j, b) or {}).get(v, 0.0)
                total += p * x["h"]
                if p > 0 and (worst is None or p * x["h"] > worst[0]):
                    worst = (p * x["h"], j, v, p, x["h"])
            return total, worst
        ra, wa = risk(a)
        if ra <= 0:
            return a
        pressed = self.__dict__.get("pressed") or collections.Counter()
        others = {b: risk(b) for b in range(len(self.world.buttons)) if b != a}
        safer = [b for b, x in others.items() if x[0] < ra - 1e-12]
        if not safer:
            return a
        b = min(safer, key=lambda b: (round(others[b][0], 12), pressed[b], b))
        _, j, v, p, h = wa
        self.spared = self.__dict__.get("spared", 0) + 1
        self.decide("spare", b, {"instead": a, "sensor": j + 1, "trap": self.display(v) if isinstance(v, str) else v,
                                 "odds": round(p, 3), "horizon": h, "odds_now": round(others[b][0] / h, 3)})
        return b

    def odds_of(self, j, a):
        """Its odds of each value sense j shows after act a."""
        L = self.learners[j]
        r = getattr(L, "recognized", None)
        try:
            if r is not None and trusted(r):
                return {r["T"][(r["p"] + r["eff"].get(a, 0)) % r["d"]]: 1.0}
            if getattr(L, "invented", None) is None and L.counts_closed():
                v = L.table.get(L.model.step(L.key, a))
                return None if v is None else {v: 1.0}
        except Exception:
            return None
        if not L.colors:
            return None
        od, now = L.odds_room(), L.colors[-1]
        past = self.__dict__.get("past") or ()

        def held(c):
            l, attr, v = c
            if l == 0 and attr == "act":
                return float(a == v)
            if 1 <= l <= len(past):
                return float(past[-l].get(attr) == v)
            return None
        ch = od["chain"].get(now)
        probs = {d: k / ch[0] for d, k in ch[1].items()} if ch and ch[0] else {}
        for d, rules in od["laws"].items():
            probs[d] = self.list_odds(od, rules, held)
        probs = {d: x for d, x in probs.items() if self.odds_target(L, now, d) is not None}
        total = sum(probs.values())
        if total > 1:
            probs, total = {d: x / total for d, x in probs.items()}, 1.0
        out = collections.defaultdict(float)
        out[now] += 1 - total
        for d, x in probs.items():
            out[self.odds_target(L, now, d)] += x
        return dict(out)

    def see_traps(self, before, a, o):
        """Values with no return."""
        log = self.__dict__.get("trap_log")
        if log is None:
            log = self.trap_log = {"x0": collections.deque(), "x1": collections.deque(), "a": collections.deque(),
                                   "hist": {}, "first": 1}
        log["x0"].append(tuple(before))
        log["x1"].append(tuple(o))
        log["a"].append(a)
        log["hist"][log["first"] + len(log["a"]) - 1] = self.past[-1]
        if len(log["a"]) > room(20_000):
            for k in ("x0", "x1", "a"):
                log[k].popleft()
            log["hist"].pop(log["first"], None)
            log["first"] += 1

    def trap_holds(self, c, t):
        """Did condition c (lag, attr, value) hold at act t of its trap log."""
        l, attr, v = c
        if is_pair(attr):
            parts = PAIRS.get(attr)
            return parts is not None and all(self.trap_holds((l + p[0], p[1], p[2]), t) for p in parts) == bool(v)
        e = self.trap_log["hist"].get(t - l)
        return e is not None and e.get(attr) == v

    def exit_laws(self, j, v):
        """The laws of odds of sense j for changes out of value v, their causes only."""
        L = self.learners[j]
        od = L.__dict__.get("odds") or {}
        out = []
        for d, rules in sorted((od.get("laws") or {}).items(), key=lambda kv: repr(kv[0])):
            tg = (v + d) if type(d) is int and type(v) is int else (d[1] if isinstance(d, tuple) else None)
            if tg is not None and tg != v and tg in (L.__dict__.get("seen_freq") or ()):
                kept = [dict(r, unless=[e for e in r["unless"] if causal(tuple(e[1]))],
                             especially=[e for e in r["especially"] if causal(tuple(e[1]))])
                        for r in rules if causal(tuple(r["cond"]))]
                if kept:
                    out.append((d, kept))
        return out

    @staticmethod
    def has_act(c):
        l, attr, v = c
        if attr == "act":
            return True
        return is_pair(attr) and any(Novalie.has_act(p) for p in PAIRS.get(attr, ()))

    def moved_by_acts(self, i):
        """Is sense i one its acts move."""
        L = self.learners[i]
        if L.counts_closed():
            return self.set_by_acts(i)
        od = L.__dict__.get("odds") or {}
        return any(self.has_act(tuple(r["cond"])) and causal(tuple(r["cond"]))
                   for rules in (od.get("laws") or {}).values() for r in rules)

    def brought(self, c, j):
        """Can it bring condition c about by its acts."""
        l, attr, v = c
        if is_pair(attr):
            got = [self.brought((l + p[0], p[1], p[2]), j) for p in PAIRS.get(attr, ())]
            return None if not got or any(g is None for g in got) else max(got)
        if attr == "act":
            return 0
        if attr[0] in "sc" and attr[1:].isdigit() and int(attr[1:]) != j and self.moved_by_acts(int(attr[1:])):
            return 1
        return None

    def traps(self):
        """The values with no return it believes now, {(sense, value)."""
        log = self.__dict__.get("trap_log")
        if not log or self.world_steps < self.__dict__.get("trap_next", 50):
            return self.__dict__.get("_traps") or {}
        self.trap_next = self.world_steps + max(50, self.world_steps // 10)
        self.trap_looks = self.__dict__.get("trap_looks", 0) + 1
        x0s, x1s, acts = list(log["x0"]), list(log["x1"]), list(log["a"])
        T, acts_n, first = len(acts), len(self.world.buttons), log["first"]
        per = []
        named = self.named_senses()
        for j in range(len(self.learners)):
            if j not in named:
                continue
            at = collections.defaultdict(list)
            for i in range(T):
                at[x0s[i][j]].append(first + i)
            for v, ts in sorted(at.items(), key=lambda kv: repr(kv[0])):
                if v is None or len(at) < 2:
                    continue
                laws = self.exit_laws(j, v)
                cells = collections.defaultdict(lambda: [0, 0])
                for t in ts:
                    key = [acts[t - first]]
                    for d, rules in laws:
                        i = next((i for i, r in enumerate(rules) if self.trap_holds(tuple(r["cond"]), t)), len(rules))
                        e = -1
                        if i < len(rules):
                            es = rules[i]["unless"] + rules[i]["especially"]
                            e = next((k for k, x in enumerate(es) if self.trap_holds(tuple(x[1]), t)), -1)
                        key.append((i, e))
                    c = cells[tuple(key)]
                    c[0] += 1
                    c[1] += x1s[t - first][j] != v
                per.append((j, v, dict(cells), laws, ts))
        bar = EVIDENCE + math.log10(max(1, len(per))) + paid(self.trap_looks)
        believed, report = {}, []
        for j, v, cells, laws, ts in per:
            done = {key[0] for key in cells}
            if len(done) < acts_n:
                report.append((j, v, None, "untried"))
                continue
            best_h, best_dig = None, None
            for h in (1, 2, 4, 8, 16, 32, 64):
                r = 1 - 2 ** (-1 / h)
                digs = [-low_tail(n, x, r) for n, x in cells.values()]
                if min(digs) < bar:
                    break
                ways_out = [(c, q) for d, rules in laws for law in rules
                            for c, q in [(tuple(law["cond"]), law["q"])] + [(tuple(e[1]), e[2]) for e in
                                                                             law["unless"] + law["especially"]] if q >= r]
                blocked = False
                for c, q in ways_out:
                    if any(self.trap_holds(c, t) for t in ts):
                        continue
                    parts = PAIRS.get(c[1], [c]) if is_pair(c[1]) else [c]
                    if all(p[1] == "act" or any(self.trap_holds(p, t) for t in ts) for p in parts):
                        blocked = True
                        break
                if blocked:
                    break
                best_h, best_dig = h, round(min(digs), 1)
            if best_h is None:
                report.append((j, v, None, "leaves"))
                continue
            power = None
            for u in sorted({x[j] for x in x0s} - {v, None}, key=repr):
                for d, rules in self.exit_laws(j, u):
                    for law in rules:
                        for c, q in [(tuple(law["cond"]), law["q"])] + [(tuple(e[1]), e[2]) for e in
                                                                        law["unless"] + law["especially"]]:
                            more = self.brought(c, j)
                            if more is None or q <= 0 or not (self.has_act(c) or more):
                                continue
                            hx = more + (1 if q >= 0.5 else math.ceil(math.log(0.5) / math.log(1 - min(q, 1 - 1e-12))))
                            if power is None or hx < power[0]:
                                power = (hx, u, c, q)
            if power is None or power[0] >= best_h:
                report.append((j, v, best_h, "no power elsewhere"))
                continue
            believed[(j, v)] = {"h": best_h, "digits": best_dig, "bar": round(bar, 1), "elsewhere": power[0]}
            report.append((j, v, best_h, "trap", best_dig, round(bar, 1)))
        said = self.__dict__.get("traps_said")
        if not isinstance(said, dict):
            said = self.traps_said = {}
        for (j, v), x in believed.items():
            if said.get((j, v)) != x["h"]:
                said[(j, v)] = x["h"]
                self.decide("trap", j + 1, {"value": self.display(v) if isinstance(v, str) else v, "horizon": x["h"],
                                            "digits": x["digits"], "bar": x["bar"], "elsewhere": x["elsewhere"]})
        self._traps_believed, self._trap_report = believed, report
        self._traps = {k: x["digits"] for k, x in believed.items()}
        return self._traps

    def choose_plain(self):
        goal = getattr(self, "odds_goal", None)
        if goal and goal["j"] < len(self.learners):
            got = self.plan_odds(goal["j"], goal["goal"], goal["H"])
            if got is not None:
                lo, hi = goal["goal"] if isinstance(goal["goal"], tuple) else (goal["goal"], goal["goal"])
                v = self.learners[goal["j"]].colors[-1]
                goal["acts"] += 1
                goal["held"] += v is not None and type(v) is not str and lo <= v <= hi
                return got[0][0]
        named = self.named_senses()
        again = [L for j, L in enumerate(self.learners) if j in named
                 and (L.__dict__.get("odds") or {}).get("again") is not None]
        for L in again:
            if L.odds["laws"] or L.exact():
                L.odds["again"] = None
        trial = next((L.odds["again"] for L in again if L.odds.get("again") is not None), None)
        if trial is not None:
            b = min(range(len(self.world.buttons)), key=lambda b: (trial[b], b))
            trial[b] += 1
            return b
        tell = self.telling_act()
        if tell is not None:
            tells, a, m = tell
            sym = (self.__dict__.get("past") or [{}])[-1].get(f"s{m}")
            if getattr(self, "_told", None) != (m, sym):
                self._told = (m, sym)
                shown = self.display(sym) if isinstance(sym, str) else sym
                self.decide("telling", a, {"sensor": m + 1, "thing": shown, "tells": round(tells, 3)})
            return a
        plan = getattr(self, "plan", None)
        if plan:
            a = plan["presses"].pop(0)
            if 0 <= a < len(self.world.buttons):
                return a
            self.plan = None
        how = self.way("explore", "nearest")
        pressed = getattr(self, "pressed", None) or collections.Counter()
        here = getattr(self, "seen_now", None)
        tried = getattr(self, "tried_from", None) or collections.Counter()
        least = sorted(range(len(self.world.buttons)), key=lambda b: (tried[(here, b)], pressed[b], b))
        effect = self.effect_act()
        if effect is not None:
            return effect
        body = self.body_unknown()
        if body and self.world_steps >= 300:
            return self.experiment(body)
        if how == "least_pressed":
            return least[0]
        open_now = tuple(j for j, L in enumerate(self.learners) if j in named and not L.sure())
        stuck = [j for j in open_now if 0 in self.learners[j].model.mods
                 and getattr(self.learners[j], "invented", None) is None
                 and getattr(self.learners[j], "recognized", None) is None and not self.learners[j].noisy()]
        if stuck and self.world_steps >= 300 and len(self.world.buttons) > 1:
            return self.experiment(stuck)
        if open_now != getattr(self, "_open_now", None):
            self._open_now = open_now
            if open_now:
                self.decide("pursue", list(open_now), how)
        chase = [j for j in open_now if not self.learners[j].noisy()]
        if open_now and not chase:
            self.aim = None
            return least[0]
        aim = getattr(self, "aim", None)
        if aim and aim["path"] and aim["j"] in chase and self.learners[aim["j"]].revisions == aim["rev"]:
            a = aim["path"].pop(0)
            if 0 <= a < len(self.world.buttons):
                return a
        unsure = chase or sorted(named)
        if how == "least":
            unsure = [min(unsure, key=lambda j: (len(self.learners[j].table)
                                                 / max(1, math.prod(self.learners[j].model.mods) or 1), j))]
        best = None
        for j in unsure:
            L = self.learners[j]
            if 0 in L.model.mods:
                continue
            path = nm.bfs_path(L.model, L.key, known=L.table, limit=2000, order=least)
            if path:
                rank = (0 in L.model.mods, len(path), len(L.table), j)
                if best is None or rank < best[0]:
                    best = (rank, j, path)
        if best is None:
            self.aim = None
            return least[0]
        _, j, path = best
        self.aim = {"j": j, "path": path[1:], "rev": self.learners[j].revisions}
        return path[0]

    def effect_act(self):
        """Its drive, by the law of effect, in the real world."""
        w = self.__dict__.get("world")
        if not isinstance(w, RealWorld) or not w.body:
            return None
        tally, m = self.__dict__.get("effect_tally") or {}, len(w.buttons)
        bar = EVIDENCE + math.log10(m * max(1, len(tally)))
        best = None
        for j, rows in sorted(tally.items()):
            for v, (n, k) in sorted(rows.items()):
                n0, k0 = sum(r[0] for u, r in rows.items() if u != v), sum(r[1] for u, r in rows.items() if u != v)
                e = two_rates_digits(n, k, n0, k0) if 0 <= v < m else 0.0
                if e >= bar and (best is None or k / n > best[0]):
                    best = (k / n, v, j, e)
        was, turns = self.__dict__.get("_effect"), self.__dict__.get("effect_turns")
        if was is not None and (best is None or (best[1], best[2]) != was):
            rows = tally.get(was[1], {})
            n, k = rows.get(was[0], (0, 0))
            n0, k0 = sum(r[0] for u, r in rows.items() if u != was[0]), sum(r[1] for u, r in rows.items() if u != was[0])
            if n and k * max(1, n0) > k0 * n:
                best = (k / n, was[0], was[1], two_rates_digits(n, k, n0, k0))
        if best is None:
            if was is not None:
                self._effect = None
                self.decide("effect", None, {"sensor": was[1] + 1})
            if turns is not None:
                v = min(range(m), key=lambda b: (turns.get(b, 0), b))
                turns[v] = turns.get(v, 0) + 1
                return v
            return None
        q, v, j, e = best
        self.effect_turns = None
        if was != (v, j):
            self._effect, self._effect_misses = (v, j), 0
            n = self.__dict__.setdefault("effect_counts", {})
            n["came"] = n.get("came", 0) + 1
            self.decide("effect", v, {"sensor": j + 1, "q": round(q, 3), "digits": round(e, 1)})
            self.emit("effect", act=v, sensor=j + 1, q=round(q, 3))
        if self.__dict__.get("_effect_misses", 0) * -math.log10(max(1e-9, 1.0 - min(q, 0.999))) >= bar:
            tally.pop(j, None)
            self._effect, self._effect_misses = None, 0
            self.effect_turns = {}
            n = self.__dict__.setdefault("effect_counts", {})
            n["broke"] = n.get("broke", 0) + 1
            self.decide("effect", None, {"sensor": j + 1, "broken": True})
            self.emit("effect_broken", act=v, sensor=j + 1)
            return None
        return v

    def effect_count(self, a, o):
        """What this act brought to its senses of what it learns and reads."""
        w, keys = self.world, [sense_key(s) for s in self.world.sensors]
        if self.__dict__.get("effect_senses") != keys:
            self.effect_senses, self.effect_tally, self._effect = keys, {}, None
        tally, e = self.effect_tally, self.__dict__.get("_effect")
        for j, s in enumerate(w.sensors):
            if s[0] == "self" and s[1] in ("learned", "reading") and j < len(o):
                got = isinstance(o[j], (int, float)) and o[j] > 0
                row = tally.setdefault(j, {}).setdefault(a, [0, 0])
                row[0] += 1
                row[1] += got
                if e is not None and e == (a, j):
                    self._effect_misses = 0 if got else self.__dict__.get("_effect_misses", 0) + 1

    def body_unknown(self):
        """The senses of its own body."""
        named = self.named_senses()
        private = sorted(j for j in (getattr(self.world, "private", None) or ()) if j in named)
        if not private or len(self.world.buttons) < 2:
            return []
        alone = getattr(self, "tried_alone", None) or collections.Counter()
        if min(alone[b] for b in range(len(self.world.buttons))) >= 2:
            return []
        return [j for j in private if j < len(self.learners) and not any(
            r["cond"][1] == "act" for rs in ((self.learners[j].__dict__.get("odds") or {}).get("laws") or {}).values()
            for r in rs)]

    def experiment(self, stuck):
        """Its laws of counts do not close a sensor and hold a count with no end, so it experiments as a
        scientist does, one thing at a time."""
        trial = getattr(self, "trial", None)
        if trial is not None and trial["left"] <= 0 and trial.get("fair", 0) > 0:
            trial["fair"] -= 1
            pressed = getattr(self, "pressed", None) or collections.Counter()
            return min(range(len(self.world.buttons)), key=lambda b: (pressed[b], b))
        if trial is None or trial["left"] <= 0:
            alone = getattr(self, "tried_alone", None)
            if alone is None:
                alone = self.tried_alone = collections.Counter()
            b = min(range(len(self.world.buttons)), key=lambda b: (alone[b], b))
            longest = max([q for L in self.learners for q in L.model.mods if q] or [60])
            n = max(120, 2 * longest) * 2 ** alone[b]
            alone[b] += 1
            trial = self.trial = {"button": b, "left": n, "fair": n}
            self.decide("experiment", b, {"sensors": list(stuck), "presses": n})
        trial["left"] -= 1
        return trial["button"]

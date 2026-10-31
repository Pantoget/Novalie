# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Goals and plans by its odds."""

import collections
import itertools

from ..evidence import trusted


class Goals:
    def odds_next(self, j, a):
        """The value sense j will likeliest show after the act a, and its odds."""
        L = self.learners[j]
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
        best, top = now, 1.0 - total
        for d, x in sorted(probs.items(), key=lambda kv: repr(kv[0])):
            if x > top:
                best, top = self.odds_target(L, now, d), x
        return best, top

    def foresee_odds(self, n, acts=None, most=20_000, every=False):
        """What each sense will show after n acts, in thought, and how likely."""
        acts, Ls = list(acts or []), self.learners
        past = list(self.__dict__.get("past") or ())
        how = []
        for L in Ls:
            r = getattr(L, "recognized", None)
            how.append("kind" if r is not None and trusted(r) else "counts" if getattr(L, "invented", None) is None
                       and L.counts_closed() else "moments" if L.moment_cell() is not None
                       else "odds" if L.odds_cell() is not None else None)
        keys = {i: (Ls[i].recognized["p"] if h == "kind" else Ls[i].key) for i, h in enumerate(how) if h in ("kind", "counts")}
        cur = [{L.colors[-1]: 1.0} if h else None for L, h in zip(Ls, how)]
        hist = []
        for t in range(1, min(n, most) + 1):
            a = acts[t - 1] if t - 1 < len(acts) else 0
            nxt = list(cur)

            def held(c, t=t, nxt=nxt):
                l, attr, v = c
                s0 = t - l
                if s0 <= 0:
                    k = len(past) - 1 + s0
                    return None if k < 0 else float(past[k].get(attr) == v)
                if attr == "act":
                    return float((acts[s0 - 1] if s0 - 1 < len(acts) else 0) == v)
                if attr[0] != "s":
                    return None
                dist = (nxt if s0 == t else hist[s0 - 1])[int(attr[1:])]
                return None if dist is None else dist.get(v, 0.0)

            for i, (L, h) in enumerate(zip(Ls, how)):
                if h == "kind":
                    r = L.recognized
                    keys[i] = (keys[i] + r["eff"].get(a, 0)) % r["d"]
                    nxt[i] = {r["T"][keys[i]]: 1.0}
                elif h == "counts":
                    keys[i] = L.model.step(keys[i], a)
                    v = L.table.get(keys[i])
                    nxt[i] = None if v is None else {v: 1.0}
                elif h is None:
                    nxt[i] = None
            for i, (L, h) in enumerate(zip(Ls, how)):
                if h == "moments" and cur[i] is not None:
                    m, v = L.moment, next(iter(cur[i]))
                    state = {f"s{x}": (next(iter(nxt[x])) if nxt[x] and len(nxt[x]) == 1 else None)
                             for x in range(len(Ls)) if x != i}
                    state["act"] = a
                    if any(state.get(k) is None for k in m["cond"]):
                        nxt[i] = None
                    elif all(state.get(k) == w for k, w in m["cond"].items()):
                        v2 = v + m["d"]
                        nxt[i] = {v2 % m["M"]: 1.0} if m["M"] else ({v2: 1.0} if v2 <= max(m["values"]) else None)
            for i, (L, h) in enumerate(zip(Ls, how)):
                if h != "odds" or cur[i] is None:
                    continue
                od = L.odds
                P = {d: self.list_odds(od, rules, held) for d, rules in od["laws"].items()}
                new = collections.defaultdict(float)
                for v, mass in cur[i].items():
                    ch, probs = od["chain"].get(v), dict(P)
                    if ch and ch[0]:
                        for d, k in ch[1].items():
                            probs.setdefault(d, k / ch[0])
                    moves = collections.defaultdict(float)
                    for d, x in probs.items():
                        tg = self.odds_target(L, v, d)
                        if tg is not None and x > 0:
                            moves[tg] += x
                    total = sum(moves.values())
                    if total > 1:
                        moves, total = {tg: x / total for tg, x in moves.items()}, 1.0
                    new[v] += mass * (1 - total)
                    for tg, x in moves.items():
                        new[tg] += mass * x
                nxt[i] = dict(new)
            hist.append(nxt)
            cur = nxt
        if every:
            return hist
        out = []
        for dist in cur:
            if not dist:
                out.append(None)
            else:
                v, pr = max(dist.items(), key=lambda kv: (kv[1], repr(kv[0])))
                out.append((v, round(pr, 4)))
        return out

    def plan_odds(self, j, goal, H=4):
        """A plan by its odds: of every way to act the next H acts."""
        lo, hi = goal if isinstance(goal, tuple) else (goal, goal)
        number = type(lo) is int and type(hi) is int
        far = lambda v: (0 if lo <= v <= hi else 1) if not number or type(v) is not int else max(0, lo - v, v - hi)
        best = None
        for acts in itertools.product(range(len(self.world.buttons)), repeat=H):
            hist = self.foresee_odds(H, list(acts), every=True)
            if not hist or hist[-1][j] is None:
                return None
            got = [sum(p for v, p in step[j].items() if far(v) == 0) for step in hist]
            away = sum(p * far(v) for step in hist for v, p in step[j].items())
            rank = (-round(away, 9), round(sum(got), 9), round(got[-1], 9), tuple(-a for a in acts))
            if best is None or rank > best[0]:
                best = (rank, list(acts), got[-1])
        return best[1], round(best[2], 4)

    def set_goal(self, j, goal, H=4):
        """A goal you (or it) set for one of its senses."""
        self.odds_goal = {"j": j, "goal": goal, "H": H, "set": self.world_steps, "acts": 0, "held": 0}
        self.decide("odds_goal", j + 1, {"goal": list(goal) if isinstance(goal, tuple) else goal, "H": H})

    def act_for(self, j, goal, now=None):
        """The act its laws of odds say most raises the odds of sense j moving toward goal."""
        L = self.learners[j]
        od = L.__dict__.get("odds") or {}
        now = L.colors[-1] if now is None else now
        if now == goal:
            return None
        best = None
        for d, law in sorted(((d, law) for d, rules in (od.get("laws") or {}).items() for law in rules if law["up"]),
                             key=lambda kv: (repr(kv[0]), kv[1]["level"])):
            l, attr, v = law["cond"]
            if attr != "act":
                continue
            if type(d) is int and type(now) is int and type(goal) is int:
                if d * (goal - now) <= 0:
                    continue
                within = abs(d) <= abs(goal - now)
            elif d == ("to", goal):
                within = True
            else:
                continue
            rank = (within, law["q"] - law["p"], law["q"], -l)
            if best is None or rank > best[0]:
                best = (rank, v)
        return None if best is None else best[1]

    def set_by_acts(self, i):
        """Is sense i set by its own acts."""
        L = self.learners[i]
        if not L.counts_closed():
            return False
        mo = L.model
        return len({tuple(e % q if q else e for e, q in zip(mo.eff[a], mo.mods)) for a in range(len(mo.eff))}) > 1

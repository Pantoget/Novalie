# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Recognizing kinds it knew, planning to a goal."""

import collections
import copy
import heapq
import itertools

from ..cells import symbol
from ..evidence import trusted


class Recognition:
    def remember(self, L):
        """Keep a kind it has just learned."""
        mo = L.model
        if len(mo.mods) != 1:
            return
        d = mo.mods[0]
        T = [L.table.get((x,)) for x in range(d)]
        if None in T:
            return
        steps = tuple(sorted({e[0] % d for e in mo.eff if e[0] % d}))
        r = min(range(d), key=lambda i: T[i:] + T[:i])
        entry = {"d": d, "T": tuple(T[r:] + T[:r]), "S": steps}
        with self.lock:
            if entry not in self.library:
                self.library.append(entry)

    def recognize(self, L):
        """Is this sensor showing a kind it already knows? Every remembered kind, every way its steps could sit
        on the buttons that changed this sensor, every starting point."""
        obs, acts = L.colors, L.actions
        moved = sorted({a for a, x, y in zip(acts, obs, obs[1:]) if x != y})
        seen, found = set(obs), []
        for e in list(self.library):
            d, T, S = e["d"], e["T"], e["S"]
            if len(S) != len(moved) or not seen <= set(T):
                continue
            for btns in itertools.permutations(moved):
                eff = dict(zip(btns, S))
                for p0 in range(d):
                    if T[p0] != obs[0]:
                        continue
                    p = p0
                    for a, x in zip(acts, obs[1:]):
                        p = (p + eff.get(a, 0)) % d
                        if T[p] != x:
                            break
                    else:
                        found.append((e, eff, p))
                        if len(found) > 1:
                            return
        if len(found) == 1:
            e, eff, p = found[0]
            L.recognized = {"d": e["d"], "T": e["T"], "eff": eff, "p": p, "calm": 0, "proof": 0.0,
                            "tests": max(1, len(self.library))}
            with self.lock:
                self.salient[symbol(("flat", (e["d"],)))] += 0.3
                self.urge += 0.2
            self.emit("recognized", s=str(e["d"]), world=self.k)
        elif not found:
            self.recognize_by_length(L)

    def recognize_by_length(self, L):
        """A sense moved by one act only, that shows the same thing again every d of those acts, for every act it
        saw and over more than one turn, for a length d it knows from anywhere."""
        obs, acts = L.colors, L.actions
        moved = {a for a, x, y in zip(acts, obs, obs[1:]) if x != y}
        if len(moved) != 1 or len(set(obs)) < 2:
            return False
        b = next(iter(moved))
        counts = [0]
        for a in acts:
            counts.append(counts[-1] + (a == b))
        n = counts[-1]
        lengths = self.known_lengths()
        for d in sorted(x for x in lengths if 2 <= x and n >= x + max(10, x // 5)):
            table, ok = {}, True
            for c, o in zip(counts, obs):
                if table.setdefault(c % d, o) != o:
                    ok = False
                    break
            if ok and len(table) == d and len(set(table.values())) > 1:
                L.recognized = {"d": d, "T": tuple(table[i] for i in range(d)), "eff": {b: 1}, "p": n % d, "calm": 0,
                                "proof": 0.0, "tests": max(1, len(lengths))}
                with self.lock:
                    self.salient[str(d)] += 0.3
                    self.urge += 0.2
                self.emit("recognized", s=str(d), world=self.k, how="length", known=lengths[d])
                self.decide("recognize", d, {"from": lengths[d], "acts": n})
                return True
        return False

    def plan_to(self, target, limit=50_000, guide=True):
        """A plan (acts) that makes its senses show target (one value each), from what it knows of this world."""
        Ls, m = self.learners, len(self.world.buttons)
        sensors = []
        for L in Ls:
            r = getattr(L, "recognized", None)
            if r is not None and trusted(r):
                sensors.append((r["p"], lambda p, a, times=1, r=r: (p + times * r["eff"].get(a, 0)) % r["d"],
                                {p: r["T"][p] for p in range(r["d"])}))
            elif getattr(L, "invented", None) is None and L.sure() and L.odds_cell() is None and 0 not in L.model.mods:
                sensors.append((L.key, L.model.step, L.table))
            else:
                return None, 0
        dist = []
        for (where, step, shows), want in zip(sensors, target):
            goals = [k for k, v in shows.items() if v == want]
            if not goals:
                return None, 0
            d, frontier = {g: 0 for g in goals}, list(goals)
            while frontier and len(d) < 200_000:
                nxt = []
                for k in frontier:
                    for a in range(m):
                        p = step(k, a, times=-1)
                        if p not in d:
                            d[p] = d[k] + 1
                            nxt.append(p)
                frontier = nxt
            dist.append(d)
        start = tuple(where for where, _, _ in sensors)
        if guide == "sum":
            h = lambda st: sum(dd.get(k, 10 ** 9) for dd, k in zip(dist, st))
        elif guide:
            h = lambda st: max(dd.get(k, 10 ** 9) for dd, k in zip(dist, st))
        else:
            h = lambda st: 0
        if h(start) >= 10 ** 9:
            return None, 0
        came, best_g, heap, n = {start: None}, {start: 0}, [(h(start), 0, start)], 0
        while heap and n < limit:
            f, g, st = heapq.heappop(heap)
            if g > best_g.get(st, 10 ** 9):
                continue
            n += 1
            if all(dd.get(k) == 0 for dd, k in zip(dist, st)):
                path = []
                while came[st] is not None:
                    st, a = came[st]
                    path.append(a)
                return path[::-1], n
            for a in range(m):
                nst = tuple(step(k, a) for (_, step, _), k in zip(sensors, st))
                if g + 1 < best_g.get(nst, 10 ** 9):
                    best_g[nst] = g + 1
                    came[nst] = (st, a)
                    heapq.heappush(heap, (g + 1 + h(nst), g + 1, nst))
        return None, n

    def self_test(self, anatomies, cols=None):
        """For the page, not for its speech."""
        cols = list(range(len(anatomies))) if cols is None else cols
        world = copy.deepcopy(self.world)
        states = [an.state_of(self.learners[j].key) for an, j in zip(anatomies, cols)]
        right = 0
        tried = collections.Counter()
        for _ in range(300):
            a = min(range(len(world.buttons)), key=lambda b: (tried[b], b))
            tried[a] += 1
            world.press(a)
            states = [an.step(s, a) for an, s in zip(anatomies, states)]
            seen = self.as_levels(world.observe(), keep=False)
            right += all(an.colour(s) == seen[j] for an, s, j in zip(anatomies, states, cols) if an.kind != "odds")
        return 100 * right / 300

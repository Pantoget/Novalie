# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Understanding a world: its cells and their laws."""

import collections
import itertools
import math
import time

from ..cells import Invented, Known, seen_symbol, symbol
from ..config import EVIDENCE
from ..laws import Moments, Odds, odds_symbol
from ..parts import org


class Understanding:
    def relations(self, per_sensor):
        """Laws between the cells of this world, found in what each sensor showed press by press, with no
        exception, believed by the one rule."""
        if not self.learners or not self.learners[0].actions:
            return []
        n = len(self.learners[0].actions)
        moved = [[L.colors[t + 1] != L.colors[t] for t in range(n)] for L in self.learners]
        count = [sum(m) for m in moved]
        pairs = [(i, j) for i in range(len(moved)) for j in range(len(moved))
                 if i != j and count[i] and count[j] and per_sensor[i] and per_sensor[j]
                 and per_sensor[i] != per_sensor[j] and "~" not in per_sensor[i] and "~" not in per_sensor[j]]
        bar = EVIDENCE + math.log10(max(1, len(pairs)))
        out = []
        for i, j in pairs:
            mi, mj = moved[i], moved[j]
            if not all(mi[t] for t in range(n) if mj[t]):
                continue
            digits = count[j] * math.log10(n / count[i])
            if count[i] == count[j]:
                if i < j and digits >= bar:
                    out.append(("together", per_sensor[i], per_sensor[j]))
            elif count[i] >= 2 * count[j]:
                at = {self.learners[i].colors[t + 1] for t in range(n) if mj[t]}
                values = max(len(at), len(set(self.learners[i].colors)))
                if len(at) <= 2:
                    digits += count[j] * math.log10(values / len(at)) - math.log10(math.comb(values, len(at)))
                    if digits >= bar:
                        out.append(("carry", per_sensor[i], per_sensor[j]))
        return out

    def link_kind(self, code, where):
        """A kind of link it found."""
        k = self.link_kinds.setdefault(code, {"first": self.k, "worlds": 0, "where": []})
        k["worlds"] += 1
        k["last"] = self.k
        if where not in k["where"]:
            k["where"] = (k["where"] + [where])[-6:]

    def invention_of(self, name):
        return next((e for e in self.inventions if e.get("symbol") == name), None)

    def understood(self, only=None):
        """What it understood of a world, kept."""
        kinds, anatomies, symbols, invented, per_sensor, cols, chance = [], [], [], [], [], [], []
        known = 0
        for j, L in enumerate(self.learners):
            if only is not None and j != only:
                per_sensor.append(self.real_known.get(j))
                continue
            cols.append(j)
            rec = getattr(L, "invented", None)
            if rec is not None:
                anatomies.append(Invented(rec, rec["sensors"].index(j)))
                per_sensor.append(rec["name"])
                if rec["name"] not in invented:
                    invented.append(rec["name"])
                continue
            if getattr(L, "recognized", None) is not None:
                an, known = Known(L.recognized), known + 1
            elif not L.counts_closed() and L.moment_cell() is not None:
                P, d, Mo = L.moment_cell()
                last = L.moment["times"][-1]
                an = Moments(P, d, Mo, len(L.colors) - 1 - last, L.colors[-1])
            elif not L.counts_closed() and L.odds_cell() is not None:
                cell = L.odds_cell()
                anatomies.append(Odds(*cell, L.colors[-1]))
                per_sensor.append(odds_symbol(cell))
                if odds_symbol(cell) not in chance:
                    chance.append(odds_symbol(cell))
                continue
            else:
                an, _ = org.compile_commuting(L)
                self.remember(L)
            anatomies.append(an)
            kinds.append((an.kind, tuple(an.cycles)))
            per_sensor.append(symbol((an.kind, tuple(an.cycles))))
        if only is not None:
            if self.real_known.get(only) == per_sensor[only]:
                return
            self.real_known[only] = per_sensor[only]
        acc = self.self_test(anatomies, cols)
        found = self.relations(per_sensor)
        if only is not None and not self.learners[only].counts_closed() and self.learners[only].moment_cell():
            carriers = [int(k[1:]) for k in self.learners[only].moment["cond"] if k[:1] == "s" and k[1:].isdigit()]
            known = [i for i in carriers if per_sensor[i]]
            if known:
                def period(i):
                    ts = (getattr(self.learners[i], "moment", None) or {}).get("times") or []
                    return (ts[-1] - ts[0]) / (len(ts) - 1) if len(ts) >= 2 else 1
                slow = max(known, key=period)
                found = list(found) + [("carry", per_sensor[slow], per_sensor[only])]
        found = list(found) + self.odds_links(per_sensor, only)
        for code, a, b in [f for f in found if f[0] == "together"]:
            for i, x in enumerate(per_sensor):
                for k, y in enumerate(per_sensor):
                    if i < k and {x, y} == {a, b}:
                        self.__dict__.setdefault("bound", set()).add((i, k))
        found = list(found) + self.make_things(per_sensor)
        with self.lock:
            for kind in kinds:
                s = symbol(kind)
                symbols.append(s)
                if not self.kinds_seen[kind]:
                    self.emit("born", s=s)
                novelty = 1.0 / (1 + self.kinds_seen[kind])
                self.kinds_seen[kind] += 1
                life = self.kind_life.setdefault(kind, {"born": round(time.time()), "world": self.k})
                life["last"], life["last_world"] = round(time.time()), self.k
                named, bored = self.word_for(s), 1 + self.asked[s]
                self.salient[s] += novelty + (0.0 if named else 0.5 / bored)
                self.urge += novelty * 0.5 if named else novelty + 0.3 / bored
            for name in chance:
                symbols.append(name)
                if not self.odds_seen[name]:
                    self.emit("born", s=name)
                novelty = 1.0 / (1 + self.odds_seen[name])
                self.odds_seen[name] += 1
                life = self.odds_life.setdefault(name, {"born": round(time.time()), "world": self.k})
                life["last"], life["last_world"] = round(time.time()), self.k
                named, bored = self.word_for(name), 1 + self.asked[name]
                self.salient[name] += novelty + (0.0 if named else 0.5 / bored)
                self.urge += novelty * 0.5 if named else novelty + 0.3 / bored
            for name in invented:
                symbols.append(name)
                novelty = 1.0 / (1 + self.invented_seen[name])
                self.invented_seen[name] += 1
                life = self.invented_life.setdefault(name, {"born": round(time.time()), "world": self.k})
                life["last"], life["last_world"] = round(time.time()), self.k
                named, bored = self.word_for(name), 1 + self.asked[name]
                self.salient[name] += novelty + (0.0 if named else 0.5 / bored)
                self.urge += novelty * 0.5 if named else novelty + 0.3 / bored
            for code, a, b in found:
                self.cell_links[(code, a, b)] += 1
                self.link_kind(code, f"{a} {code} {b}")
            for name in invented:
                for law in (self.invention_of(name) or {}).get("last", {}).get("laws", ()):
                    self.link_kind(law["law"], name)
            for pair in itertools.combinations(sorted(set(symbols)), 2):
                self.together[pair] += 1
            self.recent = symbols
            self.urge *= 0.95
            entry = {"world": self.k, "kinds": kinds, "steps": self.world_steps,
                     "size": self.world.size,
                     "accuracy": acc, "recognized": known, "real": only is not None,
                     "sensors": len(self.learners), "invented": invented,
                     "senses": list(per_sensor), "acted": [i for i in range(len(per_sensor)) if self.set_by_acts(i)],
                     "laws": sorted({(code, i, j) for code, a, b in found if code != "part"
                                     for i, x in enumerate(per_sensor) for j, y in enumerate(per_sensor)
                                     if i != j and x == a and y == b})}
            self.knowledge.append(entry)
            del self.knowledge[:-40]
        if only is None:
            self.find_analogy(entry)
        self.emit("understood", world=self.k, symbols=symbols, steps=self.world_steps, accuracy=round(acc),
                  recognized=known, real=only is not None, sensor=None if only is None else only + 1)
        for code, a, b in found:
            self.emit("law", code=code, a=a, b=b, world=self.k)
        with self.lock:
            self.make_generals()
        if only is not None:
            L = self.learners[only]
            size = max(1, math.prod((L.recognized["d"],) if getattr(L, "recognized", None) else
                                    [q for q in L.model.mods if q]))
            self.judge_ways(True, steps=self.world_steps - getattr(self, "episode_at", 0), scale=size)
            if not L.noisy():
                self.eps = min(self.eps, getattr(L, "eps", self.eps))
            self.choose_ways()

    def make_generals(self):
        """General cells, born of what its cells share."""
        sizes = {symbol(k): math.prod(k[1]) for k in self.kinds_seen}
        for k in self.seen_kinds:
            sizes.setdefault(seen_symbol(k), math.prod(k[1]))
        by_size = collections.defaultdict(list)
        for c, n in sizes.items():
            by_size[n].append(c)
        found = {}
        for a, b in itertools.combinations_with_replacement(sorted(by_size), 2):
            if a == b and len(by_size[a]) < 2:
                continue
            g = math.gcd(a, b)
            if g >= 4 and g not in found:
                members = sorted(c for n, cs in by_size.items() if n % g == 0 and n != g for c in cs)
                if len(members) >= 2:
                    found[g] = members
        flat = {k[1][0] for k in self.kinds_seen if k[0] == "flat" and len(k[1]) == 1}
        flat |= {k[1][0] for k in self.seen_kinds if len(k[1]) == 1}
        G = {g for g, _ in sorted(found.items(), key=lambda kv: -len(kv[1]) * math.log(kv[0]))[:200]}

        def nearest(n):
            ps = [g for g in G if n % g == 0 and g < n]
            return [g for g in ps if not any(h != g and h % g == 0 and n % h == 0 for h in ps)]
        kinds = collections.defaultdict(list)
        for c, n in sizes.items():
            for g in nearest(n):
                kinds[g].append(c)
        for g in G:
            if str(g) not in sizes:
                for p in nearest(g):
                    kinds[p].append(str(g))
        out = {str(g): {"kind": "part", "g": g, "members": sorted(kinds[g]), "cell": g in flat} for g in G if kinds[g]}
        laws = collections.defaultdict(list)
        for e in self.inventions:
            nat = (e.get("machine") or {}).get("nature") or {}
            for law, holds in (("undo", nat.get("group")), ("reset", nat.get("sync"))):
                if holds:
                    laws[law].append(e.get("symbol") or e["name"])
        for law, members in laws.items():
            if len(members) >= 2:
                out["≡" + law] = {"kind": "law", "law": law, "members": sorted(members), "cell": False}
        for gid, g in out.items():
            old = self.generals.get(gid)
            g["born"], g["world"] = (old["born"], old["world"]) if old else (round(time.time()), self.k)
            if old is None and not g["cell"]:
                self.emit("general", s=gid, members=g["members"][:6], general=g["kind"], law=g.get("law"))
                self.salient[gid] += 1.0
                self.urge += 0.5
        self.generals = out
        self.make_circuits()

    def generals_soon(self):
        """Its general cells and circuits, made again when new cells came."""
        if time.time() - getattr(self, "_generals_at", 0.0) >= 60:
            self._generals_at = time.time()
            self.make_generals()

    def make_circuits(self):
        """Circuits: the cells its laws join."""
        adj, laws = collections.defaultdict(set), collections.defaultdict(list)
        for (code, a, b), n in self.cell_links.items():
            if a != b and n >= 1:
                adj[a].add(b)
                adj[b].add(a)
                laws[frozenset((a, b))].append([code, a, b])
        old, out, done = getattr(self, "circuits", None) or {}, {}, set()
        for c in sorted(adj):
            if c in done:
                continue
            group, stack = set(), [c]
            while stack:
                x = stack.pop()
                if x not in group:
                    group.add(x)
                    stack.extend(adj[x] - group)
            done |= group
            into = collections.Counter(b for (code, a, b) in self.cell_links if code == "carry" and a in group)
            members = sorted(group, key=lambda x: (into[x], x))
            cid = "~".join(members)
            k = {"members": members, "laws": sorted({tuple(l) for ab, ls in laws.items() if ab <= group for l in ls}),
                 "born": (old.get(cid) or {}).get("born", round(time.time()))}
            k["laws"] = [list(l) for l in k["laws"]]
            out[cid] = k
            if cid not in old:
                self.emit("circuit", s=cid, members=members[:8], laws=k["laws"][:6])
                self.salient[members[0]] += 0.5
                self.urge += 0.3
        self.circuits = out

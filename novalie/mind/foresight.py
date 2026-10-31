# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Foresight: what each sense will show, laws and episodes."""

import collections
import math

from ..config import EVIDENCE, room
from ..evidence import sign_digits, trusted


class Foresight:
    # -- its episodes: a second kind of cell ----------------------------------------------------------------
    def episodes_room(self):
        ep = self.__dict__.get("episodes")
        if ep is None or ep.get("k") != self.k:
            ep = self.episodes = {"k": self.k, "cells": {}, "trust": {}, "served": 0}
        return ep

    def episode_key(self, seen, a):
        named = self.named_senses()
        return (tuple(x for i, x in enumerate(seen) if i in named), a)

    def episode_guess(self, cell, i):
        """What episode cell remembers of the i-th sense it names."""
        got = collections.Counter()
        for nxt, c in cell.items():
            got[nxt[i]] += c
        n = sum(got.values())
        v, c = max(got.items(), key=lambda kv: (kv[1], repr(kv[0])))
        return v, (c + 0.5) / (n + 0.5 * (len(got) + 1))

    def see_episode(self, key, cell, fore, o):
        """After an act: its laws and its episode judged where they differed, and the episode kept."""
        ep = self.episodes_room()
        named = sorted(self.named_senses())
        if cell is not None and fore is not None:
            bar = EVIDENCE + math.log10(max(1, len(named)))
            for i, j in enumerate(named):
                e, g = self.episode_guess(cell, i)[0], fore[j][0]
                if e == g or (e == o[j]) == (g == o[j]):
                    continue
                t = ep["trust"].setdefault(j, {"on": False, "k": 0, "n": 0})
                t["n"] += 1
                t["k"] += (e == o[j]) != t["on"]
                digits = sign_digits(t["k"], t["n"])
                if digits >= bar:
                    t.update(on=not t["on"], k=0, n=0)
                    self.decide("episodes", j + 1, {"on": t["on"], "digits": round(digits, 1)})
                    self.emit("episodes", sensor=j + 1, on=t["on"], digits=round(digits, 1))
        cells = ep["cells"]
        if cell is None:
            if len(cells) >= room(20_000):
                cells.pop(next(iter(cells)))
            cell = cells[key] = collections.Counter()
        cell[tuple(x for i, x in enumerate(o) if i in self.named_senses())] += 1

    def foresee_next(self, a, episodes=True):
        """What each sense will show after act a, before it is done."""
        past = self.__dict__.get("past") or ()
        out = [None] * len(self.learners)
        for j, L in enumerate(self.learners):
            r = getattr(L, "recognized", None)
            try:
                if r is not None and trusted(r):
                    out[j] = (r["T"][(r["p"] + r["eff"].get(a, 0)) % r["d"]], 1.0)
                elif getattr(L, "invented", None) is None and L.counts_closed():
                    v = L.table.get(L.model.step(L.key, a))
                    out[j] = (v, 1.0) if v is not None else None
            except Exception:
                out[j] = None
        for rnd in (0, 1):
            for j, L in enumerate(self.learners):
                if (out[j] is not None and out[j][1] == 1.0) or not L.colors:
                    continue
                od, now = L.odds_room(), L.colors[-1]

                def held(c):
                    l, attr, v = c
                    if l == 0 and attr == "act":
                        return float(a == v)
                    sym = attr.startswith("s") and attr[1:].isdigit() and isinstance(v, str)
                    if l == 0 and attr.startswith("s") and attr[1:].isdigit():
                        if rnd == 0:
                            return None
                        got = out[int(attr[1:])]
                        if got is None or got[0] is None:
                            return None
                        return 1.0 if got[0] == v or (sym and self.same_class(int(attr[1:]), got[0], v)) else 0.0
                    if 1 <= l <= len(past):
                        x = past[-l].get(attr)
                        return 1.0 if x == v or (sym and self.same_class(int(attr[1:]), x, v)) else 0.0
                    return None

                ch = od["chain"].get(now)
                probs = {d: k / ch[0] for d, k in ch[1].items()} if ch and ch[0] else {}
                for d, rules in od["laws"].items():
                    x = self.list_odds(od, rules, held)
                    if x is not None:
                        probs[d] = x
                probs = {d: x for d, x in probs.items() if self.odds_target(L, now, d) is not None}
                kind = self.kind_odds(j, a, past)
                if kind is not None:
                    probs = {d: x for d, x in kind.items() if d is not None and self.odds_target(L, now, d) is not None}
                total = sum(probs.values())
                if total > 1:
                    probs, total = {d: x / total for d, x in probs.items()}, 1.0
                best, top = now, 1.0 - total
                for d, x in sorted(probs.items(), key=lambda kv: repr(kv[0])):
                    if x > top:
                        best, top = self.odds_target(L, now, d), x
                got = self.made_next(j, a, out, rnd, follow=True)
                if got is not None and got[1] > top:
                    best, top = got
                out[j] = (best, round(top, 4))
        ep = self.__dict__.get("episodes") if episodes and self.gene("episodes") else None
        if ep and ep.get("k") == self.k and any(t["on"] for t in ep["trust"].values()):
            seen = self.__dict__.get("seen_now")
            cell = ep["cells"].get(self.episode_key(seen, a)) if seen is not None else None
            if cell:
                for i, j in enumerate(sorted(self.named_senses())):
                    t = ep["trust"].get(j)
                    if t and t["on"]:
                        out[j] = self.episode_guess(cell, i)
        return [x if x is not None else (None, 0.0) for x in out]

    def kind_odds(self, j, a, past):
        """The odds of each change of sense j under act a, by its concept."""
        room = self.__dict__.get("concepts")
        if not room or not past:
            return None
        now = past[-1]
        o = [now.get(f"s{i}") for i in range(len(self.learners))]
        for m, got in sorted((room.get("classes") or {}).items()):
            if not got or m == j or o[m] is None:
                continue
            if any(o[m] in c["members"] for c in got["classes"]):
                continue
            post = self.class_posterior(m, o[m])
            if not post:
                continue
            cellg = (got.get("cells") or {}).get((a, j))
            for grain in dict.fromkeys(([cellg] if cellg else []) + ["own", "stats"]):
                key, data = self.grain_key(grain, a, j, o, m), self.grain_room(grain, m)
                mixed, weight = collections.Counter(), 0.0
                for c in got["classes"]:
                    p = post.get(c["rep"], 0.0)
                    counts = collections.Counter()
                    for x in c["members"]:
                        counts.update((data.get(x) or {}).get(key) or {})
                    if not counts or p <= 0:
                        continue
                    n, kinds = sum(counts.values()), len(counts) + 1
                    for d, k in counts.items():
                        mixed[d] += p * (k + 0.5) / (n + 0.5 * kinds)
                    weight += p
                if weight > 0.5:
                    return {d: x / weight for d, x in mixed.items()}
        return None

    def telling_act(self):
        """The act that would best tell what kind a thing it sees is."""
        room = self.__dict__.get("concepts")
        past = self.__dict__.get("past")
        if not room or not past or not getattr(self, "world", None):
            return None
        now = past[-1]
        o = [now.get(f"s{i}") for i in range(len(self.learners))]
        asked = self.__dict__.setdefault("telling_log", {})
        best = None
        for m, got in sorted((room.get("classes") or {}).items()):
            if not got or m >= len(o) or o[m] is None or any(o[m] in c["members"] for c in got["classes"]):
                continue
            post = self.class_posterior(m, o[m])
            if not post:
                stats = room["stats"].get(m, {})
                sizes = {c["rep"]: sum(sum(cs.values()) for x in c["members"] for cs in stats.get(x, {}).values()) or 1
                         for c in got["classes"]}
                post = {r: n / sum(sizes.values()) for r, n in sizes.items()}
            key = (getattr(self.world, "name", None), m)
            if max(post.values()) >= 1 - 10 ** -EVIDENCE:
                asked.pop(key, None)
                continue
            r = asked.get(key)
            if r is not None and r[0] * r[1] >= EVIDENCE:
                continue
            acts = range(len(self.world.buttons))
            for a in acts:
                tells = self.tells(m, got, post, o, a)
                seen = self.foresee_next(a)
                then = [x if v is None else v for x, (v, _) in zip(o, seen)]
                if then[m] == o[m]:
                    tells += max(self.tells(m, got, post, then, b) for b in acts)
                if tells > 1e-9 and (best is None or tells > best[0] + 1e-12):
                    best = (tells, a, m)
        if best is not None:
            r = asked.setdefault((getattr(self.world, "name", None), best[2]), [0, best[0]])
            r[0] += 1
            while len(asked) > 2000:
                del asked[next(iter(asked))]
        return best

    def tells(self, m, got, post, o, a):
        """What act a would tell, in powers of ten, of the class of sense m's thing."""
        tells = 0.0
        for j in range(len(self.learners)):
            if j == m:
                continue
            cellg = (got.get("cells") or {}).get((a, j))
            per = {}
            for grain in dict.fromkeys(([cellg] if cellg else []) + ["own", "stats"]):
                key, data = self.grain_key(grain, a, j, o, m), self.grain_room(grain, m)
                per = {}
                for c in got["classes"]:
                    counts = collections.Counter()
                    for x in c["members"]:
                        counts.update((data.get(x) or {}).get(key) or {})
                    if counts:
                        per[c["rep"]] = counts
                if sum(post.get(r, 0.0) for r in per) > 0.5:
                    break
            if len(per) < 2:
                continue
            support = set().union(*per.values())
            w = {r: post.get(r, 0.0) for r in per}
            tot = sum(w.values())
            if tot <= 0:
                continue
            dists = {r: {d: (c.get(d, 0) + 0.5) / (sum(c.values()) + 0.5 * len(support)) for d in support}
                     for r, c in per.items()}
            mix = {d: sum(w[r] / tot * dists[r][d] for r in per) for d in support}
            h = lambda p: -sum(x * math.log10(x) for x in p.values() if x > 0)
            tells += h(mix) - sum(w[r] / tot * h(dists[r]) for r in per)
        return tells

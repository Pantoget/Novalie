# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Concepts: classes of a sense's values by what the world does."""

import collections
import math

from ..config import EVIDENCE
from ..evidence import bell, exact_digits, paid
from ..laws import age_of, change_of


class Concepts:
    # -- concepts: classes of the values of a sense, made by what the world does with them ----------------------------
    def concept_room(self):
        return self.__dict__.setdefault("concepts", {"stats": {}, "classes": {}, "steps": 0, "said": {}})

    def see_concepts(self, before, a, o):
        """Its concepts, formed again from its laws each time what it saw doubled."""
        room = self.concept_room()
        ages = room.setdefault("ages", [0] * len(before))
        if len(ages) != len(before):
            ages[:] = [0] * len(before)
        for j, v in enumerate(before):
            if isinstance(v, (int, float)) or v is None or o[j] != v:
                continue
            prof = room["stats"].setdefault(j, {}).setdefault(v, {})
            fine = room.setdefault("fine", {}).setdefault(j, {}).setdefault(v, {})
            own = room.setdefault("own", {}).setdefault(j, {}).setdefault(v, {})
            withs, since = room.setdefault("with", {}), room.setdefault("since", {})
            finer, trying = room.setdefault("both", {}), (room.get("trying") or {}).get(j) or ()
            where = self.situation(before, j)
            for i, (x, y) in enumerate(zip(before, o)):
                if i != j:
                    d = change_of(x, y)
                    for p, key in ((prof, (a, i)), (own, (a, i, x)), (fine, (a, i, where))):
                        cell = p.setdefault(key, {})
                        cell[d] = cell.get(d, 0) + 1
                    for k, xk in enumerate(before):
                        if k != j:
                            cell = withs.setdefault(k, {}).setdefault(j, {}).setdefault(v, {}).setdefault((a, i, x, xk), {})
                            cell[d] = cell.get(d, 0) + 1
                        cell = since.setdefault(k, {}).setdefault(j, {}).setdefault(v, {}).setdefault(
                            (a, i, x, age_of(ages[k])), {})
                        cell[d] = cell.get(d, 0) + 1
                        if k in trying:
                            cell = finer.setdefault(k, {}).setdefault(j, {}).setdefault(v, {}).setdefault(
                                (a, i, x, xk, age_of(ages[k])), {})
                            cell[d] = cell.get(d, 0) + 1
        for k, (x, y) in enumerate(zip(before, o)):
            ages[k] = 0 if x != y else ages[k] + 1
        room["steps"] += 1
        if room["steps"] >= max(50, 2 * room.get("formed_at", 0)):
            room["formed_at"] = room["steps"]
            for j in sorted({j for j, v in enumerate(o) if not isinstance(v, (int, float)) and v is not None}):
                self.form_classes(j)

    def law_odds_of(self, m):
        """For sense m's symbols."""
        out = {}
        for j, L in enumerate(self.learners):
            if j == m:
                continue
            od = L.__dict__.get("odds") or {}
            for d, rules in (od.get("laws") or {}).items():
                for i, law in enumerate(rules):
                    table = od.get("pairs", {}).get((d, law["level"], law["cond"])) or {}
                    got = {}
                    for c2, r in table.items():
                        if c2 is not None and c2[1] == f"s{m}" and c2[0] == law["cond"][0]:
                            got[c2[2]] = (r[0], r[2].get(d, 0))
                    if len(got) >= 2:
                        out[(j, repr(d), i)] = got
        return out

    @staticmethod
    def apart(a, b):
        """In powers of ten, how much likelier two counts."""
        ll = lambda n, k, p: k * math.log10(p) + (n - k) * math.log10(1 - p)
        (n1, k1), (n2, k2) = a, b
        own = ll(n1, k1, (k1 + 0.5) / (n1 + 1)) + ll(n2, k2, (k2 + 0.5) / (n2 + 1))
        both = ll(n1 + n2, k1 + k2, (k1 + k2 + 0.5) / (n1 + n2 + 1))
        return own - both

    @staticmethod
    def situation(o, j):
        """What the senses other than j show, as a situation."""
        return tuple(x for i, x in enumerate(o) if i != j)

    @staticmethod
    def kt_digits(counts, kinds):
        """How long, in powers of ten, Krichevsky and Trofimov's code says a run of outcomes."""
        n = sum(counts.values())
        k = max(2, kinds)
        got = math.lgamma(k / 2) - math.lgamma(n + k / 2) + sum(math.lgamma(c + 0.5) - math.lgamma(0.5) for c in counts.values())
        return -got / math.log(10)

    def grain_room(self, grain, m):
        """What it kept of sense m's symbols at a grain."""
        room = self.concept_room()
        if grain.startswith("with "):
            return (room.get("with") or {}).get(int(grain[5:]), {}).get(m, {})
        if grain.startswith("since "):
            return (room.get("since") or {}).get(int(grain[6:]), {}).get(m, {})
        if grain.startswith("both "):
            return (room.get("both") or {}).get(int(grain[5:]), {}).get(m, {})
        return room.get(grain, {}).get(m, {})

    def grain_key(self, grain, a, j, o, m):
        """The key of what act a did to sense j, at a grain of sense m's symbols, in what it sees."""
        if grain == "fine":
            return (a, j, self.situation(o, m))
        if grain == "own":
            return (a, j, o[j])
        if grain == "stats":
            return (a, j)
        if grain.startswith("since ") or grain.startswith("both "):
            ages = self.concept_room().get("ages") or ()
            k = int(grain[5:]) if grain.startswith("both ") else int(grain[6:])
            age = age_of(ages[k]) if k < len(ages) else 0
            return (a, j, o[j], o[k], age) if grain.startswith("both ") else (a, j, o[j], age)
        return (a, j, o[j], o[int(grain[5:])])

    def group_by(self, data, values):
        """Groups of values, joined two at a time while joining says their outcomes."""
        kinds = collections.defaultdict(set)
        for v in values:
            for key, counts in data[v].items():
                kinds[key].update(counts)

        def cost(vs):
            got = 0.0
            for key in {key for v in vs for key in data[v]}:
                counts = collections.Counter()
                for v in vs:
                    counts.update(data[v].get(key, {}))
                got += self.kt_digits(counts, len(kinds[key]))
            return got
        groups = [[v] for v in values]
        costs = [cost(g) for g in groups]
        tried = 0
        while len(groups) > 1:
            best = None
            for x in range(len(groups)):
                for y in range(x + 1, len(groups)):
                    tried += 1
                    joined = cost(groups[x] + groups[y])
                    gain = costs[x] + costs[y] - joined
                    if gain > 0 and (best is None or gain > best[0]):
                        best = (gain, x, y, joined)
            if best is None:
                break
            _, x, y, joined = best
            groups[x] = groups[x] + groups[y]
            costs[x] = joined
            del groups[y], costs[y]
        return groups, cost(values) - sum(costs), tried, sum(costs)

    def form_classes(self, m):
        """The classes of sense m's symbols."""
        room = self.concept_room()
        coarse = room["stats"].get(m, {})
        seen = {v: sum(sum(c.values()) for c in cells.values()) for v, cells in coarse.items()}
        values = sorted((v for v in coarse if seen[v]), key=lambda v: (-seen[v], repr(v)))[:12]
        if len(values) < 2:
            room["classes"][m] = None
            return
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
        for cell in cells:
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
        groups, _, tried, _ = self.group_by(data, values)
        per_key = collections.defaultdict(lambda: [collections.Counter() for _ in groups])
        for i, g in enumerate(groups):
            for v in g:
                for key, counts in data[v].items():
                    per_key[key][i].update(counts)
        digits = exact_digits(groups, per_key, self.kt_digits) if len(groups) >= 2 else 0.0
        tells = set()
        if len(groups) >= 2:
            for cell in cells:
                per = [collections.Counter() for _ in groups]
                for g, c in zip(groups, per):
                    for v in g:
                        c.update(coarse.get(v, {}).get(cell, {}))
                allc = sum(per, collections.Counter())
                k = len(allc)
                if self.kt_digits(allc, k) - sum(self.kt_digits(c, k) for c in per if c) >= EVIDENCE:
                    tells.add(cell)
        looks = room.setdefault("looks", {})
        looks[m] = looks.get(m, 0) + 1
        bar = EVIDENCE + math.log10(bell(len(values))) + paid(looks[m])
        concept = len(groups) >= 2 and digits >= bar
        used = collections.Counter(chosen.values())
        grain = min(used, key=lambda g: (-used[g], g)) if used else "stats"
        room.setdefault("weighed", {})[m] = {"groups": [list(g) for g in groups], "digits": round(digits, 1),
                                             "bar": round(bar, 1), "at": room["steps"], "grain": grain,
                                             "grains": dict(used)}
        classes = [{"rep": g[0], "members": list(g)} for g in groups]
        old = room["classes"].get(m)
        room["classes"][m] = {"classes": classes, "concept": concept, "tells": sorted(tells, key=repr),
                              "digits": round(digits, 1), "grain": grain, "cells": chosen} if concept else None
        if concept:
            self.start_finer(m, groups, data)
        if concept and (old is None or [c["members"] for c in old["classes"]] != [c["members"] for c in classes]):
            shown = [[self.display(x) if isinstance(x, str) else x for x in c["members"]][:8] for c in classes]
            self.emit("concept", sensor=m + 1, classes=shown, tells=len(tells), digits=round(digits, 1), grain=grain)
            self.decide("concept", m + 1, {"classes": shown, "tells": len(tells), "digits": round(digits, 1),
                                           "grain": grain})

    def start_finer(self, m, groups, data):
        """D1: where its foresight inside a class of sense m is not sure."""
        room = self.concept_room()
        trying = room.setdefault("trying", {})
        if m in trying or len(room.get("ages") or ()) < 2:
            return
        if any(len(sum((collections.Counter(data[v].get(key) or {}) for v in g), collections.Counter())) > 1
               for g in groups for key in {key for v in g for key in data[v]}):
            trying[m] = [k for k in range(len(room["ages"])) if k != m]
            self.emit("trying", sensor=m + 1, grains=len(trying[m]))
            self.decide("trying", m + 1, {"grains": len(trying[m])})

    def test_finer(self, m, values):
        """Each finer way it watches for sense m joins its ways of seeing at a cell only when the exact test
        proves that it tells the outcomes there apart beyond chance."""
        room = self.concept_room()
        trying = (room.get("trying") or {}).get(m)
        if not trying:
            return
        coarse = room["stats"].get(m, {})
        cells = sorted({cell for v in values for cell in coarse.get(v, {})}, key=repr)
        tests = room.setdefault("tests", {})
        tests[m] = tests.get(m, 0) + 1
        bar = EVIDENCE + math.log10(len(trying) * max(1, len(cells))) + paid(tests[m])
        proven = room.setdefault("proven", {}).setdefault(m, {})
        shown = room.setdefault("shown_e", {}).setdefault(m, {})
        for k in list(trying):
            seen = (room.get("both") or {}).get(k, {}).get(m, {})
            best = -math.inf
            for cell in cells:
                per = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
                for v in values:
                    for key, counts in (seen.get(v) or {}).items():
                        if key[:2] == cell:
                            per[key[:3]][key[3:]].update(counts)
                if not per:
                    continue
                e = exact_digits(None, {base: list(rows.values()) for base, rows in per.items()}, self.kt_digits)
                best = max(best, e)
                if e >= bar and k not in proven.get(cell, ()):
                    proven.setdefault(cell, []).append(k)
                    self.emit("grew", sensor=m + 1, by=k + 1, digits=round(e, 1), bar=round(bar, 1))
                    self.decide("grew", m + 1, {"by": k + 1, "cell": [cell[0], cell[1] + 1], "digits": round(e, 1),
                                                "bar": round(bar, 1)})
            shown.setdefault(k, []).append(best)
            if not any(k in ks for ks in proven.values()) and len(shown[k]) >= 2 and max(shown[k][-2:]) <= 0:
                trying.remove(k)
                (room.get("both") or {}).get(k, {}).pop(m, None)

    def class_of(self, m, v):
        """The class of sense m's symbol v."""
        room = self.concept_room()
        got = room["classes"].get(m)
        if not got:
            return None
        for c in got["classes"]:
            if v in c["members"]:
                return c["rep"]
        coarse = room["stats"].get(m, {})
        mine_c = coarse.get(v) or {}
        if not mine_c:
            return None
        cells = got.get("cells") or {}
        sizes = [sum(sum(sum(cs.values()) for cs in coarse.get(x, {}).values()) for x in c["members"]) or 1
                 for c in got["classes"]]
        logs = []
        for c, size in zip(got["classes"], sizes):
            lp = math.log10(size / sum(sizes))
            for cell in mine_c:
                data = self.grain_room(cells.get(cell, "stats"), m)
                for key, ours in (data.get(v) or {}).items():
                    if key[:2] != cell and key != cell:
                        continue
                    theirs = collections.Counter()
                    for x in c["members"]:
                        theirs.update(data.get(x, {}).get(key, {}))
                    if not theirs:
                        for x in c["members"]:
                            theirs.update(coarse.get(x, {}).get(cell, {}))
                    kinds = len(set(theirs) | set(ours))
                    both = theirs + collections.Counter(ours)
                    lp -= self.kt_digits(both, kinds) - self.kt_digits(theirs, kinds)
            logs.append(lp)
        top = max(logs)
        post = [10 ** (x - top) for x in logs]
        self._posterior = {c["rep"]: p / sum(post) for c, p in zip(got["classes"], post)}
        best = max(range(len(post)), key=lambda i: (post[i], -i))
        return got["classes"][best]["rep"] if post[best] / sum(post) > 0.5 else None

    def class_posterior(self, m, v):
        """How likely sense m's symbol v is of each class, by its outcomes so far."""
        got = (self.__dict__.get("concepts") or {}).get("classes", {}).get(m)
        if not got:
            return {}
        for c in got["classes"]:
            if v in c["members"]:
                return {c["rep"]: 1.0}
        self._posterior = {}
        self.class_of(m, v)
        return dict(self._posterior)

    def same_class(self, m, x, v):
        """Whether symbols x and v of sense m are of one class."""
        if x is None or v is None or x == v or not (self.__dict__.get("concepts") or {}).get("classes", {}).get(m):
            return False
        cache = self.__dict__.get("_class_cache")
        if cache is None or cache[0] != self.world_steps:
            cache = self._class_cache = (self.world_steps, {})
        for y in (x, v):
            if (m, y) not in cache[1]:
                cache[1][(m, y)] = self.class_of(m, y)
        k = cache[1][(m, x)]
        return k is not None and k == cache[1][(m, v)]

    def class_attrs(self, o):
        """The class of each symbol it sees now, as one more thing seen."""
        room = self.__dict__.get("concepts")
        if not room or not room["classes"]:
            return {}
        return {f"k{j}": self.class_of(j, o[j]) for j, got in room["classes"].items() if got and j < len(o)}

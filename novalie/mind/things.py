# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Analogy, things and the links between its cells."""

import collections
import itertools
import time

from ..laws import PAIRS, is_pair


class Things:
    @staticmethod
    def cell_class(sym):
        """The class of a cell, for its analogies."""
        sym = str(sym or "")
        return "odds" if "~" in sym else "thing" if sym.startswith("{") else "cycle" if sym[:1].isdigit() else "made"

    def analogy(self, A, B):
        """How world A (a kept entry) is like world B."""
        la, lb = A.get("laws") or [], set(map(tuple, B.get("laws") or []))
        senses = sorted({i for _, i, j in la} | {j for _, i, j in la})
        if not senses or not lb or len(senses) > 5:
            return None
        cls_a = [self.cell_class(x) for x in A["senses"]]
        cls_b = [self.cell_class(x) for x in B["senses"]]
        acted_a, acted_b = set(A.get("acted") or ()), set(B.get("acted") or ())
        targets = list(range(len(B["senses"])))
        best = None
        for image in itertools.permutations(targets + [None] * len(senses), len(senses)):
            f = dict(zip(senses, image))
            used = [y for y in image if y is not None]
            if len(used) != len(set(used)):
                continue
            kept = [(c, i, j) for c, i, j in la if f[i] is not None and f[j] is not None and (c, f[i], f[j]) in lb]
            if not kept:
                continue
            alike = sum(cls_a[i] == cls_b[y] for i, y in f.items() if y is not None)
            acts = sum((i in acted_a) == (y in acted_b) for i, y in f.items() if y is not None)
            rank = (len(kept), alike, acts, tuple(-1 if y is None else -y for y in image))
            if best is None or rank > best[0]:
                best = (rank, kept, {i: y for i, y in f.items() if y is not None})
        if best is None:
            return None
        return best[1], best[2]

    def find_analogy(self, entry):
        """What earlier world the one it understood now is like."""
        best = None
        for old in self.knowledge[:-1]:
            if old.get("real") or old.get("world") == entry["world"] or not old.get("laws"):
                continue
            got = self.analogy(entry, old)
            if got and (best is None or len(got[0]) > len(best[1][0])):
                best = (old, got)
        if best is None:
            return None
        old, (kept, f) = best
        pairs = [(entry["senses"][i], old["senses"][y], i + 1, y + 1) for i, y in sorted(f.items())]
        found = {"world": entry["world"], "like": old["world"], "pairs": pairs,
                 "laws": [[c, entry["senses"][i], entry["senses"][j]] for c, i, j in kept]}
        self.__dict__.setdefault("analogies", collections.deque(maxlen=40)).append(found)
        self.emit("analogy", world=entry["world"], like=old["world"], pairs=[[a, b] for a, b, _, _ in pairs], laws=len(kept))
        self.decide("analogy", old["world"], {"pairs": pairs, "laws": found["laws"]})
        return found

    def what_if(self, acts, n=None):
        """What if it did these acts."""
        n = len(acts) if n is None else n
        return self.foresee_odds(n, acts), self.foresee_odds(n)

    def make_things(self, per_sensor):
        """Things: senses whose changes come together at one act beyond chance."""
        bound = set(self.__dict__.pop("bound", set()))
        wishes = self.__dict__.pop("wishes", {})
        mutual = {tuple(sorted(p)) for p, c in wishes.items()
                  if c == "seeks" and (wishes.get((p[1], p[0])) == "seeks" or tuple(sorted(p)) in bound)}
        oneway = {p: c for p, c in wishes.items() if tuple(sorted(p)) not in mutual}
        bound = bound | mutual

        def part_of(i, without):
            got, todo = {i}, [i]
            while todo:
                x = todo.pop()
                for p in bound:
                    if x in p and without not in p:
                        y = p[1] if p[0] == x else p[0]
                        if y not in got:
                            got.add(y)
                            todo.append(y)
            return got

        for (j, i) in oneway:
            whole = part_of(i, j)
            bound = {p for p in bound if not (j in p and (p[0] in whole or p[1] in whole))}
        groups = {j: {j} for j in range(len(per_sensor))}
        for i, j in bound:
            if per_sensor[i] and per_sensor[j]:
                g = groups[i] | groups[j]
                for x in g:
                    groups[x] = g
        out, seen, thing_of = [], set(), {}
        for g in groups.values():
            key = tuple(sorted(g))
            if len(g) < 2 or key in seen:
                continue
            seen.add(key)
            parts = sorted(per_sensor[x] for x in g)
            name = "{" + "+".join(parts) + "}"
            thing_of.update({x: name for x in g})
            things = self.__dict__.setdefault("things", {})
            th = things.setdefault(name, {"parts": parts, "worlds": 0, "born": round(time.time()), "world": self.k})
            th["worlds"] += 1
            th["last"], th["last_world"] = round(time.time()), self.k
            out += [("part", p, name) for p in dict.fromkeys(parts)]
            self.emit("thing", s=name, parts=parts)
            self.decide("thing", name, {"senses": [x + 1 for x in key], "parts": parts})
        wished = set()
        for (j, i), code in sorted(oneway.items()):
            a, b = thing_of.get(j, per_sensor[j]), thing_of.get(i, per_sensor[i])
            if a and b and a != b:
                out.append((code, a, b))
                if (j, code, b) not in wished:
                    wished.add((j, code, b))
                    self.decide("wish", j + 1, {"code": code, "what": b, "sense": i + 1})
        return list(dict.fromkeys(out))

    def odds_links(self, per_sensor, only=None):
        """Laws between its cells from its laws of odds."""
        out = []
        for j, L in enumerate(self.learners):
            od = L.__dict__.get("odds")
            if (only is not None and j != only) or not od or j >= len(per_sensor) or not per_sensor[j]:
                continue
            for d, law in sorted(((d, law) for d, rules in od["laws"].items() for law in rules),
                                 key=lambda kv: (repr(kv[0]), kv[1]["level"])):
                conds = ([(law["cond"], "law")] + [(tuple(x[1]), "unless") for x in law["unless"]]
                         + [(tuple(x[1]), "especially") for x in law["especially"]])
                conds = [(tuple(p), how) for c, how in conds
                         for p in (PAIRS.get(c[1], ()) if is_pair(c[1]) else (c,))]
                for (l, attr, v), how in conds:
                    if attr.startswith("cmp:"):
                        _, x, y = attr.split(":")
                        x, y = int(x), int(y)
                        other = y if x == j else x if y == j else None
                        if other is None or type(d) is not int or not law["up"] or how != "law" or v == "=":
                            pairs = [(i, "fore") for i in (x, y)]
                        else:
                            above = (v == "<") if x == j else (v == ">")
                            pairs = [(other, "seeks" if (d > 0) == above else "flees")]
                    elif attr[0] == "c" and attr[1:].isdigit():
                        i = int(attr[1:])
                        pairs = [(i, "together" if l == 0 and v is not None and ((law["up"] and how == "law")
                                                                                or how == "especially")
                                  else "cause" if self.set_by_acts(i) else "fore")]
                    elif attr[0] == "s" and attr[1:].isdigit():
                        i = int(attr[1:])
                        pairs = [(i, "cause" if self.set_by_acts(i) else "fore")]
                    else:
                        continue
                    for i, code in pairs:
                        if i == j or i >= len(per_sensor) or not per_sensor[i]:
                            continue
                        if code in ("seeks", "flees"):
                            self.__dict__.setdefault("wishes", {})[(j, i)] = code
                        elif code == "together":
                            self.__dict__.setdefault("bound", set()).add(tuple(sorted((i, j))))
                        elif per_sensor[i] != per_sensor[j]:
                            out.append((code, per_sensor[i], per_sensor[j]))
                    if not pairs:
                        continue
                    i, code = pairs[0]
                    if i == j or i >= len(per_sensor) or not per_sensor[i]:
                        continue
                    a2, b2 = (per_sensor[j], per_sensor[i]) if code in ("seeks", "flees") else (per_sensor[i], per_sensor[j])
                    self.odds_laws[f"{code} {a2} {b2} {how}"] = {
                        "code": code, "a": a2, "b": b2, "lag": l, "how": how, "attr": attr,
                        "value": v if isinstance(v, (int, float, str)) else str(v),
                        "d": d if type(d) is int else str(d[1]), "q": law["q"], "p": law["p"],
                        "digits": law["digits"], "tests": law["tests"], "world": self.k, "up": law["up"],
                        "level": law["level"]}
        return list(dict.fromkeys(out))

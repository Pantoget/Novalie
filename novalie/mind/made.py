# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Quantities it makes of its senses."""

import collections
import fractions
import itertools
import math

from ..config import EVIDENCE, MADE_HOWS, MADE_LOOK, MADE_WAYS, ODDS_NEAR
from ..laws import PAIRS, is_pair


class Made:
    @staticmethod
    def made_values(parts, way, hist, T):
        """A made quantity's values at each act."""
        vals = None
        for i, r, c in parts:
            x = hist[i]
            if r.denominator == 1 and c.denominator == 1:
                r, c = int(r), int(c)
            v = [r * x[t] + (c if way != "sum" else 0) for t in range(T)]
            if vals is None:
                vals = v
            elif way == "least":
                vals = [p if p <= q else q for p, q in zip(vals, v)]
            elif way == "most":
                vals = [p if p >= q else q for p, q in zip(vals, v)]
            else:
                vals = [p + q for p, q in zip(vals, v)]
        return vals

    def made_digits(self, y, z, lag, ts, kinds, how="follows"):
        """How long, in powers of ten, the changes of y over the acts ts are told with z lag acts before as their
        context."""
        cells = collections.defaultdict(collections.Counter)
        if how == "follows":
            for t in ts:
                cells[z[t - lag] - y[t - 1]][y[t] - y[t - 1]] += 1
        else:
            for t in ts:
                cells[z[t - lag]][y[t] - y[t - 1]] += 1
        return sum(self.kt_digits(c, kinds) for c in cells.values()), cells

    def seek_made(self):
        """Quantities of its own, sought for each sense of numbers it does not foretell exactly."""
        hist = [L.colors for L in self.learners]
        T = min(len(h) for h in hist)
        nums = [i for i, h in enumerate(hist) if T and all(type(x) is int for x in h[-T:])]
        start = max(ODDS_NEAR + 2, T - MADE_LOOK)
        ts = range(start, T)
        if len(ts) < 2 or len(nums) < 2:
            return
        made = self.__dict__.setdefault("made", {})
        named, control = self.named_senses(), self.__dict__.get("_control")
        for j in nums:
            if j not in named and j != control:
                continue
            if self.learners[j].exact():
                made.pop(j, None)
                continue
            y = hist[j]
            ds = [y[t] - y[t - 1] for t in ts]
            kinds = len(set(ds)) + 1
            chain = collections.defaultdict(collections.Counter)
            for t, d in zip(ts, ds):
                chain[y[t - 1]][d] += 1
            base = sum(self.kt_digits(c, kinds) for c in chain.values())
            tried, singles, aligned = 0, [], {}
            plain = lambda cnt: min(cnt, key=lambda q: (-cnt[q], abs(q), q))
            for how, lag in itertools.product(MADE_HOWS, range(ODDS_NEAR + 1)):
                aligned[(how, lag)] = []
                for i in nums:
                    if i == j or i not in named:
                        continue
                    x = hist[i]
                    if how == "follows":
                        ratios = collections.Counter(fractions.Fraction(y[t] - y[t - 1], x[t - lag] - x[t - lag - 1])
                                                     for t in ts if y[t] != y[t - 1] and x[t - lag] != x[t - lag - 1])
                    else:
                        ratios = collections.Counter(fractions.Fraction(y[t] - y[t - 1], x[t - lag])
                                                     for t in ts if y[t] != y[t - 1] and x[t - lag] != 0)
                    if not ratios:
                        continue
                    r = plain(ratios)
                    if how == "follows":
                        offs = collections.Counter(y[t] - r * x[t - lag] for t in ts)
                    else:
                        offs = collections.Counter(y[t] - y[t - 1] - r * x[t - lag] for t in ts)
                    c = plain(offs)
                    aligned[(how, lag)].append((i, r, c))
                    dig, _ = self.made_digits(y, self.made_values([(i, r, c)], "one", hist, T), lag, ts, kinds, how)
                    tried += 1
                    singles.append((dig, how, lag, i, (i, r, c)))
            if not singles:
                continue
            dig0, how, lag, _, p0 = min(singles, key=lambda e: e[:4])
            best = (dig0, "one", [p0], lag, how)
            starts = {}
            for e in sorted(singles, key=lambda e: e[:4]):
                starts.setdefault((e[1], e[2]), e)
            known = self.__dict__.get("made_ways") or {}
            tried_known = 0
            for (dig0, how, lag, _, p0), way in itertools.product(sorted(starts.values(), key=lambda e: e[:4]), MADE_WAYS):
                parts, now = [p0], dig0
                while True:
                    step = None
                    for p in aligned[(how, lag)]:
                        if p in parts:
                            continue
                        dig, _ = self.made_digits(y, self.made_values(parts + [p], way, hist, T), lag, ts, kinds, how)
                        tried += 1
                        tried_known += self.made_shape(way) in known
                        if dig < now and (step is None or dig < step[0]):
                            step = (dig, p)
                    if step is None:
                        break
                    now = step[0]
                    parts.append(step[1])
                if len(parts) > 1 and now < best[0] - 1e-9:
                    best = (now, way, list(parts), lag, how)
            bar = EVIDENCE + math.log10(max(1, tried))
            if self.made_shape(best[1]) in known:
                bar = EVIDENCE + math.log10(max(1, tried_known))
            old = made.get(j)
            if best is None or base - best[0] < bar:
                if old is not None:
                    made.pop(j)
                    self.emit("made_gone", sensor=j + 1, way=old["way"], parts=[p[0] + 1 for p in old["parts"]])
                    self.decide("made_gone", j + 1, {"way": old["way"], "digits": round(base - best[0], 1) if best else 0.0,
                                                     "bar": round(bar, 1)})
                continue
            dig, way, parts, lag, how = best
            z = self.made_values(parts, way, hist, T)
            every = range(ODDS_NEAR + 2, T)
            _, cells = self.made_digits(y, z, lag, every, kinds, how)
            shift = plain(collections.Counter((y[t] if how == "follows" else y[t] - y[t - 1]) - z[t - lag] for t in every))
            fol = [(g, c) for g, c in cells.items() if sum(c.values()) >= 2]
            law = (bool(fol) and all(max(sorted(c, key=repr), key=lambda e: c[e]) == g + shift for g, c in fol)
                   and len({g + shift for g, _ in fol if g + shift != 0}) >= 2)
            hits, all_ = sum(c.get(g + shift, 0) for g, c in cells.items()), sum(sum(c.values()) for c in cells.values())
            rec = {"way": way, "parts": parts, "lag": lag, "how": how, "shift": shift,
                   "digits": round(base - dig, 1), "bar": round(bar, 1),
                   "follows": round((hits + 0.5) / (all_ + 1), 4) if law else None,
                   "cells": {g: dict(c) for g, c in cells.items()}, "at": self.world_steps, "n1": 0, "k1": 0}
            same = old is not None and (old["way"], old["parts"], old["lag"], old.get("how", "follows")) == (way, parts, lag, how)
            made[j] = rec
            if j == control and not same:
                self.control_mark("made")
            if way != "one" and j != control:
                ways = self.__dict__.setdefault("made_ways", {})
                like = ways.get(self.made_shape(way))
                if not same and like and like.get("last") and like["last"]["world"] != self.k:
                    was = like["last"]
                    self.emit("made_like", sensor=j + 1, shape=self.made_shape(way), world=was["world"], was=was)
                    self.decide("made_like", j + 1, {"shape": self.made_shape(way), "like": was,
                                                     "now": {"way": way, "parts": len(parts), "lag": lag}})
                shape = ways.setdefault(self.made_shape(way), {"worlds": set(), "n": 0})
                shape["worlds"].add(self.k)
                shape["n"] += not same
                shape["last"] = {"world": self.k, "way": way, "parts": len(parts), "lag": lag, "sensor": j + 1}
            if not same:
                shown = [[p[0] + 1, str(p[1]), str(p[2])] for p in parts]
                self.emit("made", sensor=j + 1, way=way, parts=shown, lag=lag, how=how, digits=rec["digits"], bar=rec["bar"])
                self.decide("made", j + 1, {"way": way, "parts": shown, "lag": lag, "how": how, "digits": rec["digits"],
                                            "bar": rec["bar"], "law": rec["follows"]})
            else:
                rec["n1"], rec["k1"], rec["at"] = old["n1"], old["k1"], old["at"]

    @staticmethod
    def made_shape(way):
        """The shape of a made quantity."""
        return "bound" if way in ("least", "most") else way

    def see_made(self):
        """Its made quantities, act by act."""
        made = self.__dict__.get("made")
        if made is None:
            made = self.made = {}
        if made:
            hist = [L.colors for L in self.learners]
            T = min(len(h) for h in hist)
            for j, rec in made.items():
                lag = rec["lag"]
                if T < lag + 3:
                    continue
                y = hist[j]
                z = self.made_values(rec["parts"], rec["way"], [h[T - 1 - lag:T - lag] for h in hist], 1)[0]
                gap, d = (z - y[T - 2] if rec.get("how", "follows") == "follows" else z), y[T - 1] - y[T - 2]
                cell = rec["cells"].setdefault(gap, {})
                if cell:
                    rec["n1"] += 1
                    rec["k1"] += max(sorted(cell, key=repr), key=lambda e: cell[e]) == d
                cell[d] = cell.get(d, 0) + 1
        if self.world_steps >= max(50, 2 * self.__dict__.get("made_at", 0)):
            self.made_at = self.world_steps
            self.seek_made()

    def pairs_seen(self, entry, past):
        """Each condition of two together it believes, as one more thing it sees at this act."""
        def holds(name, l):
            for pl, pa, pv in PAIRS.get(name, ()):
                lag = l + pl
                if is_pair(pa):
                    if holds(pa, lag) != bool(pv):
                        return False
                    continue
                e = entry if lag == 0 else (past[-lag] if lag <= len(past) else None)
                if e is None or e.get(pa) != pv:
                    return False
            return True
        for name in self.__dict__.get("pair_names") or ():
            entry[name] = int(holds(name, 0))

    def made_seen(self, o):
        """What its made quantities show now."""
        got = {}
        named = self.named_senses()
        for j, rec in (self.__dict__.get("made") or {}).items():
            if (j not in named or j >= len(o) or any(i >= len(o) or type(o[i]) is not int for i, _, _ in rec["parts"])
                    or type(o[j]) is not int):
                continue
            col = [[x] for x in o]
            z = self.made_values(rec["parts"], rec["way"], col, 1)[0]
            got[f"m{j}.{rec['at']}"] = z - o[j] if rec.get("how", "follows") == "follows" else z
            if rec["way"] in ("least", "most"):
                vals = [self.made_values([p], "one", col, 1)[0] for p in rec["parts"]]
                pick = min(vals) if rec["way"] == "least" else max(vals)
                got[f"w{j}.{rec['at']}"] = rec["parts"][vals.index(pick)][0]
        return got

    def made_next(self, j, a, out, rnd, follow=False):
        """What its made quantity for sense j foresees it will show after the act."""
        rec = (self.__dict__.get("made") or {}).get(j)
        if rec is None:
            return None
        hist = [L.colors for L in self.learners]
        lag = rec["lag"]
        if lag == 0:
            if rnd == 0 or any(out[i] is None or out[i][0] is None for i, _, _ in rec["parts"]):
                return None
            now = [[out[i][0]] if any(i == p[0] for p in rec["parts"]) else [None] for i in range(len(hist))]
            z = self.made_values(rec["parts"], rec["way"], now, 1)[0]
        else:
            if min(len(h) for h in hist) < lag:
                return None
            z = self.made_values(rec["parts"], rec["way"], [h[len(h) - lag:len(h) - lag + 1] for h in hist], 1)[0]
        y = hist[j][-1]
        moves = rec.get("how", "follows") == "moves"
        ctx = z if moves else z - y
        cell = rec["cells"].get(ctx)
        if follow:
            to = (y + z if moves else z) + rec.get("shift", 0)
            if not rec.get("follows") or to != int(to):
                return None
            return (int(to), rec["follows"])
        if not cell:
            return None
        n, kinds = sum(cell.values()), len(cell) + 1
        d = max(sorted(cell, key=repr), key=lambda e: cell[e])
        return (y + d, round((cell[d] + 0.5) / (n + 0.5 * kinds), 4))

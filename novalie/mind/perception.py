# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its senses: levels of what it sees, and its cells."""

import math

from ..cells import seen_symbol, symbol
from ..config import GRAIN_LOOK
from ..laws import grain_of
from ..learner import Learner


class Perception:
    # -- reasoning ---------------------------------------------------------------
    def all_cells(self):
        """Every cell it has, by its symbol."""
        out = {symbol(k) for k in self.kinds_seen} | {seen_symbol(k) for k in self.seen_kinds}
        out |= set(self.invented_seen) | set(self.generals) | set(self.odds_seen) | set(self.__dict__.get("things") or ())
        return out

    def known_lengths(self):
        """Every cycle length it knows, from anywhere."""
        out = {}
        for k in self.kinds_seen:
            for x in set(k[1]) | {math.prod(k[1])}:
                out.setdefault(x, "lived")
        for k in self.seen_kinds:
            for x in set(k[1]) | {math.prod(k[1])}:
                out.setdefault(x, "read")
        for g in self.generals.values():
            if g["kind"] == "part":
                out.setdefault(g["g"], "general")
        for e in self.library:
            out.setdefault(e["d"], "lived")
        return out

    def as_levels(self, o, keep=True):
        """What it sees, each quantity it sees with fractions."""
        if not any(type(x) is float for x in o):
            return o
        raw, grains = self.__dict__.setdefault("raw", {}), self.__dict__.setdefault("grains", {})
        out = list(o)
        for j, x in enumerate(o):
            if type(x) is not float:
                continue
            if keep and grains.get(j) is None:
                xs = raw.setdefault(j, [])
                xs.append(x)
                if len(xs) >= GRAIN_LOOK and len(getattr(self, "learners", ())) > j:
                    g = grain_of(xs)
                    if g is not None:
                        grains[j] = g
                        self.regrain(j, xs, len(xs) - 1)
            g = grains.get(j)
            out[j] = None if g is None else round(x / g)
        return tuple(out)

    def regrain(self, j, xs, upto):
        """A quantity's grain chosen."""
        g = self.grains[j]
        old = self.learners[j]
        levels = [round(x / g) for x in xs[:upto]]
        L = Learner(self.world.buttons, levels[0], getattr(old, "eps0", self.eps))
        for a, v in zip(old.actions, levels[1:]):
            L.observe(a, v)
        self.learners[j] = L
        self.raw.pop(j, None)
        shown = float(f"{g:.6g}")
        self.emit("grain", sensor=j + 1, grain=shown, levels=len(set(levels)))
        self.decide("grain", j + 1, {"grain": shown, "levels": len(set(levels)), "seen": upto})

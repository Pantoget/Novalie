# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie Organism: the part of its mind that builds its own anatomy."""
import collections
import importlib.util
import itertools
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
from . import counts as nm


# ----------------------------------------------------------------------------

CELL, LINK, GROUP = 8.0, 8.0, 12.0


def cell_bits(d):
    return CELL + math.log2(d)


def class_bits(labels):
    """Bits to say which class each item is in, canonically."""
    n, k = len(labels), len(set(labels))
    seen, bits = 0, 0.0
    for i, c in enumerate(labels):
        if k - seen == n - i:
            break
        bits += math.log2(min(seen + 1, k))
        if c == seen:
            seen += 1
    return bits


def split_bits(d1, d2, colour, n_col):
    """Description of a colour table over two cells."""
    rows, cols = {}, {}
    rc = [rows.setdefault(tuple(colour(x1, x2) for x2 in range(d2)), len(rows)) for x1 in range(d1)]
    cc = [cols.setdefault(tuple(colour(x1, x2) for x1 in range(d1)), len(cols)) for x2 in range(d2)]
    core = {(rc[x1], cc[x2]): colour(x1, x2) for x1 in range(d1) for x2 in range(d2)}
    bits = class_bits(rc) + class_bits(cc) + len(core) * math.log2(n_col)
    return bits, rc, cc, core


class Anatomy:
    """Cells with cycles and the connections between them, for a world whose buttons commute."""

    def __init__(self, kind, cycles, eff, u=1, colour=None, rc=None, cc=None, core=None, bits=0.0, phase=0):
        self.kind, self.cycles, self.eff, self.u, self.phase = kind, cycles, eff, u, phase
        self.colour_table, self.rc, self.cc, self.core, self.bits = colour, rc, cc, core, bits

    def state_of(self, key):
        if self.kind == "flat":
            return key
        d = self.cycles[0] * self.cycles[1]
        x = (self.u * key[0] - getattr(self, "phase", 0)) % d
        d1, d2 = self.cycles
        return (x % d1, x // d1) if self.kind == "gear" else (x % d1, x % d2)

    def step(self, s, a):
        if self.kind == "flat":
            return tuple((x + e) % q for x, e, q in zip(s, self.eff[a], self.cycles))
        d1, d2 = self.cycles
        e1, e2 = self.eff[a]
        if self.kind == "gear":
            x1 = s[0] + e1
            return (x1 % d1, (s[1] + e2 + x1 // d1) % d2)
        return ((s[0] + e1) % d1, (s[1] + e2) % d2)

    def colour(self, s):
        if self.kind == "flat":
            return self.colour_table.get(s)
        return self.core[(self.rc[s[0]], self.cc[s[1]])]

    def describe(self, buttons):
        parts = [f"cell {d}" for d in self.cycles]
        if self.kind == "gear":
            parts.append(f"carry {self.cycles[0]}->{self.cycles[1]}")
        for a, b in enumerate(buttons):
            for i, e in enumerate(self.eff[a]):
                if e % self.cycles[i]:
                    parts.append(f"{b}->cell {self.cycles[i]} ({e % self.cycles[i]:+d})")
        return ", ".join(parts)


def compile_commuting(mind):
    """The smallest anatomy that explains what the organism has learned."""
    mo, m = mind.model, mind.m
    n_col = len(set(mind.colors))
    eff = [[e % q for e, q in zip(mo.eff[a], mo.mods)] for a in range(m)]
    links = sum(1 for a in range(m) for i in range(len(mo.mods)) if eff[a][i])
    flat_bits = (sum(cell_bits(q) for q in mo.mods) + LINK * links
                 + math.prod(mo.mods) * math.log2(n_col))
    best = Anatomy("flat", list(mo.mods), eff, colour=mind.table, bits=flat_bits)
    tried = 0
    if len(mo.mods) != 1:
        return best, tried
    d = mo.mods[0]
    tv = [mind.table[(x,)] for x in range(d)]
    gauges = {1} | {pow(e[0], -1, d) * s % d for e in eff for s in (1, -1) if math.gcd(e[0], d) == 1}
    for u in sorted(gauges):
        ui = pow(u, -1, d)
        seq = [tv[(ui * y) % d] for y in range(d)]
        turns = [y for y in range(d) if seq[y] != seq[y - 1]]
        for d1 in range(2, d):
            if d % d1:
                continue
            d2 = d // d1
            at = collections.Counter(y % d1 for y in turns).most_common(1)
            ways = [("gear", 0)] + ([("gear", at[0][0])] if at and at[0][0] else []) + [("crt", 0)]
            for kind, c in ways:
                if kind == "crt" and math.gcd(d1, d2) != 1:
                    continue
                if kind == "gear":
                    colour = lambda x1, x2: tv[(ui * (x1 + d1 * x2 + c)) % d]
                else:
                    inv = pow(d1, -1, d2)
                    colour = lambda x1, x2: tv[(ui * (x1 + d1 * (((x2 - x1) * inv) % d2))) % d]
                bits, rc, cc, core = split_bits(d1, d2, colour, n_col)
                e2s = []
                for a in range(m):
                    e = (u * eff[a][0]) % d
                    e2s.append((e % d1, (e // d1) % d2) if kind == "gear" else (e % d1, e % d2))
                nl = sum(1 for e in e2s for x in e if x) + (kind == "gear")
                total = cell_bits(d1) + cell_bits(d2) + LINK * nl + bits
                tried += 1
                if total < best.bits - 1e-9:
                    best = Anatomy(kind, [d1, d2], e2s, u, None, rc, cc, core, total, c)
    return best, tried


class OrganismMind(nm.Mind):
    """The mind of the organism."""

    def relearn(self, t):
        if self.check(self.model) is None and self.model.gens:
            gens, best = self.model.gens, None
            for i in range(len(gens)):
                trial = nm.Model(self.m, gens[:i] + gens[i + 1:])
                n = self.check(trial)
                if n is not None and (best is None or n < best[0]):
                    best = (n, trial)
            if best is not None:
                self.model = best[1]
                self.ledger.append((t, "revised", list(best[1].mods)))
                self.freq.update(self.implied)
                self.implied.clear()
        super().relearn(t)


# ----------------------------------------------------------------------------

class TunedMind(OrganismMind):
    """A mind whose skepticism."""

    def __init__(self, world, eps, tune):
        super().__init__(world)
        self.eps, self.tune, self.revisions = eps, tune, 0

    def evidence(self, eps=1e-5):
        return super().evidence(self.eps)

    def relearn(self, t):
        before = sum(e[1] == "revised" for e in self.ledger)
        super().relearn(t)
        new = sum(e[1] == "revised" for e in self.ledger) - before
        if new:
            self.revisions += new
            if self.tune:
                self.eps = max(self.eps / 100, 1e-12)



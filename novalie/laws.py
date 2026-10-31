# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""What a law sees at one act, and the shapes, keys and anatomies of its laws."""

import collections
import hashlib
import math

from .config import ODDS_CLOSE, ODDS_LAGS, ODDS_NEAR


class Moments:
    """A sense known by its moments, as an anatomy."""
    def __init__(self, P, d, M, phase, value):
        self.P, self.d, self.M, self.phase0, self.value0 = P, d, M, phase, value
        self.kind, self.cycles = ("flat", [M]) if P == 1 else ("gear", [P, M])

    def state_of(self, key):
        return (self.phase0, self.value0)

    def step(self, s, a):
        phase, value = s[0] + 1, s[1]
        if phase >= self.P:
            phase, value = 0, (value + self.d) % self.M
        return (phase, value)

    def colour(self, s):
        return s[1]


def seen_with(o, prev, a, ordinal=None, named=None):
    """What it saw at one act, for its laws of odds."""
    shown = range(len(o)) if named is None else [i for i in range(len(o)) if i in named]
    st = {f"s{i}": o[i] for i in shown}
    st["act"] = a
    for i in shown:
        st[f"c{i}"] = None if prev is None or i >= len(prev) or prev[i] is MISSING_SEEN else change_of(prev[i], o[i])
    nums = [i for i in shown if type(o[i]) is int and (ordinal is None or i in ordinal)]
    for n, i in enumerate(nums):
        for k in nums[n + 1:]:
            st[f"cmp:{i}:{k}"] = "<" if o[i] < o[k] else "=" if o[i] == o[k] else ">"
    return st


MISSING_SEEN = object()


def since_level(n):
    """How long a sense has been as it is, as a clock it made shows it."""
    return n if n < 16 else 2 ** int(math.log2(n))


def recalled_moment(mo):
    """A law of moments it recalled, taken up again as a hypothesis."""
    return {"cond": dict(mo["cond"]), "d": mo["d"], "M": mo["M"], "proof": 0.0, "steps": 0, "held": 0, "revised": 0,
            "attrs": mo["attrs"], "values": set(mo.get("values") or ()), "times": [], "announced": False,
            "recalled": mo["P"], "tested": set()}


def age_of(acts):
    """How long ago a sense last changed, as its laws of odds look back."""
    return max(l for l in ODDS_LAGS if l <= acts)


PAIRS = {}


def is_pair(attr):
    """Is this thing it sees a condition of two together."""
    return isinstance(attr, str) and attr.startswith("and:")


def pair_name(parts):
    """The name of a condition of two together, made of what its two parts are."""
    key = repr(tuple(sorted(parts, key=repr)))
    return "and:" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def cond_depth(c):
    """How many plain conditions a condition is made of."""
    return sum(cond_depth(p) for p in PAIRS[c[1]]) if is_pair(c[1]) else 1


def causal(c):
    """Is a condition a cause."""
    l, attr, v = c
    if is_pair(attr):
        return all(causal((l + p[0], p[1], p[2])) for p in PAIRS.get(attr, ()))
    return l >= 1 or attr == "act"


def part_shape(c):
    """The shape of one condition with no sense or cell in it."""
    l, attr, v = c
    if is_pair(attr):
        return ("and",) + tuple(sorted((part_shape((l + p[0], p[1], p[2])) for p in PAIRS[attr]), key=repr))
    return (law_shape(c, 1, True)[0], l)


def law_shape(c, d, up):
    """The shape of a law of odds, with no sense or cell in it."""
    l, attr, v = c
    if is_pair(attr):
        return (part_shape(c), l, bool(up), ((d > 0) - (d < 0)) if type(d) is int else "to")
    what = ("act" if attr == "act" else "cmp" if attr.startswith("cmp:") else "made" if attr[0] in "mw" and "." in attr
            else "c" if attr[0] == "c" else "s")
    return (what, l, bool(up), ((d > 0) - (d < 0)) if type(d) is int else "to")


def odds_key(l, attr, j):
    """Whether its laws of odds for sense j may be conditioned on attr seen l acts before."""
    if attr == "act":
        return True
    if is_pair(attr):
        parts = PAIRS.get(attr)
        return l == 0 and parts is not None and all(odds_key(p[0], p[1], j) for p in parts)
    if attr.startswith("cmp:"):
        _, i, k = attr.split(":")
        return l <= ODDS_CLOSE and not (l == 0 and str(j) in (i, k))
    if attr[0] in "mw" and "." in attr:
        return not (l == 0 and attr[0] == "m" and attr[1:attr.index(".")] == str(j))
    if attr[0] == "t" and attr[1:].isdigit():
        return l == 1
    if attr[0] == "c":
        return l <= ODDS_NEAR and attr != f"c{j}"
    return attr not in (f"s{j}", f"k{j}")


def change_of(before, o):
    """A change of a sense as its laws of odds count it."""
    if o == before:
        return None
    if type(o) is int and type(before) is int:
        return o - before
    return ("to", o)


def grain_of(xs):
    """Its grain for a quantity it sees with fractions."""
    vals = sorted(set(xs))
    steps = [b - a for a, b in zip(vals, vals[1:]) if b - a > 0]
    if not steps:
        return None
    res, span = min(steps), vals[-1] - vals[0]
    best, g = None, res
    while True:
        lv = [round(x / g) for x in xs]
        ds = [b - a for a, b in zip(lv, lv[1:])]
        told, bits, K = collections.Counter(), 0.0, len(set(ds))
        for i, d in enumerate(ds):
            bits -= math.log2((told[d] + 0.5) / (i + K / 2))
            told[d] += 1
        bits += sum(2 * math.log2(abs(d) + 1) + 1 for d in told) + len(xs) * math.log2(g / res)
        if best is None or bits < best[0]:
            best = (bits, g)
        g *= 2
        if g > span / 2:
            break
    return best[1]


def odds_symbol(cell):
    """Its name for a cell of chance."""
    return f"{cell[0]}~{cell[1]}"


class Odds:
    """A sense known by its odds, as an anatomy."""
    kind = "odds"

    def __init__(self, values, dwell, last):
        self.cycles, self.last = [values, dwell], last

    def state_of(self, key):
        return self.last

    def step(self, s, a):
        return s

    def colour(self, s):
        return s

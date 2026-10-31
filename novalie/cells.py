# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Cells of what it understood: machines it invented and kinds it knew."""

from .parts import inventor


class Invented:
    """A sensor a mechanism it invented explains, used like an anatomy."""
    kind = "invented"

    def __init__(self, rec, i):
        self.mech, self.i, self.cycles = rec["mech"], i, []

    def state_of(self, key):
        return self.mech.state

    def step(self, s, a):
        ins = self.mech.assign[a] if a < len(self.mech.assign) else None
        return s if ins is None else inventor.act(ins, self.mech.shape[0], *s)

    def colour(self, s):
        return self.mech.maps[self.i].get(inventor.see(self.mech.looks[self.i], *s))


class Known:
    """A kind recognised from memory, used like an anatomy."""
    kind = "flat"

    def __init__(self, r):
        self.r, self.cycles = r, [r["d"]]

    def state_of(self, key):
        return self.r["p"]

    def step(self, s, a):
        return (s + self.r["eff"].get(a, 0)) % self.r["d"]

    def colour(self, s):
        return self.r["T"][s]


def seen_symbol(kind):
    """Its name for a structure it found in something it read."""
    return "×".join(str(w) for w in kind[1])


def symbol(kind):
    """Its own name for a kind of concept."""
    shape, cycles = kind
    if shape == "gear":
        return f"{cycles[0]}.{cycles[1]}"
    if shape == "crt":
        return f"{cycles[0]}x{cycles[1]}"
    return ",".join(str(c) for c in cycles)


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

class Gone:
    """What a memory holds of a kind of thing it no longer has."""
    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        pass

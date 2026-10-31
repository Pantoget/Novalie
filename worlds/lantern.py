# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""A lantern: oil, a wick, a flame, and gusts of wind on a hidden timer."""
import random

TITLE = "Lantern"
ABOUT = "pour, trim, light; it burns its oil, and gusts blow it out on a hidden timer"


def symbols(rng, n):
    return ["".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(2)) for _ in range(n)]


class World:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.brim, self.burn, self.gust = rng.randint(3, 6), rng.randint(2, 3), rng.randint(6, 12)
        names = symbols(rng, self.brim + 7)
        b = self.brim + 1
        self.oil_sym, self.wick_sym = names[:b], names[b:b + 2]
        self.flame_sym, self.smoke_sym = names[b + 2:b + 4], names[b + 4:b + 6]
        self.oil, self.wet, self.lit = rng.randint(0, self.brim), rng.random() < 0.5, False
        self.clock, self.burnt, self.smoke = rng.randint(0, self.gust - 1), 0, False
        self.meaning = rng.sample(range(4), 4)       # wait, pour, light, trim: in an order of its own
        self.buttons = [(f"b{i}", 1, i) for i in range(4)]
        self.sensors = [("oil", "symbol", None), ("wick", "symbol", None), ("flame", "symbol", None),
                        ("smoke", "symbol", None)]
        self.size = b * 8 * self.gust * self.burn

    @property
    def state(self):
        return [self.oil, self.wet, self.lit, self.clock, self.burnt, self.smoke]

    def press(self, a):
        self.smoke = False
        act = self.meaning[a]
        if act == 1:                                  # pour: oil up a level, the wick wet
            self.oil, self.wet = min(self.brim, self.oil + 1), True
        elif act == 2 and not self.lit and self.oil > 0 and not self.wet:
            self.lit, self.burnt = True, 0            # light: only with oil and a dry wick
        elif act == 3:                                # trim: the wick dry
            self.wet = False
        if self.lit:
            self.burnt += 1
            if self.burnt % self.burn == 0:
                self.oil -= 1
            if self.oil <= 0:
                self.oil, self.lit, self.smoke = 0, False, True
        self.clock += 1
        if self.clock >= self.gust:                   # a gust, whatever it does
            self.clock = 0
            if self.lit:
                self.lit, self.smoke = False, True

    def observe(self):
        return (self.oil_sym[self.oil], self.wick_sym[int(self.wet)], self.flame_sym[int(self.lit)],
                self.smoke_sym[int(self.smoke)])

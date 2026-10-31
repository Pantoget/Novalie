# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""A kettle that whistles a fixed, unknown number of acts after it is switched on."""
import random

TITLE = "Kettle"
ABOUT = "it whistles some acts after its switch is turned on, and stops when it is turned off"


def symbols(rng, n):
    return ["".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(2)) for _ in range(n)]


class World:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.delay = rng.randint(5, 13)
        names = symbols(rng, 4)
        self.on_sym, self.wh_sym = names[:2], names[2:]
        self.on, self.since, self.whistle = False, 0, False
        self.buttons = [("wait", 1, 0), ("switch", 1, 1)]
        self.sensors = [("switch", "symbol", None), ("whistle", "symbol", None)]
        self.size = 28

    @property
    def state(self):
        return [self.on, self.since, self.whistle]

    def press(self, a):
        if a == 1:
            self.on, self.since = not self.on, 0
        elif self.on:
            self.since += 1
        self.whistle = self.on and self.since >= self.delay

    def observe(self):
        return (self.on_sym[int(self.on)], self.wh_sym[int(self.whistle)])

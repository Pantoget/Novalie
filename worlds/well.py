# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""A well and a trough: a bucket to crank up, fill and tip; the trough drains on a hidden timer."""
import random

TITLE = "Well"
ABOUT = "crank the bucket up, fill it, tip it into the trough; the trough drains by itself"


def symbols(rng, n):
    return ["".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(2)) for _ in range(n)]


class World:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.top, self.brim, self.timer = rng.randint(2, 5), rng.randint(3, 6), rng.randint(3, 9)
        names = symbols(rng, (self.top + 1) + 2 + (self.brim + 1) + 2)
        i = self.top + 1
        self.height_sym, self.full_sym = names[:i], names[i:i + 2]
        self.trough_sym, self.bell_sym = names[i + 2:i + 3 + self.brim], names[i + 3 + self.brim:]
        self.height, self.full = rng.randint(0, self.top), rng.random() < 0.5
        self.trough, self.clock, self.bell = rng.randint(0, self.brim), rng.randint(0, self.timer - 1), False
        self.buttons = [("wait", 1, 0), ("crank", 1, 1), ("lower", 1, 2), ("tip", 1, 3)]
        self.sensors = [("bucket", "symbol", None), ("filled", "symbol", None), ("trough", "symbol", None),
                        ("bell", "symbol", None)]
        self.size = (self.top + 1) * 2 * (self.brim + 1) * 2 * self.timer

    @property
    def state(self):
        return [self.height, self.full, self.trough, self.clock, self.bell]

    def press(self, a):
        self.bell = False
        if a == 1:
            self.height = min(self.top, self.height + 1)
        elif a == 2:
            self.height, self.full = 0, True
        elif a == 3 and self.height == self.top and self.full:
            self.full = False
            if self.trough < self.brim:
                self.trough += 1
                self.bell = self.trough == self.brim
        self.clock += 1
        if self.clock >= self.timer:
            self.clock = 0
            self.trough = max(0, self.trough - 1)

    def observe(self):
        return (self.height_sym[self.height], self.full_sym[int(self.full)], self.trough_sym[self.trough],
                self.bell_sym[int(self.bell)])

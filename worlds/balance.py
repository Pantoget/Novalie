# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>

"""A balance with two pans: it sees only which way it tips."""
import random

TITLE = "Balance"
ABOUT = "weights on two pans, and a button that swaps the pans; it sees only which way it tips"


def symbols(rng, n):
    return ["".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(2)) for _ in range(n)]


class World:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.sym = symbols(rng, 3)
        self.pans = [rng.randint(0, 4), rng.randint(0, 4)]
        self.buttons = [("left+", 1, 0), ("right+", 1, 1), ("left-", 1, 2), ("right-", 1, 3), ("swap", 1, 4)]
        self.sensors = [("tilt", "symbol", None)]
        self.size = 25

    @property
    def state(self):
        return list(self.pans)

    def press(self, a):
        if a < 2:
            self.pans[a] = min(4, self.pans[a] + 1)
        elif a < 4:
            self.pans[a - 2] = max(0, self.pans[a - 2] - 1)
        else:
            self.pans.reverse()

    def observe(self):
        left, right = self.pans
        return (self.sym[(left > right) - (left < right) + 1],)

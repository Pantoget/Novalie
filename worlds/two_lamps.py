# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Two lamps of chance and a wheel that only the two together foretell."""
import random

TITLE = "Two lamps"
ABOUT = "a wheel flips when two lamps of chance show the same; each lamp alone says nothing"


def symbols(rng, n):
    return ["".join(rng.choice("bcdfghjklmnpqrstvwxz") + rng.choice("aeiou") for _ in range(2)) for _ in range(n)]


class World:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        names = symbols(self.rng, 6)
        self.left_sym, self.right_sym, self.decoy_sym = names[0:2], names[2:4], names[4:6]
        self.left = self.right = self.wheel = self.decoy = 0
        self.buttons = [("let be", 1, 0), ("wave", 1, 1)]
        self.sensors = [("left", "symbol", None), ("right", "symbol", None), ("wheel", "number", None),
                        ("decoy", "chance", None)]
        self.size = 16

    @property
    def state(self):
        return [self.left, self.right, self.wheel, self.decoy]

    def press(self, a):
        u = [self.rng.random() for _ in range(4)]
        if u[0] < (0.9 if self.left == self.right else 0.1):
            self.wheel = 1 - self.wheel
        self.left, self.right, self.decoy = int(u[1] < 0.5), int(u[2] < 0.5), int(u[3] < 0.3)

    def observe(self):
        return (self.left_sym[self.left], self.right_sym[self.right], self.wheel, self.decoy_sym[self.decoy])

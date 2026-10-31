# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Three cups: swap the first two, or move all one place; it sees the cup in the first place."""
import random

TITLE = "Three cups"
ABOUT = "a machine no innate part holds: it learns its states, and keeps it as a part of its own"


class World:
    def __init__(self, seed):
        rng = random.Random(seed)
        self.cups = rng.sample(["red", "green", "blue"], 3)
        self.swap_first = rng.random() < 0.5
        self.buttons = [("a", 1, 0), ("b", 1, 1)]
        self.sensors = [("first", "colour", None)]
        self.size = 6

    @property
    def state(self):
        return list(self.cups)

    def press(self, a):
        c = self.cups
        self.cups = [c[1], c[0], c[2]] if (a == 0) == self.swap_first else [c[2], c[0], c[1]]

    def observe(self):
        return (self.cups[0],)

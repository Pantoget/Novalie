# Worlds

Every file here is a world Novalie can live in. Choose one on its page (the **World** menu at the top); it moves
into it at once, and comes back to the real world when you choose that again. Its laws are never told to it: it
sees only symbols and chooses only acts.

## Write your own

A world is a Python file in this folder with a class `World`:

```python
import random

TITLE = "A lamp and a switch"                 # shown in the menu
ABOUT = "the lamp follows the switch, one act late"

class World:
    def __init__(self, seed):
        rng = random.Random(seed)              # its own chance: a new world for every seed
        self.on = self.lit = False
        self.buttons = [("wait", 1, 0), ("flip", 1, 1)]          # its acts: (name, 1, index)
        self.sensors = [("switch", "symbol", None), ("lamp", "symbol", None)]   # what it sees
        self.size = 4                          # about how many states it has

    @property
    def state(self):                           # the hidden state, for the page
        return [self.on, self.lit]

    def press(self, a):                        # one act
        self.lit = self.on
        if a == 1:
            self.on = not self.on

    def observe(self):                         # what each sense shows now: numbers or any symbols
        return ("on" if self.on else "off", "lit" if self.lit else "dark")
```

Rules of thumb: show symbols that mean nothing to it (it should learn what they do, not read their names); keep
`observe()` the same length every act; draw everything random from `seed`, so a world can be met again.

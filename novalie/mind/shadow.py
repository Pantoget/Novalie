# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""mind.shadow"""

from ..body import sense_key
from ..laws import recalled_moment
from . import Novalie


class Replay:
    """The world of a twin (Novalie.twins_see)."""

    def __init__(self, buttons, sensors, shown):
        self.k, self.name, self.jumped, self.factors, self.dims, self.machine = 0, "twin", False, [], [], None
        self.buttons, self.sensors, self.size, self.shown = list(buttons), list(sensors), 86400, shown

    @property
    def state(self):
        return list(self.shown)

    def press(self, a):
        pass

    def observe(self):
        return tuple(self.shown)


class Shadow(Novalie):
    """A twin of its mind, for a trial of how it is built on its real life."""

    def emit(self, *args, **kw):
        pass

    def decide(self, *args, **kw):
        pass

    def journal_begin(self, *args, **kw):
        return {}

    def journal_end(self, *args, **kw):
        return None

    def invent_for(self, *args, **kw):
        return None

    def speak(self, *args, **kw):
        pass

    def save(self, *args, **kw):
        pass

    def take_recall(self, got):
        """What its mind recalls of its senses, taken up as hypotheses."""
        for j, L in enumerate(self.learners):
            if j < len(self.world.sensors):
                mo = (got.get(sense_key(self.world.sensors[j])) or {}).get("moment")
                if mo:
                    L.moment = recalled_moment(mo)

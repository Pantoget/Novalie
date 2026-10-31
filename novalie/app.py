# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""The whole model in one namespace: what its workshop, its concepts and its memory find by name."""
import os
import sys

from . import body, cells, config, evidence, inventing, laws, learner, memory, text, web
from .mind import Novalie
from .mind.shadow import Replay, Shadow
from . import parts

parts.old_names()
_HOMES = (config, evidence, laws, text, web, body, learner, inventing, cells, memory)


def __getattr__(name):
    """A name of any of its modules (settings read live, as they are now)."""
    for mod in _HOMES:
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(name)


EPROC = None
if os.environ.get("NOVALIE_EPROC", "1") != "0" and "--workshop" not in sys.argv:
    try:                                          # (its concepts by an anytime-valid test, installed once)
        from .parts import concepts_e as EPROC
        EPROC.install(sys.modules[__name__])
        parts.EPROC = EPROC
    except Exception as e:
        print(f"its anytime-valid concepts could not be installed: {type(e).__name__}: {e}", file=sys.stderr)
        EPROC = None

# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its memory on disk: saved beside the copy before, read back across versions."""

import os
import pickle
import shutil
import sys
import time

from . import app, config
from .cells import Gone


def erase_memory():
    """Delete its memory folder, and look again until it is really gone."""
    for _ in range(20):
        shutil.rmtree(config.STATE_DIR, ignore_errors=True)
        if not os.path.exists(config.STATE_DIR):
            return True
        time.sleep(0.25)
    return False


class Recalled(pickle.Unpickler):
    """Its memory names its own kinds of things by the file that saved them."""
    def find_class(self, module, name):
        if module in ("__main__", "novalie_app"):
            return getattr(app, name, Gone)
        return super().find_class(module, name)


def load_memory():
    """Its memory from the last time, or the copy before it if that one cannot be read."""
    for path in (config.STATE_FILE, config.STATE_FILE + ".prev"):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                return Recalled(f).load()
        except Exception as e:
            aside = f"{path}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
            n = 2
            while os.path.exists(aside):
                aside = f"{path}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}-{n}"
                n += 1
            try:
                os.replace(path, aside)
            except OSError:
                pass
            print(f"[Novalie] its memory file could not be read ({type(e).__name__}); kept as {aside}", flush=True)
    from .mind import Novalie
    return Novalie()

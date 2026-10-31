# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""The worlds folder: worlds anyone can write, each a file worlds/<name>.py with a class World(seed); the page
lists them beside the real world, and the model moves into the one chosen at once (see worlds/README.md)."""
import importlib.util
import os

from . import config

FOLDER = os.path.join(config.ROOT, "worlds")


def names():
    """The worlds in the folder, by file name."""
    try:
        return sorted(f[:-3] for f in os.listdir(FOLDER) if f.endswith(".py") and not f.startswith("_"))
    except OSError:
        return []


def module(name):
    path = os.path.join(FOLDER, name + ".py")
    spec = importlib.util.spec_from_file_location("novalie_world_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def listing():
    """Each world with its title and a line about it, for the page (the real world first)."""
    out = [{"name": "real", "title": "The real world", "about": "its computer's clock and its own body"}]
    for name in names():
        try:
            mod = module(name)
            out.append({"name": name, "title": getattr(mod, "TITLE", name), "about": getattr(mod, "ABOUT", "")})
        except Exception as e:
            out.append({"name": name, "title": name, "about": f"cannot be read: {type(e).__name__}"})
    return out


def make(name, seed=1):
    """A new world of that file: its own symbols and laws, drawn from its seed."""
    world = module(name).World(seed)
    world.from_folder, world.name = True, name
    for attr, value in (("k", 0), ("jumped", False), ("factors", []), ("dims", []), ("machine", None)):
        if not hasattr(world, attr):
            setattr(world, attr, value)
    return world

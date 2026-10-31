# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its parts: the laws of counts, its anatomy, its inventor and the machines it makes, its graphics card, its
reader of files, its grammar of numbers, its concepts, its council of brains, its workshop and its page."""
import importlib
import sys

_ALIAS = {"nm": "counts", "org": "organism", "reading": "reader", "page_server": "page", "inventor": "invent"}
OLD = {"novalie_gpu": "gpu", "novalie_mind": "counts", "novalie_organism": "organism", "novalie_prime": "prime",
       "novalie_invent": "invent", "novalie_gpu_invent": "gpu_invent", "novalie_gpu_concepts": "gpu_concepts",
       "novalie_senses": "senses", "novalie_reader": "reader", "novalie_grammar": "grammar",
       "novalie_eproc": "eproc", "novalie_typebook": "typebook", "novalie_council": "council",
       "novalie_workshop": "workshop", "novalie_page": "page", "novalie_concepts_e": "concepts_e"}
EPROC = None                                      # (its concepts by an anytime-valid test: see novalie.app)


def __getattr__(name):
    """A part, imported the first time it is asked for (its inventor's process needs only a few)."""
    try:
        mod = importlib.import_module(f"{__name__}.{_ALIAS.get(name, name)}")
    except ImportError:
        raise AttributeError(name) from None
    globals()[name] = mod
    return mod


def old_names():
    """Its parts also under the names an earlier version saved them by, so its memory reads back."""
    for old, new in OLD.items():
        sys.modules.setdefault(old, importlib.import_module(f"{__name__}.{new}"))

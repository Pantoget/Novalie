# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Starts Novalie: python -m novalie [options] (see README.md)."""
import os
import sys

if __package__ in (None, ""):                     # (started by its file's path, as its brains are)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "novalie"

from novalie.runner import main

if __name__ == "__main__":
    main()

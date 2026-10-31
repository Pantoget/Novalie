# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Settings and constants: paths, the one rule, the options set at start (read as config.NAME)."""

import os
import time


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROGRAM = os.path.join(HERE, "__main__.py")
VERSION = "1.0"
STATE_DIR = os.path.join(ROOT, "novalie_state")
STATE_FILE = os.path.join(STATE_DIR, "brain.pkl")
PORT = 8765
AGENT = {"User-Agent": "Novalie/1.0 (a reader: it only reads, and follows robots.txt)"}
EVIDENCE = 6.0


ODDS_LAGS = (0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)
ODDS_RULES = 3
ODDS_NEAR = 2
ODDS_CLOSE = 1
NERVES = 4
MADE_WAYS = ("least", "most", "sum")
MADE_HOWS = ("follows", "moves")
MADE_LOOK = 4096


GRAIN_LOOK = 64


WORD_EVIDENCE = 6
TITLE_EVIDENCE = 3
LIFT = 5
EXACT = 0.95
GLUE = 0.2
MEANING_SOURCES = 4
SAME_TOPIC = 0.4
TOPIC_WORDS = 24
TOPIC = "§topic"
TOPIC_ID = "§id"
MATCHED = True


FOLD_VERSION = 3


BORN_AT = time.time()
GAP_FLOOR = 10.0
OBEY_ROBOTS = True
PRIVATE_NETWORK = False
PAGE_BYTES = 8_000_000
PAGE_HOST = "127.0.0.1"
KEEP = 1.0
CEILING_GB = None
BORN_KINDS = ("odds", "moment", "invented", "meaning", "named", "brain_made", "general")
BRAIN = None


def room(n):
    """How many of something it keeps where it once kept n."""
    return int(n * KEEP)


INBOX = os.path.join(ROOT, "novalie_inbox")


WAYS = {"invent_at": [300, 800, 1600, "learned"], "recognize": [0.5, 1.0, 2.0],
        "explore": ["nearest", "least", "least_pressed"]}
READ_WAYS = {"sites_at_once": [6, 3, 12], "round_size": [12, 6, 24], "site_pages": [8, 4, 16], "site_dry": [2, 1, 3],
             "goal_steps": [6, 3, 12], "goal_dry": [2, 1, 3],
             "site_rest": [3600, 600, 21600]}
WAY_BOUNDS = {"invent_at": (100, 8000), "recognize": (0.2, 5.0)}
GENES = {"imagine": [True, False],
         "pairs": [True, False],
         "think": [1.0, 4.0, 0.25],
         "episodes": [True, False],
         "recall": [True, False]}
TWIN_GENES = ("recall", "episodes", "pairs")

INVENT_SECONDS = 120


JSON = "application/json"

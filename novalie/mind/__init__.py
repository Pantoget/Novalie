# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie: one mind, its faculties joined in one class (each faculty a module of this folder)."""

import collections
import threading
import time

from .journal import Journal
from .words import Words
from .perception import Perception
from .odds import OddsLaws
from .concepts import Concepts
from .foresight import Foresight
from .made import Made
from .goals import Goals
from .things import Things
from .thought import Thought
from .life import Life
from .ways import Ways
from .twins import Twins
from .acting import Acting
from .living import Living
from .understanding import Understanding
from .language import Language
from .texts import Texts
from .asking import Asking
from .views import Views
from .recognition import Recognition
from .real import RealLife
from ..body import RealWorld
from ..cells import Gone
from ..config import FOLD_VERSION, WAYS
from ..laws import PAIRS
from ..parts import grammar, reading
from ..text import fold


class Novalie(Journal, Words, Perception, OddsLaws, Concepts, Foresight, Made, Goals, Things,
              Thought, Life, Ways, Twins, Acting, Living, Understanding, Language, Texts, Asking,
              Views, Recognition, RealLife):
    """Everything it is: the world it is in, what it knows of every world it understood, how skeptical it has
    become, the words it has learned from you, and its urge to speak."""

    def __init__(self):
        self.real = True
        self.k, self.steps, self.eps = 0, 0, 0.5
        self.knowledge, self.messages, self.recent = [], [], []
        self.kinds_seen = collections.Counter()
        self.together = collections.Counter()
        self.heard = collections.defaultdict(collections.Counter)
        self.urge, self.salient, self.last_said, self.last_step_said = 0.0, collections.Counter(), [], -10 ** 9
        self.last_time_said = 0.0
        self.library = []
        self.templates, self.table_books = {}, {}
        self.link_yield = {}
        self.link_kinds = {}
        self.cell_links = collections.Counter()
        self.inventions = []
        self.grammar = grammar.Grammar()
        self.generals = {}
        self.sure_at = []
        self.ledger = {}
        self.plans = collections.Counter()
        self.ways, self.worlds_judged = {}, 0
        self.decisions = collections.deque(maxlen=40)
        self._run_began = time.time()
        self.invented_seen = collections.Counter()
        self.invented_life = {}
        self.mechs = []
        self.number_words, self.numbers_heard = {}, None
        self.related = collections.defaultdict(collections.Counter)
        self.queue, self.looked = [], set()
        self.articles = 0
        self.exposure = collections.Counter()
        self.number_articles = collections.Counter()
        self.number_sentences = collections.Counter()
        self.numbered = 0
        self.met_with = collections.defaultdict(collections.Counter)
        self.defined = {}
        self.expect, self.defined_rate = {}, {}
        self.table_met = collections.defaultdict(collections.Counter)
        self.table_expect, self.table_columns = {}, collections.Counter()
        self.matched = True
        self.source, self.counted = None, collections.defaultdict(set)
        self.read_meaning, self.read_names = {}, {}
        self.co_read = collections.Counter()
        self.tries, self.retry_at = collections.Counter(), {}
        self.web_frontier, self.web_read = {}, {}
        self.round_sites, self.sites_done = {}, {}
        self.rounds, self.asks = 0, {}
        self.turn = self.meanings_made = 0
        self.sources, self.link_source, self.link_seen = 0, None, set()
        self.word_src, self.word_new = collections.Counter(), {}
        self.seen_in, self.topic_merged = {}, 0
        self.contexts, self.topic_labels, self.topics_made = {}, {}, 0
        self.topic_sets = {}
        self.topic_main, self.topic_seen = {}, collections.Counter()
        self.public_words = set()
        self.topic_cells = collections.defaultdict(collections.Counter)
        self.circuits = {}
        self.odds_seen, self.odds_life = collections.Counter(), {}
        self.odds_laws = {}
        self.pair_src, self.pair_new = collections.Counter(), {}
        self.history_day = []
        self.links, self.links_made = {}, 0
        self.asked = collections.Counter()
        self.reader = reading.Reader()
        self.seen_kinds, self.seen_meta = collections.Counter(), {}
        self.inbox_seen, self.last_read = {}, {}
        self.history, self.given = [], []
        self.kind_life, self.read_history = {}, []
        self.script_src = collections.Counter()
        self.counted_by, self.link_units = {}, {}
        self.number_by, self.number_by_full = {}, True
        self.shown, self.folded = {}, FOLD_VERSION
        self.worlds_understood, self.pruned, self.reading_now, self.reading_log = 0, 0, "", []
        self.lock = threading.RLock()
        self.born = time.time()
        self.events, self.event_id = collections.deque(maxlen=400), 0
        self.enter()

    def __getstate__(self):
        d = dict(self.__dict__)
        d.pop("lock", None)
        d.pop("events", None)
        d.pop("wiping", None)
        d.pop("_rec", None)
        d.pop("_inventing", None)
        d.pop("_since", None)
        d.pop("_space", None)
        d.pop("parts_use", None)
        d.pop("_run_began", None)
        d.pop("_twins", None)
        d.pop("link", None)
        d["counted_by"], d["link_units"] = {}, {}
        d["source"], d["link_source"] = None, None
        d["counted"], d["link_seen"] = collections.defaultdict(set), set()
        d["given"] = []
        d["seen_in"] = {}
        d["pair_parts"] = {n: PAIRS[n] for n in d.get("pair_names") or () if n in PAIRS}
        if getattr(d.get("world"), "from_folder", False):   # (a world of the folder: met again by choosing it)
            for k in ("world", "learners", "pressed", "tried_from", "seen_now", "plan", "aim", "mechs", "past", "raw"):
                d.pop(k, None)
        elif d.get("world") is None or isinstance(d.get("world"), RealWorld):
            d["real_recall"] = self.recall_of_senses()
            for k in ("world", "learners", "pressed", "tried_from", "seen_now", "plan", "aim", "mechs", "past", "raw"):
                d.pop(k, None)
        return d

    def __setstate__(self, d):
        if "links" not in d and "met_with" in d:
            d["queue"] = list(dict.fromkeys(list(d.get("queue", [])) + sorted(d.get("looked", ()))))
        PAIRS.update(d.pop("pair_parts", None) or {})
        self.__dict__.update(d)
        self._run_began = time.time()
        self.__dict__.setdefault("library", [])
        for k, v in (("number_words", None), ("related", None), ("queue", []), ("looked", set()),
                     ("articles", 0), ("exposure", None),
                     ("worlds_understood", 0), ("pruned", 0), ("reading_now", ""), ("reading_log", [])):
            if k not in self.__dict__:
                self.__dict__[k] = ({} if k == "number_words"
                                    else collections.defaultdict(collections.Counter) if k == "related"
                                    else collections.Counter() if k == "exposure" else v)
        for k, make in (("tries", collections.Counter), ("retry_at", dict), ("source", lambda: None),
                        ("counted", lambda: collections.defaultdict(set)), ("web_frontier", dict),
                        ("web_read", dict), ("round_sites", dict), ("sites_done", dict), ("rounds", int),
                        ("asks", dict),
                        ("turn", int), ("meanings_made", int), ("numbered", int), ("last_time_said", float),
                        ("sources", int), ("link_source", lambda: None), ("link_seen", set),
                        ("word_src", collections.Counter), ("word_new", dict), ("pair_src", collections.Counter),
                        ("pair_new", dict), ("links", dict), ("links_made", int), ("asked", collections.Counter),
                        ("history_day", list), ("seen_in", dict), ("topic_merged", int),
                        ("inventions", list), ("invented_seen", collections.Counter), ("invented_life", dict),
                        ("templates", dict), ("table_books", dict), ("link_yield", dict),
                        ("expect", dict), ("defined_rate", dict), ("link_kinds", dict),
                        ("table_met", lambda: collections.defaultdict(collections.Counter)), ("table_expect", dict),
                        ("grammar", grammar.Grammar), ("generals", dict), ("sure_at", list), ("ledger", dict),
                        ("plans", collections.Counter), ("ways", dict), ("worlds_judged", int),
                        ("decisions", lambda: collections.deque(maxlen=40)),
                        ("table_columns", collections.Counter),
                        ("cell_links", collections.Counter), ("contexts", dict), ("topic_labels", dict),
                        ("topics_made", int), ("topic_sets", dict), ("topic_main", dict),
                        ("topic_seen", collections.Counter), ("public_words", set), ("read_ways", dict),
                        ("topic_cells", lambda: collections.defaultdict(collections.Counter)),
                        ("mechs", list), ("odds_seen", collections.Counter), ("odds_life", dict),
                        ("odds_laws", dict), ("law_shapes", dict),
                        ("reader", reading.Reader), ("seen_kinds", collections.Counter), ("seen_meta", dict),
                        ("inbox_seen", dict), ("last_read", dict), ("history", list),
                        ("given", list), ("kind_life", dict), ("read_history", list), ("counted_by", dict),
                        ("link_units", dict), ("number_by", dict), ("shown", dict),
                        ("number_by_full", bool)):
            if k not in self.__dict__:
                self.__dict__[k] = make()
        if "script_src" not in self.__dict__:
            self.script_src = self.estimate_scripts()
        for k in ("life", "opened", "visited", "_grace",
                  "frontier", "read_titles", "link_in", "number_titles", "numbers_wanted", "editions_read",
                  "edition_letters", "edition_cache", "commons_seen", "commons_turn", "wiki_failed", "batches",
                  "host_next"):
            self.__dict__.pop(k, None)
        if isinstance(self.__dict__.get("world"), Gone):
            for k in ("world", "learners", "pressed", "tried_from", "seen_now", "plan", "aim", "mechs", "past", "raw"):
                self.__dict__.pop(k, None)
        self.real = self.__dict__.get("world") is None or isinstance(self.world, RealWorld)
        for k in [k for k in (self.__dict__.get("ways") or {}) if k not in WAYS]:
            del self.ways[k]
        if isinstance(self.web_frontier, list):
            self.web_frontier = dict.fromkeys(self.web_frontier, 1.0)
        self.__dict__.pop("hosts", None)
        self.events, self.event_id = collections.deque(maxlen=400), 0
        if "met_with" not in self.__dict__:
            self.forget_old_word_links()
        if self.__dict__.get("folded") != FOLD_VERSION:
            self.fold_memory()
        if not self.history_day:
            for h in self.history:
                if not self.history_day or h.get("t", 0) - self.history_day[-1].get("t", 0) >= 60:
                    self.history_day.append(dict(h))
        if not self.__dict__.get("matched"):
            self.match_chances()
        self.lock = threading.RLock()
        if "numbers_heard" not in self.__dict__:
            self.number_words, self.numbers_heard = {}, None
        if self.number_words:
            self.number_words = {fold(k): v for k, v in self.number_words.items()}
        if not self.__dict__.get("names_by_meetings"):
            for w in list(self.heard):
                seen = self.heard[w]
                for s in [s for s, c in seen.items() if c < 3.0]:
                    self.exposure[w] = max(0.0, self.exposure.get(w, 0.0) - seen.pop(s))
                if not seen:
                    del self.heard[w]
            self.names_by_meetings = True
        if "world" not in self.__dict__:
            self.enter()


def _late_names():
    """The names its faculties use that exist only once the class does."""
    import sys
    from .shadow import Replay, Shadow
    for key in ("journal", "words", "perception", "odds", "concepts", "foresight", "made", "goals", "things", "thought", "life", "ways", "twins", "acting", "living", "understanding", "language", "texts", "asking", "views", "recognition", "real"):
        mod = sys.modules[__name__ + "." + key]
        mod.Novalie, mod.Shadow, mod.Replay = Novalie, Shadow, Replay


_late_names()

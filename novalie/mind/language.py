# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Language: numbers, relation words, stories and their rules."""

import collections
import fractions
import itertools
import math
import re
import unicodedata

from ..cells import seen_symbol, symbol
from ..config import EVIDENCE, SAME_TOPIC, TOPIC, TOPIC_WORDS
from ..evidence import DIGITS, evidence, kl_digits
from ..text import ASKS, ENDS, SENTENCE_END, STOPS, chars, fold, is_sign, tokens


class Language:
    # -- reading -----------------------------------------------------------------
    def number_of(self, t):
        t = t.translate(DIGITS).replace(",", "")
        return int(t) if t.isdecimal() else self.number_words.get(t)

    def concept_numbers(self):
        out = collections.defaultdict(set)
        with self.lock:
            for shape, cycles in list(self.kinds_seen):
                for n in set(cycles) | {math.prod(cycles)}:
                    if n >= 3:
                        out[n].add(symbol((shape, cycles)))
            for gid, g in self.generals.items():
                if g["kind"] == "part":
                    out[g["g"]].add(gid)
            for kind, k in list(self.seen_kinds.items()):
                if k >= 2:
                    for n in set(kind[1]) | {math.prod(kind[1])}:
                        if n >= 3:
                            out[n].add(seen_symbol(kind))
        return out

    def is_word(self, t):
        """One word: letters and their marks."""
        parts = re.split(r"['’-]", t)
        return (len(t) > 1 and all(p and all(ch.isalpha() or unicodedata.combining(ch) for ch in p) for p in parts)
                and self.number_of(t) is None)

    def topic_words(self, sentences):
        """What a text is most about."""
        counts = collections.Counter(w for words in sentences for w in words if len(w) > 2)
        top = []
        for w, _ in counts.most_common():
            if not self.is_glue(w):
                top.append(w)
                if len(top) == TOPIC_WORDS:
                    break
        return top

    def same_topic(self, words):
        """A source of the last minutes on the same topic as these words."""
        if not words or SAME_TOPIC is None:
            return None
        best, score = None, 0.0
        for book in self.counted_by.values():
            theirs = book.get(TOPIC)
            if theirs:
                share = len(words & theirs) / min(len(words), len(theirs))
                if share > score:
                    best, score = book, share
        return best if score >= SAME_TOPIC else None

    def word_forms(self):
        """The beginnings and endings it found that make forms of words."""
        cached = self.__dict__.get("_forms")
        if cached is not None and cached[0] == self.articles // 50:
            return cached[1]
        vocab = {w for w in set(self.word_src) | set(getattr(self, "word_new", {}) or {}) if len(w) > 2}
        out = {"pre": [], "suf": []}
        if len(vocab) >= 50:
            for side in ("pre", "suf"):
                for n in (1, 2, 3):
                    made, total = collections.Counter(), collections.Counter()
                    for w in vocab:
                        if len(w) >= n + 3:
                            a, rest = (w[:n], w[n:]) if side == "pre" else (w[-n:], w[:-n])
                            total[a] += 1
                            made[a] += rest in vocab
                    N, K = sum(total.values()), sum(made.values())
                    if not N or not K:
                        continue
                    p, bar = K / N, EVIDENCE + math.log10(2 * 3 * max(1, len(total)))
                    for a, m_ in total.items():
                        k = made[a]
                        p = (K - k + 1) / (N - m_ + 2)
                        if k > m_ * p and kl_digits(m_, k, p) >= bar - 3:
                            e = evidence(m_, k, p)
                            if e >= bar:
                                out[side].append((a, round(e, 1), k, m_))
                out[side].sort(key=lambda x: (-len(x[0]), -x[1]))
        self.__dict__["_forms"] = (self.articles // 50, out)
        return out

    def known_as(self, t):
        """The cells a word means."""
        mine = self.all_cells()
        cs = [c for c in (self.meanings(t) or self.meanings(fold(t))) if c in mine]
        if cs:
            return cs
        forms = self.word_forms()
        for side, a in [("pre", a) for a, *_ in forms["pre"]] + [("suf", a) for a, *_ in forms["suf"]]:
            n = len(a)
            if len(t) - n < 2 or fold(t[:n] if side == "pre" else t[-n:]) != a:
                continue
            rest = t[n:] if side == "pre" else t[:-n]
            cs = [c for c in (self.meanings(rest) or self.meanings(fold(rest))) if c in mine]
            if cs:
                return cs
        return []

    def named_in(self, toks):
        """The cells a sentence names, in order."""
        mine, out = self.all_cells(), []
        for i, t in enumerate(toks):
            cs = self.known_as(t)
            if not cs and t in mine and not t.isdigit():
                cs = [t]
            if cs:
                out.append((i, cs[0]))
        return out

    def link_between(self, a, b, index=None):
        """What its own laws say joins cell a to cell b."""
        index = index if index is not None else self.link_index()
        return sorted({k + ">" for k in index.get((a, b), ())} | {k + "<" for k in index.get((b, a), ())})

    def link_index(self):
        index = collections.defaultdict(set)
        for (code, a, b) in self.cell_links:
            index[(a, b)].add(code)
        return index

    def see_relations(self, sentences):
        """Its relation words, counted."""
        rel = self.__dict__.setdefault("rel", {"n": collections.Counter(), "k": collections.defaultdict(collections.Counter),
                                              "N": 0, "K": collections.Counter(), "seen": set()})
        index = None
        for toks in sentences:
            marks = self.named_in(toks)
            if len(marks) < 2:
                continue
            key = hash(tuple(fold(t) for t in toks))
            if key in rel["seen"]:
                continue
            if len(rel["seen"]) > 200_000:
                rel["seen"].clear()
            rel["seen"].add(key)
            index = self.link_index() if index is None else index
            for (p, a), (q, b) in zip(marks, marks[1:]):
                between = [fold(w) for w in toks[p + 1:q] if self.is_word(fold(w))]
                if a == b or not 1 <= q - p - 1 <= 4 or not between:
                    continue
                kinds = self.link_between(a, b, index) or ["none"]
                rel["N"] += 1
                for kd in kinds:
                    rel["K"][kd] += 1
                for w in set(between):
                    rel["n"][w] += 1
                    for kd in kinds:
                        rel["k"][w][kd] += 1
        if index is None:
            return
        had = self.__dict__.pop("_relation_words", None) or {}
        for w, r in self.relation_words().items():
            if had.get(w, {}).get("kind") != r["kind"]:
                self.emit("relword", word=w, shown=self.display(w), link=r["kind"], way=r["way"], digits=r["digits"])
                self.decide("relword", self.display(w), dict(r))

    def relation_words(self):
        """The words it knows for kinds of link."""
        cached = self.__dict__.get("_relation_words")
        if cached is not None:
            return cached
        rel, out = self.__dict__.get("rel"), {}
        if rel and rel["N"]:
            kinds = [k for k in rel["K"] if k != "none"]
            bar = EVIDENCE + math.log10(max(1, len(rel["n"]) * max(1, len(kinds))))
            for w, n in rel["n"].items():
                for kd in kinds:
                    k, p = rel["k"][w][kd], rel["K"][kd] / rel["N"]
                    if k > n * p and kl_digits(n, k, p) >= bar - 3:
                        e = evidence(n, k, p)
                        if e >= bar and (w not in out or e > out[w]["digits"]):
                            out[w] = {"kind": kd[:-1], "way": kd[-1], "digits": round(e, 1), "n": n, "k": k,
                                      "p": round(p, 4)}
        self.__dict__["_relation_words"] = out
        return out

    def judge_sentence(self, toks):
        """What a sentence says, by its laws."""
        words, out = self.relation_words(), []
        index = self.link_index()
        marks = self.named_in(toks)
        for (p, a), (q, b) in zip(marks, marks[1:]):
            for w in [fold(x) for x in toks[p + 1:q]]:
                r = words.get(w)
                if r is None or a == b:
                    continue
                said = (a, b) if r["way"] == ">" else (b, a)
                verdict = ("true" if r["kind"] in index.get(said, ()) else
                           "backwards" if r["kind"] in index.get((said[1], said[0]), ()) else "unknown")
                out.append({"a": a, "word": w, "b": b, "kind": r["kind"], "verdict": verdict})
        return out

    OPS = {"add": lambda x, y: x + y, "take": lambda x, y: x - y, "times": lambda x, y: x * y,
           "share": lambda x, y: x // y if y and x % y == 0 else None}

    def numbers_in(self, toks):
        """The numbers a sentence says, in order."""
        return [(i, x) for i, t in enumerate(toks) if (x := self.number_of(fold(t))) is not None]

    def see_operations(self, sentences, typed=False):
        """Its words for operations, counted."""
        ops = self.__dict__.setdefault("ops", {"n": collections.Counter(), "k": collections.defaultdict(collections.Counter),
                                              "N": 0, "K": collections.Counter(), "seen": set()})
        if typed:
            self.see_taught_operations(sentences)
        counted, words = ops["N"], self.op_words()
        heard = self.__dict__.get("numbers_heard") or {"n": collections.Counter(), "N": 0, "vals": collections.Counter(),
                                                         "k": collections.defaultdict(collections.Counter)}
        self.numbers_heard, heard_before = heard, heard["N"]
        for toks in sentences:
            nums = self.numbers_in(toks)
            if len(nums) < 2:
                continue
            key = hash(tuple(fold(t) for t in toks))
            if key in ops["seen"]:
                continue
            if len(ops["seen"]) > 200_000:
                ops["seen"].clear()
            ops["seen"].add(key)
            if not self.hear_number_words(toks, nums, words, heard) and len(nums) == 2:
                later = ops.setdefault("later", collections.deque(maxlen=4000))
                later.append(list(toks))
            for (p, x), (q, y), (r, z) in zip(nums, nums[1:], nums[2:]):
                if not (1 <= q - p - 1 <= 4 and 1 <= r - q - 1 <= 4):
                    continue
                held = [op for op, f in self.OPS.items() if f(x, y) == z] or ["none"]
                ops["N"] += 1
                for op in held:
                    ops["K"][op] += 1
                for w in {fold(t) for t in toks[p + 1:q] if self.is_word(fold(t))}:
                    ops["n"][w] += 1
                    for op in held:
                        ops["k"][w][op] += 1
        if heard["N"] != heard_before:
            self.number_words_learned()
        if ops["N"] == counted:
            return
        had = self.__dict__.pop("_op_words", None) or {}
        now = self.op_words()
        if set(now) - set(had) and ops.get("later"):
            n = heard["N"]
            ops["later"] = collections.deque((t for t in ops["later"]
                                              if not self.hear_number_words(t, self.numbers_in(t), now, heard)), maxlen=4000)
            if heard["N"] != n:
                self.number_words_learned()
        for w, r in now.items():
            if had.get(w, {}).get("op") != r["op"]:
                self.emit("opword", word=w, shown=self.display(w), op=r["op"], digits=r["digits"])
                self.decide("opword", self.display(w), dict(r))

    def see_taught_operations(self, sentences):
        """Your examples of reckoning, counted apart."""
        tops = self.__dict__.setdefault("taught_ops", {"n": collections.Counter(), "k": {}, "N": 0,
                                                       "Z": collections.Counter(), "kz": {}, "seen": set()})
        for toks in sentences:
            nums = self.numbers_in(toks)
            if len(nums) < 3:
                continue
            key = hash(tuple(fold(t) for t in toks))
            if key in tops["seen"]:
                continue
            tops["seen"].add(key)
            (p, x), (q, y), (r, z) = nums[:3]
            if not (1 <= q - p - 1 <= 4 and 1 <= r - q - 1 <= 4):
                continue
            held = [op for op, f in self.OPS.items() if f(x, y) == z]
            tops["N"] += 1
            tops["Z"][z] += 1
            for w in {fold(t) for t in toks[p + 1:q] if self.is_word(fold(t)) or is_sign(t)}:
                tops["n"][w] += 1
                for op in held:
                    tops["k"].setdefault(w, collections.Counter())[op] += 1
                    tops["kz"].setdefault(w, {}).setdefault(op, collections.Counter())[z] += 1

    UNDO = {"first": {"add": lambda a, b: b - a, "take": lambda a, b: b + a, "times": lambda a, b: b // a
                      if a and b % a == 0 else None, "share": lambda a, b: b * a},
            "second": {"add": lambda a, b: b - a, "take": lambda a, b: a - b, "times": lambda a, b: b // a
                       if a and b % a == 0 else None, "share": lambda a, b: a // b if b and a % b == 0 else None}}

    def hear_number_words(self, toks, nums, words, heard):
        """Where two numbers it reads and a word for an operation it knows stand where three numbers would."""
        if not words:
            return False
        folded, stood = [fold(t) for t in toks], False
        at = dict(nums)
        op_of = lambda a, b: next((words[w]["op"] for w in folded[a + 1:b] if w in words), None)
        near = lambda a, b: 1 <= b - a - 1 <= 4
        for u, w in enumerate(folded):
            if u in at or w in words or not self.is_word(w):
                continue
            got = set()
            for (p, x), (q, y) in zip(nums, nums[1:]):
                if not near(p, q):
                    continue
                if q < u and near(q, u) and (op := op_of(p, q)):
                    got.add(self.OPS[op](x, y))
                if u < p and near(u, p) and (op := op_of(u, p)):
                    got.add(self.UNDO["first"][op](x, y))
                if p < u < q and near(p, u) and near(u, q) and (op := op_of(p, u)):
                    got.add(self.UNDO["second"][op](x, y))
            stood |= bool(got)
            for v in got:
                if v is not None and v >= 0:
                    heard["n"][w] += 1
                    heard["k"][w][v] += 1
                    heard["vals"][v] += 1
                    heard["N"] += 1
        return stood

    def number_words_learned(self):
        """Its number words, learned."""
        heard, out = self.__dict__.get("numbers_heard"), {}
        if heard and heard["N"]:
            bar = EVIDENCE + math.log10(max(1, len(heard["n"]) * len(heard["vals"])))
            for w, n in heard["n"].items():
                v, k = heard["k"][w].most_common(1)[0]
                p = (heard["vals"][v] + 1) / (heard["N"] + 2)
                if k > n * p and kl_digits(n, k, p) >= bar - 3 and (e := evidence(n, k, p)) >= bar:
                    out[w] = {"value": v, "digits": round(e, 1), "n": n, "k": k, "p": round(p, 4), "from": "reckoning"}
        for w, r in (self.__dict__.get("counted_words_learned") or {}).items():
            if w not in out:
                out[w] = r
        had = self.__dict__.get("number_known") or {}
        self.number_known = out
        self.number_words = {w: r["value"] for w, r in out.items()}
        for w, r in out.items():
            if had.get(w, {}).get("value") != r["value"]:
                self.emit("numberword", word=w, shown=self.display(w), value=r["value"], digits=r["digits"], how=r["from"])
                self.decide("numberword", self.display(w), dict(r))
        return out

    def op_words(self):
        """The words it knows for its operations."""
        cached = self.__dict__.get("_op_words")
        if cached is not None:
            return cached
        ops, out = self.__dict__.get("ops"), {}
        if ops and ops["N"]:
            bar = EVIDENCE + math.log10(max(1, len(ops["n"]) * len(self.OPS)))
            for w, n in ops["n"].items():
                for op in self.OPS:
                    k, p = ops["k"][w][op], (ops["K"][op] + 1) / (ops["N"] + 2)
                    if k > n * p and kl_digits(n, k, p) >= bar - 3:
                        e = evidence(n, k, p)
                        if e >= bar and (w not in out or e > out[w]["digits"]):
                            out[w] = {"op": op, "digits": round(e, 1), "n": n, "k": k, "p": round(p, 4)}
        tops = self.__dict__.get("taught_ops")
        if tops and tops["N"] >= 2:
            Z, N = tops["Z"], tops["N"]
            bar = EVIDENCE + math.log10(max(1, len(tops["n"]) * len(self.OPS)))
            for w, n in tops["n"].items():
                for op, k in (tops["k"].get(w) or {}).items():
                    zs = (tops["kz"].get(w) or {}).get(op) or {}
                    if not zs:
                        continue
                    p = max((Z[z] - 1 + 0.5) / (N - 1 + 0.5 * len(Z)) for z in zs)
                    p = min(max(p, 1e-9), 1 - 1e-9)
                    if k > n * p and kl_digits(n, k, p) >= bar - 3:
                        e = evidence(n, k, p)
                        if e >= bar and (w not in out or e > out[w]["digits"]):
                            out[w] = {"op": op, "digits": round(e, 1), "n": n, "k": k, "p": round(p, 4), "from": "you"}
        self.__dict__["_op_words"] = out
        return out

    def reckon(self, toks):
        """What it reckons from what is asked."""
        words, out = self.op_words(), []
        nums = self.numbers_in(toks)
        for n, ((p, x), (q, y)) in enumerate(zip(nums, nums[1:])):
            op = next((words[fold(t)]["op"] for t in toks[p + 1:q] if fold(t) in words), None)
            if op is None:
                continue
            got = self.OPS[op](x, y)
            said = nums[n + 2][1] if n + 2 < len(nums) else None
            out.append({"x": x, "op": op, "y": y, "is": got, "said": said,
                        "word": next(fold(t) for t in toks[p + 1:q] if fold(t) in words)})
        return out

    READ_AT = tuple(range(1, 7)) + (-1, -2, -3, "end", "start")

    @staticmethod
    def story_of(text):
        """A story and a question about it, and the answer said after it."""
        m = re.search(f"^(.*?)([^{chars(ENDS | STOPS)}]*[{chars(ASKS)}])(.*)$", text.strip(), re.S)
        if not m:
            return None
        story = [tokens(x) for x in SENTENCE_END.split(m.group(1)) if tokens(x)]
        question, answer = tokens(m.group(2)), tokens(m.group(3))
        return (story, question, answer or None) if story and question else None

    @staticmethod
    def read_step(story, key, sentence, at, kinds=None, stand=(), names=(), besides=None, alls=()):
        """One step of a rule of reading."""
        holds, place, last = [], {}, None
        for i, st in enumerate(story):
            st = [fold(x) for x in st]
            if besides is not None and besides in st:
                continue
            if alls:
                left = iter(st)
                if not all(w in left for w in alls):
                    continue
            if key in st:
                holds.append(i)
                place[i] = st.index(key)
            elif last == key and any(w in st for w in stand):
                holds.append(i)
                place[i] = next(n for n, w in enumerate(st) if w in stand)
            named = [w for w in st if w in names]
            if named:
                last = named[0]
        for i in (holds if sentence == "first" else holds[::-1]):
            st = [fold(x) for x in story[i]]
            p = place[i]
            j = len(st) - 1 if at == "end" else 0 if at == "start" else p + at
            if 0 <= j < len(st) and (kinds is None or st[j] in kinds):
                return st[j], i, j
            if kinds is None:
                return None
        return None

    def form_of(self, story, question):
        """The form of a question."""
        held = ({fold(x) for st in story for x in st} | (self.__dict__.get("story_words") or set())
                | (self.__dict__.get("answer_words") or set())) - (self.__dict__.get("frame_words") or set())
        out = []
        for w in (fold(x) for x in question):
            w = "_" if w in held else w
            if not (w == "_" and out and out[-1] == "_"):
                out.append(w)
        return " ".join(out) if any(w != "_" for w in out) else fold(question[0])

    @staticmethod
    def counted_tails(story, key):
        """The word after key in each sentence about it, and the words after that word."""
        out = []
        for st in story:
            st = [fold(x) for x in st]
            if key in st and st.index(key) + 1 < len(st):
                i = st.index(key) + 1
                out.append((st[i], tuple(st[i + 1:])))
        return out

    @staticmethod
    def verb_frames(exs, verbs):
        """The frame of each word a counting rule knows."""
        tails = collections.defaultdict(list)
        for story, _, _ in exs:
            for st in story:
                st = [fold(x) for x in st]
                for i, w in enumerate(st):
                    if w in verbs:
                        tails[w].append(tuple(st[i + 1:]))
                        break
        out = {}
        for w, ts in tails.items():
            n = collections.Counter(len(t) for t in ts).most_common(1)[0][0]
            ts = [t for t in ts if len(t) == n]
            out[w] = ["_" if len(ts) > 1 and len({t[i] for t in ts}) > 1 else ts[0][i] for i in range(n)]
        return out

    @staticmethod
    def frame_effect(frames, verbs, tail, besides=None):
        """What a word does to a count by the frame of its sentence."""
        effects = {verbs[u] for u, pat in frames.items() if u != besides and u in verbs and len(pat) == len(tail)
                   and all(p == "_" or p == t for p, t in zip(pat, tail))}
        return effects.pop() if len(effects) == 1 else None

    @staticmethod
    def counted_words(story, key):
        """The words after key in each sentence about it."""
        out = []
        for st in story:
            st = [fold(x) for x in st]
            if key in st and st.index(key) + 1 < len(st):
                out.append(st[st.index(key) + 1])
        return out

    @staticmethod
    def pairings(words):
        """Every way of pairing words, each with the one that goes back on it."""
        if not words:
            yield {}
            return
        a, rest = words[0], words[1:]
        for i, b in enumerate(rest):
            for more in Novalie.pairings(rest[:i] + rest[i + 1:]):
                yield dict(more, **{a: b, b: a})

    @staticmethod
    def way_between(rule, story, question):
        """The way from the first thing the question names to the last, on the map its sentences make."""
        ways, back, things = set(rule["ways"]), rule["back"], set(rule["things"])
        steps = collections.defaultdict(list)
        for st in story:
            st = [fold(x) for x in st]
            w = [x for x in st if x in ways]
            t = [x for x in st if x in things]
            if len(w) != 1 or len(t) != 2:
                continue
            a, b = t
            here, there = (b, a) if rule["from"] == "second" else (a, b)
            steps[here].append((there, w[0]))
            steps[there].append((here, back.get(w[0], w[0])))
        q = [fold(x) for x in question if fold(x) in things]
        if len(q) < 2:
            return None
        start, goal = q[0], q[-1]
        came, frontier = {start: None}, [start]
        while frontier and goal not in came:
            nxt = []
            for x in frontier:
                for y, w in steps.get(x, ()):
                    if y not in came:
                        came[y] = (x, w)
                        nxt.append(y)
            frontier = nxt
        if goal not in came:
            return None
        out, y = [], goal
        while came[y] is not None:
            x, w = came[y]
            out.append(w)
            y = x
        return " ".join(out[::-1])

    @staticmethod
    def chain_between(rule, story, question):
        """Whether a chain of its sentences leads from the first thing the question names to the last."""
        things, steps = set(rule["things"]), collections.defaultdict(list)
        for st in story:
            t = [fold(x) for x in st if fold(x) in things]
            if len(t) == 2:
                a, b = t if rule["way"] == "first" else t[::-1]
                steps[a].append(b)
        q = [fold(x) for x in question if fold(x) in things]
        if len(q) < 2:
            return None
        seen, frontier = {q[0]}, [q[0]]
        while frontier:
            frontier = [y for x in frontier for y in steps.get(x, ()) if y not in seen and not seen.add(y)]
        return rule["yes"] if q[-1] in seen else rule["no"]

    def learn_chain(self, exs):
        """A rule of chains (see chain_between), or None."""
        answers = [fold(" ".join(a)) for _, _, a in exs]
        if len(set(answers)) != 2:
            return None
        things = set()
        for story, question, _ in exs:
            held = {fold(x) for st in story for x in st}
            things |= {fold(x) for x in question if fold(x) in held}
        common = collections.Counter(w for story, _, _ in exs for st in story for w in {fold(x) for x in st})
        n_sent = sum(len(story) for story, _, _ in exs)
        things = sorted(t for t in things if common[t] < n_sent * 0.5)
        if len(things) < 3:
            return None
        best = None
        for way in ("first", "second"):
            rule = {"mode": "chain", "way": way, "things": things, "yes": True, "no": False}
            said = {True: collections.Counter(), False: collections.Counter()}
            for (story, question, _), a in zip(exs, answers):
                got = self.chain_between(rule, story, question)
                if got is not None:
                    said[got][a] += 1
            if not said[True] or not said[False]:
                continue
            yes, no = said[True].most_common(1)[0][0], said[False].most_common(1)[0][0]
            if yes == no:
                continue
            rule = dict(rule, yes=yes, no=no)
            right = sum(self.chain_between(rule, story, question) == a for (story, question, _), a in zip(exs, answers))
            if best is None or right > best[0]:
                best = (right, rule)
        if best is None:
            return None
        right, rule = best
        digits = evidence(len(exs), right, 0.5) if right > len(exs) * 0.5 else 0.0
        if digits < EVIDENCE + math.log10(2):
            return None
        return {"rule": rule, "right": right, "of": len(exs), "chance": 0.5, "digits": round(digits, 1)}

    def learn_ways(self, exs):
        """A rule of ways (see the top of this part), or None."""
        answers = [[fold(w) for w in a] for _, _, a in exs]
        ways = sorted({w for a in answers for w in a})
        if not 2 <= len(ways) <= 8:
            return None
        things = set()
        for story, question, _ in exs:
            held = {fold(x) for st in story for x in st}
            things |= {fold(x) for x in question if fold(x) in held}
        things -= set(ways)
        common = collections.Counter(w for story, _, _ in exs for st in story for w in {fold(x) for x in st})
        n_sent = sum(len(story) for story, _, _ in exs)
        things = {t for t in things if common[t] < n_sent * 0.5}
        if len(things) < 3:
            return None
        best, tried = None, 0
        for back in self.pairings(ways) if len(ways) % 2 == 0 else [{}]:
            for side in ("second", "first"):
                tried += 1
                rule = {"mode": "ways", "ways": ways, "back": back, "from": side, "things": sorted(things)}
                right = sum(self.way_between(rule, story, question) == " ".join(a)
                            for (story, question, _), a in zip(exs, answers))
                if best is None or right > best[0]:
                    best = (right, rule)
        right, rule = best
        p = 1 / len(ways) ** 2
        digits = evidence(len(exs), right, p) if right > len(exs) * p else 0.0
        if digits < EVIDENCE + math.log10(tried):
            return None
        return {"rule": rule, "right": right, "of": len(exs), "chance": round(p, 4), "digits": round(digits, 1)}

    @staticmethod
    def times_of(story, key, at):
        """The sentences about key."""
        out = []
        for i, st in enumerate(story):
            st = [fold(x) for x in st]
            if key in st:
                p = st.index(key)
                if 0 < p and 0 <= p + at < len(st):
                    out.append((" ".join(st[:p]), st[p + at], i))
        return out

    @classmethod
    def by_rule(cls, rule, story, question):
        """What a rule of reading answers."""
        if rule.get("mode") == "chain":
            got = cls.chain_between(rule, story, question)
            return None if got is None else (got, len(story) - 1, 0)
        if rule.get("mode") == "ways":
            got = cls.way_between(rule, story, question)
            return None if got is None else (got, len(story) - 1, 0)
        words = [fold(w) for w in question]
        held = {fold(x) for st in story for x in st}
        keys = [w for w in words[1:] if w in held]
        if not keys:
            return None
        key = keys[0] if rule["key"] == "first" else keys[-1]
        if rule.get("mode") == "frame":
            for i in range(len(story) - 1, -1, -1):
                st = [fold(x) for x in story[i]]
                for p in range(len(st)):
                    if all(-len(keys) <= n < len(keys) and 0 <= p + d < len(st) and st[p + d] == keys[n]
                           for n, d in rule["frame"]):
                        return st[p], i, p
            return None
        if rule.get("mode") == "before":
            places = [w for w in keys if w != key]
            if not places:
                return None
            said = cls.times_of(story, key, rule["at"])
            order = {w: n for n, w in enumerate(rule["order"])}
            then = [order.get(t) for t, w, _ in said if w == places[-1]]
            if not then or then[0] is None:
                return None
            before = [(order[t], w, i) for t, w, i in said if t in order and order[t] < then[0]]
            if not before:
                return None
            _, got, i = max(before)
            return got, i, 0
        if rule.get("mode") == "count":
            n = 0
            for w, tail in cls.counted_tails(story, key):
                e = rule["does"].get(w)
                if e is None and rule.get("analogy") and w not in (rule.get("verbs") or {}):
                    e = cls.frame_effect(rule["frames"], rule["verbs"], tail)
                n += e or 0
            n = str(n)
            return (rule.get("words") or {}).get(n, n), len(story) - 1, 0
        stand, names = set(rule.get("stand") or ()), set(rule.get("names") or ())
        if rule.get("then"):
            first = cls.read_step(story, key, rule["sentence"], rule["at"])
            if first is None:
                return None
            if rule["then"].get("then"):
                other = cls.read_step(story, first[0], rule["then"]["sentence"], rule["then"]["at"], None, (), (), key)
                if other is None:
                    return None
                last = rule["then"]["then"]
                got = cls.read_step(story, other[0], last["sentence"], last["at"], set(rule.get("kinds") or ()), stand, names)
            else:
                got = cls.read_step(story, first[0], rule["then"]["sentence"], rule["then"]["at"],
                                    set(rule.get("kinds") or ()), stand, names)
        else:
            got = cls.read_step(story, key, rule["sentence"], rule["at"], None, stand, names, None,
                                keys if rule["sentence"] == "order" else ())
        if got is None:
            return None
        got, i, j = got
        if rule["mode"] == "same":
            same = got == words[-1]
            if set(rule.get("turn") or ()) & {fold(x) for x in story[i]}:
                same = not same
            got = rule.get("yes" if same else "no", same)
        return got, i, j

    def learn_reading(self):
        """Its rules of reading, from the examples it has."""
        examples = self.__dict__.get("qa_examples") or []
        self.answer_words = {fold(w) for _, _, a in examples for w in a}
        self.story_words = {fold(x) for story, _, _ in examples for st in story for x in st}
        named, made = collections.Counter(), collections.Counter()
        for story, question, _ in examples:
            sents = [{fold(x) for x in st} for st in story]
            for w in {fold(x) for x in question}:
                if any(w in st for st in sents):
                    named[w] += 1
                    made[w] += all(w in st for st in sents)
        self.frame_words = {w for w, n in named.items() if made[w] * 2 > n} - self.answer_words
        forms = collections.defaultdict(list)
        for ex in examples:
            forms[self.form_of(ex[0], ex[1])].append(ex)
        rules = self.__dict__.setdefault("reading_rules", {})
        for form in [f for f in rules if f not in forms]:
            del rules[form]
        kinds = [{"key": k, "sentence": s_, "at": at, "mode": md} for k in ("first", "last") for s_ in ("last", "first", "order")
                 for at in self.READ_AT for md in ("word", "same")]
        for form, exs in forms.items():
            if len(exs) < 10:
                continue
            chain = self.learn_chain(exs)
            if chain is not None and chain["right"] == len(exs):
                new = rules.get(form, {}).get("rule") != chain["rule"]
                rules[form] = chain
                if new:
                    self.emit("reading_rule", form=form, rule={"mode": "chain", "way": chain["rule"]["way"]},
                              right=chain["right"], of=chain["of"], digits=chain["digits"])
                    self.decide("reading_rule", form, dict(chain))
                continue
            ways = self.learn_ways(exs)
            if ways is not None and ways["right"] == len(exs):
                new = rules.get(form, {}).get("rule") != ways["rule"]
                rules[form] = ways
                if new:
                    self.emit("reading_rule", form=form, rule={"mode": "ways", "back": ways["rule"]["back"]},
                              right=ways["right"], of=ways["of"], digits=ways["digits"])
                    self.decide("reading_rule", form, dict(ways))
                continue
            timed = self.learn_order(exs)
            if timed is not None:
                new = rules.get(form, {}).get("rule") != timed["rule"]
                rules[form] = timed
                if new:
                    self.emit("reading_rule", form=form, rule=timed["rule"], right=timed["right"], of=timed["of"],
                              digits=timed["digits"])
                    self.decide("reading_rule", form, dict(timed))
                continue
            numbers = [self.number_of(fold(" ".join(a))) for _, _, a in exs]
            counting = (self.learn_count(exs, numbers) if all(x is not None for x in numbers)
                        else self.learn_count_words(exs))
            if counting is not None:
                rule = counting
                if rule is not None:
                    new = rules.get(form, {}).get("rule") != rule["rule"]
                    rules[form] = rule
                    if new:
                        self.emit("reading_rule", form=form, rule=rule["rule"], right=rule["right"], of=rule["of"],
                                  digits=rule["digits"])
                        self.decide("reading_rule", form, dict(rule))
                continue
            best, sames = None, []
            for rule in kinds:
                if rule["mode"] == "same":
                    said = {True: collections.Counter(), False: collections.Counter()}
                    for story, question, answer in exs:
                        got = self.by_rule(rule, story, question)
                        if got is not None:
                            said[got[0]][fold(" ".join(answer))] += 1
                    if sum(map(sum, (c.values() for c in said.values()))) == len(exs):
                        sames.append(rule)
                    if not said[True] or not said[False]:
                        continue
                    yes, no = said[True].most_common(1)[0][0], said[False].most_common(1)[0][0]
                    if yes == no:
                        continue
                    rule = dict(rule, yes=yes, no=no)
                right, chance, reads = 0, 0.0, 0
                for story, question, answer in exs:
                    got = self.by_rule(rule, story, question)
                    right += got is not None and got[0] == fold(" ".join(answer))
                    reads += got is not None
                    chance += 0.5 if rule["mode"] == "same" else 1 / max(2, len({fold(w) for st in story for w in st}))
                p = chance / len(exs)
                rank = (right, -kinds.index({k: v for k, v in rule.items() if k not in ("yes", "no")}))
                if best is None or rank > best[0]:
                    best = (rank, rule, right, p)
            _, rule, right, p = best
            tried = len(kinds)
            if right < len(exs) and all(len(a) == 1 for _, _, a in exs):
                framed = self.learn_frame(exs, right)
                if framed is not None:
                    tried += framed[2]
                    if framed[1] > right:
                        rule, right = framed[0], framed[1]
            if right < len(exs) and len({fold(" ".join(a)) for _, _, a in exs}) == 2:
                def judged(r):
                    said = {True: collections.Counter(), False: collections.Counter()}
                    for story, question, answer in exs:
                        said[self.by_rule(r, story, question)[0]][fold(" ".join(answer))] += 1
                    if not said[True] or not said[False]:
                        return 0, r
                    yes, no = said[True].most_common(1)[0][0], said[False].most_common(1)[0][0]
                    if yes == no:
                        return 0, r
                    r = dict(r, yes=yes, no=no)
                    return sum(1 for story, question, answer in exs
                               if self.by_rule(r, story, question)[0] == fold(" ".join(answer))), r
                for base in sames:
                    read = collections.Counter()
                    for story, question, _ in exs:
                        read.update({fold(x) for x in story[self.by_rule(base, story, question)[1]]})
                    cands = sorted(w for w, c in read.items() if c >= 3)
                    r0, now, turn = *judged(base), []
                    while cands:
                        tried += len(cands)
                        scored = []
                        for c in cands:
                            r2, got = judged(dict(base, turn=sorted(turn + [c])))
                            scored.append((r2, c, got))
                        r2, c, got = max(scored, key=lambda x: (x[0], x[1]))
                        if r2 <= r0:
                            break
                        r0, now, turn = r2, got, sorted(turn + [c])
                        cands = [x for x in cands if x != c]
                    if r0 > right:
                        rule, right = now, r0
            if right < len(exs):
                answers = {fold(" ".join(a)) for _, _, a in exs}
                steps = [{"sentence": s_, "at": at} for s_ in ("last", "first") for at in self.READ_AT]
                tried += len(kinds) // 2 * len(steps)
                said = [fold(" ".join(a)) for _, _, a in exs]
                keyed = []
                for story, question, _ in exs:
                    held = {fold(x) for st in story for x in st}
                    keyed.append((story, [w for w in [fold(x) for x in question][1:] if w in held]))
                firsts = [k for k in kinds if k["mode"] == "word"]
                reads = [[self.read_step(story, ks[0] if f["key"] == "first" else ks[-1], f["sentence"], f["at"])
                          if ks else None for story, ks in keyed] for f in firsts]
                within = set(sorted(answers))
                for first, firsts_read in zip(firsts, reads):
                    for then in steps:
                        right2 = 0
                        for (story, _), g1, a in zip(keyed, firsts_read, said):
                            if g1 is not None:
                                g = self.read_step(story, g1[0], then["sentence"], then["at"], within, set(), set())
                                right2 += g is not None and g[0] == a
                        if right2 > right:
                            rule, right = dict(first, then=then, kinds=sorted(answers)), right2
                if right < len(exs):
                    middle = [{"sentence": s_, "at": at} for s_ in ("last", "first") for at in self.READ_AT]
                    tried += len(kinds) // 2 * len(middle) * len(steps)
                    for first, firsts_read in zip(firsts, reads):
                        for mid in middle:
                            others = [None if g1 is None else
                                      self.read_step(story, g1[0], mid["sentence"], mid["at"], None, (), (),
                                                     ks[0] if first["key"] == "first" else ks[-1])
                                      for (story, ks), g1 in zip(keyed, firsts_read)]
                            if not any(o is not None and self.read_step(story, o[0], t3["sentence"], t3["at"], within,
                                                                        set(), set()) is not None
                                       for (story, _), o in list(zip(keyed, others))[:5] for t3 in steps):
                                continue
                            for t3 in steps:
                                right3 = 0
                                for (story, _), o, a in zip(keyed, others, said):
                                    if o is not None:
                                        g = self.read_step(story, o[0], t3["sentence"], t3["at"], within, set(), set())
                                        right3 += g is not None and g[0] == a
                                if right3 > right:
                                    rule, right = dict(first, then=dict(mid, then=t3), kinds=sorted(answers)), right3
            if right < len(exs) and rule["mode"] != "count":
                names = set()
                for story, question, _ in exs:
                    words = [fold(w) for w in question]
                    keys = [w for w in words[1:] if w in {fold(x) for st in story for x in st}]
                    if keys:
                        names.add(keys[0] if rule["key"] == "first" else keys[-1])
                answers = {fold(" ".join(a)) for _, _, a in exs}
                unnamed = collections.Counter(w for story, _, _ in exs for st in story
                                              if not any(fold(x) in names for x in st)
                                              for w in {fold(x) for x in st} if w not in names and w not in answers)
                candidates = sorted(w for w, c in unnamed.items() if c >= 3)
                tried += len(candidates)
                stand = []
                for c in candidates:
                    rule2 = dict(rule, stand=sorted(stand + [c]), names=sorted(names))
                    right2 = sum(1 for story, question, answer in exs
                                 if (g := self.by_rule(rule2, story, question)) is not None and g[0] == fold(" ".join(answer)))
                    if right2 > right:
                        rule, right, stand = rule2, right2, stand + [c]
            if ways is not None and ways["right"] >= right:
                new = rules.get(form, {}).get("rule") != ways["rule"]
                rules[form] = ways
                if new:
                    self.emit("reading_rule", form=form, rule={"mode": "ways", "back": ways["rule"]["back"]},
                              right=ways["right"], of=ways["of"], digits=ways["digits"])
                    self.decide("reading_rule", form, dict(ways))
                continue
            digits = evidence(len(exs), right, p) if right > len(exs) * p else 0.0
            if digits >= EVIDENCE + math.log10(tried):
                new = rules.get(form, {}).get("rule") != rule
                rules[form] = {"rule": rule, "right": right, "of": len(exs), "chance": round(p, 4), "digits": round(digits, 1)}
                if new:
                    self.emit("reading_rule", form=form, rule=rule, right=right, of=len(exs), digits=round(digits, 1))
                    self.decide("reading_rule", form, dict(rules[form]))
        self.frames_judged(rules)
        return rules

    def frames_judged(self, rules):
        """Whether the frames of its sentences tell what a word does to a count."""
        counting = [r["rule"] for r in rules.values() if r["rule"].get("mode") == "count" and r["rule"].get("frames")]
        n = k = 0
        for rule in counting:
            for v, e in rule["verbs"].items():
                if v in rule["frames"]:
                    got = self.frame_effect(rule["frames"], rule["verbs"], tuple(rule["frames"][v]), besides=v)
                    if got is not None:
                        n += 1
                        k += got == e
        digits = evidence(n, k, 1 / 3) if k > n / 3 else 0.0
        believed = digits >= EVIDENCE + math.log10(2)
        had = (self.__dict__.get("frame_analogy") or {}).get("believed")
        self.frame_analogy = {"n": n, "k": k, "digits": round(digits, 1), "believed": believed}
        for rule in counting:
            rule["analogy"] = believed
        if believed and not had:
            self.emit("frames", n=n, got=k, digits=round(digits, 1))
            self.decide("frames", "count", dict(self.frame_analogy))

    def learn_frame(self, exs, bar=1):
        """A rule of a frame (see by_rule), or None."""
        held = collections.Counter()
        for story, question, answer in exs:
            a = fold(" ".join(answer))
            keys = [w for w in (fold(x) for x in question[1:]) if w in {fold(x) for st in story for x in st}]
            seen = set()
            for st in story:
                st = [fold(x) for x in st]
                for p in (p for p, w in enumerate(st) if w == a):
                    for q, x in enumerate(st):
                        if q != p and x in keys:
                            n = keys.index(x)
                            seen |= {(n, q - p), (n - len(keys), q - p)}
            held.update(seen)
        cands = sorted(c for c, k in held.items() if k > max(1, bar))
        frame, right, tried = [], 0, 0
        while cands:
            tried += len(cands)
            scored = []
            for c in cands:
                rule = {"key": "first", "mode": "frame", "frame": sorted(frame + [c])}
                r = sum(1 for story, question, answer in exs
                        if (g := self.by_rule(rule, story, question)) is not None and g[0] == fold(" ".join(answer)))
                scored.append((r, held[c], c))
            r, _, c = max(scored)
            if r <= right:
                break
            frame, right = sorted(frame + [c]), r
            cands = [x for x in cands if x != c and held[x] > right]
        for c in sorted((c for c, k in held.items() if frame and k == len(exs) and c not in frame),
                        key=lambda c: (-held[c], c)):
            rule = {"key": "first", "mode": "frame", "frame": sorted(frame + [c])}
            tried += 1
            if sum(1 for story, question, answer in exs
                   if (g := self.by_rule(rule, story, question)) is not None and g[0] == fold(" ".join(answer))) >= right:
                frame = sorted(frame + [c])
        if not frame:
            return None
        return {"key": "first", "mode": "frame", "frame": [list(x) for x in frame]}, right, tried

    def learn_order(self, exs):
        """A rule of time (see the top of this part), or None."""
        best = None
        for key in ("first", "last"):
            for at in (1, 2, 3, 4, 5, 6):
                phrases, usable = set(), 0
                for story, question, _ in exs:
                    words = [fold(w) for w in question]
                    keys = [w for w in words[1:] if w in {fold(x) for st in story for x in st}]
                    if len(keys) < 2:
                        continue
                    k = keys[0] if key == "first" else keys[-1]
                    said = self.times_of(story, k, at)
                    if len(said) >= 2:
                        usable += 1
                        phrases |= {t for t, _, _ in said}
                if usable < len(exs) * 0.9 or not 2 <= len(phrases) <= 6:
                    continue
                for order in itertools.permutations(sorted(phrases)):
                    rule = {"key": key, "mode": "before", "at": at, "order": list(order)}
                    right = sum(1 for story, question, answer in exs
                                if (g := self.by_rule(rule, story, question)) is not None and g[0] == fold(" ".join(answer)))
                    if best is None or right > best[0]:
                        best = (right, rule, math.factorial(len(phrases)))
        if best is None:
            return None
        right, rule, orders = best
        p = 1 / max(2, len({fold(" ".join(a)) for _, _, a in exs}))
        digits = evidence(len(exs), right, p) if right > len(exs) * p else 0.0
        if digits < EVIDENCE + math.log10(orders * 12):
            return None
        return {"rule": rule, "right": right, "of": len(exs), "chance": round(p, 4), "digits": round(digits, 1)}

    def learn_count(self, exs, numbers):
        """A rule of counting (see the top of this part)."""
        best = None
        for key in ("first", "last"):
            said = []
            for story, question, _ in exs:
                words = [fold(w) for w in question]
                keys = [w for w in words[1:] if w in {fold(x) for st in story for x in st}]
                said.append(self.counted_words(story, (keys[0] if key == "first" else keys[-1])) if keys else None)
            vocab = sorted({w for ws in said if ws for w in ws})
            does = self.solve_counts(vocab, said, numbers)
            right = lambda: sum(ws is not None and sum(does.get(w, 0) for w in ws) == x for ws, x in zip(said, numbers))
            off = lambda: sum(abs(sum(does.get(w, 0) for w in ws) - x) for ws, x in zip(said, numbers) if ws is not None)
            far = off()
            for _ in range(6):
                changed = False
                for w in vocab:
                    for e in (1, -1, 0):
                        old = does.get(w, 0)
                        does[w] = e
                        got = off()
                        if got < far:
                            far, changed = got, True
                        else:
                            does[w] = old
                if not changed:
                    break
            score = right()
            if best is None or score > best[0]:
                best = (score, key, {w: e for w, e in does.items() if e}, len(vocab), list(vocab))
        score, key, does, k, vocab = best
        p = 1 / max(2, len(set(numbers)))
        digits = evidence(len(exs), score, p) if score > len(exs) * p else 0.0
        if digits < EVIDENCE + k * math.log10(3) + math.log10(2):
            return None
        words = {str(x): fold(" ".join(a)) for (_, _, a), x in zip(exs, numbers)
                 if not fold(" ".join(a)).translate(DIGITS).isdecimal()}
        verbs = {w: does.get(w, 0) for w in vocab}
        return {"rule": {"key": key, "mode": "count", "does": does, "words": words, "verbs": verbs,
                         "frames": self.verb_frames(exs, verbs)}, "right": score, "of": len(exs),
                "chance": round(p, 4), "digits": round(digits, 1)}

    @staticmethod
    def null_space(rows, k):
        """The vectors of k numbers every row is orthogonal to."""
        M = [[fractions.Fraction(x) for x in r] for r in rows if any(r)]
        pivots, r = [], 0
        for c in range(k):
            piv = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
            if piv is None:
                continue
            M[r], M[piv] = M[piv], M[r]
            M[r] = [x / M[r][c] for x in M[r]]
            for i in range(len(M)):
                if i != r and M[i][c] != 0:
                    f = M[i][c]
                    M[i] = [a - f * b for a, b in zip(M[i], M[r])]
            pivots.append(c)
            r += 1
            if r == len(M):
                break
        basis = []
        for fc in (c for c in range(k) if c not in pivots):
            v = [fractions.Fraction(0)] * k
            v[fc] = fractions.Fraction(1)
            for i, pc in enumerate(pivots):
                v[pc] = -M[i][fc]
            basis.append(v)
        return basis

    def learn_count_words(self, exs):
        """A rule of counting when its answers are words it does not know."""
        answers = [fold(" ".join(a)) for _, _, a in exs]
        if any(len(a) != 1 for _, _, a in exs) or not 2 <= len(set(answers)) <= len(exs) // 3:
            return None
        best = None
        for key in ("first", "last"):
            said = []
            for story, question, _ in exs:
                words = [fold(w) for w in question]
                keys = [w for w in words[1:] if w in {fold(x) for st in story for x in st}]
                said.append(self.counted_words(story, (keys[0] if key == "first" else keys[-1])) if keys else None)
            vocab = sorted({w for ws in said if ws for w in ws})
            vec = [None if ws is None else [ws.count(v) for v in vocab] for ws in said]
            groups = collections.defaultdict(list)
            for i, a in enumerate(answers):
                if vec[i] is not None:
                    groups[a].append(i)
            rows = [[x - y for x, y in zip(vec[i], vec[g[0]])] for g in groups.values() for i in g[1:]]
            placed = [j for j in range(len(vocab)) if any(r[j] for r in rows)]
            vocab = [vocab[j] for j in placed]
            vec = [None if c is None else [c[j] for j in placed] for c in vec]
            rows = [[r[j] for j in placed] for r in rows]
            if not vocab:
                continue
            basis = self.null_space(rows, len(vocab))
            if len(basis) != 1:
                continue
            unit = min(abs(x) for x in basis[0] if x)
            d = [x / unit for x in basis[0]]
            if any(x.denominator != 1 or abs(x) > 1 for x in d):
                continue
            for sign in (1, -1):
                does = {v: int(sign * x) for v, x in zip(vocab, d) if x}
                counts = [None if c is None else sum(does.get(v, 0) * n for v, n in zip(vocab, c)) for c in vec]
                if any(c is not None and c < 0 for c in counts):
                    continue
                value = {a: collections.Counter(counts[i] for i in g).most_common(1)[0][0] for a, g in groups.items()}
                if len(set(value.values())) != len(value):
                    continue
                right = sum(1 for i, a in enumerate(answers) if counts[i] is not None and counts[i] == value[a])
                if best is None or right > best[0]:
                    best = (right, key, does, value, len(vocab), list(vocab))
        if best is None:
            return None
        right, key, does, value, k, vocab = best
        p = 1 / len(set(answers))
        digits = evidence(len(exs), right, p) if right > len(exs) * p else 0.0
        if digits < EVIDENCE + k * math.log10(3) + math.log10(2):
            return None
        learned = self.__dict__.setdefault("counted_words_learned", {})
        for a, v in value.items():
            learned[a] = {"value": v, "digits": round(digits, 1), "n": sum(1 for x in answers if x == a), "from": "counting"}
        self.number_words_learned()
        verbs = {w: does.get(w, 0) for w in vocab}
        return {"rule": {"key": key, "mode": "count", "does": does, "words": {str(v): a for a, v in value.items()},
                         "verbs": verbs, "frames": self.verb_frames(exs, verbs)},
                "right": right, "of": len(exs), "chance": round(p, 4), "digits": round(digits, 1)}

    @staticmethod
    def solve_counts(vocab, said, numbers):
        """What each word does to a count, all at once."""
        k = len(vocab)
        if not k:
            return {}
        at = {w: i for i, w in enumerate(vocab)}
        A = [[0.0] * k for _ in range(k)]
        b = [0.0] * k
        for ws, x in zip(said, numbers):
            if ws is None:
                continue
            row = [0.0] * k
            for w in ws:
                row[at[w]] += 1
            for i in range(k):
                if row[i]:
                    b[i] += row[i] * x
                    for j in range(k):
                        A[i][j] += row[i] * row[j]
        for i in range(k):
            A[i][i] += 1e-6
        M = [A[i] + [b[i]] for i in range(k)]
        for c in range(k):
            p = max(range(c, k), key=lambda r: abs(M[r][c]))
            M[c], M[p] = M[p], M[c]
            if abs(M[c][c]) < 1e-12:
                continue
            for r in range(k):
                if r != c:
                    f = M[r][c] / M[c][c]
                    M[r] = [x - f * y for x, y in zip(M[r], M[c])]
        e = [M[i][k] / M[i][i] if abs(M[i][i]) > 1e-12 else 0.0 for i in range(k)]
        return {w: max(-1, min(1, round(v))) for w, v in zip(vocab, e) if round(v)}

    def example_from(self, text):
        """A story, a question and its answer you gave it."""
        got = self.story_of(text)
        if not got or not got[2]:
            return False
        ex = self.__dict__.setdefault("qa_examples", [])
        ex.append(got)
        del ex[:-2000]
        n = len(ex)
        if n >= 10 and n & (n - 1) == 0 or n % 500 == 0:
            self.learn_reading()
        return True

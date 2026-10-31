# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its words: what it says and hears, and the names it learns."""

import collections
import math
import time

from ..body import RealWorld
from ..config import BORN_KINDS, EVIDENCE, room
from ..evidence import evidence
from ..parts import council
from ..text import ASKS, EDGES, SENTENCE_END, fold, is_sign, script_of, tokens, typed_tokens
from ..web import URL_IN, links_in


class Words:
    def emit(self, kind, **data):
        """What it is doing right now, for the page to show as it happens."""
        if "world" in data and isinstance(getattr(self, "world", None), RealWorld):
            data.setdefault("real", True)
        with self.lock:
            self.event_id += 1
            self.events.append(dict(data, id=self.event_id, k=kind, t=round(time.time(), 2)))
            if kind in BORN_KINDS and not data.get("council"):
                this = self.__dict__.get("this_start")
                if this is not None and isinstance(self.__dict__.get("world"), RealWorld):
                    this["born"][kind] = this["born"].get(kind, 0) + 1
        if kind in council.TEACH and not data.get("taught") and not data.get("council"):
            self.proofs = self.__dict__.get("proofs", 0) + 1
            self.__dict__.setdefault("first_proof", time.time())
            link = self.__dict__.get("link")
            if link is not None:
                link.tell(kind, **data)

    # -- its words -------------------------------------------------------------
    def say(self, text, who="model", **extra):
        with self.lock:
            self.messages.append(dict(extra, id=len(self.messages), who=who, text=text, t=time.time()))
            if len(self.messages) > room(20000):
                del self.messages[:room(5000)]
                for i, msg in enumerate(self.messages):
                    msg["id"] = i

    def word_for(self, s):
        """Its word for a symbol."""
        best, score = None, 0.0
        for w, seen in self.heard.items():
            c = seen.get(s, 0.0)
            if c >= 0.5:
                spec = c / max(self.exposure.get(w, 0.0), sum(seen.values()))
                if spec >= 0.5 and c * spec > score:
                    best, score = w, c * spec
        return best or self.read_names.get(s)

    def taught(self, w):
        seen = self.heard.get(w)
        if not seen:
            return []
        total = max(self.exposure.get(w, 0.0), sum(seen.values()))
        return [s for s, c in seen.most_common(2) if c >= 0.5 and c / total >= 0.5]

    def links_of(self, w):
        """Its concepts for a word, and how strong each link is."""
        out = {s: self.heard[w][s] for s in self.taught(w)}
        for s, e in self.read_meaning.get(fold(w), ()):
            out.setdefault(s, e)
        return list(out.items())[:2]

    def meanings(self, w):
        return [s for s, _ in self.links_of(w)]

    def named_words(self):
        """Every word that means one of its concepts."""
        taught = [w for w in self.heard if self.taught(w)]
        have = {fold(w) for w in taught}
        return list(dict.fromkeys(taught + [w for w in self.read_meaning if w not in have]))

    def speak(self):
        with self.lock:
            symbols = [s for s, _ in self.salient.most_common(4)]
            if not symbols or set(symbols) == set(self.last_said):
                self.urge *= 0.5
                return
            parts = []
            for s in symbols:
                w = self.word_for(s)
                f = self.grammar.form(script_of(w), fold(w), int(s)) if w and s.isdigit() else None
                parts.append(f"{s} {self.display(f)}" if f else self.display(w) if w else s)
            text = " ".join(dict.fromkeys(parts))
            for s in symbols:
                self.asked[s] += 1
            self.say(text)
            self.emit("spoke", text=text, symbols=symbols)
            self.last_said, self.last_step_said, self.last_time_said = symbols, self.steps, time.time()
            self.urge = 0.0
            self.salient.clear()

    def name(self, s, word):
        """You point at one of its symbols and give it a word."""
        word = word.strip()
        if not word or not s:
            return
        with self.lock:
            self.heard[word][s] += 3.0
            self.exposure[word] += 3.0
            self.salient[s] += 2.0
            self.urge += 1.0

    def name_by_meetings(self, words, symbols):
        """Your words right after it spoke about symbols."""
        ms = self.__dict__.setdefault("meetings", {"replies": 0, "said": collections.Counter(),
                                                   "word": collections.Counter(), "after": {}})
        ms["replies"] += 1
        words = list(dict.fromkeys(w for w in words if w and self.number_of(fold(w)) is None))
        for s in symbols:
            ms["said"][s] += 1
        for w in words:
            ms["word"][w] += 1
            for s in symbols:
                ms["after"].setdefault(w, collections.Counter())[s] += 1
        bar = EVIDENCE + math.log10(max(1, len(ms["word"]) * len(ms["said"])))
        for w in words:
            if self.taught(w):
                continue
            for s in symbols:
                n, k = ms["said"][s], ms["after"][w][s]
                p = min(max((ms["word"][w] - k + 0.5) / (ms["replies"] - n + 1), 1e-6), 1 - 1e-6)
                if k > n * p and evidence(n, k, p) >= bar:
                    self.heard[w][s] += 3.0
                    self.exposure[w] += 3.0
                    self.emit("named", s=s, word=w, digits=round(evidence(n, k, p), 1), n=n, k=k)
                    self.decide("named", s, {"word": w, "n": n, "k": k, "digits": round(evidence(n, k, p), 1)})
                    break

    def unname(self, s, word):
        """A name you gave by mistake."""
        with self.lock:
            if word not in self.heard:
                word = next((w for w, seen in self.heard.items() if s in seen and fold(w) == fold(word)), word)
            seen = self.heard.get(word)
            if seen and s in seen:
                gone = seen.pop(s)
                self.exposure[word] = max(0.0, self.exposure.get(word, 0.0) - gone)
                if not seen:
                    del self.heard[word]
                    if self.exposure[word] <= 0:
                        del self.exposure[word]
                self.emit("unnamed", s=s, word=word)
                return True
        return False

    def forget_meaning(self, word, s):
        """A meaning its reading proved that you judge a coincidence."""
        w = fold(word)
        with self.lock:
            if not any(c == s for c, _ in self.read_meaning.get(w, ())):
                return False
            met = self.met_with.get(w)
            if met and s in met:
                del met[s]
                self.expect.get(w, {}).pop(s, None)
            met = self.table_met.get(w)
            if met and s in met:
                del met[s]
                self.table_expect.get(w, {}).pop(s, None)
            m, hits = self.defined.get(w, (0, {}))
            if s in hits:
                self.defined[w] = (m, {c: k for c, k in hits.items() if c != s})
                self.defined_rate.get(w, {}).pop(s, None)
            self.weigh([w])
            self.emit("forgot", word=w, shown=self.display(w), s=s)
            return True

    def hear(self, text):
        """What you say to it: heard."""
        t0 = time.perf_counter()
        try:
            return self._hear(text)
        finally:
            self.metered("talk", t0)

    def _hear(self, text):
        for u in links_in(text, hosts=True):
            self.point_to(u.rstrip(EDGES.replace("/", "")))
        text = URL_IN.sub(" ", text)
        with self.lock:
            if self.example_from(text):
                return
            self.see_relations([tokens(x) for x in SENTENCE_END.split(text)])
            self.see_operations([typed_tokens(x) for x in SENTENCE_END.split(text)], typed=True)
        words = [w.strip(EDGES) for w in text.split()]
        words = [w for w in words if w]
        if not words:
            return
        typed = typed_tokens(text)
        example = len(self.numbers_in(typed)) >= 2 and any(is_sign(t) for t in typed)
        with self.lock:
            for w in words:
                self.exposure[w] += 1.0
            for w in words:
                if (len(self.queue) < 8 and w not in self.looked and fold(w) not in self.looked and not self.meanings(w)
                        and self.number_of(w) is None and len(w) > 1 and any(ch.isalpha() for ch in w)):
                    self.looked.add(w)
                    self.queue.append(w)
            asking = any(ch in ASKS for ch in text)
            if self.last_said and not asking and not example:
                said, rest = list(self.last_said), []
                for w in words:
                    m = [s for s in self.meanings(w) if s in said]
                    if m:
                        self.heard[w][m[0]] += 1.0
                        said.remove(m[0])
                    else:
                        rest.append(w)
                unnamed = [s for s in said if not self.word_for(s)] or said
                self.name_by_meetings(rest, unnamed)
                self.last_said = []
            elif example:
                self.last_said = []
            known = list(dict.fromkeys(s for w in words for s in self.meanings(w)))
            for s in known:
                self.salient[s] += 2.0
                near = sorted(((n, b if a == s else a) for (a, b), n in self.together.items() if s in (a, b)),
                              reverse=True)[:2]
                for n, other in near:
                    self.salient[other] += 0.5
                self.urge += 1.0
            if not known:
                self.urge += 0.5
                for s in self.recent:
                    if not self.word_for(s):
                        self.salient[s] += 0.5
            self.emit("heard", words=words[:12], symbols=known)
        if any(ch in ASKS for ch in text):
            self.think(text)

# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Reading text: words, meanings, chance and links."""

import collections
import copy
import itertools
import math
import threading
import time

from ..cells import symbol
from ..config import (FOLD_VERSION, GLUE, LIFT, MATCHED, MEANING_SOURCES, SAME_TOPIC, TITLE_EVIDENCE, TOPIC,
    TOPIC_ID, WORD_EVIDENCE, room)
from ..evidence import evidence
from ..text import EDGES, SENTENCE_END, fold, main_script, script_of, tokens


class Texts:
    def read(self, about, text, source=None, title=None):
        """A text read (see _read), and what reading it cost kept with its other parts' (self_view)."""
        t0 = time.perf_counter()
        try:
            return self._read(about, text, source, title)
        finally:
            self.metered("reading", t0)

    def _read(self, about, text, source=None, title=None):
        """It reads with its own numbers."""
        known, hits, shared, n = self.concept_numbers(), collections.Counter(), collections.defaultdict(set), 0
        private = isinstance(source, tuple) and source[:1] == ("any",) and str(source[1:2][0] if source[1:] else "").startswith(("inbox", "you"))
        pairs, sentences, after, said = set(), [], [], []
        label = str(title or about or (source[1] if isinstance(source, tuple) and len(source) > 1 else "") or "")[:80]
        if about:
            about = fold(about)
        for sentence in SENTENCE_END.split(text):
            toks = tokens(sentence)
            said.append(toks)
            words = []
            for t in toks:
                k = fold(t)
                if self.is_word(k):
                    self.note_form(t)
                    words.append(k)
            if words:
                sentences.append(words)
                if not private:
                    self.public_words.update(words)
            folded = [fold(t) for t in toks]
            for i in range(len(folded) - 1):
                x = self.number_of(folded[i])
                if x is not None and self.is_word(folded[i + 1]):
                    after.append((script_of(folded[i + 1]), x, folded[i + 1]))
            found = {c for t in toks if (x := self.number_of(fold(t))) is not None for c in known.get(x, ())}
            if not found:
                continue
            n += 1
            for c in found:
                hits[c] += 1
                shared[c] |= set(words)
            pairs.update(itertools.combinations(sorted(found), 2))
        with self.lock:
            self.articles += 1
            self.see_relations(said)
            self.see_operations(said)
            self.grammar.see(after, source or label)
            self.learn_links(sentences, source)
            if self.articles % 200 == 0:
                self.tidy_reading()
                threading.Thread(target=self.look_at_grammar, daemon=True, name="grammar").start()
            main0 = self.topic_words(sentences)
            if main0:
                t0 = self.topic_of(set(main0), main0)
                self.topic_seen[t0] += 1
                for c in hits:
                    self.topic_cells[t0][c] += 1
            if not n:
                return hits
            self.numbered += n
            for c, k in hits.items():
                self.number_articles[c] += 1
                self.number_sentences[c] += k
            sc = main_script(sentences)
            if sc:
                book = self.number_by.setdefault(sc, collections.Counter())
                for c in hits:
                    book[c] += 1
            for pair in pairs:
                self.co_read[pair] += 1
            main = self.topic_words(sentences)
            topic = set(main)
            if source != self.source:
                book = self.counted_by.pop(source, None)
                if book is None:
                    book = self.same_topic(topic)
                    if book is not None:
                        self.topic_merged += 1
                    else:
                        book = collections.defaultdict(set)
                        book[TOPIC_ID] = {self.topic_of(topic, main)}
                self.counted_by[source] = book
                while len(self.counted_by) > 2 * len(self.round_sites) + 16:
                    del self.counted_by[next(iter(self.counted_by))]
                self.source, self.counted = source, book
            if topic:
                theirs = self.counted.get(TOPIC)
                if theirs is None:
                    self.counted[TOPIC] = set(topic)
                elif len(theirs) < 96:
                    theirs |= topic
            fresh, trials = set(), collections.Counter()
            tid = next(iter(self.counted.get(TOPIC_ID) or {0}))
            for c, ws in shared.items():
                for w in ws:
                    if c not in self.counted[w]:
                        self.counted[w].add(c)
                        self.met_with[w][c] += 1
                        fresh.add(w)
                        trials[w] += 1
                        if tid and self.met_with[w][c] >= 2:
                            had = self.contexts.pop((w, c), ())
                            if tid not in had:
                                had = (had + (tid,))[-8:]
                            self.contexts[(w, c)] = had
                            while len(self.contexts) > 150_000:
                                del self.contexts[next(iter(self.contexts))]
                        if label and self.met_with[w][c] >= 2:
                            seen = self.seen_in.pop((w, c), None)
                            if seen is None:
                                seen = []
                                if len(self.seen_in) >= 20_000:
                                    del self.seen_in[next(iter(self.seen_in))]
                            seen.append(label)
                            del seen[:-6]
                            self.seen_in[(w, c)] = seen
            if trials:
                totals = self.chance_totals()
                for w, t in trials.items():
                    if self.is_glue(w):
                        self.expect.pop(w, None)
                    else:
                        self.expect_more(w, t, totals)
            if about and self.is_word(about):
                m, old = self.defined.get(about, (0, {}))
                self.defined[about] = (m + n, dict(collections.Counter(old) + hits))
                rate = self.defined_rate.setdefault(about, {})
                for c in set(old) | set(hits):
                    now = self.number_sentences[c] / max(1, self.numbered)
                    rate[c] = (rate.get(c, now) * m + now * n) / max(1, m + n)
                fresh.add(about)
            self.weigh(fresh if self.articles % 25 else self.candidates())
        return hits

    def note_form(self, t):
        """How a word is written, remembered for showing it."""
        k = fold(t)
        e = self.shown.get(k)
        if e is None:
            if t != k:
                self.shown[k] = [t, 1]
                if len(self.shown) > 300_000:
                    for w in list(self.shown)[:100_000]:
                        del self.shown[w]
        elif e[0] == t:
            e[1] += 1
        else:
            e[1] -= 1
            if e[1] <= 0:
                self.shown[k] = [t, 1]

    def display(self, w):
        """A word as it is most often written."""
        e = self.shown.get(w)
        return e[0] if e else w

    def fold_memory(self):
        """A memory from before it folded the case of letters."""
        forms = collections.defaultdict(collections.Counter)
        old_shown = dict(self.__dict__.get("shown") or {})

        def pair_of(p):
            x, y = fold(p[0]), fold(p[1])
            return None if x == y else ((x, y) if x < y else (y, x))

        src = collections.Counter()
        for w, k in self.word_src.items():
            src[fold(w)] += k
            forms[fold(w)][w] += k
        new = {}
        for w, at in self.word_new.items():
            new[fold(w)] = min(at, new.get(fold(w), at))
            forms[fold(w)][w] += 1
        self.word_src, self.word_new = src, {w: at for w, at in new.items() if w not in src}
        pairs, pnew, links = collections.Counter(), {}, {}
        for p, k in self.pair_src.items():
            if (q := pair_of(p)):
                pairs[q] += k
        for p, at in self.pair_new.items():
            if (q := pair_of(p)) and q not in pairs:
                pnew[q] = min(at, pnew.get(q, at))
        for p, e in self.links.items():
            if (q := pair_of(p)):
                links[q] = max(e, links.get(q, 0.0))
        self.pair_src, self.pair_new, self.links = pairs, pnew, links
        met = collections.defaultdict(collections.Counter)
        for w, cs in self.met_with.items():
            met[fold(w)].update(cs)
        self.met_with = met
        meaning = {}
        for w, ms in self.read_meaning.items():
            if fold(w) not in meaning or (ms and ms[0][1] > meaning[fold(w)][0][1]):
                meaning[fold(w)] = ms
        self.read_meaning = meaning
        self.read_names = {c: fold(w) for c, w in self.read_names.items()}
        defined = {}
        for w, (m, hits) in self.defined.items():
            m0, h0 = defined.get(fold(w), (0, {}))
            defined[fold(w)] = (m0 + m, dict(collections.Counter(h0) + collections.Counter(hits)))
        self.defined = defined
        related = collections.defaultdict(collections.Counter)
        for w, r in self.related.items():
            related[fold(w)].update(r)
        self.related = related
        self.looked = set(self.looked) | {fold(w) for w in self.looked}
        salient = collections.Counter()
        for k, v in self.salient.items():
            salient[fold(k)] += v
        self.salient = salient
        shown = {}
        for k, c in forms.items():
            best = c.most_common(1)[0][0]
            form = old_shown.get(best, [best])[0]
            if form != k:
                shown[k] = [form, 1]
        self.shown = shown
        self.counted, self.counted_by, self.source = collections.defaultdict(set), {}, None
        self.folded = FOLD_VERSION

    def estimate_scripts(self):
        """For a memory from before it counted sources per writing system."""
        n = max(1, self.sources)
        best = {}
        for w, k in self.word_src.items():
            sc = script_of(w)
            best[sc] = max(best.get(sc, 0), k)
        capped = [sc for sc, k in best.items() if k >= 0.95 * GLUE * n]
        est = {sc: k for sc, k in best.items() if sc not in capped}
        rest = max(0, n - sum(est.values()))
        for sc in capped:
            est[sc] = max(best[sc], rest // len(capped))
        return collections.Counter(est)

    def sources_in(self, w):
        """How many of the sources it read could have held this word."""
        return self.script_src.get(script_of(w), 0) or max(1, self.sources)

    def chance(self, w, c, totals=None):
        """How often, by chance, a word's sentence names concept c."""
        sc = script_of(w)
        book = self.number_by.get(sc) if self.number_by_full else None
        total = (totals or {}).get(sc) if totals is not None else (sum(book.values()) if book else 0)
        if book and total and total >= 500:
            return (book.get(c, 0) + 1) / (total + len(book) + 1)
        return self.number_articles[c] / max(1, sum(self.number_articles.values()) if totals is None
                                             else totals.get(None, 1))

    def rate_now(self, w, totals):
        """The chance, as things are now, that a concept named near this word is each concept."""
        sc = script_of(w)
        book = self.number_by.get(sc) if self.number_by_full else None
        total = totals.get(sc) if book else 0
        if book and total and total >= 500:
            n = total + len(book) + 1
            return lambda c: (book.get(c, 0) + 1) / n
        everything = max(1, totals.get(None, 1))
        return lambda c: self.number_articles[c] / everything

    def expect_more(self, w, t, totals):
        """t more meetings of word w with concepts."""
        rate, cs = self.rate_now(w, totals), self.met_with[w]
        exp = self.expect.setdefault(w, {})
        before = sum(cs.values()) - t
        for c in cs:
            p = rate(c)
            if c not in exp:
                exp[c] = before * p
            exp[c] += t * p

    def chance_of(self, w, c, totals=None):
        """The chance of concept c among the meetings of word w."""
        exp = self.expect.get(w) if MATCHED else None
        m = sum(self.met_with.get(w, {}).values())
        if exp and c in exp and m:
            return min(max(exp[c] / m, 1e-12), 1.0)
        return self.chance(w, c, totals)

    def topic_of(self, words, main):
        """The number of the topic these main words are about."""
        best, score = None, 0.0
        for t, theirs in self.topic_sets.items():
            share = len(words & theirs) / max(1, min(len(words), len(theirs)))
            if share > score:
                best, score = t, share
        if best is not None and score >= (SAME_TOPIC or 0.4):
            return best
        self.topics_made += 1
        self.topic_sets[self.topics_made] = set(words)
        self.topic_labels[self.topics_made] = " · ".join(self.display(w) for w in main[:3])
        self.topic_main[self.topics_made] = list(main[:3])
        while len(self.topic_sets) > room(1500):
            old = next(iter(self.topic_sets))
            del self.topic_sets[old]
            self.topic_labels.pop(old, None)
            self.topic_main.pop(old, None)
            self.topic_seen.pop(old, None)
            self.topic_cells.pop(old, None)
        return self.topics_made

    def general(self, w, c):
        """Is this meaning true across topics."""
        had = self.contexts.get((w, c))
        return had is None or len(had) >= 2

    def match_chances(self):
        """For a memory from before each meeting kept its own chance."""
        totals = self.chance_totals()
        for w, cs in self.met_with.items():
            rate, m = self.rate_now(w, totals), sum(cs.values())
            self.expect[w] = {c: m * rate(c) for c in cs}
        per_sentence = max(1, self.numbered)
        for w, (m, hits) in self.defined.items():
            self.defined_rate[w] = {c: self.number_sentences[c] / per_sentence for c in hits}
        self.matched = True

    def chance_totals(self):
        """The sums chance() needs, counted once for a whole batch of words."""
        out = {sc: sum(b.values()) for sc, b in self.number_by.items()}
        out[None] = max(1, sum(self.number_articles.values()))
        return out

    def is_glue(self, w):
        """A word in more than a fifth of the sources written in its letters."""
        m = self.sources_in(w)
        return m >= 50 and self.word_src.get(w, 0) > GLUE * m

    def learn_links(self, sentences, source):
        """Words that keep coming in the same sentences, in more separate articles than chance would give, become
        linked."""
        web = isinstance(source, tuple) and bool(source) and source[0] == "web"
        seen = self.link_units.pop(source, None) if web else None
        if seen is None:
            seen = set()
            self.sources += 1
        if web:
            self.link_units[source] = seen
            while len(self.link_units) > 2 * len(self.round_sites) + 8:
                del self.link_units[next(iter(self.link_units))]
        self.link_source, self.link_seen = source, seen
        n, touched = self.sources, set()
        for sc in {script_of(w) for words in sentences for w in words}:
            if ("§", sc) not in seen:
                seen.add(("§", sc))
                self.script_src[sc] += 1

        for words in sentences:
            content = [w for w in words if not self.is_glue(w)]
            for w in content:
                if w in seen:
                    continue
                seen.add(w)
                if w in self.word_src:
                    self.word_src[w] += 1
                elif w in self.word_new:
                    del self.word_new[w]
                    self.word_src[w] = 2
                else:
                    self.word_new[w] = n
            met = [w for w in content if w in self.word_src]
            for i, x in enumerate(met):
                for y in met[i + 1:i + 5]:
                    if x == y:
                        continue
                    pair = (x, y) if x < y else (y, x)
                    if pair in seen:
                        continue
                    seen.add(pair)
                    if pair in self.pair_src:
                        self.pair_src[pair] += 1
                        touched.add(pair)
                    elif pair in self.pair_new:
                        del self.pair_new[pair]
                        self.pair_src[pair] = 2
                    else:
                        self.pair_new[pair] = n
        self.weigh_links(touched)

    def weigh_links(self, pairs):
        """Two words are linked when they share more sources than chance would give."""
        for pair in pairs:
            k = self.pair_src.get(pair, 0)
            x, y = pair
            nx, ny = self.sources_in(x), self.sources_in(y)
            m = max(k, min(nx, ny))
            p = min(1.0, self.word_src.get(x, 1) / nx) * min(1.0, self.word_src.get(y, 1) / ny)
            e = evidence(m, k, p) if k >= 3 and k >= LIFT * p * m else 0.0
            if e >= WORD_EVIDENCE:
                if pair not in self.links:
                    self.links_made += 1
                    self.emit("linked", a=x, b=y, e=round(e, 1), sa=self.display(x), sb=self.display(y))
                    self.salient[x] += 1.0
                    self.salient[y] += 1.0
                    self.urge += 0.5
                self.links[pair] = round(e, 1)
            elif pair in self.links:
                del self.links[pair]
                self.pruned += 1

    def look_at_grammar(self):
        """What its reading taught it of its languages' grammar of numbers, looked at again."""
        with self.lock:
            self.grammar.tidy()
            g = copy.deepcopy(self.grammar)
        learned = g.look()
        with self.lock:
            had = {sc: len(x.get("laws", [])) for sc, x in self.grammar.learned.items()}
            self.grammar.learned = learned
            for sc, x in learned.items():
                if len(x.get("laws", [])) > had.get(sc, 0):
                    self.emit("grammar", script=sc, classes=x["classes"], laws=len(x["laws"]))

    def tidy_reading(self):
        """Every 200 articles it tidies what its reading built."""
        before = self.pruned
        for pair in list(self.co_read):
            self.co_read[pair] *= 0.97
            if self.co_read[pair] < 0.2:
                del self.co_read[pair]
                self.pruned += 1
        for w in list(self.related):
            rel = self.related[w]
            for t in list(rel):
                rel[t] *= 0.97
                if rel[t] < 0.2:
                    del rel[t]
                    self.pruned += 1
            if not rel:
                del self.related[w]
        old = self.sources - 100
        for w in [w for w, at in self.word_new.items() if at < old]:
            del self.word_new[w]
        for pair in [p for p, at in self.pair_new.items() if at < old]:
            del self.pair_new[pair]
        if len(self.pair_src) > 300000:
            for pair in [p for p, k in self.pair_src.items() if k <= 2 and p not in self.links]:
                del self.pair_src[pair]
        if len(self.met_with) > room(20000):
            for w in [w for w, cs in self.met_with.items() if sum(cs.values()) <= 1 and w not in self.read_meaning]:
                del self.met_with[w]
                self.expect.pop(w, None)
        self.weigh_links(list(self.links))
        if self.pruned > before:
            self.emit("pruned", n=self.pruned - before)
        self.curious()

    def candidates(self):
        return [w for w, cs in self.met_with.items() if max(cs.values(), default=0) >= 3] + list(self.defined)

    def weigh(self, words):
        """What its reading has taught it about these words so far, by the rule in read()."""
        totals = self.chance_totals()
        per_sentence = max(1, self.numbered)
        for w in words:
            found, cs = {}, self.met_with.get(w, {})
            if self.is_glue(w):
                cs = {}
            m, pool = sum(cs.values()), None if not cs and self.is_glue(w) else self.pooled(w, cs, totals)
            if pool:
                cs, m, p_of = pool
            for c, k in cs.items():
                p = p_of(c) if pool else self.chance_of(w, c, totals)
                if k >= MEANING_SOURCES and k >= min(LIFT * p, (1 + p) / 2) * m and (e := evidence(m, k, p)) >= WORD_EVIDENCE:
                    found[c] = e
            tcs = {} if self.is_glue(w) else self.table_met.get(w, {})
            tm, texp = sum(tcs.values()), self.table_expect.get(w, {})
            for c, k in tcs.items():
                p = min(max(texp.get(c, 0.0) / tm, 1e-12), 1.0)
                if k >= MEANING_SOURCES and k >= min(LIFT * p, (1 + p) / 2) * tm and (e := evidence(tm, k, p)) >= WORD_EVIDENCE:
                    found[c] = max(found.get(c, 0.0), e)
            m, hits = self.defined.get(w, (0, {}))
            then = self.defined_rate.get(w, {}) if MATCHED else {}
            for c, k in hits.items():
                p = then.get(c) or self.number_sentences[c] / per_sentence
                if k >= 3 and (e := evidence(m, k, p)) >= TITLE_EVIDENCE + math.log10(max(1, m)):
                    found[c] = max(found.get(c, 0.0), e)
            before = [c for c, _ in self.read_meaning.get(w, ())]
            if found:
                self.read_meaning[w] = sorted(((c, round(e, 1)) for c, e in found.items()), key=lambda x: -x[1])[:2]
            else:
                self.read_meaning.pop(w, None)
            for c, e in self.read_meaning.get(w, ()):
                if c not in before:
                    self.meanings_made += 1
                    self.emit("meaning", word=w, s=c, e=e, shown=self.display(w),
                              taught=w in (self.__dict__.get("told") or ()),
                              council=bool(pool))
                    self.salient[w] += 1.0
                    self.salient[c] += 1.0
                    self.urge += 1.0
        best = {}
        for w, ms in self.read_meaning.items():
            c, e = ms[0]
            score = (self.general(w, c), e)
            if score > best.get(c, (None, (False, 0.0)))[1]:
                best[c] = (w, score)
        self.read_names = {c: w for c, (w, _) in best.items()}

    def forget_old_word_links(self):
        """Memory from before words needed real evidence."""
        symbols = {symbol(k) for k in self.kinds_seen}
        self.heard, self.exposure = collections.defaultdict(collections.Counter), collections.Counter()
        for m in self.messages:
            if m["who"] != "me":
                continue
            sym, eq, word = m["text"].partition(" = ")
            if eq and sym in symbols and word.strip():
                self.heard[word.strip()][sym] += 3.0
                self.exposure[word.strip()] += 3.0
                continue
            for w in (w.strip(EDGES) for w in m["text"].split()):
                if w:
                    self.exposure[w] += 1.0
        self.number_articles, self.number_sentences = collections.Counter(), collections.Counter()
        self.numbered = 0
        self.met_with = collections.defaultdict(collections.Counter)
        self.defined, self.read_meaning, self.read_names = {}, {}, {}
        self.expect, self.defined_rate = {}, {}
        self.table_met = collections.defaultdict(collections.Counter)
        self.table_expect, self.table_columns = {}, collections.Counter()
        self.source, self.counted = None, collections.defaultdict(set)
        self.co_read = collections.Counter()
        self.queue = list(dict.fromkeys(list(self.queue) + sorted(self.looked)))

# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie: the grammar its languages give to numbers, learned from what it reads."""
import collections
import math
import os

EVIDENCE = 6.0
SOURCES = 4
MAX_N = 120
WORDS = 400
KEEP = 3000
ALPHA = 0.5


class Grammar:
    """What comes after each number it reads, in each writing system, and what it learned of it."""

    def __init__(self):
        self.after = {}
        self.sources = {}
        self.source, self.this = None, set()
        self.seen = 0
        self.learned = {}

    def see(self, pairs, source):
        """(script, number, word after it) of one text."""
        units = self.__dict__.setdefault("units", {})
        self.this = units.pop(source, None) or set()
        units[source] = self.this
        while len(units) > 64:
            del units[next(iter(units))]
        self.source = source
        for sc, n, w in pairs:
            if not 0 <= n <= MAX_N or (sc, n, w) in self.this:
                continue
            self.this.add((sc, n, w))
            self.after.setdefault(sc, {}).setdefault(n, collections.Counter())[w] += 1
            if (sc, w) not in self.this:
                self.this.add((sc, w))
                self.sources.setdefault(sc, collections.Counter())[w] += 1
            self.seen += 1

    def tidy(self):
        """The rarest words after numbers go, past KEEP in a script."""
        for sc, by_n in self.after.items():
            total = collections.Counter()
            for c in by_n.values():
                total.update(c)
            if len(total) <= KEEP:
                continue
            keep = {w for w, _ in total.most_common(KEEP)}
            for c in by_n.values():
                for w in [w for w in c if w not in keep]:
                    del c[w]
            src = self.sources.get(sc, collections.Counter())
            for w in [w for w in src if w not in keep]:
                del src[w]

    # -- the classes of numbers ------------------------------------------------------------------------
    def classes(self, sc):
        """The line of numbers cut where what comes after them changes."""
        by_n = self.after.get(sc, {})
        ns = sorted(n for n, c in by_n.items() if sum(c.values()))
        if len(ns) < 3:
            return [], 0.0
        total = collections.Counter()
        for n in ns:
            total.update(by_n[n])
        vocab = [w for w, c in total.most_common(WORDS) if c >= 3]
        idx = {w: i for i, w in enumerate(vocab)}
        K = len(vocab) + 1
        pre = [[0] * K]
        for n in ns:
            row = pre[-1][:]
            for w, c in by_n[n].items():
                row[idx.get(w, K - 1)] += c
            pre.append(row)
        N = len(ns)

        def cost(i, j):
            c = [b - a for a, b in zip(pre[i], pre[j])]
            C = sum(c)
            if not C:
                return 0.0
            said = math.lgamma(C + K * ALPHA) - math.lgamma(K * ALPHA)
            said -= sum(math.lgamma(x + ALPHA) - math.lgamma(ALPHA) for x in c if x)
            return said / math.log(2) + math.log2(N)

        best, cut = [0.0] + [math.inf] * N, [0] * (N + 1)
        for j in range(1, N + 1):
            for i in range(j):
                v = best[i] + cost(i, j)
                if v < best[j]:
                    best[j], cut[j] = v, i
        out, j = [], N
        while j > 0:
            i = cut[j]
            c = collections.Counter()
            for n in ns[i:j]:
                c.update(by_n[n])
            out.append((ns[i], ns[j - 1], c))
            j = i
        out.reverse()
        return out, cost(0, N) - best[N]

    # -- forms of one word, by class ---------------------------------------------------------------------
    def laws(self, sc, classes):
        """Forms of one word."""
        if len(classes) < 2:
            return []
        table = collections.defaultdict(collections.Counter)
        for k, (_, _, c) in enumerate(classes):
            for w, x in c.items():
                table[w][k] += x
        words = [w for w, t in table.items() if sum(t.values()) >= 3]
        stems = collections.defaultdict(set)
        for w in words:
            for L in range(3, len(w) + 1):
                stems[w[:L]].add(w)
        groups, done = [], set()
        for stem in sorted(stems, key=lambda s: (-len(s), s)):
            forms = sorted(f for f in stems[stem] if f not in done and len(stem) >= 0.6 * len(f))
            if len(forms) < 2:
                continue
            groups.append((stem, forms))
            done.update(forms)
        out, src = [], self.sources.get(sc, collections.Counter())
        for stem, forms in groups:
            counts = {f: table[f] for f in forms}
            N = sum(sum(t.values()) for t in counts.values())
            by_class = collections.Counter()
            for t in counts.values():
                by_class.update(t)
            ev = 0.0
            for f, t in counts.items():
                rate = sum(t.values()) / N
                for k, x in t.items():
                    ev += x * math.log10((x / by_class[k]) / rate)
            ev -= 0.5 * (len(forms) - 1) * (len(classes) - 1) * math.log10(N)
            met = sum(src[f] for f in forms)
            if ev < EVIDENCE or met < SOURCES:
                continue
            law = {}
            for k in range(len(classes)):
                got = [(t[k], f) for f, t in counts.items() if t[k]]
                if got:
                    law[k] = max(got)[1]
            if len(set(law.values())) < 2:
                continue
            out.append({"forms": forms, "law": law, "evidence": round(ev, 1), "sources": met,
                        "counts": {f: dict(t) for f, t in counts.items()}})
        out.sort(key=lambda x: -x["evidence"])
        return out

    def look(self):
        """What it learned of each of its languages, now."""
        for sc in list(self.after):
            classes, saving = self.classes(sc)
            if saving <= 0 or len(classes) < 2:
                self.learned[sc] = {"classes": [], "saving": 0.0, "laws": []}
                continue
            total = collections.Counter()
            for _, _, c in classes:
                total.update(c)
            N = sum(total.values())

            def marks(c):
                n = sum(c.values())
                lift = [(x / n / (total[w] / N), w) for w, x in c.items() if x >= 3]
                return [w for _, w in sorted(lift, reverse=True)[:6]] or [w for w, _ in c.most_common(6)]
            self.learned[sc] = {"classes": [(a, b) for a, b, _ in classes], "saving": round(saving, 1),
                                "laws": self.laws(sc, classes), "words": [marks(c) for _, _, c in classes]}
        return self.learned

    def class_of(self, sc, n):
        """Which of its classes a number is in."""
        cl = self.learned.get(sc, {}).get("classes") or []
        best, gap = None, math.inf
        for k, (a, b) in enumerate(cl):
            if a <= n <= b:
                return k
            d = min(abs(n - a), abs(n - b))
            if d < gap:
                best, gap = k, d
        return best

    def form(self, sc, word, n):
        """The form of this word its language puts after the number n."""
        k = self.class_of(sc, n)
        if k is None:
            return None
        for law in self.learned.get(sc, {}).get("laws", []):
            if word in law["forms"]:
                return law["law"].get(k)
        return None



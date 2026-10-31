# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""C4, its type book: the kinds."""
import collections
import math

from . import eproc as E


class Entry:
    """The book's kinds of one sense."""

    def __init__(self, n):
        self.n, self.classes = n, []

    def view(self, assigned):
        return View(self, assigned)

    def kind_code(self, k, own):
        """KT code (natural log) of a kind's changes at own keys, plus the counts own given."""
        tot = 0.0
        keys = set(self.classes[k]["own"]) | set(own)
        for key in keys:
            c = collections.Counter(self.classes[k]["own"].get(key, {}))
            c.update(own.get(key, {}))
            if c:
                tot += E.kt_len(c, max(2, len(c)))
        return tot

    def add(self, kind):
        """A world's kind into the book."""
        best = None
        limit = E.SELECT_MIN * E.LN10
        for k in range(len(self.classes)):
            gain, apart = 0.0, False
            mine = self.classes[k]["own"]
            for key in set(mine) | set(kind["own"]):
                a, b = mine.get(key) or collections.Counter(), kind["own"].get(key) or collections.Counter()
                both = collections.Counter(a)
                both.update(b)
                K = max(2, len(both))
                g = (E.kt_len(a, K) if a else 0.0) + (E.kt_len(b, K) if b else 0.0) - E.kt_len(both, K)
                if a and b and g < -limit:
                    apart = True
                    break
                gain += g
            if not apart and gain > 0 and (best is None or gain > best[0]):
                best = (gain, k)
        if best is None:
            self.classes.append({"own": {k: collections.Counter(v) for k, v in kind["own"].items()},
                                 "with": {k: collections.Counter(v) for k, v in kind["with"].items()},
                                 "cell": {k: collections.Counter(v) for k, v in kind["cell"].items()},
                                 "worlds": 1, "size": kind["size"]})
            return len(self.classes) - 1
        tgt = self.classes[best[1]]
        for part in ("own", "with", "cell"):
            for key, c in kind[part].items():
                tgt[part].setdefault(key, collections.Counter()).update(c)
        tgt["worlds"] += 1
        tgt["size"] += kind["size"]
        return best[1]


class View:
    """The book as one grouping reads it."""

    def __init__(self, entry, assigned):
        self.entry, self.assigned = entry, dict(assigned)
        self._apart = {}

    def apart(self, own, b):
        """Where the book's kinds this grouping reads differ."""
        if own[2] is None:
            return None
        key = (own, b)
        got = self._apart.get(key)
        if got is not None or key in self._apart:
            return got
        kinds = sorted(set(self.assigned.values()))
        per = [self.entry.classes[k]["own"].get(own) for k in kinds]
        per = [(k, c) for k, c in zip(kinds, per) if c]
        out = None
        if len(per) >= 2 and any(k == b for k, _ in per):
            both = collections.Counter()
            for _, c in per:
                both.update(c)
            K = max(2, len(both))
            saving = E.kt_len(both, K) - sum(E.kt_len(c, K) for _, c in per)
            mine = dict(per)[b]
            n, N = sum(mine.values()), sum(both.values())
            kl = 0.0
            for y in both:
                pm, pa = (mine.get(y, 0) + 0.5) / (n + K / 2), (both[y] + 0.5) / (N + K / 2)
                kl += pm * math.log(pm / pa)
            out = (saving, kl)
        self._apart[key] = out
        return out

    def prob(self, b, ab, grain, below):
        """The book kind b's odds of this change."""
        own, y, others = ab
        if y is None or own[2] is None:
            return None
        kind = self.entry.classes[b]
        if grain == "own":
            cc = kind["cell"].get(own[:2])
            p = (cc[y] + below) / (sum(cc.values()) + 1) if cc else below
            co = kind["own"].get(own)
            return (co[y] + p) / (sum(co.values()) + 1) if co else p
        if grain.startswith("with "):
            k = int(grain[5:])
            xk = others.get(k)
            if xk is None:
                return None
            cw = kind["with"].get(own + (k, xk))
            return (cw[y] + below) / (sum(cw.values()) + 1) if cw else None
        return None

    def loglik(self, b, counts_by_key):
        """ln of a symbol's (or class's) changes at its own keys (by role) under kind b, each told by the kind's
        odds smoothed as KT would (half a count each way)."""
        kind = self.entry.classes[b]
        tot = 0.0
        for key, c in counts_by_key.items():
            ref = kind["own"].get(key) or kind["cell"].get(key[:2]) or {}
            K = max(2, len(set(ref) | set(c)))
            N = sum(ref.values())
            for y, k in c.items():
                tot += k * math.log((ref.get(y, 0) + 0.5) / (N + K / 2))
        return tot


def own_counts_by_role(test, v):
    """A symbol's changes at its own keys, by role."""
    out = collections.defaultdict(collections.Counter)
    for ob in test.acts:
        if ob.v != v or not ob.ab:
            continue
        for i, (own, y, _) in ob.ab.items():
            if own[2] is not None and y is not None:
                out[own][y] += 1
    return out


def read_by_book(test, symbols):
    """Each symbol read as the book kind its changes are likeliest under, if likelier than told by a code of its
    own."""
    book = test.book
    view = book.view({})
    kinds = {}
    for v in symbols:
        own = own_counts_by_role(test, v)
        if not own:
            kinds[v] = -1
            continue
        alone = -sum(E.kt_len(c, max(2, len(c))) for c in own.values())
        best = max(range(len(book.classes)), key=lambda b: (view.loglik(b, own), -b))
        kinds[v] = best if view.loglik(best, own) > alone else -1
    groups = collections.defaultdict(list)
    for v in symbols:
        groups[("k", kinds[v]) if kinds[v] >= 0 else ("v", repr(v))].append(v)
    G = [g for _, g in sorted(groups.items(), key=lambda kv: repr(kv[0]))]
    return G, kinds


def kinds_of_groups(test, G):
    """Each class of a grouping read as the book kind its pooled changes are likeliest under, or none."""
    view = test.book.view({})
    out = {}
    for g in G:
        own = collections.defaultdict(collections.Counter)
        for v in g:
            for key, c in own_counts_by_role(test, v).items():
                own[key].update(c)
        if not own:
            continue
        alone = -sum(E.kt_len(c, max(2, len(c))) for c in own.values())
        best = max(range(len(test.book.classes)), key=lambda b: (view.loglik(b, own), -b))
        k = best if view.loglik(best, own) > alone else -1
        for v in g:
            out[v] = k
    return out


def kinds_of_world(model, m, test, classes):
    """What a world's believed classes of sense m carry into the book."""
    room = model.__dict__.get("concepts") or {}
    concept_senses = {j for j, got in (room.get("classes") or {}).items() if got}
    roles = test.roles
    out = []
    for members in classes:
        kind = {"own": collections.defaultdict(collections.Counter), "with": collections.defaultdict(collections.Counter),
                "cell": collections.defaultdict(collections.Counter), "size": len(members)}
        for v in members:
            for key, c in (room.get("own") or {}).get(m, {}).get(v, {}).items():
                a, i, x = key
                xr = E.by_role(roles, i, x)
                if xr is None:
                    continue
                for y, k in c.items():
                    yr = E.change_by_role(roles, i, y)
                    if yr is not None:
                        kind["own"][(a, i, xr)][yr] += k
                        kind["cell"][(a, i)][yr] += k
            for k2, per in (room.get("with") or {}).items():
                if k2 in concept_senses or k2 == m:
                    continue
                for key, c in per.get(m, {}).get(v, {}).items():
                    a, i, x, xk = key
                    if i == k2:
                        continue
                    xr, xkr = E.by_role(roles, i, x), E.by_role(roles, k2, xk)
                    if xr is None or xkr is None:
                        continue
                    for y, k in c.items():
                        yr = E.change_by_role(roles, i, y)
                        if yr is not None:
                            kind["with"][(a, i, xr, k2, xkr)][yr] += k
        out.append(kind)
    return out

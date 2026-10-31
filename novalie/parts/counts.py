# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie Mind: what learns the hidden structure of what it sees, from the loops in its own experience."""
import cmath
import collections
import copy
import itertools
import json
import math
import operator
import os
import sys
import time
import zlib

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
try:
    from . import gpu as gpu
except ImportError:
    gpu = None

GPU_CHECK_FROM = 4096
GPU_QUICK_FROM = 50_000
_add = operator.add
_MISSING = object()


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

def smith(rows, m):
    """Smith normal form of the lattice spanned by integer rows of length m."""
    A = [list(r) for r in rows if any(r)]
    V = [[int(i == j) for j in range(m)] for i in range(m)]
    n, t, d = len(A), 0, []

    def swap_cols(i, j):
        for row in A + V:
            row[i], row[j] = row[j], row[i]

    while t < min(n, m):
        piv = min(((abs(A[i][j]), i, j) for i in range(t, n) for j in range(t, m) if A[i][j]), default=None)
        if piv is None:
            break
        _, i, j = piv
        A[t], A[i] = A[i], A[t]
        if j != t:
            swap_cols(t, j)
        while True:
            p, moved = A[t][t], False
            for i in range(t + 1, n):
                q = A[i][t] // p
                if q:
                    A[i] = [x - q * y for x, y in zip(A[i], A[t])]
                if A[i][t]:
                    A[t], A[i] = A[i], A[t]
                    moved = True
                    break
            if moved:
                continue
            for j in range(t + 1, m):
                q = A[t][j] // p
                if q:
                    for row in A + V:
                        row[j] -= q * row[t]
                if A[t][j]:
                    swap_cols(t, j)
                    moved = True
                    break
            if moved:
                continue
            bad = next((i for i in range(t + 1, n) for j in range(t + 1, m) if A[i][j] % p), None)
            if bad is None:
                break
            A[t] = [x + y for x, y in zip(A[t], A[bad])]
        d.append(abs(A[t][t]))
        t += 1
    return d, V


class Model:
    """The agent's knowledge about a world whose buttons commute."""

    def __init__(self, m, gens=()):
        self.m, self.gens = m, [list(g) for g in gens]
        d, V = smith(self.gens, m)
        r = len(d)
        keep = [j for j in range(r) if d[j] > 1] + list(range(r, m))
        self.mods = [d[j] for j in range(r) if d[j] > 1] + [0] * (m - r)
        self.eff = [[V[a][j] for j in keep] for a in range(m)]
        self.moves = self.moves_of()

    def moves_of(self):
        """For each button, only the registers it changes."""
        return [[(j, e, q) for j, (e, q) in enumerate(zip(row, self.mods)) if e] for row in self.eff]

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.moves = self.moves_of()

    def origin(self):
        return tuple([0] * len(self.mods))

    def step(self, key, a, times=1):
        if len(key) != len(self.mods):
            return tuple((x + times * e) % q if q else x + times * e
                         for x, e, q in zip(key, self.eff[a], self.mods))
        k = list(key)
        for j, e, q in self.moves[a]:
            x = k[j] + times * e
            k[j] = x % q if q else x
        return tuple(k)

    def of(self, v):
        """The change of state that a count vector of presses makes."""
        k = [0] * len(self.mods)
        for a, n in enumerate(v):
            if n:
                for j, e, q in self.moves[a]:
                    k[j] += n * e
        return tuple(x % q if q else x for x, q in zip(k, self.mods))

    def contains(self, v):
        return not any(self.of(v))

    def add(self, key, k):
        return tuple((x + y) % q if q else x + y for x, y, q in zip(key, k, self.mods))

    def canon(self, k):
        neg = tuple((-x) % q if q else -x for x, q in zip(k, self.mods))
        return min(k, neg)

    def size(self, k):
        return sum(min(x % q, q - x % q) if q else abs(x) for x, q in zip(k, self.mods))

    def presses(self):
        """For each press: (True, the tuple it adds) when it moves only registers with no cycle, else (False, its
        moves), so a state is stepped with the same arithmetic as step(), a plain press as one sum of."""
        R = len(self.mods)
        out = []
        for mv in self.moves:
            if all(q == 0 for _, _, q in mv):
                d = [0] * R
                for j, e, _ in mv:
                    d[j] = e
                out.append((True, tuple(d)))
            else:
                out.append((False, mv))
        return out

    def keys(self, actions):
        k = self.origin()
        out = [k]
        steps = self.presses()
        app = out.append
        for a in actions:
            plain, d = steps[a]
            if plain:
                k = tuple(map(_add, k, d))
            else:
                kl = list(k)
                for j, e, q in d:
                    x = kl[j] + e
                    kl[j] = x % q if q else x
                k = tuple(kl)
            app(k)
        return out


def joint(models, m):
    """One model of all its senses together."""
    basis = [[int(i == j) for j in range(m)] for i in range(m)]
    for mo in models:
        for i, q in enumerate(mo.mods):
            col = [mo.eff[a][i] for a in range(m)]
            vals = [sum(b[a] * col[a] for a in range(m)) for b in basis]
            rows = [b for b, v in zip(basis, vals) if v == 0]
            live = [(v, b) for b, v in zip(basis, vals) if v != 0]
            while len(live) > 1:
                live.sort(key=lambda vb: abs(vb[0]))
                v0, b0 = live[0]
                nxt = [live[0]]
                for v, b in live[1:]:
                    k = v // v0
                    v, b = v - k * v0, [x - k * y for x, y in zip(b, b0)]
                    if v == 0:
                        rows.append(b)
                    else:
                        nxt.append((v, b))
                live = nxt
            if live:
                v, b = live[0]
                if q:
                    t = q // math.gcd(abs(v), q)
                    rows.append([t * x for x in b])
            basis = [b for b in rows if any(b)]
    return Model(m, basis)


def spread(seq, k):
    """k of seq, spread evenly over all of it."""
    seq = list(seq)
    if len(seq) <= k:
        return seq
    n, out, seen, i = len(seq), [], set(), 0
    while len(out) < k:
        i += 1
        j = int(((i * 0.6180339887498949) % 1.0) * n)
        if j not in seen:
            seen.add(j)
            out.append(seq[j])
    return out


def bfs_path(model, start, goal=None, known=None, limit=20000, order=None):
    """Shortest press sequence inside the model."""
    prev, queue = {start: None}, collections.deque([start])
    order = list(order) if order is not None else list(range(model.m))
    while queue and len(prev) < limit:
        k = queue.popleft()
        if (goal is not None and k == goal) or (goal is None and k not in known):
            path = []
            while prev[k] is not None:
                k, a = prev[k]
                path.append(a)
            return path[::-1]
        for a in order:
            n = model.step(k, a)
            if n not in prev:
                prev[n] = (k, a)
                queue.append(n)
    return None


class Classes:
    """The candidates of one mind's freq grouped by the change of state each makes under one model, as its search
    groups them."""

    def __init__(self, model, freq):
        self.model = model
        self.cls, self.count, self.rep, self.rep_l1, self.plain, self.buckets = {}, {}, {}, {}, {}, {}
        self.zeros, self.dead = [], set()
        m = model.m
        self.free = (not any(model.mods) and len(model.mods) == m
                     and all(model.eff[a][j] == (a == j) for a in range(m) for j in range(m)))
        if self.free:
            self.add = self.add_free
        else:
            self.mods = list(model.mods)
            self.cols = [tuple(model.eff[a][j] for a in range(m)) for j in range(len(self.mods))]
            self.cyc = [(j, q) for j, q in enumerate(self.mods) if q]
            self.add = self.add_laws
        for v, n in freq.items():
            self.add(v, n)

    def add_laws(self, v, n):
        """Candidate v, new at the end of freq, seen n times, under a model with laws."""
        mul = operator.mul
        k = [sum(map(mul, v, col)) for col in self.cols]
        for j, q in self.cyc:
            k[j] %= q
        if not any(k):
            self.cls[v] = None
            self.zeros.append(v)
            return
        neg = [-x for x in k]
        for j, q in self.cyc:
            neg[j] %= q
        k, neg = tuple(k), tuple(neg)
        c = neg if neg < k else k
        self.cls[v] = c
        count = self.count
        if c in count:
            count[c] += n
            l1 = sum(map(abs, v))
            if l1 < self.rep_l1[c]:
                self.rep[c], self.rep_l1[c] = v, l1
            return
        count[c] = n
        self.rep[c], self.rep_l1[c] = v, sum(map(abs, v))
        mods = self.mods
        self.plain[c] = all(mods[j] == 0 for j, y in enumerate(c) if y)
        s = sum(min(x, q - x) if q else abs(x) for x, q in zip(c, mods))
        self.buckets.setdefault(s, []).append(c)

    def add_free(self, v, n):
        """Candidate v under a model with no law."""
        nv = tuple(map(operator.neg, v))
        c = nv if nv < v else v
        self.cls[v] = c
        count = self.count
        if c in count:
            count[c] += n
            l1 = sum(map(abs, v))
            if l1 < self.rep_l1[c]:
                self.rep[c], self.rep_l1[c] = v, l1
            return
        count[c] = n
        l1 = sum(map(abs, v))
        self.rep[c], self.rep_l1[c] = v, l1
        self.plain[c] = True
        self.buckets.setdefault(l1, []).append(c)

    def ordered(self):
        """The classes in the order of its trials."""
        count = self.count
        for s in sorted(self.buckets):
            b = self.buckets[s]
            if len(b) > 1:
                b = sorted(b, key=lambda c: -count[c])
            yield from b


class Mind:
    """A Novalie Mind living in one world."""

    def __init__(self, world, curious=True, window=40, max_cands=200):
        self.w, self.curious = world, curious
        self.m = len(world.buttons)
        self.window, self.max_cands = window, max_cands
        self.actions, self.colors = [], [world.color(world.state)]
        self.counts = [[0] * self.m]
        self.freq = collections.Counter()
        self.implied = collections.Counter()
        self.model = Model(self.m)
        self.key = self.model.origin()
        self.table = {self.key: self.colors[0]}
        self.by_color = collections.defaultdict(list)
        self.by_color[self.colors[0]].append(0)
        self.ledger, self.surprises = [], 0

    def choose(self):
        if self.curious:
            path = bfs_path(self.model, self.key, known=self.table, limit=4000)
            if path:
                return path[0]
        used = collections.Counter(self.actions)
        return min(range(self.m), key=lambda a: (used[a], a))

    def note(self, v):
        v = tuple(v)
        if any(v):
            if next(x for x in v if x) < 0:
                v = tuple(-x for x in v)
            self.note_up(v)

    def forget_once(self):
        """Candidates seen only once, forgotten whenever it holds more than it may."""
        most = max(self.__dict__.get("most_candidates", 200_000), self.__dict__.get("_forget_at", 0))
        if len(self.freq) > most:
            for v in [v for v, n in self.freq.items() if n == 1]:
                del self.freq[v]
            self._rc = None
            self._forget_at = 2 * len(self.freq)

    def note_up(self, v):
        """A candidate already a tuple with no negative count and some press."""
        f = self.freq
        rc = self.__dict__.get("_rc")
        if v in f:
            f[v] += 1
            if rc is not None:
                c = rc.cls.get(v, _MISSING)
                if c is _MISSING:
                    self._rc = None
                elif c is not None:
                    rc.count[c] += 1
        else:
            f[v] += 1
            if rc is not None:
                if v in rc.cls:
                    self._rc = None
                else:
                    rc.add(v, 1)

    def card_history(self):
        """Its history on its graphics card, sent there as it grows."""
        if gpu is None:
            return None
        h = self.__dict__.get("_hist", _MISSING)
        if h is _MISSING:
            h = self._hist = gpu.history(self.m)
        if h is not None:
            h.sync(self.counts, self.colors)
        return h

    def __getstate__(self):
        d = dict(self.__dict__)
        d.pop("_rc", None)
        d.pop("_hist", None)
        return d

    @staticmethod
    def model_key(model, n):
        """A model and how much of its history it was checked on, for its card's table of states."""
        return tuple(map(tuple, model.gens)), tuple(model.mods), n

    def check(self, model):
        """How many hidden states the model gives the experience so far, or None if it would give one state two
        colours."""
        if gpu is not None and len(self.colors) >= GPU_CHECK_FROM:
            h = self.card_history()
            if h is not None:
                got = h.check(self.model_key(model, len(self.colors)), model.eff, model.mods)
                if got is not False:
                    return got
        steps = model.presses()
        colors = self.colors
        k = model.origin()
        seen = {k: colors[0]}
        sd = seen.setdefault
        for a, o in zip(self.actions, itertools.islice(colors, 1, None)):
            plain, d = steps[a]
            if plain:
                k = tuple(map(_add, k, d))
            else:
                kl = list(k)
                for j, e, q in d:
                    x = kl[j] + e
                    kl[j] = x % q if q else x
                k = tuple(kl)
            if sd(k, o) != o:
                return None
        return len(seen)

    def quick_on_card(self, model, n_now, order, sample):
        """Its quick test of every class in order, at once on its card."""
        h = self.card_history()
        if h is None:
            return None
        key = self.model_key(model, len(self.colors))
        if h.table is None or h.table[0] != key:
            if h.check(key, model.eff, model.mods) != n_now:
                return None
        return h.quick(key, order, list(sample))

    def evidence(self, eps=1e-5):
        """A law must survive enough chances to be refuted."""
        n = len(self.colors)
        p = sum((c / n) ** 2 for c in collections.Counter(self.colors).values())
        return math.ceil(math.log(eps) / math.log(p)) if p < 1 else 10 ** 9

    def relearn(self, t):
        old = model = self.model
        n_now = self.check(model)
        if n_now is None:
            gens = list(model.gens)
            while gens and self.check(Model(self.m, gens)) is None:
                gens.pop()
            model = Model(self.m, gens)
            n_now = self.check(model)
            self.freq.update(self.implied)
            self.implied.clear()
        rc = self.__dict__.get("_rc")
        if len(self.freq) > 200000:
            for v in [v for v, n in self.freq.items() if n == 1]:
                del self.freq[v]
            rc = None
        if rc is None or rc.model is not model:
            rc = self._rc = Classes(model, self.freq)
        need, rejected, tried = self.evidence(), set(), 0
        flagged = ()
        colors = self.colors
        while tried < self.max_cands:
            keys = model.keys(self.actions)
            first = {}
            for k, o in zip(keys, colors):
                first.setdefault(k, o)
            sample = spread(range(len(keys)), min(150, len(keys)))
            if rc.model is not model:
                rc = self._rc = Classes(model, self.freq)
                flagged = {rc.cls[v] for v in rejected if rc.cls.get(v) is not None}
            order = rc.ordered()
            quick = None
            if gpu is not None and len(sample) * len(rc.count) >= GPU_QUICK_FROM:
                order = list(order)
                quick = self.quick_on_card(model, n_now, order, sample)
            sk = [keys[i] for i in sample]
            sc = [colors[i] for i in sample]
            mods, dead, rep, plain_of = model.mods, rc.dead, rc.rep, rc.plain
            fget = first.get
            accepted = False
            for idx, c in enumerate(order):
                if c in flagged:
                    continue
                v = rep[c]
                if quick is not None:
                    bad, agree = quick[idx]
                else:
                    agree, bad = 0, False
                    if plain_of[c]:
                        for s, col in zip(sk, sc):
                            o2 = fget(tuple(map(_add, s, c)))
                            if o2 is not None:
                                if o2 != col:
                                    bad = True
                                    break
                                agree += 1
                    else:
                        moves = [(j, y, q) for j, (y, q) in enumerate(zip(c, mods)) if y]
                        for s, col in zip(sk, sc):
                            key = list(s)
                            for j, y, q in moves:
                                x = key[j] + y
                                key[j] = x % q if q else x
                            o2 = fget(tuple(key))
                            if o2 is not None:
                                if o2 != col:
                                    bad = True
                                    break
                                agree += 1
                if bad:
                    rejected.add(v)
                    dead.add(c)
                    continue
                if not agree:
                    continue
                if tried >= self.max_cands:
                    break
                tried += 1
                if c in dead:
                    rejected.add(v)
                    continue
                trial = Model(self.m, model.gens + [list(v)])
                n_trial = self.check(trial)
                if n_trial is None:
                    rejected.add(v)
                    dead.add(c)
                elif n_now - n_trial >= need:
                    model, n_now, accepted = trial, n_trial, True
                    break
            if not accepted:
                break
        if rc.model is not model:
            rc = self._rc = Classes(model, self.freq)
        implied, freq, cls = self.implied, self.freq, rc.cls
        for v in rc.zeros:
            implied[v] += freq.pop(v)
            del cls[v]
        rc.zeros = []
        grew = all(model.contains(g) for g in old.gens)
        same = grew and all(old.contains(g) for g in model.gens)
        if not same:
            self.ledger.append((t, "learned" if grew else "revised", list(model.mods)))
        self.model = model
        keys = model.keys(self.actions)
        self.key, self.table = keys[-1], {}
        self.by_color = collections.defaultdict(list)
        for i, (k, o) in enumerate(zip(keys, colors)):
            if k not in self.table:
                self.table[k] = o
                self.by_color[o].append(i)

    def exact(self):
        mo = self.model
        if 0 in mo.mods or math.prod(mo.mods) != self.w.size or len(self.table) != self.w.size:
            return False
        return self.w.kind == "abelian" and all(self.w.is_loop(g) for g in mo.gens)

    def live(self, steps, check=True):
        """Explore for a number of presses."""
        exact_at, since = None, 0
        for _ in range(steps):
            a = self.choose()
            o = self.w.press(a)
            t2 = len(self.colors)
            self.actions.append(a)
            self.colors.append(o)
            c = self.counts[-1][:]
            c[a] += 1
            self.counts.append(c)
            for t1 in range(max(0, t2 - self.window), t2):
                if self.colors[t1] == o:
                    self.note(x - y for x, y in zip(c, self.counts[t1]))
            self.key = self.model.step(self.key, a)
            known = self.table.get(self.key)
            if known is None:
                past = self.by_color[o]
                for t1 in spread(past, 200):
                    self.note(x - y for x, y in zip(c, self.counts[t1]))
                self.table[self.key] = o
                self.by_color[o].append(t2)
            surprise = known is not None and known != o
            self.surprises += surprise
            since += 1
            if surprise or since >= max(50, t2 // 10):
                self.relearn(t2)
                since = 0
            if check and exact_at is None and self.exact():
                exact_at = t2
        return exact_at



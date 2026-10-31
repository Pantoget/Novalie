# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""An anytime-valid test of a sense's concepts."""
import collections
import itertools
import math

LN10 = math.log(10.0)
LAGS = (0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)


def age_of(acts):
    return max(l for l in LAGS if l <= acts)


def dd_counter():
    return collections.defaultdict(collections.Counter)


def dd_dd_counter():
    return collections.defaultdict(dd_counter)


def change_of(before, o):
    if o == before:
        return None
    if type(o) is int and type(before) is int:
        return o - before
    return ("to", o)


def is_symbol(v):
    return not isinstance(v, (int, float)) and v is not None


def kt_len(counts, kinds):
    """Krichevsky-Trofimov code length of counts over kinds outcomes, in natural log units."""
    n = sum(counts.values())
    k = max(2, kinds)
    got = math.lgamma(k / 2) - math.lgamma(n + k / 2) + sum(math.lgamma(c + 0.5) - math.lgamma(0.5) for c in counts.values())
    return -got


def crp_log_prior(sizes):
    """ln pi(G) under the Chinese restaurant process with alpha = 1."""
    n = sum(sizes)
    return sum(math.lgamma(s) for s in sizes) - math.lgamma(n + 1)


SINCE = True
SELECT_MIN = 0.0
BOOK_STRENGTHS = (1, 8, 64, 512)


def grains_for(n, m, i, since=None, fine=True):
    """The grains of a cell."""
    since = SINCE if since is None else since
    out = ["own"]
    out += [f"with {k}" for k in range(n) if k not in (m, i)]
    if since:
        out += [f"since {k}" for k in range(n) if k not in (m, i)]
    if fine:
        out.append("fine")
    return out


class UnionML:
    """The null's maximum likelihood when, in each cell, the change may hang on its own value and any ONE other
    sense's value."""

    def __init__(self, grains_of_cell):
        self.grains_of_cell = grains_of_cell
        self.per = {}
        self.ll = 0.0

    def add(self, cell, keys, y):
        d = self.per.get(cell)
        if d is None:
            d = self.per[cell] = {g: NullML() for g in self.grains_of_cell(cell)}
        old = max(x.ll for x in d.values())
        for g, x in d.items():
            x.add(keys[g], y)
        self.ll += max(x.ll for x in d.values()) - old

    @property
    def n(self):
        out = collections.Counter()
        for d in self.per.values():
            x = next(iter(d.values()))
            out.update(x.n)
        return out


def keys_at(grains, m, i, before, a, agesb):
    x = before[i]
    out = {}
    for g in grains:
        if g == "own":
            out[g] = (a, i, x)
        elif g == "fine":
            out[g] = (a, i, tuple(v for k, v in enumerate(before) if k != m))
        elif g == "fineage":
            out[g] = (a, i, tuple(v for k, v in enumerate(before) if k != m), tuple(x for k, x in enumerate(agesb) if k != m))
        elif g.startswith("with "):
            k = int(g[5:])
            out[g] = (a, i, x, before[k])
        elif g.startswith("since "):
            k = int(g[6:])
            out[g] = (a, i, x, agesb[k])
    return out


def base_prob(y, nsym):
    """A fixed distribution over the changes of a sense, for an outcome its cell never showed."""
    if y is None:
        return 0.5
    if type(y) is int:
        return 0.25 * 2.0 ** (-abs(y))
    return 0.5 / (nsym + 1)


class Act:
    """What one act gave sense m's test."""
    __slots__ = ("v", "a", "outs", "bet", "t", "ab")

    def __init__(self, v, a, outs, bet, t, ab=None):
        self.v, self.a, self.outs, self.bet, self.t, self.ab = v, a, outs, bet, t, ab


def by_role(roles, k, x):
    """A value of sense k written by its role."""
    if is_symbol(x):
        r = roles.get(k, {}).get(x)
        return None if r is None else ("r", r)
    return x


def change_by_role(roles, k, y):
    if isinstance(y, tuple) and len(y) == 2 and y[0] == "to":
        r = by_role(roles, k, y[1])
        return None if r is None else ("to", r)
    return ("same",) if y is None else y


class NullML:
    """The null's maximum likelihood of what it bet on, at one grain, kept as it grows."""

    def __init__(self):
        self.c, self.n, self.ll = collections.defaultdict(collections.Counter), collections.Counter(), 0.0

    @staticmethod
    def xlx(x):
        return x * math.log(x) if x > 0 else 0.0

    def add(self, key, y):
        c, n = self.c[key], self.n[key]
        self.ll += self.xlx(c[y] + 1) - self.xlx(c[y]) - (self.xlx(n + 1) - self.xlx(n))
        c[y] += 1
        self.n[key] = n + 1


class Predictor:
    """The alternative of one grouping G."""

    def __init__(self, G, beta, grains_of, null=None, null_grain="withany", book=None, select="class"):
        self.cls = {}
        for c, members in enumerate(G):
            for v in members:
                self.cls[v] = c
        self.k = len(G)
        self.beta, self.grains_of, self.book = beta, grains_of, book
        self.n = collections.defaultdict(collections.Counter)
        self.tot = collections.Counter()
        self.logw = {}
        self.lnq = 0.0
        self.bets = 0
        self.null, self.null_grain, self.select = null, null_grain, select
        self.select_min = SELECT_MIN * LN10
        self.blogw = {}
        self.at = collections.defaultdict(set)
        self.ver = collections.Counter()
        self._split = {}

    def split_saving(self, key):
        """In natural log, how much shorter its past changes at an own key are told with a code for each of its
        classes than with one for all."""
        got = self._split.get(key)
        if got is not None and got[0] == self.ver[key]:
            return got[1]
        s = -math.inf
        cs = self.at.get(key)
        if cs and len(cs) >= 2:
            pooled = self.n[("ownp", -1, key)]
            K = len(pooled)
            if K >= 2:
                s = kt_len(pooled, K) - sum(kt_len(self.n[("own", c, key)], K) for c in cs)
        self._split[key] = (self.ver[key], s)
        return s

    def choose(self, ob, c):
        """The sense it bets on at this act."""
        best = None
        kb = self.book.assigned.get(c) if self.book is not None else None
        for i, (keys, y, bp) in ob.outs.items():
            key = keys["own"]
            sv = self.split_saving(key)
            if not sv > self.select_min:
                if kb is not None and ob.ab:
                    got = self.book.apart(ob.ab[i][0], kb)
                    if got is not None and got[0] > self.select_min:
                        score = (got[1], got[0], -i)
                        if best is None or score > best[0]:
                            best = (score, i)
                continue
            pooled = self.n[("ownp", -1, key)]
            N, K = self.tot[("ownp", -1, key)], len(pooled)
            mine, nv = self.n[("own", c, key)], self.tot[("own", c, key)]
            s = 0.0
            if nv:
                for yy, k in pooled.items():
                    pp = (k + 0.5) / (N + K / 2)
                    pv = (mine.get(yy, 0) + self.beta * pp) / (nv + self.beta)
                    s += pv * math.log(pv / pp)
            score = (s, sv / max(1, N), -i)
            if best is None or score > best[0]:
                best = (score, i)
        return None if best is None else best[1]

    def class_of(self, v):
        c = self.cls.get(v)
        if c is None:
            c = self.cls[v] = self.k
            self.k += 1
        return c

    def lp(self, lvl, c, key, y, below):
        n = self.tot[(lvl, c, key)]
        if n == 0:
            return below
        return (self.n[(lvl, c, key)][y] + self.beta * below) / (n + self.beta)

    def per_grain(self, c, a, i, keys, y, bp, ab=None):
        """Its odds of change y of sense i at act a for class c, at each grain."""
        cell = (a, i)
        ko = keys["own"]
        p_pc = self.lp("pc", -1, cell, y, bp)
        p_pool = self.lp("ownp", -1, ko, y, p_pc)
        p_cc = self.lp("cc", c, cell, y, p_pc)
        parent = 0.5 * (p_pool + p_cc)
        b = self.book.assigned.get(c) if self.book is not None else None
        comps = None
        pb = self.book.prob(b, ab, "own", parent) if b is not None and ab is not None else None
        if pb is None:
            p_own = self.lp("own", c, ko, y, parent)
            return {g: (p_own if g == "own" else self.lp(g, c, keys[g], y, p_own)) for g in self.grains_of(cell)}, None
        bw = self.bweights(c, cell)
        top = max(bw.values())
        ws = {s: math.exp(w - top) for s, w in bw.items()}
        z = sum(ws.values())

        def booked(lvl, key, p_book):
            n, k = self.tot[(lvl, c, key)], self.n[(lvl, c, key)][y]
            got = {s: (k + s * p_book) / (n + s) for s in BOOK_STRENGTHS}
            return got, sum(ws[s] * got[s] for s in got) / z
        comps, p_own = booked("own", ko, pb)
        out = {}
        for g in self.grains_of(cell):
            if g == "own":
                out[g] = p_own
                continue
            pg = self.book.prob(b, ab, g, pb)
            out[g] = booked(g, keys[g], pg)[1] if pg is not None else self.lp(g, c, keys[g], y, p_own)
        return out, comps

    def bweights(self, c, cell):
        lw = self.blogw.get((c, cell))
        if lw is None:
            lw = self.blogw[(c, cell)] = {s: -math.log(len(BOOK_STRENGTHS)) for s in BOOK_STRENGTHS}
        return lw

    def weights(self, cell, grains):
        lw = self.logw.get(cell)
        if lw is None:
            lw = self.logw[cell] = {g: -math.log(len(grains)) for g in grains}
        return lw

    def mix(self, lw, per):
        top = max(lw.values())
        z = sum(math.exp(w - top) for w in lw.values())
        return sum(math.exp(lw[g] - top) * per[g] for g in per) / z

    def odds(self, ob, i):
        """Its odds, now, of the change sense i makes at this act."""
        c = self.class_of(ob.v)
        keys, y, bp = ob.outs[i]
        per, _ = self.per_grain(c, ob.a, i, keys, y, bp, ob.ab.get(i) if ob.ab else None)
        return self.mix(self.weights((ob.a, i), per), per)

    def add(self, ob):
        """One act: first the bet."""
        c = self.class_of(ob.v)
        bet = self.choose(ob, c) if self.select == "class" else ob.bet
        if bet is not None:
            q = self.odds(ob, bet)
            self.lnq += math.log(q)
            self.bets += 1
            if self.null is not None:
                keys, y, _ = ob.outs[bet]
                if isinstance(self.null, UnionML):
                    self.null.add((ob.a, bet), keys, y)
                else:
                    self.null.add(keys[self.null_grain], y)
        for i, (keys, y, bp) in ob.outs.items():
            ko = keys["own"]
            cell = (ob.a, i)
            per, comps = self.per_grain(c, ob.a, i, keys, y, bp, ob.ab.get(i) if ob.ab else None)
            lw = self.weights(cell, per)
            for g, pg in per.items():
                lw[g] += math.log(pg)
            top = max(lw.values())
            for g in lw:
                lw[g] -= top
            if comps is not None:
                bw = self.bweights(c, cell)
                for s, ps in comps.items():
                    bw[s] += math.log(ps)
                top = max(bw.values())
                for s in bw:
                    bw[s] -= top
            self.at[ko].add(c)
            self.ver[ko] += 1
            for lvl, cc, key in (("pc", -1, cell), ("cc", c, cell), ("own", c, ko), ("ownp", -1, ko)):
                self.n[(lvl, cc, key)][y] += 1
                self.tot[(lvl, cc, key)] += 1
            for g in per:
                if g != "own":
                    self.n[(g, c, keys[g])][y] += 1
                    self.tot[(g, c, keys[g])] += 1


def canon(G):
    """A grouping as a canonical tuple of sorted tuples."""
    return tuple(sorted((tuple(sorted(g, key=repr)) for g in G if g), key=repr))


def is_book_key(key):
    """A grouping read by a type book."""
    return isinstance(key, tuple) and len(key) == 3 and key[0] == "book"


def book_key(G, kinds):
    """The key of a grouping G read by a type book, kinds."""
    cg = canon(G)
    return ("book", cg, tuple(kinds.get(g[0], -1) for g in cg))


class Proxy:
    """A count-only score of a grouping."""

    def __init__(self, test):
        self.T = test

    def tables(self, values):
        """(cell, grain) -> key -> {symbol."""
        out = collections.defaultdict(lambda: collections.defaultdict(dict))
        kinds = collections.defaultdict(set)
        for (cell, g), per in self.T.persym.items():
            for key, bys in per.items():
                for v, cnt in bys.items():
                    if v in values:
                        out[(cell, g)][key][v] = cnt
                        kinds[cell].update(cnt)
        return out, kinds

    def score(self, G, tabs, kinds):
        by_cell = collections.defaultdict(dict)
        for (cell, g), per in tabs.items():
            K = len(kinds[cell])
            s = 0.0
            for key, bys in per.items():
                for members in G:
                    cnt = collections.Counter()
                    for v in members:
                        x = bys.get(v)
                        if x:
                            cnt.update(x)
                    if cnt:
                        s -= kt_len(cnt, K)
            by_cell[cell][g] = s
        return sum(max(d.values()) for d in by_cell.values()) + crp_log_prior([len(g) for g in G])

    def greedy(self, values):
        tabs, kinds = self.tables(set(values))
        G = [[v] for v in values]
        best = self.score(G, tabs, kinds)
        while len(G) > 1:
            top = None
            for x in range(len(G)):
                for y in range(x + 1, len(G)):
                    H = [g for k, g in enumerate(G) if k not in (x, y)] + [G[x] + G[y]]
                    s = self.score(H, tabs, kinds)
                    if top is None or s > top[0] + 1e-9:
                        top = (s, H)
            if top is None or top[0] <= best + 1e-9:
                break
            best, G = top
        moved = True
        while moved:
            moved = False
            for v in values:
                src = next(k for k, g in enumerate(G) if v in g)
                for dst in list(range(len(G))) + [None]:
                    if dst == src:
                        continue
                    H = [list(g) for g in G]
                    H[src].remove(v)
                    if dst is None:
                        H.append([v])
                    else:
                        H[dst].append(v)
                    H = [g for g in H if g]
                    s = self.score(H, tabs, kinds)
                    if s > best + 1e-9:
                        best, G, moved = s, H, True
                        break
                if moved:
                    break
        return G, best


def partitions(items):
    """Every set partition of items."""
    items = list(items)
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for p in partitions(rest):
        yield [[first]] + p
        for k in range(len(p)):
            yield p[:k] + [[first] + p[k]] + p[k + 1:]


def rgs_all(n):
    """Every set partition of n things as a restricted growth string."""
    out, a = [], [0] * n

    def rec(j, top):
        if j == n:
            out.append(tuple(a))
            return
        for c in range(top + 2):
            a[j] = c
            rec(j + 1, max(top, c))
    if n:
        rec(1, 0) if n > 1 else out.append((0,))
    return out


class SubsetScores:
    """The count-only score of every grouping of up to a dozen symbols, exactly."""

    def __init__(self, test, values):
        self.values = list(values)
        n = len(self.values)
        idx = {v: j for j, v in enumerate(self.values)}
        self.cg = []
        self.cells = []
        rows = collections.defaultdict(list)
        kinds = collections.defaultdict(set)
        for (cell, g), per in test.persym.items():
            for key, bys in per.items():
                for v, cnt in bys.items():
                    if v in idx:
                        kinds[cell].update(cnt)
        for (cell, g), per in sorted(test.persym.items(), key=lambda kv: repr(kv[0])):
            if len(kinds[cell]) < 2:
                continue
            for key, bys in per.items():
                got = [(idx[v], cnt) for v, cnt in bys.items() if v in idx and cnt]
                if got:
                    rows[(cell, g)].append(got)
        self.T = {}
        lg = {}

        def lgam(x):
            r = lg.get(x)
            if r is None:
                r = lg[x] = math.lgamma(x)
            return r
        for ci, (cg, keys) in enumerate(sorted(rows.items(), key=lambda kv: repr(kv[0]))):
            self.cg.append(cg)
            outs = sorted(kinds[cg[0]], key=repr)
            at = {y: k for k, y in enumerate(outs)}
            K = max(2, len(outs))
            acc = [0.0] * (1 << n)
            c0 = lgam(K / 2) - K * lgam(0.5)
            for got in keys:
                vec = [None] * n
                for j, c in got:
                    row = [0] * len(outs)
                    for y, k in c.items():
                        row[at[y]] = k
                    vec[j] = row
                sums = [None] * (1 << n)
                sums[0] = [0] * len(outs)
                for mask in range(1, 1 << n):
                    low = mask & -mask
                    j = low.bit_length() - 1
                    prev = sums[mask ^ low]
                    sums[mask] = prev if vec[j] is None else [a + b for a, b in zip(prev, vec[j])]
                    tot = sum(sums[mask])
                    if tot:
                        acc[mask] += c0 - lgam(tot + K / 2) + sum(lgam(x + 0.5) for x in sums[mask])
            for mask in range(1, 1 << n):
                self.T[(mask, ci)] = acc[mask]
        self.by_cell = collections.defaultdict(list)
        for ci, (cell, g) in enumerate(self.cg):
            self.by_cell[cell].append(ci)

    def score_masks(self, masks):
        tot = 0.0
        for cell, cis in self.by_cell.items():
            tot += max(sum(self.T[(mk, ci)] for mk in masks) for ci in cis)
        sizes = [bin(mk).count("1") for mk in masks]
        return tot + crp_log_prior(sizes)

    def best(self, k=3):
        n = len(self.values)
        scored = []
        for r in rgs_all(n):
            masks = [0] * (max(r) + 1)
            for j, c in enumerate(r):
                masks[c] |= 1 << j
            scored.append((self.score_masks(masks), masks))
        scored.sort(key=lambda x: (-x[0], x[1]))
        out = []
        for s, masks in scored[:k]:
            out.append(([[self.values[j] for j in range(n) if mk >> j & 1] for mk in masks], s))
        return out


class ConceptTest:
    """The e-process of one symbol sense m."""

    def __init__(self, m, n, null_grain="withany", beta=1.0, evidence=6.0, book=None, since=None, select="class"):
        self.m, self.n, self.null_grain, self.beta, self.evidence = m, n, null_grain, beta, evidence
        self.since = (null_grain == "fineage") if since is None else since
        self.fine = null_grain in ("fine", "fineage", "own")
        self.select = select
        self.acts = []
        self.nsym = collections.defaultdict(set)
        self.null = self.new_null()
        self.tracked = {}
        self.parked = {}
        self.own = collections.defaultdict(dd_counter)
        self.persym = collections.defaultdict(dd_dd_counter)
        self.seen = collections.Counter()
        self.best = None
        self.passed_at = None
        self.book = book
        self.roles = {}
        self._grains = {}
        self._split, self._ver = {}, collections.Counter()
        self.t = 0

    def grains_of(self, cell):
        g = self._grains.get(cell)
        if g is None:
            g = self._grains[cell] = (["own"] if self.null_grain == "ownonly" else
                                      grains_for(self.n, self.m, cell[1], self.since, self.fine))
        return g

    def null_grains(self, cell):
        """The grains of the union null in a cell."""
        return [g for g in self.grains_of(cell) if g.startswith("with ") or g.startswith("since ")] or ["own"]

    def new_null(self):
        return UnionML(self.null_grains) if self.null_grain == "withany" else NullML()

    def new_predictor(self, key):
        ng = "own" if self.null_grain == "ownonly" else self.null_grain
        if is_book_key(key):
            _, G, A = key
            view = self.book.view({c: b for c, b in enumerate(A) if b >= 0})
            return Predictor(G, self.beta, self.grains_of, null=self.new_null(), null_grain=ng,
                             book=view, select=self.select)
        return Predictor(key, self.beta, self.grains_of, null=self.new_null(), null_grain=ng,
                         book=None, select=self.select)

    def split_saving(self, key):
        """In digits, how much shorter its past changes at a key are told with a code for each symbol than with
        one for all."""
        got = self._split.get(key)
        if got is not None and got[0] == self._ver[key]:
            return got[1]
        per = self.own.get(key)
        s = -math.inf
        if per and len(per) >= 2:
            pooled = collections.Counter()
            for c in per.values():
                pooled.update(c)
            K = len(pooled)
            if K >= 2:
                s = (kt_len(pooled, K) - sum(kt_len(c, K) for c in per.values())) / LN10
        self._split[key] = (self._ver[key], s)
        return s

    def choose(self, v, before, a):
        """The sense it bets on."""
        best = None
        for i in range(self.n):
            if i == self.m:
                continue
            key = (a, i, before[i])
            sv = self.split_saving(key)
            if not sv > 0:
                continue
            per = self.own[key]
            pooled = collections.Counter()
            for c in per.values():
                pooled.update(c)
            N, K = sum(pooled.values()), len(pooled)
            mine = per.get(v)
            s = 0.0
            if mine:
                nv = sum(mine.values())
                for y, k in pooled.items():
                    pp = (k + 0.5) / (N + K / 2)
                    pv = (mine.get(y, 0) + self.beta * pp) / (nv + self.beta)
                    s += pv * math.log10(pv / pp)
            score = (s, sv / max(1, N))
            if best is None or score > best[0]:
                best = (score, i)
        return None if best is None else best[1]

    def note_roles(self, values):
        for k, x in enumerate(values):
            if is_symbol(x):
                r = self.roles.setdefault(k, {})
                if x not in r:
                    r[x] = len(r)

    def see(self, before, a, after, agesb):
        """One act (before it, the act, after it."""
        self.t += 1
        m = self.m
        v = before[m]
        ob = None
        self.note_roles(before)
        if is_symbol(v) and after[m] == v:
            outs, ab = {}, {}
            for i in range(self.n):
                if i != m:
                    gr = self.grains_of((a, i))
                    extra = [self.null_grain] if self.null_grain not in gr and self.null_grain != "withany" else []
                    keys = keys_at(gr + extra, m, i, before, a, agesb)
                    y = change_of(before[i], after[i])
                    outs[i] = (keys, y, base_prob(y, len(self.nsym[i])))
                    ab[i] = ((a, i, by_role(self.roles, i, before[i])), change_by_role(self.roles, i, y),
                             {k: by_role(self.roles, k, before[k]) for k in range(self.n) if k not in (m, i)})
            bet = self.choose(v, before, a) if self.select == "symbol" else None
            ob = Act(v, a, outs, bet, self.t, ab)
            self.acts.append(ob)
            for P in self.tracked.values():
                P.add(ob)
            for i, (keys, y, _) in outs.items():
                self.own[keys["own"]][v][y] += 1
                self._ver[keys["own"]] += 1
                for g in self.grains_of((a, i)):
                    self.persym[((a, i), g)][keys[g]][v][y] += 1
            self.seen[v] += 1
        for k, x in enumerate(before):
            if is_symbol(x):
                self.nsym[k].add(x)
        self.note_roles(after)
        return ob

    def bound(self, key):
        """log10 of its weight in the mixture times M_G(t), for a grouping it follows."""
        P = self.tracked[key]
        G = key[1] if is_book_key(key) else key
        sizes = [len(g) for g in G] + [1] * (P.k - len(G))
        prior = crp_log_prior(sizes)
        if self.book is not None:
            prior -= math.log(2)
            if is_book_key(key):
                prior -= len(sizes) * math.log(len(self.book.classes) + 1)
        return (prior + P.lnq - P.null.ll) / LN10

    def track(self, G):
        """Follow a grouping: replayed from the start of what it saw."""
        key = G if is_book_key(G) else canon(G)
        if key in self.tracked or not key:
            return key
        got = self.parked.pop(key, None)
        P, done = got if got is not None else (self.new_predictor(key), 0)
        for ob in self.acts[done:]:
            P.add(ob)
        self.tracked[key] = P
        return key

    def park(self, key, cap=64):
        """Set a grouping aside."""
        P = self.tracked.pop(key)
        self.parked[key] = (P, len(self.acts))
        while len(self.parked) > cap:
            self.parked.pop(next(iter(self.parked)))

    def book_for(self, key):
        return None

    def values(self, cap=12):
        return sorted(self.seen, key=lambda v: (-self.seen[v], repr(v)))[:cap]

    def search(self, exhaustive=0):
        vals = self.values()
        if len(vals) < 2:
            return []
        if exhaustive and len(vals) <= exhaustive:
            return [G for G, _ in SubsetScores(self, vals).best(3)]
        G, _ = Proxy(self).greedy(vals)
        return [G]

    def judge(self, exhaustive=0, extra=(), search=True):
        for G in (list(self.search(exhaustive)) if search else []) + list(extra):
            self.track(G)
        best = None
        for key in self.tracked:
            b = self.bound(key)
            if best is None or b > best[0] + 1e-12 or (abs(b - best[0]) <= 1e-12 and repr(key) < repr(best[1])):
                best = (b, key)
        self.best = None if best is None else (best[0], best[1], self.t)
        if best is not None and best[0] >= self.evidence and len(best[1]) >= 2 and self.passed_at is None:
            self.passed_at = self.t
        return self.best

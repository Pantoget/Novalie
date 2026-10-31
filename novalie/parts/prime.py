# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie: machines it was never given, that become parts of its own alphabet."""
import collections
import itertools
import math
import os
import sys
import time

NEW_AT_MOST = 0.02
LETTERS = "abcdefgh"


# -- the fewest states that explain what it saw ----------------------------------------------------------
def learn(stream, first, m, most=12, budget=3_000_000, seconds=30.0, tried=0):
    """The fewest hidden states that explain every symbol it saw."""
    acts = [a for a, _ in stream]
    ys = [tuple(first)] + [tuple(o) for _, o in stream]
    half = len(acts) // 2
    rate = [collections.Counter(y[j] for y in ys) for j in range(len(ys[0]))]
    gains = {}

    def gain(o):
        g = gains.get(o)
        if g is None:
            g = gains[o] = sum(-math.log10(rate[j][x] / len(ys)) for j, x in enumerate(o))
        return g

    allowed_new = max(2, int(NEW_AT_MOST * (len(acts) - half)))
    budget += tried
    fit, tried, wait = by_window(acts, ys, m, gain, half, allowed_new, most, tried)
    if fit is not None or wait:
        return fit, tried
    apart = moments_apart(acts, ys)
    deadline = time.time() + seconds
    for n in range(max(len(set(ys)), len(surely_apart(apart, ys))), most + 1):
        fit, tried, cut = _fit(acts, ys, m, n, apart, gain, half, allowed_new, budget, deadline, tried)
        if fit is not None or cut:
            return fit, tried
    return None, tried


def by_window(acts, ys, m, gain, half, allowed_new, most, tried, longest=6):
    """A machine whose sensors show only what its last few presses were."""
    T = len(acts)
    for k in range(1, longest + 1):
        if 3 * m ** k > T:
            return None, tried, False
        tried += 1
        shows, ok = {}, True
        for t in range(k - 1, T):
            if shows.setdefault(tuple(acts[t - k + 1:t + 1]), ys[t + 1]) != ys[t + 1]:
                ok = False
                break
        if not ok:
            continue
        if len(shows) < m ** k:
            return None, tried, True
        windows = sorted(shows)
        block = {w: shows[w] for w in windows}
        while True:
            sig = {w: (block[w],) + tuple(block[w[1:] + (a,)] for a in range(m)) for w in windows}
            ids = {}
            new = {w: ids.setdefault(sig[w], len(ids)) for w in windows}
            if len(ids) == len(set(block.values())):
                break
            block = new
        order = {}
        for t in range(k - 1, T):
            order.setdefault(block[tuple(acts[t - k + 1:t + 1])], len(order))
        for w in windows:
            order.setdefault(block[w], len(order))
        n = len(order)
        if n > most:
            return None, tried, False
        state = {w: order[block[w]] for w in windows}
        table = [[-1] * n for _ in range(m)]
        out = [None] * n
        for w in windows:
            out[state[w]] = shows[w]
            for a in range(m):
                table[a][state[w]] = state[w[1:] + (a,)]
        known, ev, late = set(), 0.0, 0
        for t in range(k - 1, T):
            w = tuple(acts[t - k + 1:t + 1])
            if w in known:
                ev += gain(ys[t + 1])
            else:
                known.add(w)
                late += t >= half
        if late > allowed_new:
            return None, tried, True
        return (table, out, n, state[tuple(acts[T - k:])], ev, late), tried, False
    return None, tried, False


def moments_apart(acts, ys):
    """For each moment, the moments that were surely in another state."""
    T = len(acts)
    full = (1 << (T + 1)) - 1
    showed, pressed = collections.defaultdict(int), collections.defaultdict(int)
    for t, y in enumerate(ys):
        showed[y] |= 1 << t
    for t, a in enumerate(acts):
        pressed[a] |= 1 << t
    apart = [0] * (T + 1)
    apart[T] = full & ~showed[ys[T]]
    for t in range(T - 1, -1, -1):
        apart[t] = (full & ~showed[ys[t]]) | (pressed[acts[t]] & (apart[t + 1] >> 1))
    return apart


def surely_apart(apart, ys):
    """Moments each surely in a state of its own."""
    chosen = []
    groups = collections.defaultdict(list)
    for t, y in enumerate(ys):
        groups[y].append(t)
    for ts in groups.values():
        ts = ts[:300]
        best = []
        for seed in ts:
            got = [seed]
            for t in ts:
                if t != seed and all(apart[t] >> c & 1 for c in got):
                    got.append(t)
            if len(got) > len(best):
                best = got
        chosen += best
    return chosen


def _fit(acts, ys, m, most, apart, gain, half, allowed_new, budget, deadline, tried):
    """One machine of at most `most` states that agrees with everything."""
    T = len(acts)
    parent = list(range(T + 1))
    size = [1] * (T + 1)
    mem = [1 << t for t in range(T + 1)]
    away = list(apart)
    nxt = [[-1] * m for _ in range(T + 1)]
    for t in range(T):
        nxt[t][acts[t]] = t + 1
    red = [False] * (T + 1)
    log = []

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def merge(x, y):
        """x and y one state, and all that follows from it."""
        joined, queue = 0, [(x, y)]
        while queue:
            x, y = queue.pop()
            rx, ry = find(x), find(y)
            if rx == ry:
                continue
            if mem[rx] & away[ry]:
                return -1
            if size[rx] < size[ry]:
                rx, ry = ry, rx
            log.append((ry, rx, mem[rx], away[rx], size[rx], nxt[rx][:], red[rx]))
            parent[ry] = rx
            size[rx] += size[ry]
            mem[rx] |= mem[ry]
            away[rx] |= away[ry]
            red[rx] = red[rx] or red[ry]
            nr, ny = nxt[rx], nxt[ry]
            for a in range(m):
                if ny[a] >= 0:
                    if nr[a] >= 0:
                        queue.append((nr[a], ny[a]))
                    else:
                        nr[a] = ny[a]
            joined += 1
        return joined

    def undo(mark):
        while len(log) > mark:
            entry = log.pop()
            if entry[0] == "red":
                red[entry[1]] = False
                continue
            ry, rx, mr, ar, sr, nr, rr = entry
            parent[ry] = ry
            mem[rx], away[rx], size[rx], nxt[rx], red[rx] = mr, ar, sr, nr, rr

    choices, made, t = [], [], 0
    while True:
        while t <= T and red[find(t)]:
            t += 1
        if t > T:
            break
        roots = list(dict.fromkeys(find(r) for r in made))
        blue, options = find(t), []
        for r in roots:
            if mem[r] & away[blue]:
                continue
            mark = len(log)
            tried += 1
            joined = merge(r, blue)
            undo(mark)
            if joined >= 0:
                options.append((-joined, r))
        options = [r for _, r in sorted(options)] + ([None] if len(roots) < most else [])
        if tried > budget or time.time() > deadline:
            return None, tried, True
        choices.append([t, options, -1, len(log), len(made)])
        while True:
            if not choices:
                return None, tried, False
            ch = choices[-1]
            undo(ch[3])
            del made[ch[4]:]
            ch[2] += 1
            if ch[2] >= len(ch[1]):
                choices.pop()
                continue
            r = ch[1][ch[2]]
            tried += 1
            if r is None:
                root = find(ch[0])
                log.append(("red", root))
                red[root] = True
                made.append(root)
                break
            if merge(r, find(ch[0])) >= 0:
                break
        t = ch[0]
    states = {}
    for u in range(T + 1):
        states.setdefault(find(u), len(states))
    n = len(states)
    table = [[-1] * n for _ in range(m)]
    out = [None] * n
    for root, q in states.items():
        out[q] = ys[(mem[root] & -mem[root]).bit_length() - 1]
        for a in range(m):
            if nxt[root][a] >= 0:
                table[a][q] = states[find(nxt[root][a])]
    known, ev, late, s = set(), 0.0, 0, states[find(0)]
    for u, a in enumerate(acts):
        if (a, s) in known:
            ev += gain(ys[u + 1])
        else:
            known.add((a, s))
            late += u >= half
        s = table[a][s]
    if late > allowed_new:
        return None, tried, False
    return (table, out, n, s, ev, late), tried, False


def machine_of(fit, m):
    """Its learned machine as parts it can use."""
    nxt, out, n, state, ev, late = fit
    fs = [tuple(x if x >= 0 else None for x in nxt[a][:n]) for a in range(m)]
    gens, assign = [], []
    for a in range(m):
        f = fs[a]
        if all(x is None for x in f):
            assign.append(None)
        elif all(x in (i, None) for i, x in enumerate(f)):
            assign.append("")
        else:
            if f not in gens:
                gens.append(f)
            assign.append(LETTERS[gens.index(f)])
    return {"n": n, "gens": gens, "assign": assign, "out": out[:n], "state": state, "evidence": ev, "late": late,
            "complete": all(x is not None for f in gens for x in f)}


# -- what its machine is: the laws of its presses ----------------------------------------------------------
def then(f, g):
    """f, then g."""
    return tuple(None if x is None else g[x] for x in f)


def monoid(gens, n, most=3000):
    """Every different thing its presses can do."""
    one = tuple(range(n))
    word = {one: ""}
    order = [one]
    laws = []
    full = True
    i = 0
    while i < len(order):
        f = order[i]
        w = word[f]
        for k, g in enumerate(gens):
            h = then(f, g)
            wg = w + LETTERS[k]
            if h in word:
                if (wg[1:] in reduced(word)) and word[h] != wg:
                    laws.append((wg, word[h]))
            elif len(order) >= most:
                full = False
            else:
                word[h] = wg
                order.append(h)
        i += 1
    return order, word, laws, full


_REDUCED = {}


def reduced(word):
    """The set of shortest sequences."""
    key = id(word)
    got = _REDUCED.get(key)
    if got is None or got[0] != len(word):
        got = _REDUCED[key] = (len(word), set(word.values()))
    return got[1]


def nature_of(gens, n, most=3000):
    """What its machine is, from the laws of its presses."""
    order, word, laws, full = monoid(gens, n, most)
    perm = all(None not in g and len(set(g)) == n for g in gens)
    commute = all(then(f, g) == then(g, f) for f, g in itertools.combinations(gens, 2))
    powers = []
    for k, g in enumerate(gens):
        seen, p, j = {}, tuple(range(n)), 0
        while p not in seen and j <= n * n + 2:
            seen[p] = j
            p, j = then(p, g), j + 1
        start = seen.get(p, j)
        powers.append({"letter": LETTERS[k], "from": start, "period": j - start})
    sync = min((w for f, w in word.items() if len({x for x in f if x is not None}) == 1 and None not in f),
               key=lambda w: (len(w), w), default=None)
    laws.sort(key=lambda lw: (len(lw[0]) + len(lw[1]), lw))
    return {"states": n, "things": len(order), "all": full, "group": perm, "commute": commute,
            "powers": powers, "sync": sync, "laws": laws[:12], "laws_count": len(laws)}


def canonical(gens, n):
    """The same machine whatever names its states and its generators were given."""
    best = None
    for perm in itertools.permutations(range(len(gens))):
        gs = [gens[i] for i in perm]
        for root in range(n):
            num, queue, enc = {root: 0}, [root], []
            for q in queue:
                for g in gs:
                    x = g[q]
                    if x is None:
                        enc.append(-1)
                        continue
                    if x not in num:
                        num[x] = len(num)
                        queue.append(x)
                    enc.append(num[x])
            if len(num) < n:
                continue
            key = (n, len(gs), tuple(enc))
            if best is None or key < best:
                best = key
    return best


def old_part(gens, n):
    """Is its machine one of the parts it was given, in disguise."""
    me = canonical(gens, n)
    if me is None:
        return None
    turn = [tuple((i + d) % n for i in range(n)) for d in (1, -1)]
    walls = [tuple(min(max(i + d, 0), n - 1) for i in range(n)) for d in (1, -1)]
    for name, fs in ((f"a cycle of {n}", turn), (f"a line of {n} with walls", walls)):
        for k in (1, 2):
            if canonical(list(dict.fromkeys(fs[:k])), n) == me:
                return name
    return None


def label_for(known):
    """A name of its own for a new machine."""
    i = 0
    while True:
        name, j = "", i
        while True:
            name = chr(65 + j % 26) + name
            j = j // 26 - 1
            if j < 0:
                break
        if name not in known:
            return name
        i += 1



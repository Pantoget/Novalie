# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's universal reader."""
import base64
import math

from . import senses as senses

np = senses.np
SAMPLE = 120_000
CHUNK_SAMPLE = 60_000
EVIDENCE = 6.0


# -- evidence -------------------------------------------------------------------------------------------
def tail_digits(n, k, p):
    """How unlikely, in powers of ten, k or more of n by coincidence when each has chance p."""
    if n <= 0 or k <= 0 or p >= 1:
        return 0.0
    p = max(p, 1e-12)
    if k <= n * p:
        return 0.0
    if n > 400:
        a = k / n
        d = a * math.log(a / p) + ((1 - a) * math.log((1 - a) / (1 - p)) if a < 1 else 0.0)
        return n * d / math.log(10)
    lp, lq, top = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    logs = [top - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq for i in range(k, n + 1)]
    m = max(logs)
    return -(m + math.log(sum(math.exp(x - m) for x in logs))) / math.log(10)


def z_digits(r, n):
    """How unlikely, in powers of ten, a correlation r over n independent samples by coincidence."""
    if n <= 4 or r <= 0:
        return 0.0
    return normal_digits(math.atanh(min(r, 0.9999)) * math.sqrt(n - 3))


def machine_like(col, L):
    """How much a column is a cycle machine itself, not a thing that moves with one."""
    if len(col) < 3 or not np.all(np.isfinite(col)):
        return 0.0
    vals, codes = np.unique(col, return_inverse=True)
    K = len(vals)
    if K > L + 1 or 2 * K < L:
        return 0.0
    pairs = np.bincount(codes[:-1] * K + codes[1:], minlength=K * K).reshape(K, K)
    return float(pairs.max(axis=1).sum()) / (len(col) - 1)


def rise_digits(r, low, n):
    """How unlikely, in powers of ten, that a stream is more like itself after L steps."""
    r, low = min(r, 0.9999), min(max(low, -0.9999), 0.9999)
    if n <= 4 or not r > low:
        return 0.0
    return normal_digits((math.atanh(r) - math.atanh(low)) * math.sqrt((n - 3) / 2))


def normal_digits(z):
    """The chance of a normal deviate beyond z, in powers of ten."""
    if z <= 0:
        return 0.0
    if z < 30:
        return -math.log10(max(0.5 * math.erfc(z / math.sqrt(2)), 1e-300))
    return z * z / (2 * math.log(10)) + math.log10(z * math.sqrt(2 * math.pi))


# -- 1. how readable --------------------------------------------------------------------------------------
def _levels(sym, kind):
    """Symbols as small whole numbers."""
    x = np.asarray(sym)
    if x.dtype.kind == "f" or (kind == "values" and x.size and (x.max() - x.min()) > 255):
        lo, hi = np.percentile(x, 0.5), np.percentile(x, 99.5)
        if hi <= lo:
            return np.zeros(x.size, dtype=np.int64)
        return np.clip(((x - lo) / (hi - lo) * 255).astype(np.int64), 0, 255)
    return x.astype(np.int64)


def _cross_bits(tr, te, v, ctx_tr, ctx_te, alpha=2.0):
    """Bits per symbol on `te` when each is guessed from its context, learned on `tr`."""
    c0 = np.bincount(tr, minlength=v).astype(np.float64)
    p0 = (c0 + 0.5) / (c0.sum() + 0.5 * v)
    if ctx_tr is None:
        return float(-np.mean(np.log2(p0[te])))
    nctx = int(max(ctx_tr.max(), ctx_te.max())) + 1
    codes, counts = np.unique(ctx_tr * v + tr, return_counts=True)
    ctx = np.bincount(ctx_tr, minlength=nctx).astype(np.float64)
    q = ctx_te * v + te
    i = np.clip(np.searchsorted(codes, q), 0, codes.size - 1)
    cab = np.where(codes[i] == q, counts[i], 0).astype(np.float64)
    p = (cab + alpha * p0[te]) / (ctx[ctx_te] + alpha)
    return float(-np.mean(np.log2(p)))


def readability(sym, kind):
    """(bits per symbol, redundancy)."""
    x = _levels(sym, kind)[:SAMPLE]
    if x.size < 256:
        return 8.0, 0.0
    _, x = np.unique(x, return_inverse=True)
    v = int(x.max()) + 1
    if v < 2:
        return 0.0, 1.0
    half = x.size // 2
    best = _cross_bits(x[:half], x[half:], v, None, None)
    for lag in (1, 2, 3, 4):
        tr, te = x[lag:half], x[half + lag:]
        best = min(best, _cross_bits(tr, te, v, x[:half - lag], x[half:-lag]))
        if kind == "values":
            d = x[lag:] - x[:-lag] + v
            dh = d.size // 2
            best = min(best, _cross_bits(d[:dh], d[dh:], 2 * v + 1, None, None))
    hmax = math.log2(v)
    return best, (max(0.0, min(1.0, 1.0 - best / hmax)) if hmax > 0 else 1.0)


# -- 2. what repeats --------------------------------------------------------------------------------------
def autocorr(values, most=200_000):
    """Correlation of a stream with itself shifted by every step L = 0..most."""
    x = np.asarray(values, dtype=np.float64)[:1 << 19]
    n = x.size
    x = x - x.mean()
    var = float(np.mean(x * x))
    if n < 64 or var < 1e-12:
        return None
    m = 1 << int(math.ceil(math.log2(2 * n)))
    f = np.fft.rfft(x, m)
    r = np.fft.irfft(f * np.conj(f), m)[:min(most, n // 2) + 1]
    over = n - np.arange(r.size)
    return r / (over * var)


def shape(values):
    """The shape of a stream, found from what repeats."""
    r = autocorr(values)
    if r is None:
        return None
    n = len(values)
    out = {"element": 1, "row": None, "frame": None, "rhythms": []}
    if r.size > 25:
        best, score = 1, 0.0
        for a in range(2, 9):
            bumps = [r[k * a] - np.mean(r[k * a - a + 1:k * a]) for k in (1, 2, 3) if k * a < r.size]
            s = float(np.mean(bumps)) if bumps else 0.0
            if s > 0.03 and s > score + 0.01:
                best, score = a, s
        out["element"] = best
    a = out["element"]
    lo = 8 * a
    cs = np.concatenate([[0.0], np.cumsum(r)])
    if r.size > 2 * lo + 2:
        idx = np.arange(1, r.size - 1)
        peak = (r[1:-1] >= r[:-2]) & (r[1:-1] >= r[2:]) & (r[1:-1] > 0.25) & (idx >= lo) & (idx % a == 0) & (idx <= n // 3)
        cand = idx[peak]
        if cand.size:
            start = np.maximum(lo, cand // 2)
            stop = np.maximum(start + 1, cand - a + 1)
            base = (cs[stop] - cs[start]) / (stop - start)
            strong = cand[r[cand] - base >= 0.12].tolist()
            if strong:
                top = max(strong, key=lambda L: r[L])
                row = top
                for L in sorted(strong):
                    if top % L == 0 and r[L] >= 0.9 * r[top]:
                        row = L
                        break
                out["row"] = int(row)
    b = out["row"]
    if b and r.size > 8 * b:
        ks = np.arange(8, r.size // b)
        if ks.size:
            vals = r[ks * b]
            top = float(vals.max())
            for k in ks[vals >= 0.9 * top]:
                L = int(k) * b
                near = max(r[L - b], r[L + b] if L + b < r.size else -1.0)
                if r[L] > 0.3 and r[L] - near >= 0.05:
                    out["frame"] = L
                    break
    idx = np.arange(1, r.size - 1)
    peak = (r[1:-1] >= r[:-2]) & (r[1:-1] > r[2:]) & (r[1:-1] > 0.5) & (idx >= 2)
    first = idx[peak][:6]
    out["rhythms"] = [(int(L), float(r[L])) for L in first]
    return out


def lattice(g):
    """A repeating pattern in a grid."""
    g = np.asarray(g, dtype=np.float64)
    h, w = g.shape
    if h < 16 or w < 16:
        return None
    x = g - g.mean()
    var = float(np.mean(x * x))
    if var < 1e-6:
        return None
    f = np.fft.rfft2(x, s=(2 * h, 2 * w))
    c = np.fft.irfft2(f * np.conj(f), s=(2 * h, 2 * w))
    dy = np.arange(-h + 1, h)
    dx = np.arange(-w + 1, w)
    cc = np.roll(np.roll(c, h - 1, axis=0), w - 1, axis=1)[:2 * h - 1, :2 * w - 1]
    over = (h - np.abs(dy))[:, None] * (w - np.abs(dx))[None, :]
    rho = cc / (over * var)
    ok = over >= 0.3 * h * w
    rad = np.hypot(dy[:, None], dx[None, :])
    r0 = 2.0
    for rr in range(1, min(h, w) // 3):
        ring = (rad >= rr) & (rad < rr + 1) & ok
        if ring.any() and rho[ring].mean() < 0.5:
            r0 = float(rr)
            break
    mask = ok & (rad > r0) & ((dy[:, None] > 0) | ((dy[:, None] == 0) & (dx[None, :] > 0)))
    pad = np.pad(rho, 1, constant_values=-np.inf)
    nb = np.max(np.stack([pad[1 + i:pad.shape[0] - 1 + i, 1 + j:pad.shape[1] - 1 + j]
                          for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j]), axis=0)
    peak = mask & (rho >= nb) & (rho >= 0.5)
    ys, xs = np.nonzero(peak)
    if ys.size == 0:
        return None
    vecs = [(int(dx[j]), int(dy[i]), float(rho[i, j])) for i, j in zip(ys, xs)]
    top = max(v[2] for v in vecs)
    strong = sorted([v for v in vecs if v[2] >= 0.85 * top], key=lambda v: (v[0] ** 2 + v[1] ** 2))
    v1 = strong[0]
    v2 = None
    for v in sorted(vecs, key=lambda v: (v[0] ** 2 + v[1] ** 2)):
        cross = abs(v1[0] * v[1] - v1[1] * v[0])
        if v[2] >= 0.8 * top and cross >= 0.25 * math.hypot(*v1[:2]) * math.hypot(*v[:2]):
            v2 = v
            break
    neff = max(16.0, h * w / max(1.0, r0 * r0))

    def corr(u):
        i, j = u[1] + h - 1, u[0] + w - 1
        return float(rho[i, j]) if 0 <= i < 2 * h - 1 and 0 <= j < 2 * w - 1 and ok[i, j] else None

    if v2 is None:
        d = round(math.hypot(v1[0], v1[1]))
        return {"rank": 1, "basis": [v1[:2]], "windings": [d], "rho": round(v1[2], 3),
                "evidence": round(z_digits(v1[2], neff), 1), "tile": None, "defects": 0, "symmetry": []}
    b1, b2 = [v1[0], v1[1]], [v2[0], v2[1]]
    for _ in range(20):
        if b1[0] ** 2 + b1[1] ** 2 > b2[0] ** 2 + b2[1] ** 2:
            b1, b2 = b2, b1
        mu = round((b1[0] * b2[0] + b1[1] * b2[1]) / max(1, b1[0] ** 2 + b1[1] ** 2))
        if mu == 0:
            break
        b2 = [b2[0] - mu * b1[0], b2[1] - mu * b1[1]]
    checks = [corr(b1), corr(b2), corr((b1[0] + b2[0], b1[1] + b2[1])), corr((b1[0] - b2[0], b1[1] - b2[1]))]
    checks = [x for x in checks if x is not None]
    if len(checks) < 2 or min(checks) < 0.4:
        return None
    det = abs(b1[0] * b2[1] - b1[1] * b2[0])
    if det < 4:
        return None
    d1 = math.gcd(math.gcd(abs(b1[0]), abs(b1[1])), math.gcd(abs(b2[0]), abs(b2[1])))
    wind = [d for d in (d1, det // d1) if d > 1] or [det]
    m = np.array([[b1[0], b2[0]], [b1[1], b2[1]]], dtype=np.float64)
    inv = np.linalg.inv(m)
    yy, xx = np.mgrid[0:h, 0:w]
    uv = inv @ np.stack([xx.ravel(), yy.ravel()]).astype(np.float64)
    fu, fv = uv[0] % 1.0, uv[1] % 1.0
    n1, n2 = max(2, round(math.hypot(*b1))), max(2, round(math.hypot(*b2)))
    iu = np.minimum((fu * n1).astype(np.int64), n1 - 1)
    iv = np.minimum((fv * n2).astype(np.int64), n2 - 1)
    cell = iv * n1 + iu
    sums = np.bincount(cell, weights=g.ravel(), minlength=n1 * n2)
    cnt = np.bincount(cell, minlength=n1 * n2)
    unit = sums / np.maximum(cnt, 1)
    resid = np.abs(g.ravel() - unit[cell]).reshape(h, w)
    med = float(np.median(resid))
    mad = float(np.median(np.abs(resid - med))) + 1e-6
    bad = resid > max(med + 8 * mad, 0.2 * math.sqrt(var) + med)
    blocks = 0
    if bad.any():
        k = max(4, min(h, w) // 32)
        hb, wb = h // k, w // k
        grid = bad[:hb * k, :wb * k].reshape(hb, k, wb, k).mean(axis=(1, 3)) > 0.15
        seen = np.zeros_like(grid)
        for i in range(hb):
            for j in range(wb):
                if grid[i, j] and not seen[i, j]:
                    blocks += 1
                    stack = [(i, j)]
                    seen[i, j] = True
                    while stack:
                        a, b = stack.pop()
                        for p, q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                            if 0 <= p < hb and 0 <= q < wb and grid[p, q] and not seen[p, q]:
                                seen[p, q] = True
                                stack.append((p, q))
    sym = []
    sq = g[:min(h, w), :min(h, w)]
    for name, t in (("turn2", np.rot90(sq, 2)), ("mirror", sq[:, ::-1]), ("flip", sq[::-1, :]),
                    ("turn4", np.rot90(sq, 1)), ("diagonal", sq.T)):
        if _match(sq, t) >= 0.7:
            sym.append(name)
    return {"rank": 2, "basis": [tuple(b1), tuple(b2)], "windings": wind, "rho": round(min(checks), 3),
            "evidence": round(z_digits(min(checks), neff), 1), "unit": unit.reshape(n2, n1),
            "defects": blocks, "broken": round(float(bad.mean()), 4), "symmetry": sym}


def _match(a, b):
    """Best correlation of a grid with another over every shift that keeps at least half of them overlapping."""
    a = a - a.mean()
    b = b - b.mean()
    var = float(np.sqrt(np.mean(a * a) * np.mean(b * b)))
    if var < 1e-9:
        return 0.0
    n = a.shape[0]
    f = np.fft.rfft2(a, s=(2 * n, 2 * n)) * np.conj(np.fft.rfft2(b, s=(2 * n, 2 * n)))
    c = np.roll(np.roll(np.fft.irfft2(f, s=(2 * n, 2 * n)), n - 1, axis=0), n - 1, axis=1)[:2 * n - 1, :2 * n - 1]
    d = np.abs(np.arange(-n + 1, n))
    over = (n - d)[:, None] * (n - d)[None, :]
    ok = over >= 0.5 * n * n
    return float(np.max(np.where(ok, c / (over * var), -1.0)))


# -- 3. what comes back together --------------------------------------------------------------------------
def chunks(sym, rounds=120):
    """Pieces that follow each other far more often than chance become one new piece, again and again."""
    raw = np.asarray(sym[:CHUNK_SAMPLE], dtype=np.int64)
    if raw.size < 128:
        return []
    values, s = np.unique(raw, return_inverse=True)
    s = s.astype(np.int64).ravel()
    made, seq = [], {}
    nxt = len(values)
    big = nxt + rounds + 1
    for _ in range(rounds):
        n = s.size
        if n < 64:
            break
        a, b = s[:-1], s[1:]
        codes, counts = np.unique(a * big + b, return_counts=True)
        uni, ucnt = np.unique(s, return_counts=True)
        fa = dict(zip(uni.tolist(), ucnt.tolist()))
        order = np.argsort(-counts)[:400]
        best, gain = None, 0.0
        for i in order:
            c = int(counts[i])
            if c < 4:
                break
            x, y = int(codes[i] // big), int(codes[i] % big)
            e = fa[x] * fa[y] / n
            lift = c / max(e, 1e-9)
            if lift < 3:
                continue
            g = c * math.log2(lift)
            if g > gain:
                ev = tail_digits(n - 1, c, (fa[x] / n) * (fa[y] / n))
                if ev >= EVIDENCE:
                    best, gain = (x, y, c, ev), g
        if best is None:
            break
        x, y, c, ev = best
        pos = np.nonzero((a == x) & (b == y))[0]
        keep, last = [], -2
        for p in pos.tolist():
            if p > last + 1:
                keep.append(p)
                last = p
        keep = np.asarray(keep, dtype=np.int64)
        s[keep] = nxt
        s = np.delete(s, keep + 1)
        seq[nxt] = seq.get(x, (x,)) + seq.get(y, (y,))
        made.append((tuple(int(values[i]) for i in seq[nxt]), len(keep), round(ev, 1)))
        nxt += 1
    return made


# -- reading anything ------------------------------------------------------------------------------------
def signature(data):
    """How a stream of bytes begins, and how random it looks."""
    head = data[:4].hex()
    sample = np.frombuffer(data[:65536], dtype=np.uint8)
    if sample.size == 0:
        return head + ":empty"
    p = np.bincount(sample, minlength=256) / sample.size
    ent = float(-np.sum(p[p > 0] * np.log2(p[p > 0])))
    return f"{head}:{int(ent)}"


def _score(out):
    """(score, redundancy, bits, symbols) of one way of reading."""
    sym = out["symbols"]
    if sym is None:
        sym = np.frombuffer(out["raw"][:SAMPLE * 8], dtype=np.uint8).astype(np.int64)
    if len(sym) < 256:
        return None
    bits, red = readability(sym, out["kind"])
    x = np.asarray(sym)
    wide = x.dtype.kind == "f" or (x.size and float(x.max()) - float(x.min()) > 255)
    held = len(sym) * (2 if wide else 1)
    score = red + 0.1 * math.log10(max(1.0, held / 1000)) + (0.03 if out["kind"] == "symbols" else 0.0)
    return score, red, bits, sym


class Reader:
    """What it has learned about reading."""

    def __init__(self):
        self.ways = {}
        self.pieces = {}
        self.types = {}
        self.open = {}
        self.read_count = 0

    def search(self, data, allow=(), budget=16, on_try=None):
        """Ways of opening the bytes, as."""
        sig = signature(data)
        tools = [(name, f) for name, f, needs in senses.TOOLS if not needs or name in allow]
        names = dict(tools)
        tried, spent = [], 0
        first = senses.as_bytes(data)[0]
        sc = _score(first)
        if sc:
            tried.append(([], first, sc))
        known = self.ways.get(sig)
        if known and known["chain"] and all(step in names for step in known["chain"]):
            b, ok, o = data, True, None
            for i, step in enumerate(known["chain"]):
                outs = names[step](b)
                spent += 1
                if not outs:
                    ok = False
                    break
                o = outs[0]
                if i < len(known["chain"]) - 1:
                    if o["raw"] is None:
                        ok = False
                        break
                    b = o["raw"]
            if ok and o is not None:
                s2 = _score(o)
                if on_try:
                    on_try(list(known["chain"]), round(s2[1], 3) if s2 else None)
                if s2:
                    extra = []
                    for also in (known.get("also"), known.get("table")):
                        if not also or also == known["chain"] or not all(step in names for step in also):
                            continue
                        b2, o2 = data, None
                        for i, step in enumerate(also):
                            outs = names[step](b2)
                            spent += 1
                            o2 = outs[0] if outs else None
                            if o2 is None or (i < len(also) - 1 and o2["raw"] is None):
                                o2 = None
                                break
                            b2 = o2["raw"]
                        s3 = _score(o2) if o2 is not None else None
                        if s3:
                            extra.append((list(also), o2, s3))
                    ranked = self._rank(tried + [(list(known["chain"]), o, s2)] + extra)
                    if ranked[0][0] == list(known["chain"]) and ranked[0][2][0] >= known["score"] - 0.05:
                        return sig, ranked, sc
        frontier = [([], data)]
        while frontier and spent < budget:
            chain, raw = frontier.pop(0)
            if len(chain) >= 3:
                continue
            for name, f in tools:
                if spent >= budget:
                    break
                if chain and name == chain[-1]:
                    continue
                outs = f(raw)
                spent += 1
                got = None
                for o in outs[:6]:
                    s2 = _score(o)
                    if s2:
                        tried.append((chain + [name], o, s2))
                        got = max(got or 0.0, round(s2[1], 3))
                    if o["raw"] is not None and o["kind"] == "values":
                        frontier.append((chain + [name], o["raw"]))
                if on_try:
                    on_try(chain + [name], got)
        return sig, self._rank(tried), sc

    def _rank(self, tried):
        """Most readable first, where a reading that shows structure counts for more."""
        tried.sort(key=lambda t: -t[2][0])
        ranked = []
        for i, (chain, o, sc) in enumerate(tried):
            bonus = 0.0
            if o.get("dims"):
                bonus += 0.1
            elif o["kind"] == "values" and i < 4:
                with np.errstate(all="ignore"):
                    shp = shape(sc[3])
                if shp and shp["row"]:
                    bonus += 0.08
            ranked.append((chain, o, (sc[0] + bonus,) + tuple(sc[1:])))
        return sorted(ranked, key=lambda t: -t[2][0])

    def read(self, data, allow=(), source="", on_try=None):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return self._read(data, allow, source, on_try)

    def _read(self, data, allow=(), source="", on_try=None):
        """Read any bytes. Returns what it found, for its memory and its page. Besides the most readable way, a
        reading of the other kind."""
        if not senses.available() or not data:
            return None
        self.read_count += 1
        sig, ranked, raw_score = self.search(data, allow, on_try=on_try)
        before = raw_score[1] if raw_score else 0.0
        best = ranked[0] if ranked else None
        if best is None or best[2][1] < 0.12:
            self.open[sig] = self.open.get(sig, 0) + 1
            return {"source": source, "signature": sig, "readable": False, "before": round(before, 3),
                    "chain": [], "size": len(data)}
        chain, out, (score, red, bits, sym) = best
        known = self.ways.get(sig)
        new_way = known is None or (known["chain"] != chain and score > known["score"] + 0.02)
        if new_way:
            self.ways[sig] = {"chain": chain, "score": round(score, 3), "redundancy": round(red, 3),
                              "uses": (known or {}).get("uses", 0)}
        self.ways[sig]["uses"] += 1
        self.open.pop(sig, None)
        report = {"source": source, "signature": sig, "readable": True, "chain": chain or ["as it is"],
                  "before": round(before, 3), "after": round(red, 3), "bits": round(bits, 2),
                  "symbols": int(len(sym)), "size": len(data), "new_way": new_way, "types": []}
        other = next((t for t in ranked if t[1]["kind"] != out["kind"] and t[2][1] >= 0.3 and t[0]), None)
        vread = out if out["kind"] == "values" else (other[1] if other else None)
        values = sym if out["kind"] == "values" else (other[2][3] if other else None)
        if other:
            report["also"] = {"chain": other[0], "after": round(other[2][1], 3)}
            self.ways[sig]["also"] = list(other[0])
        table = next((t for t in ranked if t[1]["kind"] == "values" and len(t[1].get("dims") or ()) == 2
                      and t[2][1] >= 0.3 and t[0]), None)
        if table is not None and len((vread or {}).get("dims") or ()) != 2:
            vread, values = table[1], table[2][3]
            self.ways[sig]["table"] = list(table[0])
            report["table"] = list(table[0])
        if other is None and len((vread or {}).get("dims") or ()) == 2:
            other = next((t for t in ranked if t[1]["kind"] == "symbols" and t[0]), None)
            if other:
                report["also"] = {"chain": other[0], "after": round(other[2][1], 3)}
                self.ways[sig]["also"] = list(other[0])
        dims = vread.get("dims") if vread else None
        if values is not None and (len(values) >= 512 or (dims and len(dims) == 2 and dims[0] >= 64)):
            self._values(values, dims, report)
        if out["kind"] == "symbols":
            labels, lkind = sym, "symbols"
        elif other and other[1]["kind"] == "symbols":
            labels, lkind = other[2][3], "symbols"
        elif "seen" not in report and "columns" not in report and red > 0.25:
            labels, lkind = sym, "values"
        else:
            labels, lkind = None, None
        if labels is not None:
            found = chunks(labels)
            report["pieces"] = self._pieces(found, lkind, source)
            if lkind == "symbols":
                report["text"] = "".join(chr(c) for c in np.asarray(labels[:200000]).tolist() if 0 < c < 0x110000)
            if found:
                self._type("pieces", [len(found)], source, report)
        return report

    def _values(self, values, dims, report):
        """Magnitudes: their shape."""
        with np.errstate(all="ignore"):
            shp = shape(values)
        if shp:
            report["found"] = {k: shp[k] for k in ("element", "row", "frame")}
            a = shp["element"]
            report["rhythms"] = [(L // a if L % a == 0 else round(L / a, 1), round(r, 3)) for L, r in shp["rhythms"][:4]]
        if dims and len(dims) == 2:
            n, k = dims
            cols = []
            for j in range(k):
                col = np.asarray(values[j::k], dtype=np.float64)
                with np.errstate(all="ignore"):
                    rr = autocorr(col, most=max(4, len(col) // 3))
                if rr is None or rr.size < 6:
                    continue
                low = np.minimum.accumulate(rr)
                back = [L for L in range(2, rr.size - 1)
                        if rr[L] >= 0.5 and rr[L] >= rr[L - 1] and rr[L] >= rr[L + 1]
                        and rise_digits(float(rr[L]), float(low[L - 1]), len(col) - L) >= EVIDENCE]
                if back:
                    top = max(float(rr[L]) for L in back)
                    L = next(L for L in back if rr[L] >= 0.9 * top)
                    ev = rise_digits(float(rr[L]), float(low[L - 1]), len(col) - L)
                    cols.append({"column": j + 1, "every": L, "match": round(float(rr[L]), 3), "evidence": round(ev, 1),
                                 "exact": round(machine_like(col, L), 3)})
            report["shape"] = {"lines": n, "columns": k}
            if cols:
                report["columns"] = cols
                for c in cols:
                    self._type("repeats in a column", [c["every"]], report["source"], report)
            return
        if dims and len(dims) == 3 and dims[2] in (3, 4):
            h, w, a = dims
            report["shape"] = {"height": h, "width": w, "values": a}
            if shp:
                report["found_itself"] = shp["row"] == w * a
            self._grid(values, (h, w, a), None, report)
        elif dims and len(dims) == 3:
            t, h, w = dims
            report["shape"] = {"frames": t, "height": h, "width": w}
            if shp:
                report["found_itself"] = shp["row"] == w
            self._grid(values, (h, w, 1), t, report)
        elif shp and shp["row"]:
            a, b, f = shp["element"], shp["row"], shp["frame"]
            w = b // a
            h = (f // b) if f else min(len(values) // b, 2048)
            t = len(values) // f if f else None
            report["shape"] = {"height": h, "width": w, "values": a, "frames": t}
            self._grid(values, (h, w, a), t, report)
        elif shp and shp["rhythms"]:
            self._type("rhythm", [report["rhythms"][0][0]], report["source"], report)

    def _grid(self, values, hwa, frames, report):
        h, w, a = hwa
        if w < 8 or h < 8 or len(values) < w * h * a:
            return
        g = np.asarray(values[:w * h * a], dtype=np.float64).reshape(h, w, a)
        lo, hi = np.percentile(g, 1), np.percentile(g, 99)
        g = np.clip((g - lo) / max(hi - lo, 1e-9), 0, 1)
        light = g.mean(axis=2)
        report["seen"] = _png(g if a in (3, 4) else light)
        name = "grid" + (f"·{a}" if a > 1 else "") + ("·frames" if frames else "")
        self._type(name, [w, h], report["source"], report)
        if frames and frames >= 4:
            size = w * h * a
            per = np.asarray(values[:frames * size], dtype=np.float64).reshape(frames, size)[:, ::max(1, size // 512)]
            per = per - per.mean(axis=1, keepdims=True)
            norm = np.sqrt((per * per).sum(axis=1)) + 1e-9
            best = None
            for lag in range(2, frames // 2 + 1):
                c = float(np.mean((per[:-lag] * per[lag:]).sum(axis=1) / (norm[:-lag] * norm[lag:])))
                if c > 0.9 and best is None:
                    best = (lag, round(c, 3))
            if best:
                report["time"] = {"every": best[0], "match": best[1]}
                self._type("repeats in time", [best[0]], report["source"], report)
        shade = light
        if a >= 3:
            flat = g.reshape(-1, a)[:, :3]
            sample = flat[::max(1, len(flat) // 20000)]
            with np.errstate(all="ignore"):
                vals, vecs = np.linalg.eigh(np.cov(sample.T))
            if np.all(np.isfinite(vals)) and vals[-1] > 1.5 * max(1e-9, float(light.var())):
                shade = (flat @ vecs[:, -1]).reshape(h, w)
        with np.errstate(all="ignore"):
            lat = lattice(shade[:min(h, 256), :min(w, 256)])
        if lat and lat["evidence"] >= EVIDENCE:
            pub = {k: lat[k] for k in ("rank", "windings", "rho", "evidence", "defects", "symmetry")}
            pub["basis"] = [list(v) for v in lat["basis"]]
            if lat.get("unit") is not None:
                u = lat["unit"]
                u = (u - u.min()) / max(1e-9, u.max() - u.min())
                pub["unit_png"] = _png(u, side=32)
                pub["broken"] = lat["broken"]
            report["lattice"] = pub
            self._type("repeats" + "".join("·" + s for s in lat["symmetry"]), lat["windings"], report["source"], report)

    def _pieces(self, found, kind, source):
        shown = []
        for run, count, ev in found:
            key = tuple(run)
            text = "".join(chr(c) for c in run if 0 < c < 0x110000) if kind == "symbols" else \
                bytes(c for c in run if 0 <= c < 256).decode("latin-1")
            text = text.replace("\n", "↵").replace("\r", "").replace("\t", "→")
            p = self.pieces.get(key)
            if p is None:
                p = self.pieces[key] = {"text": text, "count": 0, "sources": 0, "evidence": 0.0}
            p["count"] += count
            p["sources"] += 1
            p["evidence"] = max(p["evidence"], ev)
            shown.append(text)
        if len(self.pieces) > 60000:
            for key in [k for k, p in self.pieces.items() if p["sources"] <= 1][:20000]:
                del self.pieces[key]
        return shown[:24]

    def _type(self, name, sizes, source, report):
        t = self.types.get(name)
        if t is None:
            t = self.types[name] = {"count": 0, "first": source, "sizes": sizes}
            report["types"].append(name)
        t["count"] += 1


def _png(g, side=96):
    """A small picture of a grid it found by itself."""
    if senses.Image is None:
        return None
    a = np.asarray(g)
    a = np.clip(a * 255, 0, 255).astype(np.uint8)
    img = senses.Image.fromarray(a, "RGB" if a.ndim == 3 and a.shape[2] == 3 else
                                 "RGBA" if a.ndim == 3 and a.shape[2] == 4 else "L")
    if max(img.size) > side:
        img.thumbnail((side, side), senses.Image.Resampling.BOX)
    elif max(img.size) < side // 2:
        k = max(1, side // max(img.size))
        img = img.resize((img.size[0] * k, img.size[1] * k), senses.Image.Resampling.NEAREST)
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")

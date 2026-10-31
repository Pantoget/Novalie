# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""The one rule's arithmetic: evidence in digits, tails, test martingales, the bars of its laws."""

import math
import unicodedata

from .config import EVIDENCE


class _Digits(dict):
    """For str.translate: each decimal digit of every script as the digit it is."""
    def __missing__(self, cp):
        ch = chr(cp)
        self[cp] = str(unicodedata.decimal(ch)) if ch.isdecimal() else ch
        return self[cp]


DIGITS = _Digits()


def moment_trusted(m):
    """A law of moments is trusted once the changes it foresaw are worth the one rule, and more for every
    attribute its condition could have used."""
    if not m or m.get("cond") is None:
        return False
    return m["proof"] >= EVIDENCE + math.log10(1 + m["revised"]) + 0.30103 * m["attrs"]


def moment_holds(m):
    """A law of moments that says when its sense changes, not only that it does."""
    return moment_trusted(m) and bool(m.get("tested"))


def act_beyond(c, m):
    """Its own act as a cause its law of moments does not say."""
    return c[1] == "act" and "act" not in ((m or {}).get("tested") or ())


def bell(n):
    """How many ways n things can be grouped."""
    row = [1]
    for _ in range(n):
        new = [row[-1]]
        for x in row:
            new.append(new[-1] + x)
        row = new
    return row[0]


def sign_digits(k, n):
    """Digits of evidence that one way of foreseeing is right more often than another."""
    if n == 0 or 2 * k <= n:
        return 0.0
    lb = math.lgamma(k + 0.5) + math.lgamma(n - k + 0.5) - math.lgamma(n + 1) - math.log(math.pi)
    return (lb + n * math.log(2)) / math.log(10)


def two_rates_digits(n1, k1, n0, k0):
    """Digits of evidence that one way of things."""
    if n1 == 0 or k1 * max(1, n0) <= k0 * n1:
        return 0.0
    kt = lambda n, k: math.lgamma(k + 0.5) + math.lgamma(n - k + 0.5) - math.lgamma(n + 1) - math.log(math.pi)
    n, k = n1 + n0, k1 + k0
    best = 0.0 if k in (0, n) else k * math.log(k / n) + (n - k) * math.log1p(-k / n)
    return max(0.0, (kt(n1, k1) + kt(n0, k0) - best) / math.log(10))


def half_beta(n, x):
    """log P(X = x), X Beta-binomial(n, 1/2, 1/2)."""
    return math.lgamma(x + 0.5) + math.lgamma(n - x + 0.5) - math.lgamma(x + 1) - math.lgamma(n - x + 1) - math.log(math.pi)


def sum_of_half_betas(ns, t):
    """log P(X_1 + ... + X_g = t), each X_i Beta-binomial(n_i, 1/2, 1/2), independent."""
    dp, left = {0: 0.0}, sum(ns)
    for n in ns:
        left -= n
        new = {}
        for got, lp in dp.items():
            for x in range(max(0, t - got - left), min(n, t - got) + 1):
                v = lp + half_beta(n, x)
                w = new.get(got + x)
                new[got + x] = v if w is None else max(v, w) + math.log1p(math.exp(-abs(v - w)))
        dp = new
    return dp.get(t, -math.inf)


def exact_digits(groups, per_key, kt):
    """How much a grouping of symbols says beyond chance, in powers of ten, as an exact conditional e-value."""
    total = 0.0
    for key, rows in per_key.items():
        sizes = [sum(r.values()) for r in rows]
        if sum(1 for n in sizes if n) < 2:
            continue
        outcomes = sorted({o for r in rows for o in r}, key=repr)
        if len(outcomes) < 2:
            continue
        n_all = sum(sizes)
        es = []
        for o in (outcomes[:1] if len(outcomes) == 2 else outcomes):
            ks = [r.get(o, 0) for r in rows]
            k_all = sum(ks)
            said = kt({1: k_all, 0: n_all - k_all}, 2) - sum(kt({1: k, 0: n - k}, 2) for k, n in zip(ks, sizes) if n)
            t = min(k_all, n_all - k_all)
            mean = (sum_of_half_betas([n for n in sizes if n], t) - half_beta(n_all, t)) / math.log(10)
            es.append(said - mean)
        top = max(es)
        total += top + math.log10(sum(10 ** (e - top) for e in es) / len(es))
    return total


def odds_bar(tests, revised=0, look=0, depth=1):
    """What a law of odds must be worth before it believes it, in powers of ten."""
    return EVIDENCE + math.log10(max(1, tests)) + math.log10(1 + revised) + paid(look) + paid(depth)


def paid(look):
    """What its look number L pays, in powers of ten."""
    return math.log10(look * (look + 1)) if look > 0 else 0.0


def kl_digits(n, k, p):
    """A first, careful look at evidence(n, k, p)."""
    if n <= 0 or k <= n * p or p >= 1:
        return 0.0
    p, a = max(p, 1e-12), k / n
    d = a * math.log(a / p) + ((1 - a) * math.log((1 - a) / (1 - p)) if a < 1 else 0.0)
    return n * d / math.log(10)


def coarse(x):
    """Its own coarse number for an amount."""
    return 0 if not x or x < 0.5 else max(1, 2 ** round(math.log2(x)))


def trusted(rec):
    """A kind it knew again, or a machine it made, is trusted once what it foresaw here and came true is worth
    the one rule, and more for every kind it tried before taking this one."""
    return rec.get("proof", 0.0) >= EVIDENCE + math.log10(max(1, rec.get("tests", 1)))
def evidence(n, k, p):
    """How unlikely it is, in powers of ten, that k or more of n go one way by coincidence when each goes that
    way with chance p."""
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


def low_tail(n, k, p):
    """log10 of the chance of at most k of n, each with chance p."""
    terms = [math.lgamma(n + 1) - math.lgamma(x + 1) - math.lgamma(n - x + 1) + x * math.log(p) + (n - x) * math.log1p(-p)
             for x in range(0, min(k, n) + 1)]
    top = max(terms)
    return (top + math.log(sum(math.exp(t - top) for t in terms))) / math.log(10)

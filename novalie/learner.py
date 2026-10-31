# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""One sense's learner: laws of counts, moments and odds."""

import array
import collections
import math
import operator

from .config import EVIDENCE, ODDS_LAGS, room
from .evidence import kl_digits, moment_holds, moment_trusted, odds_bar, trusted
from .laws import change_of, odds_key
from .parts import nm, org


class _View:
    def __init__(self, buttons, first):
        self.buttons, self._first, self.state = buttons, first, None

    def color(self, s):
        return self._first


class Learner(org.TunedMind):
    """One sensor's stream, learned by the organism's mind."""

    def __init__(self, buttons, first, eps):
        super().__init__(_View(buttons, first), eps, True)
        self.since, self.calm = 0, 0
        self.seen_freq, self.stays, self.proof = collections.Counter([first]), 0, 0.0
        self.eps0 = eps

    def worth(self, o):
        """What foreseeing o is worth when it comes true, in powers of ten."""
        freq = self.__dict__.get("seen_freq")
        if freq is None:
            freq = self.seen_freq = collections.Counter(self.colors)
        n = max(1, len(self.colors))
        q = (freq.get(o, 0) + 1) / (n + 1)
        if self.colors and o == self.colors[-1]:
            q = max(q, (getattr(self, "stays", 0) + 1) / (n + 1))
        return -math.log10(min(1.0, q))

    def see_moment(self, before, o, state):
        """Its law of moments for this sense."""
        m = self.__dict__.get("moment")
        if m is None:
            m = self.moment = {"cond": None, "d": None, "M": None, "proof": 0.0, "steps": 0, "held": 0, "revised": 0,
                               "attrs": len(state), "values": {before}, "times": [], "announced": False}
        tested = m.setdefault("tested", set())
        cond = m["cond"] or {}
        if cond and o == before:
            off = [k for k, v in cond.items() if state.get(k) != v]
            if len(off) == 1:
                tested.add(off[0])
        fresh = {k for k, v in cond.items() if k not in tested and state.get(k) != v}
        if fresh and o != before:
            rest = {k: v for k, v in cond.items() if k not in fresh}
            if all(state.get(k) == v for k, v in rest.items()):
                m["cond"] = rest
        held = m["cond"] is not None and all(state.get(k) == v for k, v in m["cond"].items())
        rate = (m["held"] + 1) / (m["steps"] + 1)
        m["steps"] += 1
        m["held"] += held
        if o == before:
            if held:
                m["cond"], m["proof"], m["revised"] = None, 0.0, m["revised"] + 1
                m.pop("recalled", None)
            return
        t = len(self.colors) - 1
        m["times"] = (m["times"] + [t])[-8:]
        step = o - before if isinstance(o, int) and isinstance(before, int) else None
        if m["cond"] is None:
            m["cond"], m["d"] = dict(state), step
            m["tested"] = set()
            m["values"].add(o)
            return
        if m["d"] is not None and step is not None and step != m["d"]:
            turn = before + m["d"] - o
            seen = [v for v in m["values"] if type(v) is int]
            if seen and turn > max(seen) and m["M"] in (None, turn):
                m["M"], step = turn, m["d"]
        what = step is not None and step == m["d"]
        if held and what:
            m["proof"] += -math.log10(min(1.0, rate)) + math.log10(max(2, len(m["values"])))
        else:
            m["cond"] = {k: v for k, v in m["cond"].items() if state.get(k) == v} or None
            m["proof"], m["revised"], m["tested"] = 0.0, m["revised"] + 1, set()
            m.pop("recalled", None)
            if not what:
                m["d"] = step
        m["values"].add(o)

    def moment_cell(self):
        """(P, d, M) when its law of moments is trusted, it has seen it turn, and its changes come every P acts."""
        m = getattr(self, "moment", None)
        if not moment_trusted(m) or not m.get("M") or m.get("d") is None:
            return None
        gaps = {b - a for a, b in zip(m["times"], m["times"][1:])}
        P = m.get("recalled")
        if P and m["times"] and gaps <= {P}:
            return (P, m["d"], m["M"])
        if len(m["times"]) < 3:
            return None
        return (gaps.pop(), m["d"], m["M"]) if len(gaps) == 1 else None

    def odds_room(self):
        """Its laws of odds for this sense, and what they are counted from."""
        od = self.__dict__.get("odds")
        if od is None:
            od = self.odds = {"n": collections.Counter(), "K": collections.Counter(), "Kany": collections.Counter(),
                              "rows": {}, "chain": {}, "laws": {}, "pairs": {}, "verdict": None, "revised": 0,
                              "looks": 0, "next": 50, "steps": 0, "tests": 0, "determined": None, "cal": {},
                              "levels": {}}
        return od

    def see_odds(self, j, past, before, o):
        """Its laws of odds for this sense, counted act by act."""
        od = self.odds_room()
        d = change_of(before, o)
        own = f"s{j}"
        od["steps"] += 1
        self.count_chain(od["chain"], before, d)
        rows, n, K, Kany = od["rows"], od["n"], od["K"], od["Kany"]
        now = []
        for l in ODDS_LAGS:
            if len(past) <= l:
                break
            n[l] += 1
            if d is not None:
                K[(l, d)] += 1
                Kany[l] += 1
            for attr, v in past[-1 - l].items():
                if odds_key(l, attr, j):
                    now.append((l, attr, v))
        self.count_rows(rows, now, before, d)
        lg = self.__dict__.get("pair_log")
        if lg is None:
            lg = self.pair_log = {"id": {}, "conds": collections.deque(), "t": collections.deque(),
                                  "before": collections.deque(), "d": collections.deque()}
        ids = lg["id"]
        lg["conds"].append(array.array("I", sorted({ids.setdefault(c, len(ids)) for c in now})))
        lg["t"].append(len(self.colors) - 1)
        lg["before"].append(before)
        lg["d"].append(d)
        if len(lg["t"]) > room(20_000):
            for k in ("conds", "t", "before", "d"):
                lg[k].popleft()
        here = set(now)

        def nerve(counted):
            watch = od.get("watch")
            if not watch:
                return
            H = 2 * max(1, len(od["rows"])) * max(1, len({dd for (_, dd) in od["K"]}))
            rise = max(0.0, odds_bar(H, od["revised"], od["looks"] + 1) - watch[0]["bar"])
            for w in watch:
                if w["c"] not in here or not counted(w):
                    continue
                r = self.chain_rate(before, w["d"], self.level_chain(w["d"], w["i"]))
                if r is None:
                    continue
                w["nf"] += 1
                w["E"] += r
                w["k"] += d == w["d"]
                base = w["E"] / w["nf"]
                dig = kl_digits(w["nf"], w["k"], base) if w["up"] else kl_digits(w["nf"], w["nf"] - w["k"], 1 - base)
                if dig >= w["need"] + rise:
                    od["next"], od["watch"] = od["steps"], []
                    od["woke"] = od.get("woke", 0) + 1
                    return
        nerve(lambda w: w["i"] == 0)
        if not od["laws"] and not od["pairs"]:
            return
        first = {}
        for dd, rules in od["laws"].items():
            first[dd] = next((i for i, r in enumerate(rules) if r["cond"] in here), len(rules))
            for i, lv in enumerate(od["levels"].get(dd, ())):
                if lv is not None and first[dd] >= i:
                    self.count_rows(lv["rows"], now, before, d)
                    self.count_chain(lv["chain"], before, d)
        nerve(lambda w: w["i"] > 0 and first.get(w["d"], 0) >= w["i"])
        for (dd, i, c1), table in od["pairs"].items():
            if c1 in here and first.get(dd, 0) >= i:
                self.count_rows(table, [None] + [c2 for c2 in now if c2 != c1], before, d)
        for dd, rules in od["laws"].items():
            i = first[dd]
            if i >= len(rules):
                continue
            law = rules[i]
            rate = self.chain_rate(before, dd, self.level_chain(dd, i))
            if rate is None:
                continue
            hit = d == dd
            q0, rate = law["q0"], min(max(rate, 1e-6), 1 - 1e-6)
            law["n1"] += 1
            law["k1"] += hit
            step = math.log10(q0 / rate) if hit else math.log10((1 - q0) / (1 - rate))
            law["lr"] += step
            if (rate < q0 if law["up"] else rate > q0) and not any(tuple(e[1]) in here for e in law["unless"] + law["especially"]):
                drift = max(0.0, law.get("drift", 0.0) - step)
                if drift == 0.0:
                    law["since"] = len(self.colors) - 1
                law["drift"] = drift
            drift = law.get("drift", 0.0)
            if drift >= EVIDENCE + math.log10(sum(len(r) for r in od["laws"].values())) and not od.get("drifted"):
                od["drifted"] = {"d": dd, "cond": law["cond"], "from": law.get("since", 0) + 1, "against": round(drift, 1),
                                 "n1": law["n1"], "k1": law["k1"]}
                od["next"] = od["steps"]
            b = law["cal"].setdefault(min(9, int(10 * law["q"])), [0, 0])
            b[0] += 1
            b[1] += hit

    @staticmethod
    def count_rows(rows, now, before, d):
        """One act counted in a table of things seen."""
        for key in now:
            r = rows.get(key)
            if r is None:
                r = rows[key] = [0, 0, collections.Counter(), collections.Counter()]
            r[0] += 1
            r[3][before] += 1
            if d is not None:
                r[1] += 1
                r[2][d] += 1

    @staticmethod
    def count_chain(chain, before, d):
        """One act counted in a chain."""
        ch = chain.get(before)
        if ch is None:
            ch = chain[before] = [0, collections.Counter()]
        ch[0] += 1
        if d is not None:
            ch[1][d] += 1

    def level_chain(self, d, i):
        """What the sense does by itself at the acts none of the first i laws of change d held."""
        if i == 0:
            return self.odds["chain"]
        lv = self.odds["levels"].get(d)
        return lv[i]["chain"] if lv and i < len(lv) and lv[i] is not None else self.odds["chain"]

    def chain_rate(self, v, d, chain=None):
        """What the sense does by itself."""
        t = (v + d) if type(d) is int and type(v) is int else (d[1] if isinstance(d, tuple) else None)
        if t not in (self.__dict__.get("seen_freq") or ()) or (isinstance(d, tuple) and t == v):
            return None
        ch = (self.odds["chain"] if chain is None else chain).get(v)
        nv, k = (ch[0], ch[1].get(d, 0)) if ch else (0, 0)
        return (k + 0.5) / (nv + 1)

    def by_itself(self, hv, d, chain=None):
        """Over the acts a thing held."""
        E, nf = 0.0, 0
        for v, h in hv.items():
            r = self.chain_rate(v, d, chain)
            if r is not None:
                E += h * r
                nf += h
        return E, nf

    def odds_cell(self):
        """(values, about how many acts between its changes) when it holds this sense by its odds."""
        od = self.__dict__.get("odds")
        if not od or not self.__dict__.get("odds_gate") or not (od["laws"] or od["verdict"]):
            return None
        rate = od["Kany"][0] / max(1, od["n"][0])
        dwell = 2 ** round(math.log2(1 / rate)) if rate > 0 else 0
        return (len(self.__dict__.get("seen_freq") or set(self.colors)), dwell)

    def noisy(self):
        """Has it found this sense to be one of chance."""
        od = self.__dict__.get("odds")
        return bool(od and (od["laws"] or od["verdict"]))

    def exact(self):
        """Does it foretell this sense exactly."""
        r, inv = getattr(self, "recognized", None), getattr(self, "invented", None)
        return (self.counts_closed() or self.moment_cell() is not None or (r is not None and trusted(r))
                or (inv is not None and trusted(inv)))

    def held(self):
        """Is it held by laws that leave its laws of odds nothing to find."""
        r, inv = getattr(self, "recognized", None), getattr(self, "invented", None)
        return (self.counts_closed() or (r is not None and trusted(r)) or (inv is not None and trusted(inv))
                or (self.moment_cell() is not None and moment_holds(self.__dict__.get("moment"))))

    def counts_closed(self):
        mo = self.model
        return 0 not in mo.mods and len(self.table) == math.prod(mo.mods) and getattr(self, "proof", 0.0) >= self.need()

    def need(self):
        """How much its laws of a sense must have foreseen, in powers of ten, before it is sure of them."""
        return EVIDENCE + math.log10(max(1, len(self.ledger)))

    def observe(self, a, o):
        w = self.worth(o)
        if self.colors and o == self.colors[-1]:
            self.stays = getattr(self, "stays", 0) + 1
        sf = self.__dict__.get("seen_freq")
        if sf is None:
            sf = self.seen_freq = collections.Counter(self.colors)
        sf[o] += 1
        r = getattr(self, "recognized", None)
        if r is not None:
            self.actions.append(a)
            self.colors.append(o)
            c = self.counts[-1][:]
            c[a] += 1
            self.counts.append(c)
            r["p"] = (r["p"] + r["eff"].get(a, 0)) % r["d"]
            if r["T"][r["p"]] == o:
                r["calm"] += 1
                r["proof"] = r.get("proof", 0.0) + w
            else:
                self.recognized, self.calm, self.proof = None, 0, 0.0
            return
        t2 = len(self.colors)
        self.actions.append(a)
        self.colors.append(o)
        c = self.counts[-1][:]
        c[a] += 1
        self.counts.append(c)
        if self.odds_cell() is not None:
            self.eps = getattr(self, "eps0", self.eps)
            self.key = self.model.step(self.key, a)
            return
        colors, counts, up, sub = self.colors, self.counts, self.note_up, operator.sub
        for t1 in range(max(0, t2 - self.window), t2):
            if colors[t1] == o:
                up(tuple(map(sub, c, counts[t1])))
        self.key = self.model.step(self.key, a)
        known = self.table.get(self.key)
        first_return = False
        if known is None:
            past = self.by_color[o]
            first_return = len(past) == 1
            for t1 in nm.spread(past, 200):
                up(tuple(map(sub, c, counts[t1])))
            self.table[self.key] = o
            self.by_color[o].append(t2)
        self.forget_once()
        surprise = known is not None and known != o
        self.surprises += surprise
        self.since += 1
        self.calm = 0 if surprise else self.calm + 1
        self.proof = 0.0 if surprise else getattr(self, "proof", 0.0) + (w if known is not None else 0.0)
        if ((surprise and not self.noisy())
                or self.since >= max(50, t2 // 10)
                or (first_return and 0 in self.model.mods)):
            before = len(self.ledger)
            self.relearn(t2)
            self.since = 0
            if len(self.ledger) != before:
                self.calm, self.proof = 0, 0.0

    def sure(self):
        """Sure of a sense once what it foresaw of it came true worth the one rule."""
        inv = getattr(self, "invented", None)
        if inv is not None:
            return trusted(inv)
        r = getattr(self, "recognized", None)
        if r is not None:
            return trusted(r)
        return (self.counts_closed() or self.moment_cell() is not None
                or self.odds_cell() is not None)

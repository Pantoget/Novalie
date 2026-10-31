# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Laws of odds: what raises or lowers the odds of each change."""

import array
import bisect
import collections
import itertools
import math
import os

from ..config import EVIDENCE, NERVES, ODDS_CLOSE, ODDS_LAGS, ODDS_NEAR, ODDS_RULES, room
from ..evidence import act_beyond, evidence, kl_digits, moment_holds, odds_bar, paid
from ..laws import PAIRS, causal, change_of, cond_depth, is_pair, law_shape, odds_key, pair_name, seen_with
from ..parts import gpu


class OddsLaws:
    @staticmethod
    def odds_rows(L, R, chain, d, ds, bar, i, cache):
        """The rows of a table of things seen worth a first look for change d."""
        if gpu is None or len(R) * max(1, len(ds)) < 2048:
            return R.items()
        key = (id(R), id(chain), i)
        got = cache.get(key)
        if got is None:
            items, dd = list(R.items()), (list(ds) if i == 0 else [d])
            res = gpu.singles(items, lambda v, x: L.chain_rate(v, x, chain), dd, screen=bar - 4.0)
            per = None
            if res is not None:
                _, kept, D = res
                per = {}
                for q in kept:
                    ci, di = divmod(q, D)
                    per.setdefault(repr(dd[di]), []).append(ci)
            got = cache[key] = (items, per)
        items, per = got
        if per is None:
            return R.items()
        return [items[ci] for ci in sorted(per.get(repr(d), ()))]

    @staticmethod
    def odds_nf(L, table, chain, d):
        """For each thing seen with a law."""
        if gpu is None or len(table) < 2048:
            return None
        items = list(table.items())
        res = gpu.singles(items, lambda v, x: L.chain_rate(v, x, chain), [d])
        if res is None:
            return None
        return {c: res[0][ci] for ci, (c, _) in enumerate(items)}

    def judge_odds(self, j):
        """Its laws of odds for sense j, judged."""
        L = self.learners[j]
        od = L.odds_room()
        had = {d: len(r) for d, r in od["laws"].items()}
        if od.get("drifted"):
            self.odds_again(j, od["drifted"])
        held_by_moments = moment_holds(L.__dict__.get("moment"))
        od["looks"] += 1
        od["next"] = od["steps"] + max(50, od["steps"] // 10)
        rows, Kany = od["rows"], od["Kany"]
        ds = sorted({d for (l, d) in od["K"]}, key=repr)
        H = od["tests"] = 2 * max(1, len(rows)) * max(1, len(ds))
        bar = odds_bar(H, od["revised"], od["looks"])
        laws, levels = od["laws"], od["levels"]
        shapes = self.__dict__.get("law_shapes") or {}
        expected = sum(1 for c, (nc, kany, kd, hv) in rows.items() for d in ds for up in (True, False)
                       if law_shape(c, d, up) in shapes) if shapes else 0
        bar_known = odds_bar(max(1, expected), od["revised"], od["looks"])
        for d, rules in list(laws.items()):
            for i, law in enumerate(rules):
                if law["lr"] <= -(EVIDENCE + math.log10(sum(len(r) for r in laws.values()))):
                    gone = rules[i:]
                    del rules[i:]
                    del levels.setdefault(d, [])[i + 1:]
                    od["revised"] += 1
                    for g in gone:
                        od["pairs"].pop((d, g["level"], g["cond"]), None)
                        self.journal_end(("odds", self.k, j, repr(g["cond"]), repr(d)), "refuted")
                    cond = [law["cond"][0], law["cond"][1], str(law["cond"][2])]
                    self.emit("odds_revised", sensor=j + 1, cond=cond, after=law["n1"], came=law["k1"])
                    self.decide("odds_revised", j + 1, {"cond": cond, "after": law["n1"], "came": law["k1"]})
                    break
            if not rules:
                del laws[d]
                levels.pop(d, None)
        found, always = False, set()
        on_card = {}
        near = []
        for d in ds:
            rules = laws.get(d, [])
            for i in range(min(len(rules) + 1, ODDS_RULES)):
                R, chain = ((rows, od["chain"]) if i == 0 else (levels[d][i]["rows"], levels[d][i]["chain"]))
                prior = {r["cond"] for r in rules[:i]}
                best = None
                for c, (nc, kany, kd, hv) in self.odds_rows(L, R, chain, d, ds, bar, i, on_card):
                    if nc < 2 or c in prior:
                        continue
                    k = kd.get(d, 0)
                    E, nf = L.by_itself(hv, d, chain)
                    if nf < 2:
                        continue
                    base = E / nf
                    up = k > E
                    quick = kl_digits(nf, k, base) if up else kl_digits(nf, nf - k, 1 - base)
                    if quick < bar - 3:
                        continue
                    dig = quick if nf > 400 else (evidence(nf, k, base) if up else evidence(nf, nf - k, 1 - base))
                    need = bar_known if expected and law_shape(c, d, up) in shapes else bar
                    if dig < need:
                        near.append((need - dig, repr(c), c, d, i, up, k, nf, E, need))
                        continue
                    is_cause = causal(c)
                    if (up and kany == nc and is_cause and held_by_moments
                            and not act_beyond(c, L.__dict__.get("moment"))):
                        always.add(d)
                        continue
                    rank = (is_cause, round(dig, 9), -c[0], c[1], repr(c[2]))
                    if best is None or rank > best[0]:
                        best = (rank, c, k, nf, base, up)
                if best is None or d in always:
                    break
                rank, c, k, nf, base, up = best
                if i < len(rules) and rules[i]["cond"] == c:
                    self.odds_restate(L, d, i, rules[i], R, chain, rank, k, nf, base, H)
                    found = True
                    continue
                was = rules[i]["cond"] if i < len(rules) else None
                if was is not None and rank[0] and not causal(was):
                    gone = rules[i:]
                    del rules[i:]
                    del levels.setdefault(d, [])[i + 1:]
                    for g in gone:
                        od["pairs"].pop((d, g["level"], g["cond"]), None)
                        self.journal_end(("odds", self.k, j, repr(g["cond"]), repr(d)), "replaced by a cause")
                    self.emit("odds_cause", sensor=j + 1, was=list(was), cause=list(c))
                elif i < len(rules):
                    found = True
                    continue
                table = self.odds_pairs(j, d, i, c, [r["cond"] for r in rules])
                kany = (table.get(None) or [0, 0])[1]
                sure_with = next((c2 for c2, (n2, k2, _, _) in sorted(table.items(), key=lambda kv: repr(kv[0]))
                                  if c2 is not None and n2 >= 2 and k2 == n2 == kany
                                  and causal(c2)), None)
                if (up and sure_with is not None and held_by_moments
                        and not any(act_beyond(x, L.__dict__.get("moment")) for x in (c, sure_with))):
                    od["determined"] = [list(c), list(sure_with)]
                    always.add(d)
                    break
                known = law_shape(c, d, up) in shapes
                law = {"cond": c, "d": d, "level": i, "up": up, "q": 0.0, "p": 0.0, "base": 0.0, "digits": 0.0,
                       "tests": H, "n": nf, "k": k, "q0": (k + 0.5) / (nf + 1), "lr": 0.0, "n1": 0, "k1": 0, "cal": {},
                       "at": self.world_steps, "unless": [], "especially": [], "known": known}
                used_bar = bar_known if expected and known else bar
                self.journal_begin("odds", ("odds", self.k, j, repr(c), repr(d)), sensor=j + 1, level=i, up=up,
                                   known=known, n=nf, digits=round(rank[1], 1), margin=round(rank[1] - used_bar, 1),
                                   depth=cond_depth(c), cause=bool(rank[0]))
                if j in self.named_senses():
                    shp = self.__dict__.setdefault("law_shapes", {}).setdefault(law_shape(c, d, up),
                                                                                {"worlds": set(), "n": 0})
                    shp["n"] += 1
                    shp["worlds"].add(self.k)
                self.odds_restate(L, d, i, law, R, chain, rank, k, nf, base, H)
                rules.append(law)
                laws[d] = rules
                lv = levels.setdefault(d, [None])
                Ls = self.learners
                conds = [r["cond"] for r in rules]
                lv.append(self.odds_count(j, without=conds))
                found = True
                shown = d if type(d) is int else str(d[1])
                cond = [c[0], c[1], c[2] if isinstance(c[2], (int, float, str)) else str(c[2])]
                self.emit("odds", sensor=j + 1, cond=cond, d=shown, up=up, q=law["q"], p=law["p"], base=law["base"],
                          digits=law["digits"], tests=H, level=i, known=known)
                self.decide("odds", j + 1, {"cond": cond, "d": shown, "up": up, "q": law["q"], "p": law["p"],
                                            "base": law["base"], "digits": law["digits"], "tests": expected if known and rank[1] < bar else H,
                                            "level": i, "known": known})
        for d, rules in laws.items():
            for i, law in enumerate(rules):
                table, q = self.odds_pairs(j, d, i, law["cond"], [r["cond"] for r in rules]), min(max(law["q"], 1e-6), 1 - 1e-6)
                bar2 = odds_bar(2 * max(1, len(table)))
                chain = L.level_chain(d, i)
                up, down = [], []
                nfs = self.odds_nf(L, table, chain, d)
                for c2, (n2, _, kd2, hv2) in table.items():
                    if c2 is None or (c2[1].startswith("cmp:") and str(j) in c2[1].split(":")[1:]):
                        continue
                    k2 = kd2.get(d, 0)
                    n2f = nfs[c2] if nfs is not None else L.by_itself(hv2, d, chain)[1]
                    if n2f < 2:
                        continue
                    if k2 > n2f * q and kl_digits(n2f, k2, q) >= bar2 - 3:
                        e = evidence(n2f, k2, q)
                        if e >= bar2:
                            up.append([round(e, 1), list(c2), round(k2 / n2f, 3), n2f])
                    elif k2 < n2f * q and kl_digits(n2f, n2f - k2, 1 - q) >= bar2 - 3:
                        e = evidence(n2f, n2f - k2, 1 - q)
                        if e >= bar2:
                            down.append([round(e, 1), list(c2), round(k2 / n2f, 3), n2f])
                law["especially"] = sorted(up, key=lambda x: (-x[0], repr(x[1])))[:3]
                law["unless"] = sorted(down, key=lambda x: (-x[0], repr(x[1])))[:3]
        keep = {(d, i, law["cond"]) for d, rules in laws.items() for i, law in enumerate(rules)}
        for key in [key for key in od["pairs"] if key not in keep]:
            del od["pairs"][key]
        od["watch"] = ([{"c": c, "d": d, "i": i, "up": up, "k": k, "nf": nf, "E": E, "need": need, "bar": bar}
                        for _, _, c, d, i, up, k, nf, E, need in
                        sorted(near, key=lambda x: (x[0], x[1], repr(x[3]), x[4]))[:NERVES]]
                       if os.environ.get("NOVALIE_NERVES", "1") != "0" else [])
        named = self.named_senses()
        if (not laws and Kany[0] and od["looks"] >= 3 and j in named and not L.exact()
                and not self.__dict__.get("clocks") and os.environ.get("NOVALIE_CLOCKS", "1") != "0"):
            self.clocks = set(named)
            self.emit("clocks", sensor=j + 1, senses=len(named))
            self.decide("clocks", j + 1, {"senses": sorted(i + 1 for i in named)})
        verdict = None
        if (not laws and not found and not always and Kany[0] and not L.exact()
                and (L.__dict__.get("moment") or {}).get("revised", 0) >= 1):
            lift, judged, chain = 0.0, 0, od["chain"]
            ref = min(Kany[0], od["n"][0] / 2)
            for c, (nc, _, _, hv) in rows.items():
                if nc < ref:
                    continue
                E = sum(h * (sum(chain[v][1].values()) + 0.5) / (chain[v][0] + 1) for v, h in hv.items() if v in chain)
                rate = E / nc
                if not 0 < rate < 1:
                    continue
                judged += 1
                if kl_digits(nc, nc, rate) < bar:
                    lift = math.inf
                    break
                lo, hi = int(E), nc
                while hi - lo > 1:
                    mid = (lo + hi) // 2
                    lo, hi = (lo, mid) if kl_digits(nc, mid, rate) >= bar else (mid, hi)
                q = hi / nc
                lift = max(lift, math.inf if q >= 1 else (q / (1 - q)) / (rate / (1 - rate)))
            if judged and lift <= 2.0:
                verdict = {"lift": round(lift, 2), "rows": judged, "of": len(rows), "tests": H, "at": self.world_steps,
                           "rate": round(Kany[0] / max(1, od["n"][0]), 4)}
        if verdict and not od["verdict"]:
            self.emit("lawless", sensor=j + 1, lift=verdict["lift"], rate=verdict["rate"], rows=verdict["rows"])
            self.decide("lawless", j + 1, {"lift": verdict["lift"], "rate": verdict["rate"], "rows": verdict["rows"]})
        od["verdict"] = verdict
        if od.get("pair_from") != od.get("from", 1):
            od["pair_from"], od["pair_next"] = od.get("from", 1), 50
        if (od["steps"] >= od.get("pair_next", 50) and self.gene("pairs")
                and j in self.named_senses()):
            od["pair_next"] = 2 * od["steps"]
            od["pair_looks"] = od.get("pair_looks", 0) + 1
            self.judge_pairs(j, had)

    @staticmethod
    def odds_restate(L, d, i, law, R, chain, rank, k, nf, base, H):
        """A law's odds as they are now."""
        tot_n = sum(nv for v, (nv, _) in chain.items() if L.chain_rate(v, d, chain) is not None)
        tot_k = sum(kv.get(d, 0) for v, (nv, kv) in chain.items())
        law.update(q=round(k / nf, 4), p=round(max(0, tot_k - k) / max(1, tot_n - nf), 4), base=round(base, 4),
                   digits=round(rank[1] if len(rank) > 1 else rank[0], 1), tests=H, n=nf, k=k)

    def judge_pairs(self, j, had):
        """Two things together (a change that hangs on both, when neither alone passes its rule)."""
        L = self.learners[j]
        od = L.odds
        lg = L.__dict__.get("pair_log")
        if not lg or len(lg["t"]) < 2 or od.get("determined"):
            return
        t0 = od.get("from", 1)
        T, C, B, D = (list(lg[k]) for k in ("t", "conds", "before", "d"))
        idx = [k for k, t in enumerate(T) if t >= t0]
        ds = sorted({d for (l, d) in od["K"]}, key=repr)
        held_by_moments = moment_holds(L.__dict__.get("moment"))
        F = len(lg["id"])
        inv = {v: c for c, v in lg["id"].items()}
        alone = collections.Counter((c[0], c[1]) for c in lg["id"])
        pairs_n = F * (F - 1) // 2 - sum(n * (n - 1) // 2 for n in alone.values())
        H2 = 2 * max(1, pairs_n) * max(1, len(ds))
        bar2 = EVIDENCE + math.log10(H2) + math.log10(1 + od["revised"]) + paid(od["pair_looks"])

        def digits_of(n, k, E, up):
            base = E / n
            quick = kl_digits(n, k, base) if up else kl_digits(n, n - k, 1 - base)
            if n > 400:
                return quick
            return evidence(n, k, base) if up else evidence(n, n - k, 1 - base)

        report = od.setdefault("pair_report", [])
        for d in ds:
            rules = od["laws"].get(d, [])
            i = len(rules)
            if i >= ODDS_RULES or i != had.get(d, 0):
                continue
            prior = [lg["id"].get(tuple(r["cond"])) for r in rules]
            chain = L.level_chain(d, i)
            acts, changes, rates = [], [], []
            for k in idx:
                ids = C[k]
                if any(c is not None and c in ids for c in prior):
                    continue
                r = L.chain_rate(B[k], d, chain)
                if r is None:
                    continue
                acts.append(ids)
                changes.append(0 if D[k] == d else -1)
                rates.append([r])
            if len(acts) < 2 or not any(c == 0 for c in changes):
                continue
            thr = bar2 + paid(2) - 3
            cand = gpu.pair_candidates([list(a) for a in acts], F, changes, rates, 1, thr)
            where = collections.defaultdict(list)
            wanted = {x for p in cand for x in p}
            for row, ids in enumerate(acts):
                for x in ids:
                    if x in wanted:
                        where[x].append(row)
            best, looked = None, 0
            for a, b in sorted(cand):
                ca, cb = inv[a], inv[b]
                ra, rb = where[a], where[b]
                rows = sorted(set(ra) & set(rb))
                nf = len(rows)
                if nf < 2 or nf == len(ra) or nf == len(rb):
                    continue
                if alone[(ca[0], ca[1])] < 2 or alone[(cb[0], cb[1])] < 2:
                    continue
                looked += 1
                k = sum(changes[r] == 0 for r in rows)
                E = sum(rates[r][0] for r in rows)
                up = k > E
                dig = digits_of(nf, k, E, up)
                bar = bar2 + paid(cond_depth(ca) + cond_depth(cb))
                if dig < bar:
                    continue
                more = True
                for rs in (ra, rb):
                    kx, Ex = sum(changes[r] == 0 for r in rs), sum(rates[r][0] for r in rs)
                    if (kx > Ex) == up and digits_of(len(rs), kx, Ex, up) >= dig:
                        more = False
                if not more:
                    continue
                cause = causal(ca) and causal(cb)
                if (up and k == nf and cause and held_by_moments
                        and not any(act_beyond(x, L.__dict__.get("moment")) for x in (ca, cb))):
                    continue
                rank = (cause, round(dig, 9), repr(sorted((ca, cb), key=repr)))
                if best is None or rank > best[0]:
                    best = (rank, ca, cb, k, nf, E / nf, up, dig, bar)
            report.append({"at": self.world_steps, "d": str(d), "level": i, "acts": len(acts), "F": F,
                           "bar": round(bar2 + paid(2), 2), "candidates": len(cand), "looked": looked,
                           "best": None if best is None else [list(best[1]), list(best[2]), round(best[7], 1)]})
            del report[:-room(40)]
            if best is not None:
                _, ca, cb, k, nf, base, up, dig, bar = best
                self.make_pair_law(j, d, i, ca, cb, k, nf, base, up, dig, bar, H2)

    def make_pair_law(self, j, d, i, ca, cb, k, nf, base, up, dig, bar, H2):
        """A law of two things together believed."""
        L = self.learners[j]
        od = L.odds
        parts = tuple(sorted((ca, cb), key=repr))
        name = pair_name(parts)
        PAIRS.setdefault(name, parts)
        names = self.__dict__.setdefault("pair_names", [])
        if name not in names:
            names.append(name)
            self.pair_backfill(name)
        c = (0, name, 1)
        rules = od["laws"].get(d, [])
        R = od["rows"] if i == 0 else od["levels"][d][i]["rows"]
        chain = L.level_chain(d, i)
        known = law_shape(c, d, up) in (self.__dict__.get("law_shapes") or {})
        law = {"cond": c, "d": d, "level": i, "up": up, "q": 0.0, "p": 0.0, "base": 0.0, "digits": 0.0,
               "tests": H2, "n": nf, "k": k, "q0": (k + 0.5) / (nf + 1), "lr": 0.0, "n1": 0, "k1": 0, "cal": {},
               "at": self.world_steps, "unless": [], "especially": [], "known": known, "parts": list(parts),
               "depth": cond_depth(c), "bar": round(bar, 2)}
        shp = self.__dict__.setdefault("law_shapes", {}).setdefault(law_shape(c, d, up), {"worlds": set(), "n": 0})
        shp["n"] += 1
        shp["worlds"].add(self.k)
        self.odds_restate(L, d, i, law, R, chain, (dig,), k, nf, base, H2)
        law["digits"] = round(dig, 1)
        self.journal_begin("odds", ("odds", self.k, j, repr(c), repr(d)), sensor=j + 1, level=i, up=up, known=known,
                           n=nf, digits=round(dig, 1), margin=round(dig - bar, 1), depth=cond_depth(c),
                           cause=causal(ca) and causal(cb))
        rules.append(law)
        od["laws"][d] = rules
        od["verdict"] = None
        lv = od["levels"].setdefault(d, [None])
        conds = [r["cond"] for r in rules]
        lv.append(self.odds_count(j, without=conds))
        shown = d if type(d) is int else str(d[1])
        show = lambda p: [p[0], p[1], p[2] if isinstance(p[2], (int, float, str)) else str(p[2])]
        self.emit("odds", sensor=j + 1, cond=[0, name, 1], parts=[show(p) for p in parts], d=shown, up=up,
                  q=law["q"], p=law["p"], base=law["base"], digits=law["digits"], tests=H2, level=i, known=known)
        self.decide("odds", j + 1, {"cond": [0, name, 1], "parts": [show(p) for p in parts], "d": shown, "up": up,
                                    "q": law["q"], "p": law["p"], "base": law["base"], "digits": law["digits"],
                                    "tests": H2, "level": i, "known": known})

    def pair_backfill(self, name):
        """A pair just made: what it lived before is counted with it too."""
        cols_all, acts_all = [M.colors for M in self.learners], (self.learners[0].actions if self.learners else [])
        for j2, L2 in enumerate(self.learners):
            lg = L2.__dict__.get("pair_log")
            od = L2.__dict__.get("odds")
            if not lg or not od or not odds_key(0, name, j2):
                continue
            ids = lg["id"]
            plain = not any(is_pair(p[1]) for p in PAIRS[name])
            pids = [ids.get(p) for p in PAIRS[name]]
            nid = {1: ids.setdefault((0, name, 1), len(ids)), 0: ids.setdefault((0, name, 0), len(ids))}
            t0 = od.get("from", 1)
            T, C, B, D = (list(lg[k]) for k in ("t", "conds", "before", "d"))
            for k in range(len(T)):
                ids_t = C[k]
                if plain:
                    val = int(all(p is not None and p in ids_t for p in pids))
                else:
                    val = int(bool(self.cond_at((0, name, 1), T[k], cols_all, acts_all)))
                ids_t = C[k] = array.array("I", sorted(set(ids_t) | {nid[val]}))
                if T[k] < t0:
                    continue
                key = [(0, name, val)]
                before, dd = B[k], D[k]
                L2.count_rows(od["rows"], key, before, dd)
                for d2, lv in (od.get("levels") or {}).items():
                    rules2 = od["laws"].get(d2, [])
                    for i2 in range(1, len(lv)):
                        if lv[i2] is None:
                            continue
                        if any(lg["id"].get(tuple(r["cond"])) in ids_t for r in rules2[:i2]):
                            continue
                        L2.count_rows(lv[i2]["rows"], key, before, dd)
                for (d2, i2, c1), table in (od.get("pairs") or {}).items():
                    rules2 = od["laws"].get(d2, [])
                    cid = lg["id"].get(tuple(c1))
                    if cid is None or cid not in ids_t or any(lg["id"].get(tuple(r["cond"])) in ids_t for r in rules2[:i2]):
                        continue
                    L2.count_rows(table, key, before, dd)
            lg["conds"] = collections.deque(C)

    @staticmethod
    def seen_at(t, cols, acts, named=None):
        """What it saw at act t of what it lived here."""
        ordinal = {i for i, c in enumerate(cols) if len(set(c[max(0, t - 4095):t + 1])) > 2}
        return seen_with([c[t] for c in cols], [c[t - 1] for c in cols] if t >= 1 else None, acts[t - 1], ordinal,
                         named)

    @classmethod
    def cond_at(cls, c, t, cols, acts):
        """Did condition c hold at act t of what it lived here."""
        l, attr, v = c
        if is_pair(attr):
            got = [cls.cond_at((l + p[0], p[1], p[2]), t, cols, acts) for p in PAIRS.get(attr, ())]
            if not got or any(g is None for g in got):
                return None
            return all(got) == bool(v)
        s0 = t - l
        if s0 < 1:
            return None
        if attr == "act":
            return acts[s0 - 1] == v
        if attr[0] == "s":
            return cols[int(attr[1:])][s0] == v
        return cls.seen_at(s0, cols, acts).get(attr) == v

    def keys_at(self, t, j, cols, acts):
        """The things it saw at act t and before, as its laws of odds for sense j count them."""
        keys = []
        named = self.named_senses()
        for l in ODDS_LAGS:
            if t - l < 1:
                break
            if l <= max(ODDS_NEAR, ODDS_CLOSE):
                st = self.seen_at(t - l, cols, acts, named)
            else:
                st = {f"s{x}": cols[x][t - l] for x in range(len(cols)) if x in named}
                st["act"] = acts[t - l - 1]
            keys += [(l, attr, v) for attr, v in st.items() if odds_key(l, attr, j)]
        for name in self.__dict__.get("pair_names") or ():
            if odds_key(0, name, j):
                keys.append((0, name, 1 if self.cond_at((0, name, 1), t, cols, acts) else 0))
        return keys

    def odds_again(self, j, drifted):
        """Its laws of odds for sense j no longer hold."""
        L = self.learners[j]
        od = L.odds
        t0 = max(1, drifted["from"])
        od["from"] = t0
        got = self.odds_count(j, since=t0)
        n, K, Kany = collections.Counter(), collections.Counter(), collections.Counter()
        for t in range(t0, len(L.colors)):
            d = change_of(L.colors[t - 1], L.colors[t])
            for l in ODDS_LAGS:
                if t - l < 1:
                    break
                n[l] += 1
                if d is not None:
                    K[(l, d)] += 1
                    Kany[l] += 1
        gone = sum(len(r) for r in od["laws"].values())
        for d, rules in od["laws"].items():
            for r in rules:
                self.journal_end(("odds", self.k, j, repr(r["cond"]), repr(d)), "broken")
        od.update(rows=got["rows"], chain=got["chain"], n=n, K=K, Kany=Kany, laws={}, levels={}, pairs={}, verdict=None,
                  determined=None, drifted=None, steps=len(L.colors) - t0, revised=od["revised"] + 1, again=collections.Counter())
        od["next"] = od["steps"] + max(50, od["steps"] // 10) if od["steps"] < 50 else od["steps"]
        cond = [drifted["cond"][0], drifted["cond"][1], str(drifted["cond"][2])]
        self.emit("odds_drift", sensor=j + 1, cond=cond, since=t0, against=drifted["against"], laws=gone)
        self.decide("odds_drift", j + 1, {"cond": cond, "since": t0, "against": drifted["against"], "laws": gone,
                                          "after": drifted["n1"], "came": drifted["k1"]})

    def lived(self, j, since=None, most=None):
        """What it lived here for sense j, act by act, as see_odds counted it."""
        most = room(20_000) if most is None else most
        Ls = self.learners
        L, acts = Ls[j], Ls[0].actions
        start = max(1, len(L.colors) - most, (L.__dict__.get("odds") or {}).get("from", 1), since or 1)
        lg = L.__dict__.get("pair_log") or {}
        names = {i: c for c, i in (lg.get("id") or {}).items()}
        pairs = [n for n in (self.__dict__.get("pair_names") or ()) if odds_key(0, n, j)]
        ts = lg.get("t") or ()
        first = ts[0] if ts else len(L.colors)
        cols = None
        for t in range(start, min(first, len(L.colors))):
            if cols is None:
                cols = [M.colors for M in Ls]
            yield t, self.keys_at(t, j, cols, acts), L.colors[t - 1], change_of(L.colors[t - 1], L.colors[t]), None
        if not ts:
            return
        k0 = bisect.bisect_left(ts, start)
        rows = zip(*(itertools.islice(lg[k], k0, None) for k in ("t", "conds", "before", "d")))
        for t, conds, before, d in rows:
            if t >= len(L.colors):
                break
            ids = set(conds)
            keys = [names[x] for x in conds if not is_pair(names[x][1])]
            keys += [(0, n, 1 if self.log_holds((0, n, 1), ids, lg["id"]) else 0) for n in pairs]
            yield t, keys, before, d, ids

    def held_then(self, c, t, here, ids, idmap):
        """Did condition c hold at act t."""
        if c in here or not is_pair(c[1]):
            return c in here
        if ids is not None:
            return self.log_holds(c, ids, idmap)
        Ls = self.learners
        return bool(self.cond_at(c, t, [M.colors for M in Ls], Ls[0].actions))

    @classmethod
    def log_holds(cls, c, ids, idmap):
        """Did condition c hold at an act whose things."""
        l, attr, v = c
        if is_pair(attr):
            parts = PAIRS.get(attr, ())
            return bool(parts) and all(cls.log_holds((l + p[0], p[1], p[2]), ids, idmap) for p in parts) == bool(v)
        x = idmap.get(c)
        return x is not None and x in ids

    def odds_count(self, j, since=None, without=(), most=None):
        """Over what it lived here."""
        L = self.learners[j]
        idmap = (L.__dict__.get("pair_log") or {}).get("id") or {}
        rows, chain = {}, {}
        for t, keys, before, d, ids in self.lived(j, since, most):
            if without:
                here = set(keys)
                if any(self.held_then(c, t, here, ids, idmap) for c in without):
                    continue
            L.count_chain(chain, before, d)
            L.count_rows(rows, keys, before, d)
        return {"rows": rows, "chain": chain}

    def odds_pairs(self, j, d, i, c1, conds):
        """For the law of change d at place i of its list."""
        od = self.learners[j].odds
        key = (d, i, c1)
        if key in od["pairs"]:
            return od["pairs"][key]
        L = self.learners[j]
        idmap = (L.__dict__.get("pair_log") or {}).get("id") or {}
        prior = list(conds[:i])
        table = {}
        for t, keys, before, dd, ids in self.lived(j):
            here = set(keys)
            if not self.held_then(c1, t, here, ids, idmap) or any(self.held_then(x, t, here, ids, idmap) for x in prior):
                continue
            L.count_rows(table, [None] + [c2 for c2 in keys if c2 != c1], before, dd)
        od["pairs"][key] = table
        return table

    @staticmethod
    def odds_target(L, v, d):
        """Where a change d takes a sense from v."""
        t = (v + d) if type(d) is int and type(v) is int else (d[1] if isinstance(d, tuple) else None)
        return t if t in (L.__dict__.get("seen_freq") or ()) else None

    @staticmethod
    def list_odds(od, rules, held):
        """The odds of a change from its list of laws."""
        plain = held

        def held(c):
            l, attr, v = c
            if is_pair(attr):
                hs = [held((l + p[0], p[1], p[2])) for p in PAIRS.get(attr, ())]
                if not hs or any(h is None for h in hs):
                    return None
                x = math.prod(hs)
                return x if v else 1 - x
            return plain(c)

        def excepted(q, es):
            for i, e in enumerate(es):
                h2 = held(tuple(e[1]))
                if h2:
                    return h2 * e[2] + (1 - h2) * excepted(q, es[i + 1:])
            return q

        out, left = 0.0, 1.0
        for law in rules:
            h = held(law["cond"])
            if h is None:
                c = law["cond"]
                h = od["rows"].get(c, [0])[0] / max(1, od["n"][c[0]])
            q = excepted(law["q"], law["unless"] + law["especially"])
            out += left * h * q
            left *= 1 - h
        return out + left * rules[-1]["p"]

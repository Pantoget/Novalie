# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its ways of working and its genes."""

import collections
import math
import time

from ..config import EVIDENCE, GENES, READ_WAYS, WAYS, WAY_BOUNDS
from ..evidence import evidence


class Ways:
    def choose_ways(self):
        """How it will work in this world."""
        if not self.ways:
            self.ways = {name: {"options": list(options), "stats": {}} for name, options in WAYS.items()}
        now, why = {}, {}
        for name, w in self.ways.items():
            total = sum(w["stats"].get(str(o), (0,))[0] for o in w["options"])
            best, pick, reason = None, None, ""
            for opt in w["options"]:
                n, mean, m2 = tuple(w["stats"].get(str(opt), (0, 0.0, 0.0)))[:3]
                if n == 0:
                    score, r = math.inf, "untried"
                else:
                    room = 1.5 * math.sqrt(2.0 * math.log(total + 1) / n)
                    score, r = mean + room, ("best" if room < 0.5 else "curious")
                if best is None or score > best:
                    best, pick, reason = score, opt, r
            now[name], why[name] = pick, reason
        self.ways_now, self.ways_why = now, why
        self.decide("ways", {k: str(v) for k, v in now.items()}, why)
        self._invent_at = None
        self.episode_at = getattr(self, "world_steps", 0)

    @staticmethod
    def way_row(w, o):
        """How one option of a way did, for its page."""
        n, mean, m2, ok, logs = (tuple(w["stats"].get(str(o), ())) + (0, 0.0, 0.0, None, None))[:5]
        presses = round(2 ** (logs / n)) if n and logs is not None else (round(2 ** -mean) if n else 0)
        return {"value": str(o), "n": n, "ok": ok, "presses": presses}

    def decide(self, what, choice, why):
        """What it decided, and why, kept for its page."""
        if getattr(self, "decisions", None) is None:
            self.decisions = collections.deque(maxlen=40)
        self.decisions.append({"what": what, "choice": choice, "why": why, "world": self.k, "t": round(time.time())})

    def way(self, name, default):
        return (getattr(self, "ways_now", None) or {}).get(name, default)

    def gene(self, name):
        """How it is built now, in one of its genes."""
        trial = self.__dict__.get("_gene_trial") or {}
        if name in trial:
            return trial[name]
        return (self.__dict__.get("genome") or {}).get(name, GENES[name][0])

    def gene_result(self, gene, value, better, worse):
        """One trial of a gene of its."""
        trials = self.__dict__.setdefault("gene_trials", {})
        row = trials.setdefault(f"{gene}={value}", [0, 0, 0])
        if len(row) < 3:
            row.append(row[0])
        row[2] += 1
        if better:
            row[0] += 1
            row[1] += 1
        elif worse:
            row[0] += 1
        n, k = row[0], row[1]
        tried = sum(len(v) - 1 for v in GENES.values())
        bar = EVIDENCE + math.log10(max(1, tried)) + math.log10(max(1, n))
        if n and k > n / 2 and evidence(n, k, 0.5) >= bar:
            genome = self.__dict__.setdefault("genome", {})
            was = genome.get(gene, GENES[gene][0])
            genome[gene] = value
            change = {"gene": gene, "from": was, "to": value, "n": n, "wins": k, "digits": round(evidence(n, k, 0.5), 1),
                      "bar": round(bar, 1), "t": round(time.time())}
            self.__dict__.setdefault("gene_changes", []).append(change)
            for key in [key for key in trials if key.startswith(gene + "=")]:
                del trials[key]
            self.emit("self_change", **{k2: (str(v) if k2 in ("from", "to") else v) for k2, v in change.items()})
            self.decide("self_change", gene, {k2: str(v) for k2, v in change.items()})
            return change
        return None

    def read_way(self, name):
        """One of its ways of reading, as it chose it for this episode."""
        rw = self.__dict__.setdefault("read_ways", {})
        if name not in rw:
            rw[name] = {"options": list(READ_WAYS[name]), "stats": {}, "now": None, "judged": 0}
        w = rw[name]
        if w["now"] is None:
            total = sum(w["stats"].get(str(o), (0,))[0] for o in w["options"])
            best = None
            for o in w["options"]:
                n, mean = tuple(w["stats"].get(str(o), (0, 0.0)))[:2]
                score = math.inf if n == 0 else mean + 1.5 * math.sqrt(2.0 * math.log(total + 1) / n)
                if best is None or score > best[0]:
                    best = (score, o)
            w["now"] = best[1]
            self.decide("read_way", name, {"value": w["now"], "tried": total})
        return w["now"]

    def judge_read(self, names, reward):
        """How the ways of reading it used in an episode did."""
        rw = self.__dict__.setdefault("read_ways", {})
        for name in names:
            w = rw.get(name)
            if not w or w["now"] is None:
                continue
            n, mean = tuple(w["stats"].get(str(w["now"]), (0, 0.0)))[:2]
            n += 1
            mean += (reward - mean) / n
            w["stats"][str(w["now"])] = (n, mean)
            w["now"], w["judged"] = None, w["judged"] + 1
            if w["judged"] % 10 == 0:
                tried = sorted((w["stats"][str(o)][1], o) for o in w["options"] if w["stats"].get(str(o), (0,))[0] >= 2)
                if tried:
                    best = tried[-1][1]
                    values = sorted(v for _, v in tried)
                    k = values.index(best)
                    if k == len(values) - 1:
                        new = best * 1.4
                    elif k == 0:
                        new = best * 0.7
                    else:
                        sc = {v: m for m, v in tried}
                        new = (best + (values[k + 1] if sc[values[k + 1]] >= sc[values[k - 1]] else values[k - 1])) / 2
                    new = max(1, int(round(new)))
                    if new not in w["options"]:
                        w["options"].append(new)
                        self.emit("new_way", way=name, value=new, best=best)

    def judge_ways(self, understood, steps=None, scale=1):
        """How the ways it chose did in the world it leaves, or in an episode of the real world."""
        now = getattr(self, "ways_now", None)
        if not now or not self.ways:
            return
        steps = self.world_steps if steps is None else steps
        r = -math.log2(max(1, steps / max(1, scale))) - (0.0 if understood else 3.0)
        for name, opt in now.items():
            st = self.ways.get(name, {}).get("stats")
            if st is None:
                continue
            n, mean, m2, ok, logs = (tuple(st.get(str(opt), ())) + (0, 0.0, 0.0, 0, 0.0))[:5] if str(opt) in st else (0, 0.0, 0.0, 0, 0.0)
            n += 1
            d = r - mean
            mean += d / n
            m2 += d * (r - mean)
            st[str(opt)] = (n, mean, m2, ok + bool(understood), logs + math.log2(max(1, steps)))
        self.worlds_judged += 1
        if self.worlds_judged % 20 == 0:
            self.new_ways()

    def new_ways(self):
        """A way of working it never had."""
        for name, w in self.ways.items():
            nums = [o for o in w["options"] if isinstance(o, (int, float)) and not isinstance(o, bool)]
            tried = [(w["stats"][str(o)][1], o) for o in nums if w["stats"].get(str(o), (0,))[0] >= 3]
            if not tried:
                continue
            best = max(tried)[1]
            lo, hi = WAY_BOUNDS.get(name, (0, math.inf))
            values = sorted(v for _, v in tried)
            i = values.index(best)
            if i == len(values) - 1:
                new = best * 1.4
            elif i == 0:
                new = best * 0.7
            else:
                score = {v: m for m, v in tried}
                side = values[i + 1] if score[values[i + 1]] >= score[values[i - 1]] else values[i - 1]
                new = (best + side) / 2
            new = min(hi, max(lo, new))
            new = int(round(new)) if isinstance(best, int) else round(new, 2)
            if new in w["options"]:
                continue
            w["options"].append(new)
            self.emit("new_way", way=name, value=new, best=best)
            if len(w["options"]) > 6:
                worst = min(((w["stats"][str(o)][1], o) for o in w["options"]
                             if w["stats"].get(str(o), (0,))[0] >= 3 and o != new), default=None)
                if worst is not None:
                    w["options"].remove(worst[1])

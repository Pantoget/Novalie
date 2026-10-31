# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Twins: how it is built, judged on its real life."""

import math
import time

from ..config import EVIDENCE, GENES, TWIN_GENES, room
from ..evidence import sign_digits


class Twins:
    # -- twins: how it is built, judged on its real life ---------------------------------------------------
    def twin_start(self, o):
        genome = dict(self.__dict__.get("genome") or {})
        options = [(g, v) for g in TWIN_GENES for v in GENES[g] if v != genome.get(g, GENES[g][0])]
        if not options:
            return None
        trials = self.__dict__.setdefault("life_trials", {})
        g, v = min(options, key=lambda gv: (trials.get(f"{gv[0]}={gv[1]}", {}).get("tried", 0),
                                            gv[1] != GENES[gv[0]][0], TWIN_GENES.index(gv[0]), repr(gv[1])))
        named = sorted(self.named_senses())
        sensors = [self.world.sensors[j] for j in named]
        recall = self.recall_of_senses()
        pair = []
        for change in (None, (g, v)):
            s = Shadow()
            s.genome = dict(genome, **({change[0]: change[1]} if change else {}))
            s.enter(world=Replay(self.world.buttons, sensors, tuple(o[j] for j in named)))
            if s.gene("recall"):
                s.take_recall(recall)
            pair.append(s)
        self._twins = {"g": g, "v": v, "pair": pair, "named": named, "k": 0, "n": 0, "acts": 0, "options": len(options)}
        return self._twins

    def twins_see(self, a, o):
        tw = self.__dict__.get("_twins")
        if tw is None:
            if self.world_steps >= 600:
                self.twin_start(o)
            return
        shown = tuple(o[j] for j in tw["named"])
        fore = [s.foresee_next(a) for s in tw["pair"]]
        for s in tw["pair"]:
            s.world.shown = shown
            s.choose = lambda a=a: a
            s.step()
            s.__dict__.pop("choose", None)
        for i in range(len(shown)):
            ra, rb = (fore[n][i][0] == tw["pair"][n].seen_now[i] for n in (0, 1))
            if ra != rb:
                tw["n"] += 1
                tw["k"] += rb
        tw["acts"] += 1
        bar = EVIDENCE + math.log10(max(1, tw["options"]))
        better, worse = sign_digits(tw["k"], tw["n"]), sign_digits(tw["n"] - tw["k"], tw["n"])
        verdict = "better" if better >= bar else "worse" if worse >= bar else "even" if tw["acts"] >= room(3600) else None
        if verdict is None:
            return
        key = f"{tw['g']}={tw['v']}"
        row = self.life_trials.setdefault(key, {"tried": 0})
        row.update(tried=row["tried"] + 1, verdict=verdict, acts=tw["acts"], n=tw["n"], wins=tw["k"],
                   digits=round(max(better, worse), 1), bar=round(bar, 1), t=round(time.time()))
        self._twins = None
        self.decide("life_trial", tw["g"], {"to": str(tw["v"]), "verdict": verdict, "digits": row["digits"],
                                            "acts": tw["acts"]})
        if verdict == "better":
            genome = self.__dict__.setdefault("genome", {})
            change = {"gene": tw["g"], "from": genome.get(tw["g"], GENES[tw["g"]][0]), "to": tw["v"], "n": tw["n"],
                      "wins": tw["k"], "digits": row["digits"], "bar": row["bar"], "t": row["t"], "where": "life"}
            genome[tw["g"]] = tw["v"]
            self.__dict__.setdefault("gene_changes", []).append(change)
            self.emit("self_change", **{k2: (str(v2) if k2 in ("from", "to") else v2) for k2, v2 in change.items()})

    def twins_view(self):
        """Its trials of how it is built on its real life, for its page."""
        tw = self.__dict__.get("_twins")
        now = None if tw is None else {"gene": tw["g"], "to": str(tw["v"]), "acts": tw["acts"], "n": tw["n"],
                                       "wins": tw["k"]}
        return {"now": now, "judged": {k: dict(v) for k, v in (self.__dict__.get("life_trials") or {}).items()},
                "genome": {g: str(self.gene(g)) for g in GENES}}

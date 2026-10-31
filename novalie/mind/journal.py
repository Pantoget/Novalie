# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its journal: every belief, when and how it was born, and its fate."""

import time

from ..config import room


class Journal:
    # -- the journal of its mind (H4): every belief, when it was born and how, and what became of it ------------------
    def journal_begin(self, kind, what, **facts):
        """A belief born, kept in its journal with its world and act, the tool that made it and the evidence it
        had."""
        jr = self.__dict__.setdefault("journal", [])
        n = self.__dict__.get("journal_n", 0) + 1
        self.journal_n = n
        source = facts.pop("source", "@1")
        rec = {"id": n, "kind": kind, "what": what, "world": self.k, "at": self.world_steps, "t": round(time.time()),
               "from": source, "facts": facts, "end": None}
        rec["doubt"] = self.self_doubt(kind, facts)
        if (kind in ("odds", "moment") and facts.get("sensor") is not None
                and facts["sensor"] - 1 == self.__dict__.get("_control")):
            self.control_mark("laws" if kind == "odds" else "moments")
        jr.append(rec)
        self.__dict__.setdefault("journal_open", {})[what] = rec
        if len(jr) > room(20_000):
            for i, old in enumerate(jr):
                if old["end"] is not None:
                    del jr[i]
                    break
            else:
                del jr[0]
        return rec

    def journal_end(self, what, how):
        """A belief let go."""
        rec = (self.__dict__.get("journal_open") or {}).pop(what, None)
        if rec is not None:
            rec["end"] = {"at": self.world_steps, "world": self.k, "how": how, "t": round(time.time())}
        return rec

    @staticmethod
    def doubt_key(kind, facts):
        """What its doubt of a belief is judged by."""
        margin = facts.get("margin")
        step = None if margin is None else min(4, max(0, int(margin // 5)))
        return (kind, step, facts.get("depth", 1) > 1)

    def self_doubt(self, kind, facts):
        """Its doubt of a belief at its birth, from its journal."""
        stats = self.__dict__.get("journal_stats")
        if stats is None:
            stats = self.journal_stats = {}
        got = stats.get(self.doubt_key(kind, facts))
        if not got:
            return None
        n, gone = got
        return round((gone + 0.5) / (n + 1), 4)

    def journal_close_world(self):
        """Its world ends: every belief of it still held lasted to the end."""
        for what in list((self.__dict__.get("journal_open") or {})):
            rec = self.journal_open[what]
            if rec["world"] == self.k and rec["kind"] in ("odds", "moment", "concept", "made"):
                self.journal_end(what, "world ended")
        stats = self.__dict__.setdefault("journal_stats", {})
        for rec in self.__dict__.get("journal") or ():
            if rec["end"] is not None and not rec.get("counted"):
                rec["counted"] = True
                if rec["kind"] == "self":
                    continue
                key = self.doubt_key(rec["kind"], rec["facts"])
                n, gone = stats.get(key, (0, 0))
                stats[key] = (n + 1, gone + (rec["end"]["how"] != "world ended"))

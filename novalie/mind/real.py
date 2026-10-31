# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its real life: its senses of itself, memory and recall."""

import hashlib
import os
import pickle
import time

from .. import config
from ..body import RealWorld, sense_key
from ..evidence import coarse
from ..parts import council


class RealLife:
    def named_senses(self):
        """The senses its laws may name."""
        named = getattr(self.__dict__.get("world"), "named", None)
        return frozenset(range(len(self.__dict__.get("learners") or ()))) if named is None else frozenset(named)

    def self_senses(self):
        """Its senses of itself, each a small whole number as it is now."""
        inventing = int(self.__dict__.get("_inventing") is not None)
        ws, now = self.__dict__.get("workshop_view") or {}, time.time()
        pace = coarse(ws.get("per_second") or 0.0) if now - (ws.get("t") or 0) <= 60 else 0
        took = self.__dict__.get("journal_n", 0) + self.__dict__.get("meanings_made", 0)
        learned = coarse(took - self.__dict__.get("_took_total", took))
        self._took_total = took
        total = self.__dict__.get("acts_read", 0)
        read = coarse(total - self.__dict__.get("_read_total", total))
        self._read_total = total
        bit = hashlib.sha256(b"novalie control %d" % self.steps).digest()[0] & 1
        return (inventing, pace, learned, read, bit)

    def abilities_view(self):
        """Its awareness, causal knowledge and feeling, for its page."""
        w = self.__dict__.get("world")
        if not isinstance(w, RealWorld) or not w.body:
            return None
        sensors, L = list(w.sensors), self.learners
        laws = lambda j: (L[j].__dict__.get("odds") or {}).get("laws") or {}
        selfish = [j for j, s in enumerate(sensors) if s[0] in ("body", "self") and j < len(L)]
        causes = []
        for j, s in enumerate(sensors):
            if j < len(L) and s[0] != "control":
                for d, rules in laws(j).items():
                    for r in rules:
                        _, attr, v = r["cond"]
                        if attr == "act" and isinstance(v, int) and 0 <= v < len(w.buttons):
                            causes.append({"sense": sense_key(s), "act": w.buttons[v][0], "up": bool(r.get("up")),
                                           "change": str(d), "q": round(r.get("q", 0.0), 2)})
        fw = (self.__dict__.get("this_start") or {}).get("foresaw") or {}
        e, n = self.__dict__.get("_effect"), self.__dict__.get("effect_counts") or {}
        brought = [{"sense": sense_key(sensors[j]), "act": w.buttons[v][0], "n": c[0], "k": c[1]}
                   for j, rows in sorted((self.__dict__.get("effect_tally") or {}).items()) if j < len(sensors)
                   for v, c in sorted(rows.items()) if 0 <= v < len(w.buttons)]
        return {"aware": {"senses": len(selfish), "laws": sum(sum(len(r) for r in laws(j).values()) for j in selfish),
                          "sure": fw.get("sure") or [0, 0], "guess": fw.get("guess") or [0, 0]},
                "causes": causes[:24],
                "feel": {"act": w.buttons[e[0]][0] if e else None, "sense": sense_key(sensors[e[1]]) if e else None,
                         "came": n.get("came", 0), "broke": n.get("broke", 0), "brought": brought}}

    def control_mark(self, what):
        """Something its rule came to believe of its control."""
        this = self.__dict__.get("this_start")
        if this is not None:
            c = this.setdefault("control", {})
            c[what] = c.get(what, 0) + 1

    def go_real(self):
        """Its life in the real world."""
        self.real = True
        if not (isinstance(getattr(self, "world", None), RealWorld) and self.steps == 0):
            self.enter()
        self.start_record()

    def save(self):
        """Everything it knows, to its memory folder."""
        if getattr(self, "wiping", False):
            return
        os.makedirs(config.STATE_DIR, exist_ok=True)
        tmp = config.STATE_FILE + ".tmp"
        self.start_seen()
        for _ in range(5):
            try:
                with self.lock, open(tmp, "wb") as f:
                    pickle.dump(self, f)
                break
            except RuntimeError:
                time.sleep(0.05)
            except OSError:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        else:
            return
        if getattr(self, "wiping", False):
            try:
                os.remove(tmp)
            except OSError:
                pass
            return
        for i in range(10):
            try:
                if os.path.exists(config.STATE_FILE):
                    os.replace(config.STATE_FILE, config.STATE_FILE + ".prev")
                os.replace(tmp, config.STATE_FILE)
                self.share_recall()
                return
            except PermissionError:
                if i == 9:
                    raise
                time.sleep(0.2)

    def share_recall(self):
        """What it recalls of its real senses."""
        folder = os.path.join(config.STATE_DIR, "council")
        if config.BRAIN is not None or not isinstance(self.__dict__.get("world"), RealWorld) or not os.path.isdir(folder):
            return
        try:
            council.write_json(os.path.join(folder, "real_recall.json"), self.__dict__.get("real_recall") or {})
        except (OSError, TypeError, ValueError):
            pass

    def status(self):
        with self.lock:
            cells = sum(len(k[1]) for e in self.knowledge for k in e["kinds"])
            last = self.knowledge[-1] if self.knowledge else {}
            words = len(self.named_words())
            return {"worlds": len(self.knowledge), "cells": cells, "steps": self.steps, "world": self.k,
                    "born": round(self.born), "seen": len(self.seen_kinds), "read": self.reader.read_count,
                    "last_steps": last.get("steps", 0), "recognized": last.get("recognized", 0),
                    "sensors": last.get("sensors", 0), "kinds": len(self.library), "invented": len(self.inventions),
                    "articles": self.articles, "lookups": len(self.looked),
                    "worlds_total": self.worlds_understood, "kinds_seen": len(self.kinds_seen),
                    "known_words": len(self.known_words()), "reading": self.reading_now, "pruned": self.pruned,
                    "words": words, "size": last.get("size", 0), "visited": last.get("visited", 0),
                    "accuracy": round(last.get("accuracy", 0)), "novel": round(last.get("novel", 0))}

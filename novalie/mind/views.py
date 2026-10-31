# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""What its page shows."""

import collections
import csv
import io
import itertools
import math
import os
import threading
import time

from .. import config
from ..body import CODE, RealWorld, code_now, sense_key
from ..cells import seen_symbol, symbol
from ..config import GENES, ODDS_LAGS, WORD_EVIDENCE
from ..evidence import evidence, kl_digits, moment_trusted, trusted
from ..inventing import nature_text
from ..laws import PAIRS, is_pair, odds_symbol
from ..parts import gpu, nm
from ..text import fold
from ..web import palette, site_of


class Views:
    def reorganize(self):
        """It tidies the links its worlds built."""
        with self.lock:
            before = self.pruned
            for pair in list(self.together):
                self.together[pair] *= 0.97
                if self.together[pair] < 0.2:
                    del self.together[pair]
                    self.pruned += 1
            if self.pruned > before:
                self.emit("pruned", n=self.pruned - before)

    def known_words(self):
        named = self.named_words()
        linked = {w for pair in self.links for w in pair}
        return named + sorted((linked | set(self.related)) - set(named))

    def node_ids(self):
        """The id of each of its cells on the page."""
        ids = {seen_symbol(k): "s:" + seen_symbol(k) for k in self.seen_kinds}
        ids.update({symbol(k): "c:" + symbol(k) for k in self.kinds_seen})
        ids.update({name: "i:" + name for name in self.invented_seen})
        ids.update({name: "o:" + name for name in self.odds_seen})
        ids.update({name: "b:" + name for name in (self.__dict__.get("things") or {})})
        for gid, g in self.generals.items():
            ids.setdefault(gid, ("c:" if g["cell"] else "g:") + gid)
        return ids

    def graph(self):
        """Its network as it is now, for the page."""
        with self.lock:
            nodes, edges = {}, []
            ids = self.node_ids()
            links = collections.Counter()
            for (a, b), v in self.together.items():
                links[a] += v
                links[b] += v
            colours = {e["d"]: e["T"] for e in self.library}
            numbers = {}
            chosen = self.kinds_seen.most_common(120)
            have, per_shape = {k for k, _ in chosen}, collections.Counter()
            for kind, n in self.kinds_seen.most_common():
                sh = "gear" if kind[0] == "gear" else "crt" if kind[0] == "crt" else "torus" if len(kind[1]) > 1 else "cycle"
                if kind not in have and per_shape[sh] < 12:
                    chosen.append((kind, n))
                    have.add(kind)
                per_shape[sh] += kind in have
            for kind, n in chosen:
                c = symbol(kind)
                act = min(1.0, self.salient.get(c, 0.0) / 2 + (0.5 if c in self.recent else 0.0))
                node = {"id": "c:" + c, "label": self.display(self.word_for(c) or c), "symbol": c, "group": "cell", "n": n,
                        "w": round(n + links[c] ** 0.5, 2), "act": round(act, 2), "asked": self.asked.get(c, 0),
                        "shape": kind[0], "cycles": list(kind[1])}
                if kind[0] == "flat" and len(kind[1]) == 1 and kind[1][0] in colours:
                    node["T"] = palette(colours[kind[1][0]])
                nodes[node["id"]] = node
                numbers[node["id"]] = {x for x in set(kind[1]) | {math.prod(kind[1])} if x >= 3}
            for kind, n in self.seen_kinds.most_common(100):
                c = seen_symbol(kind)
                meta = self.seen_meta.get(kind, {})
                node = {"id": "s:" + c, "label": self.display(self.word_for(c) or c), "symbol": c, "group": "cell", "n": n,
                        "w": round(n, 2), "act": round(min(1.0, self.salient.get(c, 0.0) / 2), 2), "shape": "seen",
                        "cycles": list(kind[1]), "origin": meta.get("origin", ""), "asked": self.asked.get(c, 0)}
                if meta.get("unit"):
                    node["unit"] = meta["unit"]
                nodes[node["id"]] = node
                numbers[node["id"]] = {x for x in set(kind[1]) | {math.prod(kind[1])} if x >= 3}
            for name, n in self.invented_seen.most_common(60):
                entry = self.invention_of(name) or {}
                act = min(1.0, self.salient.get(name, 0.0) / 2 + (0.5 if name in self.recent else 0.0))
                nodes["i:" + name] = {"id": "i:" + name, "label": self.display(self.word_for(name) or name),
                                      "symbol": name, "group": "cell", "n": n, "w": round(n + links[name] ** 0.5, 2),
                                      "act": round(act, 2), "asked": self.asked.get(name, 0), "shape": "invented",
                                      "cycles": [], "nature": nature_text(entry.get("nature"))}
            for name, th in sorted((self.__dict__.get("things") or {}).items(), key=lambda kv: -kv[1]["worlds"])[:40]:
                nodes["b:" + name] = {"id": "b:" + name, "label": self.display(self.word_for(name) or name), "symbol": name,
                                      "group": "cell", "n": th["worlds"], "w": round(th["worlds"] + links[name] ** 0.5, 2),
                                      "act": round(min(1.0, self.salient.get(name, 0.0) / 2 + (0.5 if name in self.recent else 0.0)), 2),
                                      "asked": self.asked.get(name, 0), "shape": "thing", "cycles": [len(th["parts"])],
                                      "members": th["parts"]}
            for name, n in self.odds_seen.most_common(60):
                act = min(1.0, self.salient.get(name, 0.0) / 2 + (0.5 if name in self.recent else 0.0))
                nodes["o:" + name] = {"id": "o:" + name, "label": self.display(self.word_for(name) or name),
                                      "symbol": name, "group": "cell", "n": n, "w": round(n + links[name] ** 0.5, 2),
                                      "act": round(act, 2), "asked": self.asked.get(name, 0), "shape": "odds",
                                      "cycles": [int(x) for x in name.split("~")]}
            for gid, g in self.generals.items():
                target = ("c:" if g["cell"] else "g:") + gid
                if not g["cell"]:
                    nodes[target] = {"id": target, "label": self.display(self.word_for(gid) or gid), "symbol": gid,
                                     "group": "cell", "n": len(g["members"]), "w": float(len(g["members"])),
                                     "act": round(min(1.0, self.salient.get(gid, 0.0) / 2), 2),
                                     "asked": self.asked.get(gid, 0), "shape": "general",
                                     "cycles": [g["g"]] if g["kind"] == "part" else [], "law": g.get("law")}
                for m in g["members"]:
                    edges.append({"a": ids.get(m, "c:" + m), "b": target, "w": 1.0, "t": "kindof"})
            for (a, b), w in self.together.most_common(240):
                edges.append({"a": ids.get(a, "c:" + a), "b": ids.get(b, "c:" + b), "w": round(w, 2), "t": "lived"})
            for (code, a, b), w in self.cell_links.most_common(200):
                edges.append({"a": ids.get(a, "c:" + a), "b": ids.get(b, "c:" + b), "w": w, "t": "law:" + code})
            for (a, b), w in self.co_read.most_common(160):
                edges.append({"a": ids.get(a, "c:" + a), "b": ids.get(b, "c:" + b), "w": round(w, 2), "t": "read"})
            kin = []
            for a, b in itertools.combinations(numbers, 2):
                same = numbers[a] & numbers[b]
                if same:
                    kin.append({"a": a, "b": b, "w": len(same), "t": "kin", "n": sorted(same)})
            edges += sorted(kin, key=lambda e: -e["w"])[:300]
            words = []
            for w in self.named_words():
                for c, strength in self.links_of(w):
                    words.append(w)
                    edges.append({"a": "w:" + w, "b": ids.get(c, "c:" + c), "w": round(strength, 2), "t": "means"})
            strength = collections.Counter()
            for (x, y), e in sorted(self.links.items(), key=lambda kv: -kv[1])[:80]:
                words += [x, y]
                strength[x] += e
                strength[y] += e
                edges.append({"a": "w:" + x, "b": "w:" + y, "w": e, "t": "assoc"})
            for w, rel in list(self.related.items())[-30:]:
                words.append(w)
                for t, n in rel.most_common(4):
                    words.append(t)
                    edges.append({"a": "w:" + w, "b": "w:" + t, "w": round(n, 2), "t": "rel"})
            for cid, k in (getattr(self, "circuits", None) or {}).items():
                nid = "k:" + cid
                nodes[nid] = {"id": nid, "label": " · ".join(self.display(self.word_for(c) or c) for c in k["members"]),
                              "symbol": cid, "group": "cell", "n": len(k["members"]), "w": float(len(k["members"]) + len(k["laws"])),
                              "act": round(min(1.0, max(self.salient.get(c, 0.0) for c in k["members"]) / 2), 2),
                              "shape": "circuit", "cycles": [], "members": k["members"]}
                for c in k["members"]:
                    edges.append({"a": nid, "b": ids.get(c, "c:" + c), "w": 1.0, "t": "part"})
            for tid, n in self.topic_seen.most_common(40):
                if n < 2 or tid not in self.topic_labels:
                    continue
                nid = f"t:{tid}"
                nodes[nid] = {"id": nid, "label": self.topic_labels[tid], "symbol": str(tid), "group": "cell", "n": n,
                              "w": round(1 + n ** 0.5, 2), "act": 0.0, "shape": "topic", "cycles": []}
                for w in self.topic_main.get(tid, ())[:3]:
                    words.append(w)
                    edges.append({"a": nid, "b": "w:" + w, "w": 1.0, "t": "about"})
                for c, k in self.topic_cells.get(tid, collections.Counter()).most_common(2):
                    edges.append({"a": nid, "b": ids.get(c, "c:" + c), "w": float(k), "t": "about"})
            fresh = {x for r in self.reading_log[-6:] for x in (r.get("word"), r.get("title")) if x}
            meaning = set(self.named_words())
            for w in list(dict.fromkeys(words))[:200]:
                weight = sum(x for _, x in self.links_of(w)) + sum(self.related.get(w, {}).values()) + strength[w]
                nodes["w:" + w] = {"id": "w:" + w, "label": self.display(w), "group": "word", "means": w in meaning,
                                   "w": round(1 + weight, 2),
                                   "act": round(min(1.0, (w in fresh) + self.salient.get(w, 0.0) / 4), 2)}
            edges = [e for e in edges if e["a"] in nodes and e["b"] in nodes]
            stats = {"cells": len(self.kinds_seen), "words": len(self.known_words()), "links": len(edges),
                     "pruned": self.pruned, "articles": self.articles, "meanings": len(self.read_meaning),
                     "assoc": len(self.links), "sources": self.sources, "seen": len(self.seen_kinds),
                     "anything": self.reader.read_count, "ways": len(self.reader.ways),
                     "types": len(self.reader.types), "open": len(self.reader.open),
                     "worlds": self.worlds_understood, "steps": self.steps, "library": len(self.library),
                     "real": isinstance(self.world, RealWorld), "senses_known": len(getattr(self, "real_known", {})),
                     "topics": sum(1 for n in self.topic_seen.values() if n >= 2),
                     "circuits": len(getattr(self, "circuits", None) or {}),
                     "generals": sum(1 for g in self.generals.values() if not g["cell"]),
                     "invented": len(self.inventions), "chance": len(self.odds_seen),
                     "things": len(self.__dict__.get("things") or {}),

                     "laws": {code: k["worlds"] for code, k in self.link_kinds.items()},
                     "use": {"invent_at": self.invent_times()[0], "closed": len(self.sure_at),
                             "ledger": {k: list(v) for k, v in self.ledger.items()}, "plans": dict(self.plans),
                             "ways": {name: {"now": str(self.way(name, "")), "options": [self.way_row(w, o) for o in w["options"]]}
                                      for name, w in self.ways.items()}, "judged": self.worlds_judged,
                             "generals": len(self.generals),
                             "goals": {"made": getattr(self, "goals_made", 0), "reached": getattr(self, "goals_reached", 0),
                                       "now": self.display(self.goal["word"]) if getattr(self, "goal", None)
                                       and not self.goal["done"] else None},
                             "pending": len(getattr(self, "pending", None) or []),
                             "relation_words": [dict(r, word=self.display(w)) for w, r in sorted(self.relation_words().items(),
                                                                                              key=lambda kv: -kv[1]["digits"])[:24]],
                             "reading_rules": {f: dict(r) for f, r in (self.__dict__.get("reading_rules") or {}).items()},
                             "frame_words": sorted(self.display(w) for w in (self.__dict__.get("frame_words") or ()))[:24],
                             "number_words": [dict(r, word=self.display(w)) for w, r in sorted(
                                 (self.__dict__.get("number_known") or {}).items(), key=lambda kv: kv[1]["value"])[:30]],
                             "frames": self.__dict__.get("frame_analogy"),
                             "op_words": [dict(r, word=self.display(w)) for w, r in sorted(self.op_words().items(),
                                                                                    key=lambda kv: -kv[1]["digits"])[:16]],
                             "forms": {side: [[self.display(a), e] for a, e, _, _ in fs[:12]]
                                       for side, fs in self.word_forms().items()},
                             "read_ways": {name: {"now": w["now"], "options": [{"value": o, "n": w["stats"].get(str(o), (0, 0.0))[0],
                                                                            "mean": round(w["stats"].get(str(o), (0, 0.0))[1], 2)}
                                                                           for o in w["options"]]}
                                           for name, w in (getattr(self, "read_ways", None) or {}).items()}},
                     "shapes": dict(collections.Counter(
                         "gear" if sh == "gear" else "crt" if sh == "crt" else "torus" if len(cy) > 1 else "cycle"
                         for sh, cy in self.kinds_seen), seen=len(self.seen_kinds), invented=len(self.invented_seen),
                         chance=len(self.odds_seen),
                         general=sum(1 for g in self.generals.values() if not g["cell"]),
                         circuit=len(getattr(self, "circuits", None) or {}),
                         topic=sum(1 for n in self.topic_seen.values() if n >= 2)),
                     "sites": len(self.sites_done) + len(self.round_sites), "rounds": self.rounds,
                     "pages": sum(v[0] for v in self.sites_done.values())
                              + sum(st["pages"] for st in self.round_sites.values()),
                     "asks": len(self.asks), "asks_trusted": sum(1 for w in self.asks.values() if w.get("trusted"))}
            return {"nodes": list(nodes.values()), "edges": edges, "stats": stats, "reading": self.reading_log[-6:]}

    def live(self, since):
        """What it is doing at this moment, for the page."""
        with self.lock:
            sensors = []
            known = self.__dict__.get("real_known") or {}
            for j, L in enumerate(self.learners):
                inv = getattr(L, "invented", None)
                if inv is not None:
                    sensors.append({"s": inv["name"], "cycles": [], "p": [], "T": [], "sure": trusted(inv),
                                    "known": False, "invented": True, "nature": inv.get("nature", "")})
                    continue
                cell = L.moment_cell() if j in known and isinstance(L.colors[-1], int) else None
                if cell is not None:
                    P, d, M = cell
                    m = L.moment
                    phase = (len(L.colors) - 1 - m["times"][-1]) % P if m.get("times") else 0
                    sensors.append({"s": str(known[j]), "cycles": [P, M] if P > 1 else [M],
                                    "p": [phase, L.colors[-1] % M] if P > 1 else [L.colors[-1] % M], "T": [],
                                    "sure": moment_trusted(m), "known": True})
                    continue
                r = getattr(L, "recognized", None)
                if r is not None:
                    sensors.append({"s": str(r["d"]), "cycles": [r["d"]], "p": [r["p"]], "T": palette(r["T"]),
                                    "sure": trusted(r), "known": True})
                    continue
                mods, key = list(L.model.mods), L.key
                one = len(mods) == 1 and 0 < mods[0] <= 120
                sensors.append({"s": None, "cycles": mods, "p": list(key) if isinstance(key, tuple) else [],
                                "T": palette([L.table.get((x,)) for x in range(mods[0])]) if one else [],
                                "mapped": len(L.table), "sure": L.sure(), "known": False})
            sites = [{"site": h, "pages": st["pages"], "gain": round(st["gain"], 1), "done": st["done"]}
                     for h, st in self.round_sites.items()]
            sps = self.history[-1]["sps"] if self.history else 0
            goal = []
            for j, L in enumerate(self.learners):
                tool = ("machine" if getattr(L, "invented", None) is not None else
                        "kind" if getattr(L, "recognized", None) is not None else "counts")
                mods = list(getattr(L.model, "mods", []))
                goal.append({"sensor": j + 1, "sure": L.sure(), "tool": tool, "mapped": len(L.table),
                             "of": math.prod(mods) if mods and 0 not in mods else None,
                             "plan": bool(getattr(self, "plan", None)) and self.plan.get("sensor") == j})
            real = isinstance(self.world, RealWorld)
            return {"world": self.k, "real": real, "steps": self.world_steps,
                    "size": self.world.size, "sensors": sensors,
                    "senses": [x[1] for x in self.world.sensors] if real else [],
                    "now": list(getattr(self, "seen_now", None) or ()) if real else [],
                    "goal": goal, "why": list(self.decisions)[-10:][::-1],
                    "ways": {k: str(v) for k, v in (getattr(self, "ways_now", None) or {}).items()},
                    "reading": self.reading_now, "last": self.event_id, "sites": sites, "sps": sps,
                    "urge": round(self.urge, 2), "worlds": self.worlds_understood, "queue": len(self.queue) + len(self.given),
                    "brains": self.__dict__.get("council_view") or [],
                    "card": gpu.describe(ask=False),
                    "inventor_card": self.__dict__.get("inventor_card"),
                    "workshop": self.__dict__.get("workshop_view"),
                    "space": self.space(),
                    "innate": self.innate_view(),
                    "self": self.self_view(),
                    "lab": dict(self.__dict__.get("lab_view") or {},
                                genes={g: [str(v) for v in vals] for g, vals in GENES.items()},
                                now={g: str(self.gene(g)) for g in GENES}),
                    "made_senses": self.made_view(),
                    "senses_known": len(getattr(self, "real_known", {})),
                    "waiting": list(self.queue)[:8] + [n for n, _ in self.given][:4], "born": round(self.born),
                    "next": {"articles": list(self.queue[:4]),
                             "sites": list(dict.fromkeys(site_of(u) for u, _ in sorted(self.web_frontier.items(),
                                                                                    key=lambda x: -x[1])[:12]))[:4]},
                    "events": [e for e in self.events if e["id"] > since][-200:]}

    def space(self):
        """The space of this world as its laws see it."""
        closed = [L for L in self.learners if L.counts_closed()]
        out = {"dims": [], "trail": [], "senses": len(closed), "of": len(self.learners), "machines": []}
        if closed and closed[0].actions:
            key = (self.k, tuple((id(L.model), len(L.model.gens)) for L in closed))
            got = self.__dict__.get("_space")
            if got is None or got[0] != key:
                got = self._space = (key, nm.joint([L.model for L in closed], closed[0].model.m))
            jm, L0 = got[1], closed[0]
            T = len(L0.actions)
            start = max(0, T - 48)
            if len(L0.counts) == T + 1:
                k = jm.of(L0.counts[start])
                trail = [k]
                for a in list(L0.actions)[start:]:
                    k = jm.step(k, a)
                    trail.append(k)
            else:
                trail = [jm.of(L0.counts[-1])]
            out["dims"] = [{"kind": "cycle" if q else "line", "size": q, "at": x} for q, x in zip(jm.mods, trail[-1])]
            out["trail"] = [list(t) for t in trail]
        for L in self.learners:
            cell = None if L.counts_closed() else L.moment_cell()
            if cell is not None and type(L.colors[-1]) is int and cell[2]:
                P, d, M = cell
                out["dims"].append({"kind": "cycle", "size": M, "at": L.colors[-1] % M, "moments": P})
        if out["trail"] and len(out["dims"]) > len(out["trail"][-1]):
            extra = [x["at"] for x in out["dims"][len(out["trail"][-1]):]]
            out["trail"] = [t + extra for t in out["trail"]]
        for rec in getattr(self, "mechs", ()):
            mech = rec["mech"]
            kinds, pile_on = mech.shape
            regs, pile = mech.state
            out["machines"].append({"name": rec["name"], "pile": len(pile) if pile_on else None,
                                    "dims": [{"kind": kd[0], "size": kd[1] if len(kd) > 1 else 2 if kd[0] == "bit" else 0,
                                              "at": v} for kd, v in zip(kinds, regs)]})
        n = len(out["dims"]) + sum(len(x["dims"]) for x in out["machines"])
        self.space_most, self._space_n = max(n, self.__dict__.get("space_most", 0)), n
        out["n"], out["most"] = n, self.space_most
        return out

    def self_view(self):
        """What it knows of itself, for its page."""
        use = dict(self.__dict__.get("parts_use") or {})
        run = max(1.0, time.time() - self.__dict__.get("_run_began", time.time()))
        total = sum(u[1] for u in use.values()) or 1e-9
        parts = [{"part": p, "calls": n, "ms_per_min": round(60_000 * s / run, 1), "share": round(100 * s / total, 1),
                  "longest_ms": round(1000 * longest, 1)}
                 for p, (n, s, longest) in sorted(use.items(), key=lambda kv: -kv[1][1])]
        beliefs = {}
        for rec in list(self.__dict__.get("journal") or ()):
            b = beliefs.setdefault(rec["kind"], {"born": 0, "held": 0, "gone": {}})
            b["born"] += 1
            if rec["end"] is None:
                b["held"] += 1
            else:
                how = rec["end"]["how"]
                b["gone"][how] = b["gone"].get(how, 0) + 1
        try:
            size = os.path.getsize(config.STATE_FILE)
        except OSError:
            size = 0
        ws = self.__dict__.get("workshop_view") or {}
        return {"parts": parts, "run_s": round(run), "think_ms_per_min": round(60_000 * total / run, 1),
                "ledger": {k: list(v) for k, v in (self.__dict__.get("ledger") or {}).items()}, "beliefs": beliefs,
                "memory_bytes": size, "card": gpu.describe(ask=False), "inventor_card": self.__dict__.get("inventor_card"),
                "workshop": {"worlds": ws.get("worlds"), "understood": ws.get("understood"), "pace": ws.get("pace")},
                "brains": sum(1 for b in (self.__dict__.get("council_view") or []) if b.get("alive")),
                "threads": threading.active_count(), "recalled": sorted(self.__dict__.get("real_recall") or ()),
                "experiment": dict(self.trial) if isinstance(self.__dict__.get("trial"), dict) else None,
                "senses": [{"key": sense_key(s), "watched": j not in self.named_senses(), "sure": L.sure(),
                            "candidates": len(L.freq), "log": len((L.__dict__.get("pair_log") or {}).get("t") or ()),
                            "states": len(L.table), "laws": sum(len(r) for r in ((L.__dict__.get("odds") or {})
                                                                                .get("laws") or {}).values())}
                           for j, (s, L) in enumerate(zip(getattr(self.world, "sensors", ()), self.learners))]
                if isinstance(self.__dict__.get("world"), RealWorld) else [],
                "since": self.since_view(),
                "minds": self.minds_view(),
                "acts": {str(b[0]): self.pressed.get(i, 0) for i, b in enumerate(getattr(self.world, "buttons", ()))}
                if isinstance(self.__dict__.get("pressed"), collections.Counter) else {},
                "effect": (lambda e: None if e is None else {"act": e[0], "sensor": e[1] + 1})(self.__dict__.get("_effect")),
                "reading_acts": dict(self.__dict__.get("read_acts") or {}),
                "abilities": self.abilities_view(),
                "one": {"pairs": len(self.__dict__.get("pair_names") or ()), "made": len(self.__dict__.get("made") or {}),
                        "parts": sum(1 for e in self.inventions if e.get("machine")), "kinds": len(self.library)},
                "twins": self.twins_view(),
                "episodes": (lambda ep: {"cells": len(ep.get("cells") or ()), "trusted": sorted(
                    j + 1 for j, t in (ep.get("trust") or {}).items() if t.get("on"))})(self.__dict__.get("episodes") or {}),
                "clocks": sorted(i + 1 for i in (self.__dict__.get("clocks") or ())),
                "nerves": sum((L.__dict__.get("odds") or {}).get("woke", 0) for L in self.learners),
                "code": dict(code_now(), brains_other=sum(
                    1 for b in (self.__dict__.get("council_view") or [])[1:]
                    if b.get("alive") and b.get("code") and b.get("code") != CODE["print"]
                    and (b.get("at") or 0) >= CODE["began"]))}

    def innate_view(self):
        """What it was born able to do."""
        L = self.learners
        room = self.__dict__.get("concepts") or {}
        ws = self.__dict__.get("workshop_view") or {}
        inv = self.__dict__.get("inventor_card") or {}
        return [
            {"key": "self", "now": len(self.__dict__.get("parts_use") or {}),
             "all": len(self.__dict__.get("real_recall") or {})},
            {"key": "counts", "now": sum(1 for x in L if x.counts_closed()), "all": len(self.kinds_seen)},
            {"key": "moments", "now": sum(1 for x in L if x.moment_cell() is not None)},
            {"key": "odds", "now": sum(len((x.__dict__.get("odds") or {}).get("laws") or {}) for x in L)},
            {"key": "pairs", "now": len(self.__dict__.get("pair_names") or ()), "all": len(PAIRS)},
            {"key": "concepts", "now": sum(1 for c in (room.get("classes") or {}).values() if c)},
            {"key": "invent", "now": len(getattr(self, "mechs", ())), "all": len(self.inventions),
             "tried": inv.get("tried")},
            {"key": "machines", "all": sum(1 for e in self.inventions if e.get("machine"))},
            {"key": "recognize", "now": sum(1 for x in L if getattr(x, "recognized", None) is not None),
             "all": len(self.library)},
            {"key": "imagine", "now": len(self.__dict__.get("_traps") or {})},
            {"key": "made", "now": len(self.__dict__.get("made") or {})},
            {"key": "words", "all": len(self.named_words())},
            {"key": "workshop", "now": ws.get("worlds"), "all": ws.get("understood")},
            {"key": "space", "now": (self.__dict__.get("_space_n") or 0), "all": self.__dict__.get("space_most", 0)},
        ]

    def made_view(self):
        """The senses it made for itself, for its page."""
        out = []
        for j, rec in (self.__dict__.get("made") or {}).items():
            out.append({"kind": "made", "of": j, "parts": [[i, str(r), str(c)] for i, r, c in rec["parts"]],
                        "way": rec["way"], "lag": rec.get("lag", 0), "n": rec.get("n1", 0), "right": rec.get("k1", 0)})
        for name in list(self.__dict__.get("pair_names") or ())[:12]:
            out.append({"kind": "pair", "name": name,
                        "parts": [[pl, str(pa), str(pv)] for pl, pa, pv in PAIRS.get(name, ())]})
        return out

    def proven(self):
        """What it has proven, for the page."""
        with self.lock:
            ids = self.node_ids()
            means = []
            for w in self.named_words():
                taught = self.taught(w)
                for c, x in self.links_of(w):
                    means.append({"word": self.display(w), "key": w, "cell": c, "id": ids.get(c, "c:" + c),
                                  "strength": round(x, 1), "taught": c in taught})
            means.sort(key=lambda d: (not d["taught"], -d["strength"]))
            links = [{"a": self.display(a), "b": self.display(b), "ka": a, "kb": b, "e": e}
                     for (a, b), e in sorted(self.links.items(), key=lambda kv: -kv[1])[:24]]
            return {"means": means[:40], "links": links, "meanings": len(self.read_meaning),
                    "taught": sum(1 for w in self.heard if self.taught(w)), "assoc": len(self.links)}

    def growth_table(self, day=False):
        """Its growth as a table to plot."""
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\r\n")
        cols = ["steps", "sps", "ideas", "worlds", "words", "meanings", "links", "articles", "read", "types", "ways"]
        w.writerow(["time"] + cols)
        with self.lock:
            rows = list(self.history_day if day else self.history)
        for h in rows:
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(h.get("t", 0)))] + [h.get(c, "") for c in cols])
        return "\ufeff" + out.getvalue()

    def table(self):
        """Everything it has proven, as a table to keep or to check by hand."""
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\r\n")
        w.writerow(["kind", "word", "means / goes with", "its word for it", "evidence (digits)", "taught by you",
                    "met with it", "of all meetings", "share by chance"])
        with self.lock:
            totals = self.chance_totals()
            for word in self.named_words():
                fw = fold(word)
                taught = self.taught(word)
                met = self.met_with.get(fw, {})
                n = sum(met.values())
                for c, x in self.links_of(word):
                    mine = c in taught
                    w.writerow(["meaning", self.display(word), c, self.display(self.word_for(c) or "") or "", round(x, 1),
                                "yes" if mine else "no", met.get(c, 0), n,
                                round(self.chance_of(fw, c, totals), 5) if n else ""])
            for (a, b), e in sorted(self.links.items(), key=lambda kv: -kv[1]):
                w.writerow(["pair", self.display(a), self.display(b), "", round(e, 1), "", "", "", ""])
        return "\ufeff" + out.getvalue()

    def find(self, q, most=12):
        """Everything it knows whose name begins with."""
        q = fold(q.strip())
        if not q:
            return []
        with self.lock:
            out = []
            for k in self.kinds_seen:
                sym = symbol(k)
                word = self.word_for(sym) or ""
                if sym.startswith(q) or (word and fold(word).startswith(q)):
                    out.append((0 if sym == q else 1, -self.kinds_seen[k], {"id": "c:" + sym, "label": sym, "word": self.display(word) if word else "",
                                                                         "kind": "gear" if k[0] == "gear" else "crt" if k[0] == "crt" else "torus" if len(k[1]) > 1 else "cycle"}))
            for k in self.seen_kinds:
                sym = seen_symbol(k)
                if sym.startswith(q):
                    out.append((0 if sym == q else 1, -self.seen_kinds[k], {"id": "s:" + sym, "label": sym, "word": "", "kind": "seen"}))
            words = list(self.named_words()) + [w for pair in self.links for w in pair] + list(self.word_src)
            seen = set()
            for w in words:
                fw = fold(w)
                if fw in seen or not (fw.startswith(q) or (len(q) > 2 and q in fw)):
                    continue
                seen.add(fw)
                out.append((0 if fw == q else 2 if fw.startswith(q) else 3, -self.word_src.get(fw, 0),
                            {"id": "w:" + w, "label": self.display(fw) if fw == w else w, "word": "", "kind": "word"}))
                if len(seen) > 400:
                    break
            out.sort(key=lambda x: (x[0], x[1]))
            return [d for _, _, d in out[:most]]

    def worlds(self):
        """The last worlds it lived in, newest first."""
        with self.lock:
            ids = self.node_ids()
            out = []
            for w in self.knowledge[::-1]:
                cells = []
                for kind in w["kinds"]:
                    sym = symbol(tuple(kind) if not isinstance(kind, tuple) else kind)
                    word = self.word_for(sym)
                    cells.append({"id": ids.get(sym, "c:" + sym), "symbol": sym, "shape": kind[0],
                                  "cycles": list(kind[1]), "word": self.display(word) if word else None})
                for name in w.get("invented", ()):
                    word = self.word_for(name)
                    entry = self.invention_of(name) or {}
                    cells.append({"id": "i:" + name, "symbol": name, "shape": "invented", "cycles": [],
                                  "nature": nature_text(entry.get("nature")),
                                  "word": self.display(word) if word else None})
                out.append({"world": w["world"], "real": bool(w.get("real")), "steps": w["steps"],
                            "accuracy": round(w.get("accuracy", 0)),
                            "recognized": w.get("recognized", 0), "sensors": w.get("sensors", len(cells)),
                            "size": w.get("size", 0), "cells": cells})
            return out

    def record(self):
        """A point of its growth, every ten seconds, for the page."""
        now = time.time()
        with self.lock:
            last = getattr(self, "_rec", None)
            sps = (self.steps - last[1]) / max(1e-6, now - last[0]) if last else 0.0
            self._rec = (now, self.steps)
            self.history.append({"t": round(now), "steps": self.steps, "sps": round(sps),
                                 "ideas": len(self.kinds_seen) + len(self.seen_kinds) + len(self.invented_seen),
                                 "worlds": self.worlds_understood, "senses": len(getattr(self, "real_known", {})),
                                 "words": len(self.known_words()), "meanings": len(self.read_meaning),
                                 "links": len(self.links), "articles": self.articles,
                                 "read": self.reader.read_count, "types": len(self.reader.types),
                                 "ways": len(self.reader.ways), "pages": self.__dict__.get("pages_read", 0)})
            del self.history[:-720]
            day = self.history_day
            if not day or now - day[-1]["t"] >= 60:
                day.append(dict(self.history[-1]))
                del day[:-1440]

    def cell_info(self, node_id):
        """Everything about one cell of its network, for the page."""
        with self.lock:
            ids = self.node_ids()

            def ref(c):
                return {"id": ids.get(c, "c:" + c), "cell": c, "label": self.display(self.word_for(c) or c)}

            out = {"id": node_id}
            if node_id.startswith("w:"):
                w = node_id[2:]
                fw = fold(w)
                taught = self.taught(w)
                out.update(kind="word", label=self.display(fw) if fw == w else w,
                           heard=round(self.exposure.get(w, 0.0), 1), looked=w in self.looked or fw in self.looked,
                           sources=self.word_src.get(fw, 0), needs=WORD_EVIDENCE)
                totals = self.chance_totals()
                cs0 = self.met_with.get(fw, {})
                n0 = sum(cs0.values())
                out["means"] = [dict(ref(c), strength=round(x, 1), taught=c in taught, articles=cs0.get(c, 0), of=n0,
                                     chance=round(self.chance_of(fw, c, totals), 4), seen=self.seen_in.get((fw, c), [])[-4:],
                                     topics=[self.topic_labels.get(t, "") for t in self.contexts.get((fw, c), ())][-4:],
                                     general=self.general(fw, c))
                                for c, x in self.links_of(w)]
                out["with"] = sorted(({"id": "w:" + (y if x == fw else x), "word": self.display(y if x == fw else x),
                                       "evidence": round(e, 1)}
                                      for (x, y), e in self.links.items() if fw in (x, y)), key=lambda d: -d["evidence"])[:12]
                out["related"] = [{"id": "w:" + t, "word": t}
                                  for t, _ in self.related.get(fw, collections.Counter()).most_common(8)]
                totals = self.chance_totals()
                w = fw
                cs = self.met_with.get(w, {})
                n = sum(cs.values())
                out["near"] = sorted((dict(ref(c), articles=k, evidence=round(evidence(n, k, self.chance_of(w, c, totals)), 1))
                                      for c, k in cs.items() if k >= 2), key=lambda d: -d["evidence"])[:5]
                return out
            if node_id.startswith("i:"):
                return self.invention_info(node_id, ref)
            if node_id.startswith("o:"):
                return self.odds_info(node_id, ref)
            if node_id.startswith("b:"):
                th = (self.__dict__.get("things") or {}).get(node_id[2:])
                if th is None:
                    return {"id": node_id, "kind": "gone"}
                word = self.word_for(node_id[2:])
                return {"id": node_id, "kind": "thing", "symbol": node_id[2:], "label": self.display(word) if word else node_id[2:],
                        "word": self.display(word) if word else word, "parts": [ref(p) for p in dict.fromkeys(th["parts"])],
                        "n": len(th["parts"]), "worlds": th["worlds"],
                        "life": {"born": th["born"], "world": th["world"], "last": th.get("last"), "last_world": th.get("last_world")},
                        "links": [dict(ref(b if a == node_id[2:] else a), law=code, times=n, out=a == node_id[2:])
                                  for (code, a, b), n in self.cell_links.most_common() if node_id[2:] in (a, b)][:8]}
            if node_id.startswith("t:"):
                tid = int(node_id[2:]) if node_id[2:].isdigit() else None
                if tid is None or tid not in self.topic_sets:
                    return {"id": node_id, "kind": "gone"}
                ws = sorted(self.topic_sets[tid], key=lambda w: (-self.word_src.get(w, 0), w))[:16]
                return {"id": node_id, "kind": "topic", "label": self.topic_labels.get(tid, ""),
                        "articles": self.topic_seen.get(tid, 0),
                        "words": [{"id": "w:" + w, "word": self.display(w)} for w in ws],
                        "cells": [dict(ref(c), times=k) for c, k in
                                  self.topic_cells.get(tid, collections.Counter()).most_common(8)]}
            if node_id.startswith("k:"):
                k = (getattr(self, "circuits", None) or {}).get(node_id[2:])
                if k is None:
                    return {"id": node_id, "kind": "gone"}
                return {"id": node_id, "kind": "circuit", "symbol": node_id[2:], "born": k["born"],
                        "label": " · ".join(c for c in k["members"]), "members": [ref(c) for c in k["members"]],
                        "laws": [{"law": code, "a": ref(a), "b": ref(b)} for code, a, b in k["laws"]][:12]}
            if node_id.startswith("g:"):
                gid = node_id[2:]
                g = self.generals.get(gid)
                if g is None:
                    return {"id": node_id, "kind": "gone"}
                word = self.word_for(gid)
                word = self.display(word) if word else word
                return {"id": node_id, "kind": "general", "symbol": gid, "label": word or gid, "word": word,
                        "general": g["kind"], "g": g.get("g"), "law": g.get("law"), "born": g["born"],
                        "world": g["world"], "members": [ref(c) for c in g["members"]][:12],
                        "spoke": self.asked.get(gid, 0),
                        "words": [{"id": "w:" + w, "word": self.display(w), "strength": round(x, 1)}
                                  for w in self.named_words() for c, x in self.links_of(w) if c == gid][:10]}
            sym = node_id[2:]
            kind = next((k for k in self.kinds_seen if symbol(k) == sym), None) if node_id.startswith("c:") else None
            seen = next((k for k in self.seen_kinds if seen_symbol(k) == sym), None) if node_id.startswith("s:") else None
            word = self.word_for(sym)
            word = self.display(word) if word else word
            out.update(label=word or sym, symbol=sym, word=word, spoke=self.asked.get(sym, 0),
                       taught=[w for w in self.heard if sym in self.taught(w)][:6])
            if kind:
                out.update(kind="idea", shape=kind[0], cycles=list(kind[1]), worlds=self.kinds_seen[kind])
                life = self.kind_life.get(kind)
                if life:
                    out["life"] = life
                colours = {e["d"]: e["T"] for e in self.library}
                if kind[0] == "flat" and len(kind[1]) == 1 and kind[1][0] in colours:
                    out["T"] = palette(colours[kind[1][0]])
                out["remembered"] = len(kind[1]) == 1 and kind[1][0] in colours
                entry = next((e for e in self.library if len(kind[1]) == 1 and e["d"] == kind[1][0]), None)
                if entry:
                    out["moves"] = sorted(entry["S"])
            elif seen:
                meta = self.seen_meta.get(seen, {})
                out.update(kind="seen", cycles=list(seen[1]), times=self.seen_kinds[seen], origin=meta.get("origin"),
                           first=meta.get("first"), last=meta.get("last"), unit=meta.get("unit"))
            else:
                out.update(kind="gone")
                return out
            out["lived"] = []
            if kind:
                out["lived"] = [dict(ref(b if a == sym else a), times=round(v, 1))
                                for (a, b), v in self.together.most_common() if sym in (a, b)][:8]
            out["read"] = [dict(ref(b if a == sym else a), times=round(v, 1))
                           for (a, b), v in self.co_read.most_common() if sym in (a, b)][:6]
            out["laws"] = [dict(ref(b if a == sym else a), law=code, times=n, out=a == sym)
                           for (code, a, b), n in self.cell_links.most_common() if sym in (a, b)][:8]
            mine = {x for x in set(out["cycles"]) | {math.prod(out["cycles"])} if x >= 3}
            kin = []
            for k in list(self.kinds_seen) + list(self.seen_kinds):
                other = ("s:" + seen_symbol(k)) if k[0] == "seen" else ("c:" + symbol(k))
                same = mine & (set(k[1]) | {math.prod(k[1])})
                if other != node_id and same:
                    kin.append({"id": other, "cell": other[2:], "label": self.word_for(other[2:]) or other[2:],
                                "numbers": sorted(same)})
            out["kin"] = sorted(kin, key=lambda d: -len(d["numbers"]))[:10]
            out["words"] = [{"id": "w:" + w, "word": self.display(w), "strength": round(x, 1)} for w in self.named_words()
                            for c, x in self.links_of(w) if c == sym][:10]
            return out

    def odds_info(self, node_id, ref):
        """A cell of chance, for its page."""
        name = node_id[2:]
        if name not in self.odds_seen:
            return {"id": node_id, "kind": "gone"}
        values, dwell = (int(x) for x in name.split("~"))
        word = self.word_for(name)
        word = self.display(word) if word else word
        live = []
        for j, L in enumerate(self.learners):
            cell = L.odds_cell()
            if cell is None or odds_symbol(cell) != name:
                continue
            od = L.odds
            live.append({"sense": j + 1, "laws": [self.odds_view(L, law) for d, rules in sorted(od["laws"].items(), key=lambda kv: repr(kv[0]))
                                                  for law in rules],
                         "verdict": od["verdict"], "tests": od["tests"], "revised": od["revised"],
                         "rate": round(od["Kany"][0] / max(1, od["n"][0]), 4),
                         "cal": {str(b): v for b, v in sorted(od["cal"].items())}})
        return {"id": node_id, "kind": "odds", "label": word or name, "symbol": name, "word": word, "values": values,
                "dwell": dwell, "worlds": self.odds_seen.get(name, 0), "life": self.odds_life.get(name),
                "spoke": self.asked.get(name, 0), "live": live,
                "laws": [dict(v) for v in self.odds_laws.values() if name in (v["a"], v["b"])][:12],
                "links": [dict(ref(b if a == name else a), law=code, times=n, out=a == name)
                          for (code, a, b), n in self.cell_links.most_common() if name in (a, b)][:8]}

    @staticmethod
    def odds_view(L, law):
        """One law of odds, for its page."""
        od = L.odds
        l, attr, v = law["cond"]
        d = law["d"]
        show = lambda x: x if isinstance(x, (int, float, str)) else str(x)
        prof, i = [], law["level"]
        lv = od["levels"].get(d) or []
        R = od["rows"] if i == 0 or i >= len(lv) or lv[i] is None else lv[i]["rows"]
        chain = L.level_chain(d, i)
        for l2 in ODDS_LAGS:
            r = R.get((l2, attr, v))
            if r:
                E, nf = L.by_itself(r[3], d, chain)
                k = r[2].get(d, 0)
                prof.append([l2, round(kl_digits(nf, k, E / nf) if k > E else kl_digits(nf, nf - k, 1 - E / nf), 1) if nf else 0.0])
        return {"lag": l, "attr": attr, "value": show(v), "d": d if type(d) is int else show(d[1]), "q": law["q"],
                "up": law["up"], "level": law["level"],
                "p": law["p"], "base": law.get("base"), "digits": law["digits"], "tests": law["tests"], "n": law["n"],
                "k": law["k"], "after": law["n1"], "came": law["k1"], "at": law["at"],
                "unless": [[x[0], [show(y) for y in x[1]], x[2], x[3]] for x in law["unless"]],
                "especially": [[x[0], [show(y) for y in x[1]], x[2], x[3]] for x in law["especially"]],
                "profile": prof, "cal": {str(b): c for b, c in sorted(law["cal"].items())},
                "parts": [[p[0], p[1], show(p[2])] for p in PAIRS.get(attr, ())] if is_pair(attr) else None}

    def invention_info(self, node_id, ref):
        """A kind it invented, for its page."""
        name = node_id[2:]
        entry = self.invention_of(name)
        if entry is None:
            return {"id": node_id, "kind": "gone"}
        word = self.word_for(name)
        word = self.display(word) if word else word
        last = entry.get("last", {})
        return {"id": node_id, "kind": "invented", "label": word or name, "symbol": name, "word": word,
                "spoke": self.asked.get(name, 0), "taught": [w for w in self.heard if name in self.taught(w)][:6],
                "nature": nature_text(entry.get("nature")), "ops": sorted(entry["ops"] - {"keep"}),
                "worlds": self.invented_seen.get(name, 0), "life": self.invented_life.get(name),
                "mechanism": last.get("mechanism"), "evidence": last.get("evidence"), "tried": last.get("tried"),
                "sensors": last.get("sensors"), "laws": last.get("laws", []), "met": list(entry["uses"][-6:]),
                "foreseen": entry.get("foreseen", 0),
                "machine": dict({k: entry["machine"]["nature"].get(k) for k in ("states", "things", "all", "group",
                                                                                 "commute", "sync", "laws_count")},
                                old=entry["machine"].get("old"), name=entry["machine"]["name"])
                if entry.get("machine") else None,
                "links": [dict(ref(b if a == name else a), law=code, times=n, out=a == name)
                          for (code, a, b), n in self.cell_links.most_common() if name in (a, b)][:8],
                "lived": [dict(ref(b if a == name else a), times=round(v, 1))
                          for (a, b), v in self.together.most_common() if name in (a, b)][:8],
                "words": [{"id": "w:" + w, "word": self.display(w), "strength": round(x, 1)} for w in self.named_words()
                          for c, x in self.links_of(w) if c == name][:10]}

    def reading_report(self):
        """How it reads anything, for the page."""
        r = self.reader
        for _ in range(3):
            try:
                ways = sorted(r.ways.items(), key=lambda kv: -kv[1]["uses"])[:10]
                types = sorted(r.types.items(), key=lambda kv: -kv[1]["count"])[:14]
                pieces = sorted(r.pieces.values(), key=lambda p: (-p["sources"], -p["count"]))[:18]
                asks = sorted(self.asks.items(), key=lambda kv: (-len(kv[1]["trusted"]), -kv[1]["k"], -kv[1]["n"], repr(kv[0])))[:12]
                opened = len(r.open)
                break
            except RuntimeError:
                time.sleep(0.01)
        else:
            return {}
        last = {k: v for k, v in self.last_read.items() if k != "pieces"}
        last["pieces"] = (self.last_read.get("pieces") or [])[:10]
        try:
            names = [n for n in os.listdir(config.INBOX) if os.path.isfile(os.path.join(config.INBOX, n))]
        except OSError:
            names = []
        done = {k.rsplit(":", 2)[0] for k in list(self.inbox_seen)}
        inbox = {"files": len(names), "read": sum(1 for n in names if n in done)}
        gram = []
        for sc, x in sorted(self.grammar.learned.items()):
            if x.get("classes"):
                gram.append({"script": sc, "classes": x["classes"], "saving": x.get("saving"),
                             "laws": [{"forms": [self.display(f) for f in law["forms"]],
                                       "law": {str(k): self.display(f) for k, f in law["law"].items()},
                                       "evidence": law["evidence"], "sources": law["sources"]}
                                      for law in x.get("laws", [])[:12]]})
        return {"last": last, "count": r.read_count, "open": opened, "history": self.read_history[-14:][::-1],
                "inbox": inbox, "grammar": gram, "grammar_seen": self.grammar.seen,
                "ways": [{"begins": sig.split(":")[0], "chain": w["chain"] or ["as it is"], "uses": w["uses"]} for sig, w in ways],
                "types": [{"name": n, "count": t["count"], "sizes": t["sizes"]} for n, t in types],
                "pieces": [p["text"] for p in pieces if p["sources"] > 1],
                "asks": [{"site": w["host"], "how": w["kind"], "asked": w["n"], "answered": w["k"], "trusted": sorted(w["trusted"]),
                          "taught": w.get("taught")} for _, w in asks], "asks_met": len(self.asks)}

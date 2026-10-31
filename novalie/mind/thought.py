# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Thinking: foresight in thought, the graph of its laws, answers."""

import collections
import re
import time

from ..body import RealWorld
from ..evidence import moment_trusted, trusted
from ..text import fold, main_script, script_of, typed_tokens


class Thought:
    def foresee_all(self, n, most=400_000):
        """What each of its senses will show after n of its acts, in thought."""
        out = [self.foresee_direct(j, n) for j in range(len(self.learners))]
        moving = [j for j, L in enumerate(self.learners) if out[j] is None and moment_trusted(getattr(L, "moment", None))]
        if not moving or n > most:
            return out
        Ls, now = self.learners, list(self.seen_now or [L.colors[-1] for L in self.learners])
        order = sorted(moving, key=lambda j: sum(1 for k in Ls[j].moment["cond"] if k[1:].isdigit() and int(k[1:]) in moving))
        keys, cur, top = {}, list(now), {j: max(Ls[j].moment["values"]) for j in moving}
        for t in range(1, n + 1):
            for i, L in enumerate(Ls):
                if i in moving:
                    continue
                r = getattr(L, "recognized", None)
                if r is not None and trusted(r):
                    keys[i] = (keys.get(i, r["p"]) + r["eff"].get(0, 0)) % r["d"]
                    cur[i] = r["T"][keys[i]]
                elif getattr(L, "invented", None) is None and L.counts_closed():
                    keys[i] = L.model.step(keys.get(i, L.key), 0)
                    cur[i] = L.table.get(keys[i])
                else:
                    cur[i] = None
            for j in order:
                m = Ls[j].moment
                if cur[j] is None:
                    continue
                state = {f"s{i}": x for i, x in enumerate(cur) if i != j}
                state["act"] = 0
                if any(state.get(k) is None for k in m["cond"]):
                    cur[j] = None
                    continue
                if all(state.get(k) == v for k, v in m["cond"].items()):
                    v = cur[j] + m["d"]
                    if m["M"]:
                        v %= m["M"]
                    elif v > top[j]:
                        v = None
                    cur[j] = v
        for j in moving:
            out[j] = cur[j]
        return out

    def foresee(self, j, n):
        """What sensor j will show after n more of its acts."""
        v = self.foresee_direct(j, n)
        if v is None and moment_trusted(getattr(self.learners[j], "moment", None)):
            v = self.foresee_all(n)[j]
        return v

    def foresee_direct(self, j, n):
        """foresee, from a kind it recognised or its laws of counts only."""
        L = self.learners[j]
        r = getattr(L, "recognized", None)
        if r is not None and trusted(r):
            return r["T"][(r["p"] + n * r["eff"].get(0, 0)) % r["d"]]
        if getattr(L, "invented", None) is None and L.counts_closed():
            return L.table.get(L.model.step(L.key, 0, times=n))
        return None

    def tick(self, j):
        """How many of its acts a sense takes to change, when that is always the same."""
        cs = self.learners[j].colors[-4000:]
        at = [t for t in range(1, len(cs)) if cs[t] != cs[t - 1]]
        gaps = {b - a for a, b in zip(at, at[1:])}
        return gaps.pop() if len(gaps) == 1 else 1

    def unit_of(self, text, toks):
        """The unit an amount is counted in."""
        senses = {s: j for j, s in getattr(self, "real_known", {}).items()}
        for i, t in enumerate(toks[:-1]):
            if self.number_of(fold(t)) is not None:
                for c in self.meanings(fold(toks[i + 1])):
                    if c in senses:
                        return self.tick(senses[c])
        return 1

    def law_graph(self):
        """Its knowledge as a graph between cells, each link a law it found or a relation it holds."""
        g = collections.defaultdict(list)
        for (code, a, b), n in self.cell_links.items():
            if a != b:
                g[a].append((b, code, n))
                g[b].append((a, {"carry": "carried", "fore": "fored", "cause": "caused"}.get(code, code), n))
        for gid, gen in self.generals.items():
            for m in gen["members"]:
                g[m].append((gid, "kindof", 1))
                g[gid].append((m, "has", 1))
        for (a, b), n in self.co_read.most_common(400):
            g[a].append((b, "read", round(n, 1)))
            g[b].append((a, "read", round(n, 1)))
        return g

    def through(self, c):
        """What follows from its laws about one cell."""
        out, frontier, seen = [], [(c, [c])], {c}
        while frontier:
            x, path = frontier.pop(0)
            for (code, a, b), n in self.cell_links.items():
                if code == "carry" and a == x and b not in seen:
                    seen.add(b)
                    out.append(path + [b])
                    frontier.append((b, path + [b]))
        return out

    def think(self, text):
        """A question you asked, answered from what it knows, in its own symbols and the words it learned, never
        a reply written for it."""
        with self.lock:
            mine = self.all_cells()
            senses = set(getattr(self, "real_known", {}).values())
            toks = [p for piece in text.split()
                    for p in ([piece] if piece in mine else typed_tokens(piece))]
            cells, unknown, amounts = [], [], []
            for i, t in enumerate(toks):
                k = fold(t)
                x = self.number_of(k) if not (t in mine and not t.isdigit()) else None
                if x is not None:
                    after = fold(toks[i + 1]) if i + 1 < len(toks) else ""
                    unit = any(c in senses for c in self.meanings(after)) if after else False
                    (amounts if str(x) not in mine or unit else cells).append(x if str(x) not in mine or unit else str(x))
                    continue
                if t in mine:
                    cells.append(t)
                    continue
                ms = self.meanings(t) or self.meanings(k) or self.known_as(t)
                if ms:
                    cells.extend(ms)
                elif self.is_word(k) and len(k) > 2 and not self.is_glue(k):
                    unknown.append(t)
            cells = [c for c in dict.fromkeys(str(c) for c in cells) if c in mine]
            named = lambda c: self.display(self.word_for(c)) if self.word_for(c) else c
            proof, parts = [], []
            words = self.relation_words()
            sc = main_script([[fold(x) for x in toks if self.is_word(fold(x))]])
            said = {(r["kind"], r["way"]): w for w, r in sorted(words.items(), key=lambda kv: (script_of(kv[0]) == sc, kv[1]["digits"]))}
            judged = self.judge_sentence(toks)
            for j in judged:
                mark = {"true": "✓", "backwards": "⇆", "unknown": "?"}[j["verdict"]]
                parts.append(f"{named(j['a'])} {self.display(j['word'])} {named(j['b'])} {mark}")
                proof.append({"step": "said", "a": j["a"], "word": j["word"], "b": j["b"], "law": j["kind"], "verdict": j["verdict"]})
            if judged:
                cells = []
            story = self.story_of(text)
            rule = (self.__dict__.get("reading_rules") or {}).get(self.form_of(*story[:2])) if story else None
            got = self.by_rule(rule["rule"], story[0], story[1]) if rule else None
            if got is not None:
                parts.append(self.display(got[0]))
                proof.append({"step": "read_rule", "form": self.form_of(*story[:2]), "rule": rule["rule"], "sentence": got[1] + 1,
                              "word": got[2] + 1, "right": rule["right"], "of": rule["of"], "digits": rule["digits"]})
                cells, amounts, judged = [], [], []
            for r in self.reckon(toks):
                mark = {"add": "+", "take": "−", "times": "×", "share": "÷"}[r["op"]]
                verdict = "" if r["said"] is None else (" ✓" if r["said"] == r["is"] else f" ✗ ({r['said']})")
                parts.append(f"{r['x']} {mark} {r['y']} = {'?' if r['is'] is None else r['is']}{verdict}")
                proof.append({"step": "reckon", "x": r["x"], "op": r["op"], "y": r["y"], "is": r["is"], "said": r["said"],
                              "word": r["word"]})
                amounts, cells = [], []
            if amounts and isinstance(self.world, RealWorld):
                n = amounts[0] * self.unit_of(text, toks)
                values = dict(enumerate(self.foresee_all(n)))
                chance = {j: L.odds_cell() is not None and not L.exact() for j, L in enumerate(self.learners)}
                odds = self.foresee_odds(min(n, 600)) if any(chance.values()) else []
                for j, v in values.items():
                    L = self.learners[j]
                    how = ("kind" if getattr(L, "recognized", None) else "laws" if L.counts_closed()
                           else "moments" if moment_trusted(getattr(L, "moment", None))
                           else "odds" if chance[j] else "none")
                    proof.append({"step": "foresee", "sense": j + 1, "cell": self.real_known.get(j), "after": n,
                                  "value": v if not chance[j] or not odds or odds[j] is None else odds[j][0],
                                  "odds": odds[j][1] if chance[j] and odds and odds[j] is not None else None, "how": how})
                shown = [("?" if v is None else str(v)) if not (chance[j] and odds and odds[j] is not None)
                         else f"{odds[j][0]} ({round(100 * odds[j][1])}%)" for j, v in values.items()]
                parts.append(f"+{n}: " + " · ".join(shown))
                if n <= 86_400:
                    self.foretold = (getattr(self, "foretold", None) or [])[-50:]
                    self.foretold.append({"due": self.world_steps + n, "values": {j: v for j, v in values.items()
                                                                                    if v is not None}, "text": text[:80]})
            asked_acts = [int(x) - 1 for x in re.findall(r"#(\d+)", text)]
            asked_acts = [a for a in asked_acts if 0 <= a < len(self.world.buttons)]
            if asked_acts or (amounts and not isinstance(self.world, RealWorld)):
                n = amounts[0] if amounts else len(asked_acts)
                shown = lambda x: "?" if x is None else str(x[0]) if x[1] >= 0.9995 else f"{x[0]} ({round(100 * x[1])}%)"
                got, waiting = self.what_if(asked_acts, n)
                for j, x in enumerate(got):
                    proof.append({"step": "foresee", "sense": j + 1, "after": n, "value": None if x is None else x[0],
                                  "odds": None if x is None else x[1], "acts": [a + 1 for a in asked_acts], "how": "odds"})
                parts.append(f"+{n}: " + " · ".join(shown(x) for x in got))
                if asked_acts and got != waiting:
                    parts.append("(" + " · ".join(shown(x) for x in waiting) + ")")
            if len(cells) == 2:
                g, a, b = self.law_graph(), cells[0], cells[1]
                prev, queue = {a: None}, [a]
                while queue and b not in prev:
                    x = queue.pop(0)
                    if len(prev) > 5000:
                        break
                    for y, code, n in g.get(x, ()):
                        if y not in prev:
                            prev[y] = (x, code, n)
                            queue.append(y)
                if b in prev:
                    chain, y = [], b
                    while prev[y] is not None:
                        x, code, n = prev[y]
                        chain.append((x, code, y, n))
                        y = x
                    chain.reverse()
                    mark = {"carry": "→", "carried": "←", "together": "⇄", "kindof": "⊂", "has": "⊃", "read": "∾",
                            "fore": "⇢", "fored": "⇠", "cause": "⇒", "caused": "⇐", "seeks": "↣", "flees": "↢", "part": "∈"}
                    back = {"carried": "carry", "fored": "fore", "caused": "cause"}

                    def joined(code):
                        w = said.get((back.get(code, code), "<" if code in back else ">"))
                        return f"{mark.get(code, '~')}{' ' + self.display(w) if w else ''}"

                    parts.append(" ".join([named(chain[0][0])] + [f"{joined(code)} {named(y)}" for _, code, y, _ in chain]))
                    proof += [{"step": "law", "a": x, "law": code, "b": y, "times": n} for x, code, y, n in chain]
                else:
                    parts.append(f"{named(a)} ? {named(b)}")
                    proof.append({"step": "no_chain", "a": a, "b": b})
            elif cells:
              for c in cells[:6]:
                  c, g = c, self.law_graph()
                  laws = [(code, y, n) for y, code, n in g.get(c, ())
                          if code in ("carry", "carried", "together", "fore", "fored", "cause", "caused", "seeks", "part")]
                  mark = {"carry": "→", "carried": "←", "together": "⇄", "fore": "⇢", "fored": "⇠", "cause": "⇒", "caused": "⇐",
                          "seeks": "↣", "part": "∈"}
                  back = {"carried": "carry", "fored": "fore", "caused": "cause"}
                  bits = []
                  for code, y, n in laws[:4]:
                      w = said.get((back.get(code, code), "<" if code in back else ">"))
                      a_, b_ = (y, c) if code in back else (c, y)
                      odd = next((v for v in self.odds_laws.values() if v["a"] == a_ and v["b"] == b_
                                  and v["code"] == back.get(code, code) and v["how"] == "law"), None)
                      more = f" ({'+' if type(odd['d']) is int and odd['d'] > 0 else ''}{odd['d']} · {odd['lag']}: {odd['q']} · {odd['p']})" if odd else ""
                      bits.append(f"{mark[code]}{' ' + self.display(w) if w else ''} {named(y)}{more}")
                      if odd:
                          proof.append({"step": "odds_law", "a": a_, "b": b_, "law": odd["code"], "lag": odd["lag"], "d": odd["d"],
                                        "q": odd["q"], "p": odd["p"], "digits": odd["digits"]})
                  for path in self.through(c):
                      if len(path) > 2:
                          bits.append("→→ " + named(path[-1]))
                          proof.append({"step": "through", "path": path})
                  ups = [y for y, code, n in g.get(c, ()) if code == "kindof"][:2]
                  bits += [f"⊂ {named(y)}" for y in ups]
                  sense = next((j for j, s0 in getattr(self, "real_known", {}).items() if s0 == c), None)
                  parts.append(named(c) + (" " + " · ".join(bits) if bits else ""))
                  proof += [{"step": "law", "a": c, "law": code, "b": y, "times": n} for code, y, n in laws[:4]]
                  proof += [{"step": "kindof", "a": c, "b": y} for y in ups]
                  if sense is not None:
                      proof.append({"step": "sense", "cell": c, "sense": sense + 1})
                  for an in list(self.__dict__.get("analogies") or ())[::-1]:
                      like = [b for a, b, _, _ in an["pairs"] if a == c and b != c]
                      if like:
                          bits.append(f"≈ {named(like[0])}")
                          proof.append({"step": "analogy", "cell": c, "like": like[0], "world": an["like"], "laws": an["laws"]})
                          break
                  parts[-1] = named(c) + (" " + " · ".join(bits) if bits else "")
                  if not bits and sense is None:
                      proof.append({"step": "alone", "cell": c})
            if not parts:
                parts.append("? " + " ".join(unknown[:4]) if unknown else "?")
                proof.append({"step": "unknown", "words": unknown[:6]})
                if unknown:
                    self.pending = (getattr(self, "pending", None) or [])[-19:] + [{"text": text[:200], "words": unknown[:6],
                                                                                   "t": round(time.time())}]
            answer = " | ".join(parts)
        self.say(answer, kind="answer", proof=proof[:12], asked=text[:200])
        self.emit("answered", text=answer, steps=len(proof))
        self.decide("answer", answer, {"asked": text[:80], "steps": [p["step"] for p in proof][:8]})
        return {"text": answer, "proof": proof}

    def answer_pending(self):
        """Questions it could not answer, asked again of itself when one of their words came to mean something."""
        pending = getattr(self, "pending", None)
        if not pending:
            return
        ready = [p for p in pending if any(self.meanings(w) or self.meanings(fold(w)) for w in p["words"])]
        for p in ready:
            pending.remove(p)
            self.think(p["text"])

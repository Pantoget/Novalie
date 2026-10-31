# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Asking the web, its council of brains, its reading goals."""

import collections
import concurrent.futures
import heapq
import itertools
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

from .. import config
from ..body import CODE
from ..cells import seen_symbol
from ..config import BORN_AT, EVIDENCE, EXACT, WORD_EVIDENCE, room
from ..evidence import evidence
from ..parts import council, senses
from ..text import SENTENCE_END, column_heads, fold, main_script, script_of, tokens
from ..web import (HOSTS, HOSTS_LOCK, OFFLINE, PAGES, READ_ANY, SLOT, fetch, fetch_page, link_end, links_in,
    robots_say, safe_url, site_of, turn, web_page)


class Asking:
    # -- asking the web: ways it learns itself -------------------------------------------------------------------
    def meet_ways(self, page, url):
        """Ways to ask the web that it meets in a page it read."""
        if not page:
            return
        found = []
        for f in page.get("forms") or ():
            q = urllib.parse.urlencode(f["hidden"])
            tmpl = f["action"] + "?" + (q + "&" if q else "") + urllib.parse.quote_plus(f["field"]) + "=" + SLOT
            found.append((("form", site_of(f["action"]), f["action"], f["field"]), tmpl, "form"))
        by_prefix = collections.Counter()
        for u, t in zip(page.get("links") or (), page.get("texts") or ()):
            try:
                parts = urllib.parse.urlsplit(u)
            except ValueError:
                continue
            if (parts.scheme not in ("http", "https") or parts.query or not parts.path.startswith("/")
                    or parts.path.endswith("/") or not any(ch.isalpha() for ch in t)):
                continue
            head, _, last = parts.path.rpartition("/")
            if fold(urllib.parse.unquote(last).replace("_", " ")) == fold(t):
                by_prefix[f"{parts.scheme}://{parts.netloc}{head}/"] += 1
        for prefix, n in by_prefix.items():
            if n > 2:
                found.append((("path", site_of(prefix), prefix), prefix + SLOT, "path"))
        with self.lock:
            for key, tmpl, kind in found:
                if key not in self.asks and safe_url(tmpl.replace(SLOT, "x")):
                    self.asks[key] = {"url": tmpl, "host": key[1], "kind": kind, "n": 0, "k": 0, "by": {},
                                      "trusted": {}, "met": url, "at": round(time.time())}
                    self.emit("way_met", how=kind, site=key[1])
            while len(self.asks) > room(500):
                worst = min(self.asks, key=lambda k: ((self.asks[k]["k"] + 0.5) / (self.asks[k]["n"] + 1),
                                                      -self.asks[k]["n"], repr(k)))
                del self.asks[worst]

    def ask_kind(self, word):
        """The kind of a word, for its ways to ask."""
        return "number" if self.number_of(word) is not None else script_of(word)

    def ask_chance(self, word):
        """How likely a page it reads holds a word anyway."""
        return (self.word_src.get(fold(word), 0) + 0.5) / (self.sources + 1)

    def ask_digits(self, way, kind):
        """How sure it is that a way to ask answers words of a kind."""
        got = tuple(way["by"].get(kind, ()))
        n, k = (got + (0, 0))[:2]
        e = got[2] if len(got) > 2 else 0.5 * n
        return evidence(n, k, min(0.999, e / n)) if n else 0.0

    def ways_to_ask(self, word):
        """Its ways to ask the web, in the order it tries them for this word."""
        kind, total = self.ask_kind(word), sum(w["n"] for w in self.asks.values())

        def rank(key):
            w = self.asks[key]
            e = self.ask_digits(w, kind)
            if e >= EVIDENCE + math.log10(max(1, len(self.asks))):
                return (0, -e)
            if w["n"] == 0:
                return (1, 0.0)
            return (2, -((w["k"] + 0.5) / (w["n"] + 1) + 1.5 * math.sqrt(2.0 * math.log(total + 1) / w["n"])))
        link = self.__dict__.get("link")
        return sorted((key for key in self.asks if link is None or link.mine(self.asks[key]["host"])),
                      key=lambda key: (rank(key), repr(key)))

    @staticmethod
    def holds(text, word):
        """How many sentences of a text hold a word."""
        w = fold(word)
        return sum(1 for sent in SENTENCE_END.split(text or "") if w in {fold(t) for t in tokens(sent)})

    def ask(self, word, source, most=3):
        """It asks the web about a word with the first of its ways to ask whose site may be asked now and that it
        did not ask this word before."""
        shown, w, chance = self.display(word), fold(word), self.ask_chance(word)
        for key in self.ways_to_ask(word):
            way = self.asks[key]
            q = urllib.parse.quote_plus(shown) if way["kind"] == "form" else urllib.parse.quote(shown)
            url = way["url"].replace(SLOT, q)
            if url in self.web_read or turn(way["host"]) > 0:
                continue
            ok, page = fetch_page(url)
            if ok is None:
                continue
            with self.lock:
                self.mark_read(url)
            hits, read, answered = collections.Counter(), 0, False
            if page and page["text"]:
                hits.update(self.read(None, page["text"], source + (site_of(page["final"]),), page["title"]))
                read, answered = 1, self.holds(page["text"], word) >= 3
                self.meet_ways(page, page["final"])
                links = [u for u, t in zip(page["links"], page["texts"])
                         if u != page["final"] and u not in self.web_read
                         and (w in fold(t) or w in fold(urllib.parse.unquote(u)))][:most]
                for u in links:
                    pause = turn(site_of(u))
                    if pause > 60:
                        continue
                    if pause > 0:
                        time.sleep(pause)
                    ok2, p2 = fetch_page(u)
                    if not ok2:
                        continue
                    with self.lock:
                        self.mark_read(u)
                    if p2 and p2["text"]:
                        got = self.read(None, p2["text"], source + (site_of(u),), p2["title"])
                        hits.update(got)
                        read += 1
                        answered = answered or self.holds(p2["text"], word) >= 2
                        self.log_reading(None, p2["title"] or u, sorted(got), site_of(u))
                        self.meet_ways(p2, u)
                        with self.lock:
                            self.related[w][p2["title"] or u] += 1
                log = page["title"] or page["final"]
                self.log_reading(word, log, sorted(hits), site_of(page["final"]))
            self.judge_ask(key, word, answered, chance)
            return hits, read
        return None

    def judge_ask(self, key, word, answered, chance):
        """What a way to ask did, counted for it and for words of this kind, with the chance a page held the word
        anyway."""
        kind = self.ask_kind(word)
        with self.lock:
            way = self.asks.get(key)
            if way is None:
                return
            way["n"] += 1
            way["k"] += answered
            n, k, e0 = (tuple(way["by"].get(kind, ())) + (0, 0, 0.0))[:3]
            way["by"][kind] = (n + 1, k + answered, e0 + chance)
            e = self.ask_digits(way, kind)
            chance_all = sum((tuple(x) + (0, 0, 0.0))[2] for x in way["by"].values())
            if not way["k"] and chance_all >= 1:
                del self.asks[key]
                self.emit("way_dropped", site=way["host"], how=way["kind"], asked=way["n"])
                self.decide("way_dropped", way["host"], {"kind": way["kind"], "asked": way["n"],
                                                         "chance": round(chance_all, 2)})
                return
            if answered and e >= EVIDENCE + math.log10(max(1, len(self.asks))) and kind not in way["trusted"]:
                way["trusted"][kind] = round(e, 1)
                self.emit("way_trusted", site=way["host"], how=way["kind"], words=kind, asked=n + 1, answered=k + answered,
                          url=way["url"].replace(SLOT, "\u00a7"), taught=way.get("taught"))
                self.decide("way_trusted", way["host"], {"kind": way["kind"], "words": kind, "asked": n + 1,
                                                         "answered": k + answered, "digits": round(e, 1)})

    def lookup(self, word):
        """A word you said that it does not know."""
        with self.lock:
            self.reading_now = word
        self.emit("reading", title=word, source="ask")
        got = self.ask(word, ("lookup", word))
        if got is None or not got[1]:
            with self.lock:
                self.tries[word] += 1
                if self.tries[word] < 6:
                    self.retry_at[word] = time.time() + 30 * 2 ** self.tries[word]
                    self.queue.append(word)
                    return
            self.log_reading(word, None, [], "")
            return
        with self.lock:
            self.salient[fold(word)] += 2.0
            for c in got[0]:
                self.salient[c] += 2.0
            self.urge += 1.0
        self.answer_pending()

    def learn_from_brains(self, lines):
        """What its other brains said."""
        link = self.__dict__.get("link")
        if link is None:
            return
        with self.lock:
            for line in lines:
                kind = line.get("kind")
                if kind == "way_trusted" and line.get("url"):
                    tmpl = line["url"].replace("\u00a7", SLOT)
                    if not any(w["url"] == tmpl for w in self.asks.values()) and safe_url(tmpl.replace(SLOT, "x")):
                        self.asks[("told", line.get("site"), tmpl)] = {
                            "url": tmpl, "host": line.get("site"), "kind": line.get("how") or "form", "n": 0, "k": 0,
                            "by": {}, "trusted": {}, "met": line.get("by"), "at": round(time.time()), "taught": line.get("by")}
                elif kind == "meaning" and line.get("word"):
                    w = line["word"]
                    self.__dict__.setdefault("told", set()).add(w)
                    self.__dict__.setdefault("told_by", {}).setdefault(w, line.get("by"))
                    del_old = len(self.told_by) - room(20_000)
                    for old in list(self.told_by)[:max(0, del_old)]:
                        del self.told_by[old]
                    if w not in self.looked and not self.meanings(w) and len(self.queue) < 8:
                        self.looked.add(w)
                        self.queue.append(line.get("shown") or w)
                elif kind == "link" and line.get("url") and link.mine(site_of(line["url"])):
                    self.add_web([line["url"]], float(line.get("promise") or 1.0))
                elif kind == "read" and line.get("url"):
                    self.__dict__.setdefault("council_read", set()).add(council.page_key(line["url"]))
            share = tuple(link.living)
            if share != self.__dict__.get("_share", share):
                theirs = [(u, p) for u, p in self.web_frontier.items() if not link.mine(site_of(u))]
                for u, p in theirs:
                    del self.web_frontier[u]
                    link.tell("link", url=u, promise=round(p, 3))
            self._share = share

    def minds_view(self):
        """Its view of its other minds."""
        out = {}
        for w in self.asks.values():
            by = w.get("taught")
            if not by:
                continue
            r = out.setdefault(by, {"told": 0, "held": 0, "failed": 0})
            r["told"] += 1
            if w.get("trusted"):
                r["held"] += 1
            elif w.get("n", 0) >= 6 and not w.get("k", 0):
                r["failed"] += 1
        for word, by in (self.__dict__.get("told_by") or {}).items():
            if not by:
                continue
            r = out.setdefault(by, {"told": 0, "held": 0, "failed": 0})
            r["told"] += 1
            if self.meanings(word):
                r["held"] += 1
        for r in out.values():
            r["trust"] = round((r["held"] + 0.5) / (r["held"] + r["failed"] + 1), 3)
        return out

    def brain_status(self):
        """How it is doing, for its council."""
        return {"pages": len(self.web_read), "sites": len(self.sites_done) + len(self.round_sites), "ways": len(self.asks),
                "trusted": sum(1 for w in self.asks.values() if w.get("trusted")), "meanings": len(self.read_meaning),
                "words": len(self.word_src), "proved": self.__dict__.get("proofs", 0),
                "first_proof": self.__dict__.get("first_proof"), "first_page": self.__dict__.get("first_page"),
                "waiting": len(self.web_frontier), "pooled": len(self.__dict__.get("_pool") or {}),
                "up": round(time.time() - BORN_AT), "code": CODE["print"], "at": round(time.time())}

    def mark_read(self, url):
        """A page it is reading."""
        self.web_read[url] = 1
        link = self.__dict__.get("link")
        if link is not None:
            link.tell("read", url=url)

    def share_counts(self):
        """Its brains prove meanings together."""
        link = self.__dict__.get("link")
        if link is None:
            return
        pool, changed = link.pooled()
        with self.lock:
            self._pool = pool
            totals, mine = self.chance_totals(), {}
            for w, cs in self.met_with.items():
                if cs and not self.is_glue(w):
                    m = sum(cs.values())
                    mine[w] = [[c, k, round(self.chance_of(w, c, totals) * m, 4)] for c, k in cs.items()]
            if changed:
                self.weigh(sorted(w for w in changed if not self.is_glue(w)))
        link.publish({"t": round(time.time()), "met": mine})

    def pooled(self, w, cs, totals):
        """The meetings of word w in all its brains' reading."""
        others = [b[w] for b in (self.__dict__.get("_pool") or {}).values() if w in b]
        if not others:
            return None
        own_m, ks = sum(cs.values()), collections.Counter(cs)
        rows = [({c: (k, e) for c, k, e in r}, sum(k for _, k, _ in r)) for r in others]
        for got, _ in rows:
            for c, (k, _) in got.items():
                ks[c] += k
        m = own_m + sum(mi for _, mi in rows)

        def p_of(c):
            p = self.chance_of(w, c, totals)
            e = p * own_m + sum(got[c][1] if c in got else mi * p for got, mi in rows)
            return min(max(e / m, 1e-12), 1.0)
        return ks, m, p_of

    def resting(self, host):
        """A site it finished with, that it does not go back to yet."""
        done = self.sites_done.get(host)
        if not done:
            return False
        return time.time() - (done[2] if len(done) > 2 else 0) < self.read_way("site_rest")

    def point_to(self, url):
        """A page you pointed it to."""
        host, url = site_of(url), url.split("#")[0]
        reachable = safe_url(url)
        with self.lock:
            if reachable and host:
                self.web_read.pop(url, None)
                self.sites_done.pop(host, None)
                self.add_web([url], promise=1e6)
            ok = reachable and url in self.web_frontier
            if ok and host not in self.round_sites:
                self.round_sites[host] = {"pages": 0, "gain": 0.0, "dry": 0, "done": False}
                self.emit("connected", site=host)
        self.emit("pointed", url=url, ok=ok)

    def link_promise(self, url):
        """How much more promising a link is for how it ends."""
        stats = self.link_yield
        reads, gave = stats.get(link_end(url), (0, 0))
        everyone = (sum(g for _, g in stats.values()) + 1) / (sum(r for r, _ in stats.values()) + 2)
        return min(5.0, max(0.5, (gave + 1) / (reads + 2) / everyone))

    def add_web(self, urls, promise=1.0):
        """Pages it may read later, each with how promising it looks."""
        link = self.__dict__.get("link")
        for u in urls:
            u = ("https:" + u if u.startswith("//") else u).split("#")[0]
            if not u.startswith(("http://", "https://")) or u in self.web_read or self.resting(site_of(u)):
                continue
            if council.page_key(u) in (self.__dict__.get("council_read") or ()):
                continue
            if link is not None and not link.mine(site_of(u)):
                link.tell("link", url=u, promise=round(promise * self.link_promise(u), 3))
                continue
            self.web_frontier[u] = max(self.web_frontier.get(u, 0.0), promise * self.link_promise(u))
        if len(self.web_frontier) > room(5000):
            keep = sorted(self.web_frontier.items(), key=lambda x: -x[1])[:room(4000)]
            self.web_frontier = dict(keep)

    def browse(self):
        """Its own reading turn, beside the open web it reads all the time."""
        if self.pursue_goal():
            return True
        for w in self.wants(most=4):
            if fold(w) not in self.looked:
                if not self.can_ask(w):
                    return False
                with self.lock:
                    self.looked.add(fold(w))
                self.emit("curious", word=w, shown=self.display(w))
                return self.ask(w, ("curious", w)) is not None
        return False

    def can_ask(self, word):
        """Has it a way to ask the web about this word now."""
        return any(turn(self.asks[key]["host"]) <= 0 for key in self.ways_to_ask(word))

    def new_goal(self):
        """Its next goal: a word you asked about that it could not place."""
        with self.lock:
            done0 = getattr(self, "goals_done", None) or {}
            tried = {w for w, x in done0.items()
                     if not isinstance(x, tuple) or x[0] == "reached" or sum(self.met_with.get(w, {}).values()) <= x[1]}
            for p in getattr(self, "pending", None) or []:
                for w in p["words"]:
                    k = fold(w)
                    if k not in tried and not self.meanings(k):
                        return {"kind": "asked", "word": k, "cell": None, "steps": [], "dry": 0, "done": False,
                                "born": round(time.time()), "evidence": 0.0}
            totals, best = self.chance_totals(), None
            for w, cs in list(self.met_with.items()):
                if w in tried or len(w) < 3 or self.is_glue(w) or w not in self.public_words:
                    continue
                have, m = {c for c, _ in self.read_meaning.get(w, ())}, sum(cs.values())
                for c, k in cs.items():
                    if k >= 2 and c not in have:
                        e = evidence(m, k, self.chance_of(w, c, totals))
                        if e > 0 and (best is None or e > best[0]):
                            best = (e, w, c)
            if best is None:
                return None
            e, w, c = best
            return {"kind": "meaning", "word": w, "cell": c, "steps": [], "dry": 0, "done": False,
                    "born": round(time.time()), "evidence": round(e, 1)}

    def pursue_goal(self):
        """One step of its goal."""
        goal = getattr(self, "goal", None)
        if goal is None or goal["done"]:
            goal = self.goal = self.new_goal()
            if goal is None:
                return False
            self.goals_made = getattr(self, "goals_made", 0) + 1
            self.emit("goal", word=self.display(goal["word"]), cell=goal["cell"], what=goal["kind"], evidence=goal["evidence"])
            self.decide("goal", self.display(goal["word"]), {"kind": goal["kind"], "cell": goal["cell"],
                                                             "evidence": goal["evidence"]})
        w = goal["word"]
        before = dict(self.met_with.get(w, {}))
        got = self.ask(w, ("goal", w, len(goal["steps"])))
        if got is None:
            return False
        read = got[1]
        with self.lock:
            after = self.met_with.get(w, {})
            gained = {c: after.get(c, 0) - before.get(c, 0) for c in after if after.get(c, 0) > before.get(c, 0)}
            goal["steps"].append({"step": len(goal["steps"]), "read": read, "gained": gained})
            toward = gained.get(goal["cell"], 0) if goal["cell"] is not None else sum(gained.values())
            goal["dry"] = 0 if toward else goal["dry"] + 1
            reached = bool(self.meanings(w)) and (goal["cell"] is None or goal["cell"] in self.meanings(w))
            self.decide("goal_step", self.display(w), {"step": len(goal["steps"]), "read": read,
                                                      "gained": {c: n for c, n in list(gained.items())[:4]}})
            if reached or goal["dry"] >= self.read_way("goal_dry") or len(goal["steps"]) >= self.read_way("goal_steps"):
                ahead = sum((st["gained"].get(goal["cell"], 0) if goal["cell"] is not None else sum(st["gained"].values()))
                            for st in goal["steps"])
                self.judge_read(("goal_steps", "goal_dry"), 3.0 * reached + ahead / max(1, len(goal["steps"])))
                goal["done"] = True
                self.goals_done = (getattr(self, "goals_done", None) or {})
                self.goals_done[w] = ("reached" if reached else "dropped", sum(self.met_with.get(w, {}).values()))
                while len(self.goals_done) > 2000:
                    del self.goals_done[next(iter(self.goals_done))]
                self.goals_reached = getattr(self, "goals_reached", 0) + reached
                self.emit("goal_reached" if reached else "goal_dropped", word=self.display(w), cell=goal["cell"],
                          steps=len(goal["steps"]), means=self.meanings(w)[:2])
                if not reached:
                    self.decide("replan", self.display(w), {"steps": len(goal["steps"]), "dry": goal["dry"]})
        self.answer_pending()
        return True

    def wants(self, most=20):
        """What it wants to know."""
        known = set(self.read_meaning) | set(self.looked)
        public = self.public_words
        words = [self.display(w) for w, _ in self.word_src.most_common(4000)
                 if w in public and len(w) > 2 and w not in known and not self.is_glue(w)][:most]
        cells = sorted({x for k in self.kinds_seen for x in set(k[1]) | {math.prod(k[1])}},
                       key=lambda x: -self.kinds_seen.get(("flat", (x,)), 0))
        private = set(getattr(self.__dict__.get("world"), "private", None) or ())
        sees = [x for x in dict.fromkeys(x for j, x in enumerate(getattr(self, "seen_now", None) or ()) if j not in private)
                if isinstance(x, int) and x not in cells]
        for x in cells + sees:
            if len(words) >= most:
                break
            if str(x) not in known:
                words.append(str(x))
        return words[:most]

    def wanted_now(self):
        """The words it wants to know."""
        at, got = self.__dict__.get("_wanted", (0.0, frozenset()))
        if time.time() - at > 60:
            got = frozenset(fold(w) for w in self.wants(most=40))
            self._wanted = (time.time(), got)
        return got

    def read_web(self, most=None):
        """The open web, read only, a group of sites at a time."""
        most = most or self.read_way("sites_at_once")
        with self.lock:
            if self.round_sites and all(st["done"] for st in self.round_sites.values()):
                self.end_round()
            if not self.web_frontier and not self.round_sites:
                if time.time() - self.__dict__.get("_nowhere_at", 0.0) > 3600:
                    self._nowhere_at = time.time()
                    self.emit("nowhere")
                return False
            mine = lambda h: self.__dict__.get("link") is None or self.link.mine(h)
            if not self.round_sites:
                for u, _ in sorted(self.web_frontier.items(), key=lambda x: -x[1]):
                    h = site_of(u)
                    if h and h not in self.round_sites and not self.resting(h) and mine(h):
                        self.round_sites[h] = {"pages": 0, "gain": 0.0, "dry": 0, "done": False}
                        self.emit("connected", site=h)
                        if len(self.round_sites) >= self.read_way("round_size"):
                            break
            waiting = {h for h, st in self.round_sites.items() if not st["done"]}
            best_of, open_to = {}, set()
            read_by_others = self.__dict__.get("council_read") or ()
            for u, promise in self.web_frontier.items():
                h = site_of(u)
                if h in waiting and mine(h) and council.page_key(u) not in read_by_others:
                    open_to.add(h)
                    if turn(h) <= 0 and promise > best_of.get(h, ("", -1.0))[1]:
                        best_of[h] = (u, promise)
            ranked = sorted(best_of.values(), key=lambda x: -x[1])[:most]
            picks, promise_of = [u for u, _ in ranked], dict(ranked)
            if not picks:
                for h in waiting:
                    if h not in open_to or turn(h) > 3 * config.GAP_FLOOR:
                        self.round_sites[h]["done"] = True
                return False
            for u in picks:
                del self.web_frontier[u]
                self.mark_read(u)
            if len(self.web_read) > room(20000):
                for u in list(self.web_read)[:room(5000)]:
                    del self.web_read[u]
        with concurrent.futures.ThreadPoolExecutor(len(picks)) as pool:
            got = list(pool.map(fetch_page, picks))
        for u, (ok, page) in zip(picks, got):
            tries = self.web_retry.get(u, 0) if hasattr(self, "web_retry") else 0
            if (ok is None or (ok and page is None)) and tries < 2:
                with self.lock:
                    self.web_retry = getattr(self, "web_retry", {})
                    self.web_retry[u] = tries + 1
                    while len(self.web_retry) > room(5000):
                        del self.web_retry[next(iter(self.web_retry))]
                    self.web_read.pop(u, None)
                    self.web_frontier[u] = promise_of.get(u, 1.0)
                continue
            self.took_page(u, bool(ok), page)
        return any(page for _, page in got)

    def read_by_act(self, wait=2.0):
        """Its act of reading: the most promising page it may ask now."""
        seen = self.__dict__.setdefault("read_acts", {})
        for k in ("off", "nothing", "asked", "in_time", "late", "failed", "not_reached"):
            seen.setdefault(k, 0)
        seen.setdefault("seconds", 0.0)
        if OFFLINE.is_set():
            seen["off"] += 1
            return False
        with self.lock:
            mine = lambda h: self.__dict__.get("link") is None or self.link.mine(h)
            others = self.__dict__.get("council_read") or ()
            best, key = None, None
            for u, promise in heapq.nlargest(400, self.web_frontier.items(), key=lambda x: x[1]):
                h = site_of(u)
                if not h or turn(h) > 0 or self.resting(h) or not mine(h) or council.page_key(u) in others:
                    continue
                say = robots_say(u)
                if say is False:
                    continue
                with HOSTS_LOCK:
                    good = HOSTS.get(h, {}).get("good", 0) > 0 and not HOSTS.get(h, {}).get("bad", 0)
                k = (say is True and good, say is True, promise)
                if key is None or k > key:
                    best, key = (u, promise), k
            if best is None:
                seen["nothing"] += 1
                return False
            u, promise = best
            del self.web_frontier[u]
            self.mark_read(u)
            seen["asked"] += 1
        t0, came, act = time.time(), threading.Event(), {"waits": True}

        def go():
            try:
                final, status, kind, raw = fetch(u)
                ok = False if status == 403 and raw is None else None if raw is None else True
                page = web_page(final, kind, raw) if ok else None
                with self.lock:
                    answers = seen.setdefault("answers", {})
                    answers[str(status)] = answers.get(str(status), 0) + 1
                tries = self.__dict__.get("web_retry", {}).get(u, 0)
                if (ok is None or (ok and page is None)) and tries < 2:
                    with self.lock:
                        seen["not_reached"] += 1
                        self.web_retry = self.__dict__.get("web_retry") or {}
                        self.web_retry[u] = tries + 1
                        self.web_read.pop(u, None)
                        self.web_frontier[u] = promise
                    return
                with self.lock:
                    seen["seconds"] = round(0.9 * seen["seconds"] + 0.1 * (time.time() - t0), 3)
                    if page is None:
                        seen["failed"] += 1
                    elif act["waits"]:
                        self.acts_read = self.__dict__.get("acts_read", 0) + 1
                        seen["in_time"] += 1
                    else:
                        seen["late"] += 1
                came.set()
                self.took_page(u, bool(ok), page)
            except Exception as e:
                self.emit("trouble", where="reading", what=f"{type(e).__name__}: {e}"[:200])
            finally:
                came.set()
        threading.Thread(target=go, daemon=True).start()
        came.wait(wait)
        with self.lock:
            act["waits"] = False
        return True

    def took_page(self, best, ok, page):
        """One page of the open web, come in."""
        with PAGES:
            self._took_page(best, ok, page)

    def _took_page(self, best, ok, page):
        """One page of the open web, come in."""
        host = site_of(best)
        self.__dict__.setdefault("first_page", time.time())
        with self.lock:
            self.reading_now = best
            if ok and page:
                self.pages_read = self.__dict__.get("pages_read", 0) + 1
        if ok:
            self.emit("reading", title=best, source=host)
        made = self.meanings_made
        hits, seen, rep = collections.Counter(), 0, None
        if page and page["bytes"] is not None:
            rep = self.read_any(page["bytes"], allow=("pixels",), source=host)
            seen = 1 if rep and rep.get("readable") else 0
        elif page and page["text"]:
            hits = self.read(None, page["text"], ("web", host), best)
        if page:
            gave = bool(page["bytes"] is not None and rep and (rep.get("columns") or rep.get("time") or rep.get("lattice")))
            with self.lock:
                got = self.link_yield.setdefault(link_end(best), [0, 0])
                got[0] += 1
                got[1] += gave
        if page and page["images"] and senses.available():
            img = page["images"][0]
            ih = site_of(img)
            if turn(ih) <= 0:
                _, _, _, raw = fetch(img, config.PAGE_BYTES // 2)
                if raw:
                    rep = self.read_any(raw, allow=("pixels",), source=ih or host)
                    seen += 1 if rep and rep.get("lattice") else 0
        gain = 5 * (self.meanings_made - made) + min(3, len(hits)) / 3 + seen
        with self.lock:
            st = self.round_sites.get(host)
            if st is not None:
                st["pages"] += 1
                st["gain"] += gain
                st["dry"] = 0 if gain else st["dry"] + 1
                st["done"] = st["pages"] >= self.read_way("site_pages") or st["dry"] >= self.read_way("site_dry")
            if page:
                wanted = self.wanted_now()
                links = [(u, t) for u, t in zip(page["links"], page.get("texts") or [""] * len(page["links"]))
                         if u not in self.web_read]
                away = [x for x in links if site_of(x[0]) != host]
                for u, t in away[:room(15)] + [x for x in links if site_of(x[0]) == host][:room(10)]:
                    near = len(wanted & {fold(x) for x in tokens(t)}) if t else 0
                    self.add_web([u], (1.0 + gain) * (1 + near))
        if page:
            self.meet_ways(page, best)
        if page and page["text"]:
            self.log_reading(None, page["title"] or page["final"], sorted(hits), host)

    def end_round(self):
        """It has finished with this group of sites, so it cuts the connection."""
        sites = list(self.round_sites)
        for h, st in self.round_sites.items():
            self.sites_done[h] = (st["pages"], round(st["gain"], 1), round(time.time()))
        while len(self.sites_done) > room(5000):
            del self.sites_done[next(iter(self.sites_done))]
        self.web_frontier = {u: v for u, v in self.web_frontier.items() if site_of(u) not in self.round_sites}
        self.rounds += 1
        self.emit("disconnected", sites=sites, round=self.rounds,
                  pages=sum(st["pages"] for st in self.round_sites.values()),
                  gain=round(sum(st["gain"] for st in self.round_sites.values()), 1))
        pages = sum(st["pages"] for st in self.round_sites.values())
        if pages:
            self.judge_read(("sites_at_once", "round_size", "site_pages", "site_dry", "site_rest"),
                            sum(st["gain"] for st in self.round_sites.values()) / pages)
        self.round_sites = {}

    def read_any(self, data, allow=(), source="", seeds=False):
        """Anything at all, read by its universal reader."""
        if seeds or b"http" in data[:2_000_000]:
            found = links_in(data[:2_000_000].decode("utf-8", errors="ignore"), hosts=seeds)
            if found:
                with self.lock:
                    self.add_web(found, promise=1e3 if seeds else 1.0)
        with READ_ANY:
            rep = self.reader.read(data, allow=allow, source=source,
                                   on_try=lambda chain, got=None: self.emit("try", chain=chain, got=got, source=source))
        if rep is None:
            return None
        text = rep.pop("text", None)
        if text:
            self.read(None, text, ("any", source))
            with self.lock:
                self.add_web(links_in(text[:2_000_000], hosts=seeds), promise=1e3 if seeds else 1.0)
            rep["words"] = list(dict.fromkeys(self.display(fold(t)) for t in tokens(text[:20000]) if self.is_word(fold(t))))[:16]
        found, near = [], {}
        lat = rep.get("lattice")
        if lat:
            found.append(("repeats", lat["windings"]))
        heads = column_heads(text, rep["shape"]["columns"]) if text and rep.get("columns") else None
        for c in rep.get("columns", []):
            near[len(found)] = (heads or {}).get(c["column"], "") if c.get("exact", 0) >= EXACT else ""
            found.append(("column", [c["every"]]))
        if rep.get("time"):
            found.append(("time", [rep["time"]["every"]]))
        if not found and rep.get("rhythms") and not rep.get("shape"):
            found.append(("rhythm", [int(rep["rhythms"][0][0])]))
        with self.lock:
            for origin, wind in found:
                kind = ("seen", tuple(int(w) for w in wind))
                if not self.seen_kinds[kind]:
                    self.emit("born", s=seen_symbol(kind))
                    self.salient[seen_symbol(kind)] += 1.0
                    self.urge += 0.5
                self.seen_kinds[kind] += 1
                meta = self.seen_meta.setdefault(kind, {"origin": origin, "first": source})
                meta["last"] = source
            syms = sorted({seen_symbol(("seen", tuple(int(w) for w in wd))) for _, wd in found})
            for pair in itertools.combinations(syms, 2):
                self.co_read[pair] += 1
            if text and found:
                self.ground(text, found, self.table_source(heads, source) if heads else ("any", source), near)
                if origin == "repeats" and lat.get("unit_png"):
                    meta["unit"] = lat["unit_png"]
            self.last_read = dict(rep, at=round(time.time(), 1))
            self.read_history.append({"source": source, "at": round(time.time()), "readable": rep.get("readable", True),
                                      "chain": rep.get("chain") or [], "after": rep.get("after"),
                                      "found": [seen_symbol(("seen", tuple(int(w) for w in wd))) for _, wd in found],
                                      "types": rep.get("types") or [], "size": rep.get("size")})
            del self.read_history[:-40]
            if found:
                self.generals_soon()
            if len(self.seen_kinds) > room(5000):
                for kind, _ in self.seen_kinds.most_common()[room(4000):]:
                    del self.seen_kinds[kind]
                    self.seen_meta.pop(kind, None)
        short = {k: rep.get(k) for k in ("source", "readable", "chain", "after", "new_way", "types")}
        if rep.get("shape"):
            short["shape"] = rep["shape"]
        if lat:
            short["windings"], short["defects"] = lat["windings"], lat["defects"]
        if found:
            short["found"] = [seen_symbol(("seen", tuple(w))) for _, w in found]
        self.emit("read-any", **short)
        return rep

    def table_source(self, heads, source):
        """Whose evidence a table is."""
        names = {fold(t) for h in (heads or {}).values() for t in tokens(h) if self.is_word(fold(t))}
        if len(names) < 2:
            return ("any", source)
        best, score = None, 0.0
        for key, theirs in self.templates.items():
            share = len(names & theirs) / len(names | theirs)
            if share > score:
                best, score = key, share
        if best is not None and score >= 0.6:
            return ("table", best)
        key = max(self.templates, default=0) + 1
        self.templates[key] = names
        while len(self.templates) > room(500):
            old = next(iter(self.templates))
            del self.templates[old]
            self.table_books.pop(old, None)
        return ("table", key)

    def ground(self, text, found, source, near=None):
        """Words of a file go with the structures it found in that same file."""
        def content(s):
            return sorted({w for w in (fold(t) for t in tokens(s)) if self.is_word(w) and not self.is_glue(w)})[:2000]

        words = content(text)
        if source[0] == "table":
            book = self.table_books.setdefault(source[1], collections.defaultdict(set))
        else:
            book = self.counted_by.pop(source, None)
            if book is None:
                book = collections.defaultdict(set)
            self.counted_by[source] = book
        done = book["§"]
        weighed, trials, columns = set(), collections.Counter(), collections.Counter()
        for i, (_, wind) in enumerate(found):
            sym = seen_symbol(("seen", tuple(int(x) for x in wind)))
            if sym not in done:
                done.add(sym)
                self.number_articles[sym] += 1
                sc = main_script([words])
                if sc:
                    self.number_by.setdefault(sc, collections.Counter())[sym] += 1
            column = bool(near) and bool(near.get(i))
            if column and ("§c", sym) not in done:
                done.add(("§c", sym))
                self.table_columns[sym] += 1
            these = content(near[i]) if near and i in near else words
            weighed.update(these)
            for w in these:
                if sym not in book[w]:
                    book[w].add(sym)
                    self.met_with[w][sym] += 1
                    trials[w] += 1
                    if column:
                        self.table_met[w][sym] += 1
                        columns[w] += 1
        totals = self.chance_totals()
        for w, t in trials.items():
            self.expect_more(w, t, totals)
        every = max(1, sum(self.table_columns.values()))
        for w, t in columns.items():
            exp, cs = self.table_expect.setdefault(w, {}), self.table_met[w]
            before = sum(cs.values()) - t
            for c in cs:
                p = self.table_columns[c] / every
                if c not in exp:
                    exp[c] = before * p
                exp[c] += t * p
        self.weigh(weighed)

    def look_inbox(self):
        """Files you put in its folder."""
        link = self.__dict__.get("link")
        if link is not None and link.name != "Nova(1)":
            return False
        try:
            names = sorted(os.listdir(config.INBOX))
        except OSError:
            return False
        for name in names:
            path = os.path.join(config.INBOX, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            key = f"{name}:{st.st_size}:{int(st.st_mtime)}"
            if not os.path.isfile(path) or key in self.inbox_seen:
                continue
            with self.lock:
                self.inbox_seen[key] = round(time.time())
                self.reading_now = name
            try:
                with open(path, "rb") as f:
                    data = f.read(64_000_000)
            except OSError:
                continue
            shown = name + (" [0–64 MB]" if st.st_size > 64_000_000 else "")
            self.emit("reading", title=shown, source="inbox")
            self.read_any(data, allow=("pixels", "frames", "sound"), source="inbox · " + shown, seeds=True)
            return True
        return False

    def curious(self):
        """What it wants to know more about, chosen by itself."""
        totals = self.chance_totals()
        near = []
        for w, cs in self.met_with.items():
            if w in self.looked or w in self.read_meaning:
                continue
            m = sum(cs.values())
            for c, k in cs.items():
                if k >= 3:
                    e = evidence(m, k, self.chance_of(w, c, totals))
                    if 3 <= e < WORD_EVIDENCE:
                        near.append((e, w, c))
        for e, w, c in sorted(near, reverse=True)[:2]:
            if len(self.queue) < 8:
                self.looked.add(w)
                self.queue.append(w)
                self.emit("curious", word=w, s=c, e=round(e, 1), shown=self.display(w))

    def log_reading(self, word, title, concepts, source=""):
        with self.lock:
            self.reading_log.append({"word": word, "title": title, "concepts": concepts, "source": source})
            del self.reading_log[:-30]
        self.emit("read", word=word, title=title, concepts=concepts[:8], source=source)

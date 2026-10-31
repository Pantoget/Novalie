/* Novalie's page: the panels beside its network — what it is doing now, your talk with it, how it reads, what happened, how it grew, and a guide. */
"use strict";

const $ = (s, root) => (root || document).querySelector(s);
const $$ = (s, root) => [...(root || document).querySelectorAll(s)];
function el(tag, cls, txt) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = txt;
  return e;
}
function svgIcon(name, cls) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  if (cls) s.setAttribute("class", cls);
  const u = document.createElementNS("http://www.w3.org/2000/svg", "use");
  u.setAttribute("href", "#i-" + name);
  s.appendChild(u);
  return s;
}
function clear(e) { while (e.firstChild) e.removeChild(e.firstChild); return e; }
const isSymbol = (w) => /^\d+(?:[.,x×]\d+)*$/.test(w);
function ago(ts) {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return t("unit.s", Math.round(s));
  if (s < 3600) return t("unit.m", Math.round(s / 60));
  if (s < 86400) return t("unit.h", Math.round(s / 3600));
  return t("unit.d", Math.round(s / 86400));
}
function age(born) {
  const s = Math.max(0, Date.now() / 1000 - born);
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${t("unit.d", d)} ${t("unit.h", h)}` : h ? `${t("unit.h", h)} ${t("unit.m", m)}` : t("unit.m", m);
}
const clock = (ts) => new Date(ts * 1000).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit", second: "2-digit", numberingSystem: "latn" });

const EVENT_KIND = {
  world: ["world", "world", "cycle"], understood: ["world", "check", "ok"],
  recognized: ["world", "eye", "ok"], born: ["cells", "spark", "seen"], pruned: ["cells", "scissors", "dim"],
  invented: ["cells", "spark", "invented"], inventing: ["cells", "cpu", "dim"], invention_failed: ["cells", "close", "dim"],
  law: ["cells", "link", "accent"],
  grammar: ["words", "key", "accent"],
  surprise: ["cells", "close", "warn"], plan: ["cells", "spark", "dim"], plan_dropped: ["cells", "close", "dim"],
  general: ["cells", "spark", "general"], new_way: ["cells", "key", "accent"], circuit: ["cells", "spark", "circuit"],
  odds: ["cells", "spark", "odds"], lawless: ["cells", "eye", "odds"], odds_revised: ["cells", "close", "warn"],
  grain: ["cells", "eye", "odds"], thing: ["cells", "spark", "thing"], relword: ["words", "key", "word"], opword: ["words", "key", "word"], numberword: ["words", "key", "word"], frames: ["words", "link", "word"],
  goal: ["reading", "key", "accent"], goal_reached: ["reading", "check", "ok"], goal_dropped: ["reading", "skip", "dim"],
  answered: ["speech", "spark", "accent"], foretold: ["world", "check", "ok"],
  heard: ["speech", "ear", "accent"], spoke: ["speech", "talk", "accent"],
  meaning: ["words", "key", "word"], linked: ["words", "link", "word"], curious: ["words", "question", "word"],
  read: ["reading", "doc", "gear"], reading: ["reading", "read", "gear"], "read-any": ["reading", "cpu", "seen"],
  given: ["reading", "file", "accent"], connected: ["web", "plug", "cycle"], disconnected: ["web", "unplug", "dim"],
  trouble: ["trouble", "warn", "bad"], paused: ["world", "pause", "warn"], offline: ["web", "unplug", "dim"],
  pointed: ["web", "link", "accent"], unnamed: ["speech", "close", "dim"], gentle: ["world", "cpu", "dim"], forgot: ["words", "scissors", "dim"],
  way_met: ["web", "key", "accent"], way_trusted: ["web", "check", "ok"], way_dropped: ["web", "close", "dim"], nowhere: ["web", "unplug", "dim"],
  brain_made: ["brains", "spark", "accent"], brain_gone: ["brains", "close", "dim"],
  concept: ["cells", "eye", "accent"], made: ["cells", "spark", "invented"], made_gone: ["cells", "close", "dim"], made_like: ["cells", "link", "accent"],
  moment: ["cells", "eye", "odds"], odds_cause: ["cells", "key", "odds"], odds_drift: ["cells", "close", "warn"], reading_rule: ["words", "key", "word"],
  trying: ["cells", "eye", "dim"], grew: ["cells", "spark", "accent"],
};
const colorOf = (k) => ({ ok: C.ok, dim: C.dim, accent: C.accent, bad: C.bad, warn: C.warn })[k] || C[k] || C.accent;

function targetOf(e) {
  const id = (x) => (x == null ? null : Brain.idOf(x));
  const word = (w) => (w != null && Brain.get("w:" + w) ? "w:" + w : null);
  switch (e.k) {
    case "born": case "recognized": case "invented": return id(e.s);
    case "law": return id(e.a);
    case "meaning": return word(e.word) || id(e.s);
    case "linked": return word(e.a) || word(e.b);
    case "curious": return word(e.word) || id(e.s);
    case "understood": case "spoke": case "heard":
      return (e.symbols || []).map(id).find(Boolean) || (e.words || []).map(word).find(Boolean) || null;
    case "read-any": return (e.found || []).map((s) => (Brain.get("s:" + s) ? "s:" + s : id(s))).find(Boolean) || null;
    case "read": return (e.concepts || []).map(id).find(Boolean) || word(e.word);
    case "unnamed": return id(e.s) || word(e.word);
    case "forgot": return word(e.word) || id(e.s);
    default: return null;
  }
}

const Panels = (() => {
  /* ---------- the world it is in, drawn as its sensors ---------- */
  const sensorState = new Map();
  let sensors = [], worldNum = null;

  function drawSensor(ctx, cx, cy, R, s, key, time) {
    if (s.invented) {
      drawCell(ctx, "invented", cx, cy, R * 0.82, { nature: s.nature, symbol: s.s, t: time, rate: 1, act: s.sure ? 0.9 : 0.4 });
      return;
    }
    const cyc = (s.cycles || []).filter((d) => d > 0).slice(0, 3);
    if (!cyc.length) {
      const spin = time * 0.8;
      ctx.strokeStyle = rgba(C.dim, 0.55);
      ctx.setLineDash([2, 3]);
      ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(cx, cy, R * 0.86, spin, spin + TAU); ctx.stroke();
      ctx.setLineDash([]);
      const m = s.mapped || 0;
      ctx.strokeStyle = rgba(C.cycle, 0.8);
      ctx.lineWidth = Math.max(1.5, R * 0.1);
      ctx.beginPath(); ctx.arc(cx, cy, R * 0.86, -Math.PI / 2, -Math.PI / 2 + TAU * Math.min(1, Math.log10(1 + m) / 3)); ctx.stroke();
      text(ctx, cx, cy - (m ? R * 0.12 : 0), "?", R * 0.56, C.muted, 700);
      if (m) text(ctx, cx, cy + R * 0.38, fmtK(m), R * 0.28, C.dim, 650);
      return;
    }
    const col = s.known ? C.word : s.sure ? C.ok : C.cycle;
    let st = sensorState.get(key);
    if (!st) { st = { a: [] }; sensorState.set(key, st); }
    const rings = cyc.map((d, i) => ({ d, rad: R * (0.88 - i * 0.22) }));
    rings.forEach(({ d, rad }, i) => {
      if (i === 0 && cyc.length === 1) ring(ctx, cx, cy, rad, R * 0.16, d, s.T && s.T.length ? s.T : null, col, -Math.PI / 2);
      else {
        ctx.strokeStyle = rgba(col, 0.28);
        ctx.lineWidth = R * 0.1;
        ctx.beginPath(); ctx.arc(cx, cy, rad, 0, TAU); ctx.stroke();
        ticks(ctx, cx, cy, rad + R * 0.05, d, col, 0.8, R * 0.1);
      }
      const p = (s.p || [])[i];
      if (p != null) {
        const target = -Math.PI / 2 + ((p + (cyc.length === 1 ? 0.5 : 0)) * TAU) / d;
        let a = st.a[i] == null ? target : st.a[i];
        let diff = ((target - a + Math.PI) % TAU + TAU) % TAU - Math.PI;
        a += diff * 0.25;
        st.a[i] = a;
        marker(ctx, cx, cy, rad, a, Math.max(1.6, R * 0.09), col);
      }
    });
    const label = cyc.length === 1 ? String(cyc[0]) : cyc.join("·");
    text(ctx, cx, cy, label, Math.min(R * 0.5, (R * 1.5) / Math.max(2, label.length * 0.62)), C.text, 750);
    if (s.sure) {
      ctx.fillStyle = C.ok;
      ctx.beginPath(); ctx.arc(cx + R * 0.72, cy - R * 0.72, R * 0.2, 0, TAU); ctx.fill();
      text(ctx, cx + R * 0.72, cy - R * 0.72, "✓", R * 0.26, "#062", 900);
    }
  }

  function paintStrip(time) {
    const cv = $("#stripCanvas");
    if (!cv) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (!sensors.length) return;
    const R = Math.min(h / 2 - 3, 27);
    const gap = 14;
    const n = Math.min(sensors.length, Math.max(1, Math.floor((w + gap) / (R * 2 + gap))));
    const total = n * R * 2 + (n - 1) * gap;
    const rtl = dir() === "rtl";
    stripHits = [];
    for (let i = 0; i < n; i++) {
      const idx = rtl ? n - 1 - i : i;
      const cx = (w - total) / 2 + R + i * (R * 2 + gap);
      drawSensor(ctx, cx, h / 2, R, sensors[idx], "strip" + idx, time);
      stripHits.push({ cx, R, idx });
    }
  }

  function sensorCell(s) {
    if (s.invented) return s.sure ? Brain.idOf(s.s) : null;
    if (s.known && s.s) {
      const id = Brain.idOf(s.s);
      if (id) return id;
    }
    const cyc = (s.cycles || []).filter((d) => d > 0);
    if (!cyc.length || !(s.known || s.sure)) return null;
    return Brain.idOf(cyc.join(","));
  }
  function currentCells() {
    return sensors.map(sensorCell).filter(Boolean);
  }

  function cellStates() {
    const out = {};
    for (const s of sensors) {
      const id = sensorCell(s);
      if (id && Array.isArray(s.p) && s.p.length) out[id] = s.p;
    }
    return out;
  }
  let stripHits = [];
  function sensorAt(x) {
    const hit = stripHits.find((h) => Math.abs(x - h.cx) <= h.R + 4);
    return hit ? { s: sensors[hit.idx], i: hit.idx, cx: hit.cx } : null;
  }
  function sensorTip(s, i) {
    const cyc = (s.cycles || []).filter((d) => d > 0);
    const head = `${t("sensorN", i + 1)} · ` + (s.known ? t("fromMemory") : s.sure ? t("sure") : t("learning"));
    const body = cyc.length ? t("cycleOf", cyc.reduce((a, b) => a * b, 1)) + (cyc.length > 1 ? ` (${cyc.join(" × ")})` : "")
      : t("mappedN", s.mapped || 0, fmtN(s.mapped || 0));
    return [head, body];
  }

  function paintSensorCards(time) {
    for (const cv of $$("#sensors canvas")) {
      const i = +cv.dataset.i;
      const s = sensors[i];
      if (!s) continue;
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = cv.clientWidth || 76;
      if (cv.width !== Math.round(w * dpr)) { cv.width = cv.height = Math.round(w * dpr); }
      const ctx = cv.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, w);
      drawSensor(ctx, w / 2, w / 2, w / 2 - 3, s, "card" + i, time);
    }
  }

  function world(live) {
    const changed = live.world !== worldNum;
    sensors = live.sensors || [];
    if (changed) {
      worldNum = live.world;
      sensorState.clear();
      const strip = $("#strip");
      strip.classList.remove("swap");
      void strip.offsetWidth;
      strip.classList.add("swap");
    }
    const real = !!live.real;
    $("#wNum").textContent = real ? t("realWorld") : fmtN(live.world);
    $("#wSteps").textContent = fmtN(live.steps);
    $("#wStates").textContent = fmtK(live.size);
    $("#nowWorldNum").textContent = real ? `${t("realWorldLong")} · ${t("realFor", fmtN(live.steps))}`
      : `#${fmtN(live.world)} · ${fmtN(live.steps)} ${t("steps")}`;
    const box = $("#sensors");
    if (changed || box.children.length !== sensors.length || (sensors.length && !box.querySelector(".sense"))) {
      clear(box);
      sensors.forEach((s, i) => {
        const card = el("div", "sensor");
        const cv = el("canvas");
        cv.dataset.i = i;
        card.append(cv, el("b", "num"), el("small"), el("span", "st"), el("em", "sense"));
        box.appendChild(card);
      });
    }
    [...box.children].forEach((card, i) => {
      const s = sensors[i];
      card.classList.toggle("sure", !!s.sure);
      card.classList.toggle("known", !!s.known);
      const cyc = (s.cycles || []).filter((d) => d > 0);
      card.querySelector("b").textContent = cyc.length ? cyc.join(" · ") : "?";
      card.querySelector("small").textContent = cyc.length && (s.known || s.sure)
        ? t("cycleOf", cyc.length === 1 ? cyc[0] : cyc.reduce((a, b) => a * b, 1))
        : t("mappedN", s.mapped || 0, fmtN(s.mapped || 0));
      card.querySelector(".st").textContent = s.known ? t("fromMemory") : s.sure ? t("sure") : t("learning");
      const sense = card.querySelector(".sense"), name = real && live.senses ? live.senses[i] : null;
      sense.hidden = !name;
      if (name) sense.textContent = t("sense_" + name, live.now && live.now[i] != null ? fmtN(live.now[i]) : "—");
    });
  }

  /* ---------- now ---------- */
  function controls(live) {
    const lt = $("#learnTog"), nt = $("#netTog");
    lt.setAttribute("aria-checked", String(!live.paused));
    nt.setAttribute("aria-checked", String(!live.offline));
    $("#paceTog").setAttribute("aria-checked", String(!!live.gentle));
    $("#paceSub").textContent = t(live.gentle ? "paceGentle" : "paceFull");
    $("#learnSub").textContent = t(live.paused ? "learningOff" : "learningOn");
    $("#netSub").textContent = t(live.offline ? "internetOff" : "internetOn");
    const mem = $("#memLine");
    mem.textContent = `${t("memoryDisk")}: ${live.memory ? fmtBytes(live.memory) : "—"}` + (live.saved ? ` · ${t("savedAgo", ago(live.saved))}` : "");
    const pill = $("#live");
    pill.classList.toggle("paused", !!live.paused);
    const pb = $("#pauseBtn");
    pb.classList.toggle("on", !!live.paused);
    pb.querySelector("use").setAttribute("href", live.paused ? "#i-resume" : "#i-pause");
    pb.title = t(live.paused ? "resume" : "pause");
  }
  /* ---------- its latest discoveries: the few really new things among all that happens ---------- */
  const found = [];
  function discInfo(e) {
    if (e.k === "meaning") return { icon: "key", color: C.word, text: t("dMeaning", e.shown || e.word, e.s) };
    if (e.k === "born") {
      const seen = String(e.s).includes("×");
      return { icon: "spark", color: seen ? C.seen : C.cycle, text: t(seen ? "dSeen" : "dBorn", e.s) };
    }
    if (e.k === "read-any" && e.readable !== false && (e.types || []).length) return { icon: "spark", color: C.seen, text: t("dType", e.types.join(" · ")) };
    if (e.k === "read-any" && e.readable !== false && e.new_way) return { icon: "key", color: C.gear, text: t("dWay", (e.chain || []).join(" → ")) };
    return null;
  }
  function discover(e, fresh) {
    if (!discInfo(e)) return;
    found.unshift({ e, fresh });
    if (found.length > 6) found.length = 6;
    paintDiscoveries();
  }
  function paintDiscoveries() {
    const box = $("#disc");
    if (!box) return;
    clear(box);
    if (!found.length) { box.appendChild(el("div", "empty", t("discNone"))); return; }
    for (const d of found) {
      const info = discInfo(d.e);
      const b = el("button", "dsc" + (d.fresh ? " fresh" : ""));
      d.fresh = false;
      b.type = "button";
      const i = el("span", "ic");
      i.style.color = info.color;
      i.style.background = rgba(info.color, 0.14);
      i.appendChild(svgIcon(info.icon));
      b.append(i, el("bdi", null, info.text), el("small", null, ago(d.e.t)));
      b.title = info.text;
      b.dataset.t = d.e.t;
      b.addEventListener("click", () => { const id = targetOf(d.e); if (id) Brain.focus(id); });
      box.appendChild(b);
    }
  }

  function safely2(f) { try { f(); } catch (e) { console.warn("goal/why", e); } }

  function goalAndWhy(live) {
    const g = $("#goalList"), w = $("#whyList");
    if (g) {
      clear(g);
      const goals = live.goal || [];
      const done = goals.filter((x) => x.sure).length;
      g.appendChild(el("p", "hint why", t("goalHead", fmtN(done), fmtN(goals.length), fmtN(live.steps || 0))));
      for (const x of goals) {
        const known = x.of ? t("goalOf", fmtN(x.mapped), fmtN(x.of)) : t("goalMapped", fmtN(x.mapped));
        g.appendChild(el("p", "hint", t("goalRow", x.sensor, x.sure, t("tool_" + x.tool), known, !!x.plan)));
      }
    }
    if (w) {
      clear(w);
      for (const d of live.why || []) w.appendChild(el("p", "hint", whyText(d)));
      if (!(live.why || []).length) w.appendChild(el("span", "empty", t("none")));
    }
  }
  function whyText(d) {
    const c = d.choice, y = d.why || {};
    if (d.what === "ways") return t("dec_ways", Object.entries(c).map(([k, v]) => `${t("way_" + k)}: ${has("wayv_" + v) ? t("wayv_" + v) : v} (${t("why_" + (y[k] || "best"))})`).join(sep("semi")));
    if (d.what === "pursue") return t("dec_pursue", c.map((j) => j + 1).join(sep("and")), has("wayv_" + y) ? t("wayv_" + y) : y);
    if (d.what === "invent") return t("dec_invent", c.map((j) => j + 1).join(sep("and")), fmtN(y.steps || 0), has("wayv_" + y.way) ? t("wayv_" + y.way) : y.way);
    if (d.what === "plan") return t("dec_plan", c, fmtN(y.presses || 0), fmtN(y.seen || 0), y.machine);
    if (d.what === "adapt") return t("dec_adapt", c, fmtN(y.steps || 0));
    if (d.what === "experiment") return t("dec_experiment", (y.sensors || []).map((j) => j + 1).join(sep("and")), c + 1, fmtN(y.presses || 0));
    if (d.what === "answer") return t("dec_answer", c, y.asked || "", (y.steps || []).length);
    if (d.what === "goal") return t("dec_goal", c, y.kind, y.cell, y.evidence);
    if (d.what === "goal_step") return t("dec_goal_step", c, y.step, fmtN(y.read || 0), Object.entries(y.gained || {}).map(([k, v]) => `⁦${k}⁩ +${v}`).join(" ") || t("nothing"));
    if (d.what === "replan") return t("dec_replan", c, y.steps);
    if (d.what === "recognize") return t("dec_recognize", c, y.from, fmtN(y.acts || 0));
    if (d.what === "read_way") return t("dec_read_way", t("rway_" + c), fmtN(y.value), fmtN(y.tried || 0));
    if (d.what === "rebase") return t("dec_rebase");
    if (d.what === "odds") return t("dec_odds", c, y.cond, y.d, y.up, y.q, y.p, y.digits, y.tests, y.known);
    if (d.what === "odds_goal") return t("dec_odds_goal", c, y);
    if (d.what === "lawless") return t("dec_lawless", c, y.lift, y.rate, y.rows);
    if (d.what === "grain") return t("dec_grain", c, y.grain, y.levels, y.seen);
    if (d.what === "thing") return t("dec_thing", c, y);
    if (d.what === "wish") return t("dec_wish", c, y);
    if (d.what === "relword") return t("dec_relword", c, y);
    if (d.what === "opword") return t("dec_opword", c, y);
    if (d.what === "numberword") return t("dec_numberword", c, y);
    if (d.what === "frames") return t("dec_frames", y);
    if (d.what === "reading_rule") return t("dec_reading_rule", c, y);
    if (d.what === "odds_revised") return t("dec_odds_revised", c, y.cond, y.after, y.came);
    if (["brain_made", "brain_gone", "way_trusted", "way_dropped"].includes(d.what)) return t("dec_way", d);
    if (["concept", "made", "made_like", "moment", "odds_drift", "trying", "grew"].includes(d.what)) return evText(Object.assign({}, y, { k: d.what, sensor: c }));
    if (d.what === "made_gone") return t("dec_made_gone", { sensor: c, digits: y.digits, bar: y.bar });
    if (d.what === "telling") return t("dec_telling", { act: iso(c), sensor: y.sensor, thing: iso(y.thing), tells: y.tells });
    if (d.what === "spare") return t("dec_spare", { act: iso(c), instead: iso(y.instead), sensor: y.sensor, trap: iso(y.trap), odds: y.odds });
    if (d.what === "trap") return t("dec_trap", { sensor: c, value: iso(y.value), digits: y.digits, bar: y.bar });
    if (d.what === "workshop") return t("dec_workshop", c, madeWords(y));
    if (d.what === "named") return t("dec_named", { s: c, word: y.word, n: y.n, k: y.k, digits: y.digits });
    if (d.what === "recall") return t("dec_recall", (c || []).join(sep("list")));
    if (d.what === "self_change") return t("dec_self_change", `${t("gene_" + c)}: ${y.from} → ${y.to} (${y.digits})`);
    return `${d.what}: ${JSON.stringify(c)}`;
  }

  function now(live) {
    world(live);
    controls(live);
    safely2(() => brains(live));
    safely2(() => goalAndWhy(live));
    safely2(() => mindTab(live));
    for (const b of $$("#disc .dsc")) b.lastChild.textContent = ago(+b.dataset.t);
    $("#typing").classList.toggle("hidden", !(live.urge >= 1) || !!live.paused);
    const reading = live.reading || "";
    $("#rnTitle").textContent = reading || t("nothing");
    $("#rnShim").classList.toggle("hidden", !reading);
    if (!reading) { $("#rnSrc").textContent = "·"; $("#rnFrom").textContent = ""; }
    const urge = Math.max(0, live.urge || 0);
    const a = Math.min(1, urge / 1.4);
    const arc = $("#urgeArc");
    const len = arc.getTotalLength ? arc.getTotalLength() : 170;
    arc.style.strokeDasharray = `${len}`;
    arc.style.strokeDashoffset = `${len * (1 - a)}`;
    $("#urgeVal").textContent = urge.toFixed(2);
    $("#mSps").textContent = fmtK(live.sps);
    $("#mWorlds").textContent = fmtN(live.senses_known || 0);
        if (live.born) $("#mAge").textContent = age(live.born);
    const sites = $("#sites");
    clear(sites);
    if (!(live.sites || []).length) sites.appendChild(el("div", "empty", t("noSites")));
    const top = Math.max(1, ...(live.sites || []).map((s) => s.gain || 0));
    for (const s of live.sites || []) {
      const row = el("div", "site" + (s.done ? " done" : ""));
      const name = el("bdi", null, s.site);
      row.append(name, el("span", "muted num", `${s.pages} ${t("pages")} · ${s.gain} ${t("gain")}`));
      const bar = el("div", "bar"), i = el("i");
      i.style.width = Math.round((100 * (s.gain || 0)) / top) + "%";
      bar.appendChild(i);
      row.appendChild(bar);
      sites.appendChild(row);
    }
    for (const [id, list] of [["#nextArticles", (live.next || {}).articles], ["#nextSites", (live.next || {}).sites]]) {
      const box = $(id);
      clear(box);
      if (!(list || []).length) box.appendChild(el("span", "empty", t("none")));
      for (const x of list || []) box.appendChild(el("span", "tag", x));
    }
    const w = $("#waiting");
    clear(w);
    if (!(live.waiting || []).length) w.appendChild(el("span", "empty", t("none")));
    for (const x of live.waiting || []) w.appendChild(el("span", "tag", x));
    narrative(live);
  }

  function readingFrom(source) {
    const f = $("#rnFrom");
    f.textContent = source || "";
    const letter = String(source || "").replace(/^(https?:\/\/)?(www\.)?/, "").trim()[0];
    if (letter) $("#rnSrc").textContent = letter;
  }
  function narrative(live) {
    const r = $("#wRead");
    r.textContent = live.reading || t("nothing");
    r.title = live.reading || "";
  }

  /* ---------- the last worlds it lived in ---------- */
  function cellChip(c) {
    const b = el("button", "cchip");
    b.type = "button";
    const ty = typeOf({ shape: c.shape, cycles: c.cycles });
    const i = el("i");
    i.style.background = C[ty];
    b.append(i, el("bdi", null, c.symbol));
    if (c.word) b.append(el("small", null, c.word));
    b.title = t("t_" + ty);
    b.addEventListener("click", () => Brain.focus(c.id || Brain.idOf(c.symbol)));
    return b;
  }
  function worlds(list) {
    const box = $("#worlds");
    clear(box);
    if (!list || !list.length) { box.appendChild(el("div", "empty", t("noWorlds"))); return; }
    for (const w of list.slice(0, 10)) {
      const row = el("div", "wrow");
      const h = el("div", "wh");
      h.append(el("b", null, w.real ? t("realWorldLong") : "#" + fmtN(w.world)),
        el("span", null, w.real ? t("realFor", fmtN(w.steps)) : `${fmtN(w.steps)} ${t("steps")}`),
        el("span", w.accuracy >= 99 ? "ok" : null, `${w.accuracy}%`));
      if ((w.recognized || []).length) h.append(el("span", null, t("fromMem", w.recognized.length, w.sensors)));
      row.appendChild(h);
      const cells = el("div", "wcells");
      const seen = new Set();
      for (const c of w.cells) { if (seen.has(c.symbol)) continue; seen.add(c.symbol); cells.appendChild(cellChip(c)); }
      row.appendChild(cells);
      box.appendChild(row);
    }
  }
  function readHistory(list) {
    const box = $("#readHist");
    clear(box);
    if (!list || !list.length) { box.appendChild(el("div", "empty", t("noRead"))); return; }
    for (const r of list.slice(0, 10)) {
      const row = el("div", "rrow");
      const h = el("div", "rh");
      h.append(el("b", null, r.source), el("span", "num", r.readable === false ? "—" : pct(r.after)), el("time", null, ago(r.at)));
      row.appendChild(h);
      if (r.readable === false) row.appendChild(el("div", "hint", t("unreadable")));
      else row.appendChild(chainEl(r.chain));
      if ((r.found || []).length || (r.types || []).length) {
        const tags = el("div", "tags");
        for (const f of r.found || []) {
          const b = el("button", "tag seen", f);
          b.type = "button";
          b.addEventListener("click", () => Brain.focus(Brain.get("s:" + f) ? "s:" + f : Brain.idOf(f)));
          tags.appendChild(b);
        }
        for (const ty of r.types || []) tags.appendChild(el("span", "tag new", ty));
        row.appendChild(tags);
      }
      box.appendChild(row);
    }
  }

  /* ---------- talk ---------- */
  let lastWho = null;

  function leads(a, b) { return `${a} ${sep("arrow")} ${b}`; }

  function dirOf(text) {
    const m = String(text).match(/[A-Za-z\u00C0-\u024F\u0370-\u03FF\u0400-\u04FF]|[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/);
    if (!m) return document.documentElement.dir || dir();
    return /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/.test(m[0]) ? "rtl" : "ltr";
  }

  function message(m, onSymbol) {
    const box = $("#msgs");
    const empty = box.querySelector(".empty");
    if (empty) empty.remove();
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    const wrap = el("div", "msg " + (m.who === "me" ? "me" : "it"));
    if (lastWho !== m.who) wrap.appendChild(el("div", "who", (m.who === "me" ? t("you") : t("it")) + " · " + clock(m.t)));
    lastWho = m.who;
    const body = el("div", "body");
    body.dir = dirOf(m.text);
    const parts = String(m.text).split(/(\s+)/);
    for (const p of parts) {
      if (isSymbol(p)) {
        const id = Brain.idOf(p);
        const b = el("button", "sym" + (id && id.startsWith("s:") ? " seen" : ""), p);
        b.type = "button";
        const node = id && Brain.get(id);
        b.title = node ? `${t("t_" + node.type)} ${p}` + (node.label !== node.symbol ? ` — ${t("quoted", node.label)}` : ` — ${t("noWord")}`) + ` · ${t("nameTitle")}`
          : t("nameTitle");
        b.addEventListener("click", (ev) => onSymbol(p, ev.currentTarget));
        body.appendChild(b);
      } else {
        const w = p.replace(/^\p{P}+|\p{P}+$/gu, "");
        const wid = w && (Brain.get("w:" + w) ? "w:" + w : Brain.get("w:" + w.toLowerCase()) ? "w:" + w.toLowerCase() : null);
        if (wid) {
          const b = el("button", "wlink", p);
          b.type = "button";
          b.addEventListener("click", () => Brain.focus(wid));
          body.appendChild(b);
        } else body.appendChild(document.createTextNode(p));
      }
    }
    wrap.appendChild(body);
    if (m.kind === "answer" && (m.proof || []).length) {
      const pr = el("div", "proof");
      for (const p of m.proof) pr.appendChild(el("p", null, proofText(p)));
      wrap.appendChild(pr);
    }
    box.appendChild(wrap);
    while (box.children.length > 300) box.removeChild(box.firstChild);
    if (atBottom || m.who === "me") box.scrollTop = box.scrollHeight;
  }
  function proofText(p) {
    const law = (c) => (c === "carry" || c === "together" ? lawName("law:" + c) : t("pr_" + c));
    if (p.step === "foresee") return t("pr_foresee", p.sense, fmtN(p.after), p.value, p.cell);
    if (p.step === "law") return t("pr_law", iso(p.a), law(p.law), iso(p.b), fmtN(p.times || 0));
    if (p.step === "through") return t("pr_through", (p.path || []).map(iso).join(" " + sep("arrow") + " "));
    if (p.step === "kindof") return t("pr_kindof_", iso(p.a), iso(p.b));
    if (p.step === "sense") return t("pr_sense", iso(p.cell), p.sense);
    if (p.step === "unknown") return t("pr_unknown", (p.words || []).join(sep("list")));
    if (p.step === "no_chain") return t("pr_nochain", iso(p.a), iso(p.b));
    if (p.step === "alone") return t("pr_alone", iso(p.cell));
    if (p.step === "said") return t("pr_said", iso(p.a), p.word, iso(p.b), t("law_" + p.law), p.verdict);
    if (p.step === "reckon") return t("pr_reckon", p.x, t("op_" + p.op), p.y, p.is, p.word, p.said);
    if (p.step === "read_rule") return t("pr_read_rule", p.form, p.sentence, p.word, p.right, p.of, p.digits, !!(p.rule || {}).then);
    if (p.step === "odds_law") return t("pr_odds_law", iso(p.a), t("law_" + p.law), iso(p.b), p.lag, p.d, p.q, p.p, p.digits);
    if (p.step === "analogy") return t("pr_analogy", iso(p.cell), iso(p.like), p.world);
    return p.step;
  }

  function wantNames(list, onPick) {
    const box = $("#wantNames"), row = $("#wantList");
    const key = list.map((n) => n.id).join("|") + "|" + LANG;
    box.classList.toggle("hidden", !list.length);
    if (row.dataset.key === key) return;
    row.dataset.key = key;
    clear(row);
    for (const n of list) {
      const b = el("button", "sym" + (n.type === "seen" ? " seen" : ""), n.symbol);
      b.type = "button";
      b.title = `${t("t_" + n.type)} ${n.symbol}` + (n.asked ? ` · ${t("spokeOf", n.asked)}` : "") + ` · ${t("nameTitle")}`;
      b.addEventListener("click", (ev) => onPick(n.symbol, ev.currentTarget));
      row.appendChild(b);
    }
  }

  function note(text) {
    const box = $("#msgs");
    const empty = box.querySelector(".empty");
    if (empty) empty.remove();
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    const wrap = el("div", "msg note");
    wrap.appendChild(el("div", "body", text));
    box.appendChild(wrap);
    lastWho = null;
    while (box.children.length > 300) box.removeChild(box.firstChild);
    if (atBottom) box.scrollTop = box.scrollHeight;
  }
  function chatEmpty() {
    const box = $("#msgs");
    if (!box.children.length) box.appendChild(el("div", "empty", t("chatEmpty")));
  }

  /* ---------- reading ---------- */
  function chainEl(chain) {
    const c = el("div", "chain");
    (chain && chain.length ? chain : [t("asIs")]).forEach((s, i) => {
      if (i) c.appendChild(el("span", "arr", "→"));
      c.appendChild(el("span", "step", s === "as it is" ? t("asIs") : s));
    });
    return c;
  }
  function imgEl(b64, cls) {
    if (!b64 || !/^[A-Za-z0-9+/=]+$/.test(b64)) return null;
    const im = el("img", cls);
    im.src = "data:image/png;base64," + b64;
    im.alt = "";
    return im;
  }
  function readBar(label, v, cls) {
    const r = el("div", "rbar " + cls);
    const tr = el("div", "track"), i = el("i");
    i.style.width = Math.round(Math.max(0, Math.min(1, v || 0)) * 100) + "%";
    tr.appendChild(i);
    r.append(el("span", "muted", label), tr, el("b", "num", pct(v)));
    return r;
  }
  function reading(rep) {
    safely2(() => asks(rep));
    const box = $("#lastRead");
    clear(box);
    const L = rep.last || {};
    if (!L.source) { box.appendChild(el("div", "empty", t("noRead"))); }
    else {
      const head = el("div", "readnow");
      head.append(el("div", "src", (L.source || "·").replace(/^.*·\s*/, "").trim()[0] || "·"));
      const tt = el("div", "t");
      tt.append(el("b", null, L.source), el("small", "num", `${fmtBytes(L.size || 0)}` + (L.symbols ? ` · ${fmtN(L.symbols)} ${t("symbols")}` : "") + (L.bits != null ? ` · ${L.bits} ${t("bits")}` : "")));
      head.appendChild(tt);
      box.appendChild(head);
      if (L.at) $("#lastAt").textContent = ago(L.at);
      if (L.readable === false) box.appendChild(el("p", "hint", t("unreadable")));
      else {
        const wl = el("div", "sect", t("way"));
        box.append(wl, chainEl(L.chain));
        if (L.new_way) box.appendChild(el("span", "tag new", t("newWay")));
        box.append(el("div", "sect", t("readability")), readBar(t("before"), L.before, "b"), readBar(t("after"), L.after, "a"));
        if (L.also) {
          const a = el("div", "hint");
          a.style.marginTop = "6px";
          a.append(document.createTextNode(t("also") + ": "), el("bdi", "mono", (L.also.chain || []).join(" → ")), document.createTextNode(" · " + pct(L.also.after)));
          box.appendChild(a);
        }
        const tags = el("div", "tags");
        const sh = L.shape || {};
        if (sh.height && sh.width) tags.appendChild(el("span", "tag", `${t("shape")}: ${sh.width}×${sh.height}` + (sh.frames ? ` × ${sh.frames} ${t("frames")}` : "")));
        if (sh.lines) tags.appendChild(el("span", "tag", `${fmtN(sh.lines)} ${t("lines")} × ${sh.columns} ${t("cols")}`));
        if (L.found_itself) tags.appendChild(el("span", "tag new", t("foundItself")));
        if (L.lattice) {
          tags.appendChild(el("span", "tag seen", `${t("windings")}: ${(L.lattice.windings || []).join("×")}`));
          tags.appendChild(el("span", "tag", `${t("defects")}: ${L.lattice.defects}`));
          if ((L.lattice.symmetry || []).length) tags.appendChild(el("span", "tag", `${t("symmetry")}: ${L.lattice.symmetry.join(" ")}`));
        }
        if (L.time) tags.appendChild(el("span", "tag seen", `${t("inTime")} ${L.time.every} ${t("frames")}`));
        for (const c of L.columns || []) tags.appendChild(el("span", "tag seen", `${t("columns")} ${c.column}: ${t("inTime")} ${c.every}`));
        if ((L.rhythms || []).length && !L.lattice) tags.appendChild(el("span", "tag", `${t("rhythms")}: ${L.rhythms.map((r) => r[0]).join(", ")}`));
        for (const ty of L.types || []) tags.appendChild(el("span", "tag new", ty));
        if (tags.children.length) box.appendChild(tags);
        const seen = imgEl(L.seen), unit = imgEl(L.lattice && L.lattice.unit_png);
        if (seen || unit) {
          const g = el("div", "rgrid");
          if (seen) { const d = el("div"); d.append(el("div", "sect", t("picture")), seen); g.appendChild(d); }
          if (unit) { const d = el("div"); d.append(el("div", "sect", t("unit")), unit); g.appendChild(d); }
          box.appendChild(g);
        }
        if ((L.words || []).length) {
          box.appendChild(el("div", "sect", t("wordsIn")));
          const ws = el("div", "links");
          for (const w of L.words) {
            const id = Brain.get("w:" + w) ? "w:" + w : Brain.get("w:" + w.toLowerCase()) ? "w:" + w.toLowerCase() : null;
            const known = !!id;
            const b = el(known ? "button" : "span", "lk", null);
            if (known) { b.type = "button"; b.addEventListener("click", () => Brain.focus(id)); }
            const i = el("i");
            i.style.background = known ? C.word : C.dim;
            b.append(i, el("bdi", null, w));
            ws.appendChild(b);
          }
          box.appendChild(ws);
        }
        if ((L.pieces || []).length) {
          box.appendChild(el("div", "sect", t("pieces")));
          const cl = el("div", "cloud");
          L.pieces.slice(0, 12).forEach((p) => cl.appendChild(el("span", null, p)));
          box.appendChild(cl);
        }
      }
    }
    const ways = $("#ways");
    clear(ways);
    $("#waysN").textContent = fmtN((rep.ways || []).length);
    for (const w of rep.ways || []) {
      const tr = el("tr");
      const a = el("td"); a.appendChild(chainEl(w.chain));
      tr.append(el("td", "sig", w.begins), a, el("td", "n", `${fmtN(w.uses)}×`));
      ways.appendChild(tr);
    }
    if (!(rep.ways || []).length) { const tr = el("tr"); const td = el("td", "empty", t("none")); tr.appendChild(td); ways.appendChild(tr); }
    const types = $("#types");
    clear(types);
    $("#typesN").textContent = fmtN((rep.types || []).length);
    for (const ty of rep.types || []) {
      const s = el("span", "tag seen");
      s.append(document.createTextNode(ty.name + " "), el("b", "num", "×" + ty.count));
      types.appendChild(s);
    }
    if (!(rep.types || []).length) types.appendChild(el("span", "empty", t("none")));
    const pieces = $("#pieces");
    clear(pieces);
    (rep.pieces || []).forEach((p) => pieces.appendChild(el("span", null, p)));
    if (!(rep.pieces || []).length) pieces.appendChild(el("span", "empty", t("none")));
    $("#openN").textContent = fmtN(rep.open || 0);
    const gram = $("#grammar");
    if (gram) {
      clear(gram);
      $("#grammarN").textContent = fmtN(rep.grammar_seen || 0);
      for (const g of rep.grammar || []) {
        const cls = g.classes.map(([a, b]) => (a === b ? `${a}` : `${a}–${b}`));
        gram.appendChild(el("p", "hint why", t("grammarClasses", has("script_" + g.script) ? t("script_" + g.script) : g.script, cls.join(" | "))));
        for (const law of g.laws) {
          const by = Object.entries(law.law).map(([k, f]) => leads(iso(cls[+k]), iso(f))).join(sep("items"));
          gram.appendChild(el("p", "hint", t("grammarLaw", law.forms.join(" / "), by, law.evidence, law.sources)));
        }
      }
      if (!(rep.grammar || []).length) gram.appendChild(el("span", "empty", t("grammarNone")));
    }
    readHistory(rep.history);
    if (rep.inbox) $("#inboxCount").textContent = t("inboxCount", fmtN(rep.inbox.files), fmtN(rep.inbox.read));
  }

  let trySource = null;
  function tryRow(e) {
    const box = $("#tries");
    if (e.source !== trySource) {
      trySource = e.source;
      box.insertBefore(el("div", "trysrc", e.source || ""), box.firstChild);
    }
    const row = el("div", "try" + (e.got == null ? " fail" : ""));
    const res = el("div", "res"), i = el("i");
    i.style.width = e.got == null ? "0%" : Math.round(Math.min(1, e.got) * 100) + "%";
    res.appendChild(i);
    res.title = e.got == null ? "—" : pct(e.got);
    row.append(chainEl(e.chain), res);
    const label = box.querySelector(".trysrc");
    label.after(row);
    while (box.children.length > 22) box.removeChild(box.lastChild);
  }

  /* ---------- events ---------- */
  let feedFilter = "all", feedPaused = false;
  const feedBuf = [];
  function eventRow(e) {
    const [cat, icon, colk] = EVENT_KIND[e.k] || ["cells", "spark", "accent"];
    const row = el("div", "ev");
    row.dataset.cat = cat;
    const ic = el("div", "ic");
    const col = colorOf(colk);
    ic.style.background = rgba(col.startsWith("#") ? col : "#6ea8ff", 0.14);
    ic.style.color = col;
    ic.appendChild(svgIcon(icon));
    const p = el("p", null, evText(e));
    row.append(ic, p, el("time", null, clock(e.t)));
    if (["born", "recognized", "meaning", "linked", "curious", "understood", "spoke", "heard", "read-any", "read"].includes(e.k)) {
      row.classList.add("link");
      row.tabIndex = 0;
      const go = () => { const id = targetOf(e); if (id) Brain.focus(id); };
      row.addEventListener("click", go);
      row.addEventListener("keydown", (ev) => { if (ev.key === "Enter") go(); });
    }
    if (feedFilter !== "all" && feedFilter !== cat) row.classList.add("hidden");
    return row;
  }

  const GROUP = { recognized: (e) => e.s, read: (e) => e.title || e.word, connected: (e) => e.site, born: (e) => e.s,
    curious: (e) => e.shown || e.word, linked: (e) => `${e.sa || e.a} ↔ ${e.sb || e.b}` };
  function feed(e) {
    countEvent(e);
    if (e.k === "try") return;
    if (feedPaused) { feedBuf.push(e); return; }
    const box = $("#feed");
    const empty = box.querySelector(".empty");
    if (empty) empty.remove();
    const top = box.firstElementChild;
    const item = GROUP[e.k] ? GROUP[e.k](e) : null;
    if (item != null && top && top._k === e.k && e.t - top._t0 < 45 && top._items.length < 40) {
      if (!top._items.includes(item)) top._items.push(item);
      top._e = e;
      top.querySelector("p").textContent = top._items.length > 1 && has("evg." + e.k) ? t("evg." + e.k, top._items) : evText(e);
      top.querySelector("time").textContent = clock(e.t);
      return;
    }
    const row = eventRow(e);
    row._e = e;
    row._k = e.k;
    row._t0 = e.t;
    row._items = item != null ? [item] : [];
    box.insertBefore(row, box.firstChild);
    while (box.children.length > 400) box.removeChild(box.lastChild);
  }

  function refeed() {
    for (const row of $$("#feed .ev")) {
      const p = row.querySelector("p");
      if (!p || !row._e) continue;
      p.textContent = (row._items || []).length > 1 && has("evg." + row._k) ? t("evg." + row._k, row._items) : evText(row._e);
    }
  }

  const RHYTHM = ["world", "cells", "words", "reading", "web", "brains", "speech", "trouble"];
  const rhythmCols = () => ({ world: C.cycle, cells: C.seen, words: C.word, reading: C.gear, web: C.torus, brains: C.general, speech: C.accent, trouble: C.bad });
  const minutes = new Map();
  function countEvent(e) {
    const [cat] = EVENT_KIND[e.k] || ["cells"];
    const m = Math.floor(e.t / 60);
    let row = minutes.get(m);
    if (!row) { row = {}; minutes.set(m, row); }
    row[cat] = (row[cat] || 0) + 1;
    for (const k of minutes.keys()) if (k < m - 20) minutes.delete(k);
  }
  function rhythm() {
    const svg = $("#rhythm");
    if (!svg || !svg.isConnected) return;
    const NS = "http://www.w3.org/2000/svg";
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    const W = 300, H = 64, n = 15, now = Math.floor(Date.now() / 60000);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "none");
    const rows = [];
    for (let i = n - 1; i >= 0; i--) rows.push(minutes.get(now - i) || {});
    const top = Math.max(4, ...rows.map((r) => RHYTHM.reduce((a, k) => a + (r[k] || 0), 0)));
    const cols = rhythmCols(), bw = W / n;
    rows.forEach((r, i) => {
      let y = H;
      for (const k of RHYTHM) {
        const v = r[k] || 0;
        if (!v) continue;
        const h = (v / top) * (H - 4);
        const rect = document.createElementNS(NS, "rect");
        const x = dir() === "rtl" ? W - (i + 1) * bw : i * bw;
        rect.setAttribute("x", (x + 2).toFixed(1));
        rect.setAttribute("y", (y - h).toFixed(1));
        rect.setAttribute("width", (bw - 4).toFixed(1));
        rect.setAttribute("height", h.toFixed(1));
        rect.setAttribute("rx", "1.5");
        rect.setAttribute("fill", cols[k]);
        rect.setAttribute("opacity", i === n - 1 ? "1" : "0.8");
        svg.appendChild(rect);
        y -= h;
      }
    });
    const keys = $("#rkeys");
    if (!keys.children.length || keys.dataset.lang !== LANG) {
      clear(keys);
      keys.dataset.lang = LANG;
      for (const k of RHYTHM) {
        const s = el("span");
        const i = el("i");
        i.style.background = cols[k];
        s.append(i, document.createTextNode(t("f_" + k)));
        keys.appendChild(s);
      }
    }
  }

  function setFeedFilter(f) {
    feedFilter = f;
    $$("#filters .fbtn").forEach((b) => b.classList.toggle("on", b.dataset.f === f));
    $$("#feed .ev").forEach((r) => r.classList.toggle("hidden", f !== "all" && r.dataset.cat !== f));
  }
  function setFeedPaused(p) {
    feedPaused = p;
    if (!p) { const buf = feedBuf.splice(0); buf.forEach(feed); }
  }

  /* ---------- growth ---------- */
  const SERIES = [["ideas", "g_ideas", "cycle"], ["words", "g_words", "word"], ["meanings", "g_meanings", "word"],
    ["links", "g_links", "assoc"], ["articles", "g_articles", "gear"], ["read", "g_read", "seen"], ["types", "g_types", "seen"],
    ["ways", "g_ways", "torus"], ["sps", "g_sps", "accent"]];
  function pathOf(vals, w, h, pad) {
    const n = vals.length;
    if (n < 2) return null;
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (hi - lo < 1e-9) { hi = lo + 1; }
    const x = (i) => (i * w) / (n - 1);
    const y = (v) => h - pad - ((v - lo) / (hi - lo)) * (h - pad * 2);
    let d = `M${x(0).toFixed(1)},${y(vals[0]).toFixed(1)}`;
    for (let i = 1; i < n; i++) d += `L${x(i).toFixed(1)},${y(vals[i]).toFixed(1)}`;
    return { line: d, area: d + `L${w},${h}L0,${h}Z`, last: [x(n - 1), y(vals[n - 1])] };
  }
  function spark(svg, vals, color, w, h) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("preserveAspectRatio", "none");
    const p = pathOf(vals, w, h, 2);
    if (!p) return;
    const NS = "http://www.w3.org/2000/svg";
    const id = "g" + Math.random().toString(36).slice(2, 8);
    const defs = document.createElementNS(NS, "defs");
    const lg = document.createElementNS(NS, "linearGradient");
    lg.setAttribute("id", id); lg.setAttribute("x1", "0"); lg.setAttribute("y1", "0"); lg.setAttribute("x2", "0"); lg.setAttribute("y2", "1");
    [["0", 0.35], ["1", 0]].forEach(([o, a]) => { const s = document.createElementNS(NS, "stop"); s.setAttribute("offset", o); s.setAttribute("stop-color", color); s.setAttribute("stop-opacity", a); lg.appendChild(s); });
    defs.appendChild(lg);
    svg.appendChild(defs);
    const area = document.createElementNS(NS, "path");
    area.setAttribute("d", p.area); area.setAttribute("fill", `url(#${id})`);
    const line = document.createElementNS(NS, "path");
    line.setAttribute("d", p.line); line.setAttribute("fill", "none"); line.setAttribute("stroke", color);
    line.setAttribute("stroke-width", "1.6"); line.setAttribute("vector-effect", "non-scaling-stroke"); line.setAttribute("stroke-linejoin", "round");
    svg.append(area, line);
  }
  function growth(hist, span) {
    const box = $("#charts");
    if (!hist || hist.length < 2) { clear(box); box.appendChild(el("div", "empty", t("noHistory"))); return; }
    if (box.querySelector(".empty") || !box.children.length || box.dataset.lang !== LANG) {
      clear(box);
      box.dataset.lang = LANG;
      for (const [key, label, col] of SERIES) {
        const c = el("div", "chart" + (key === "sps" ? " wide" : ""));
        c.dataset.key = key;
        const ct = el("div", "ct");
        const left = el("div");
        left.append(el("small", null, t(label)));
        ct.append(left, el("div"));
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        c.append(ct, svg);
        c.dataset.col = col;
        box.appendChild(c);
      }
    }
    const day = span === "day";
    const recent = day ? hist : hist.slice(-360);
    const hourAgo = Date.now() / 1000 - (day ? 86400 : 3600);
    for (const c of box.children) {
      const key = c.dataset.key;
      const vals = recent.map((p) => +p[key] || 0);
      const lastV = vals[vals.length - 1];
      const past = hist.find((p) => p.t >= hourAgo) || hist[0];
      const delta = lastV - (+past[key] || 0);
      const right = c.querySelector(".ct > div:last-child");
      clear(right);
      right.append(el("b", null, fmtK(lastV)));
      if (key !== "sps" && delta > 0) right.append(document.createTextNode(" "), el("em", null, "+" + fmtK(delta)));
      spark(c.querySelector("svg"), vals, colorOf(c.dataset.col), 300, 54);
    }
  }

  /* ---------- its cells by kind: a ring and a list, drawn with the cells themselves ---------- */

  function use(u) {
    const box = $("#brainUse");
    if (!box || !u) return;
    clear(box);
    box.appendChild(el("p", "hint why", u.closed >= 40 ? t("useInvent", u.invent_at, u.closed) : t("useInventFirst", u.invent_at, u.closed)));
    for (const tool of ["counts", "kind", "machine", "odds", "answer"]) {
      for (const sure of ["sure", "unsure"]) {
        const row = (u.ledger || {})[`${tool}:${sure}`];
        if (!row || !(row[0] + row[1] + row[2])) continue;
        const n = row[0] + row[1] + row[2];
        const pc = (x) => { const p = 100 * x / n; return !x ? "0" : p < 0.1 ? p.toPrecision(2) : p.toFixed(1); };
        box.appendChild(el("p", "hint", t("useRow", t("tool_" + tool), sure === "sure", pc(row[0]), pc(row[1]), pc(row[2]), fmtN(n))));
      }
    }
    const p = u.plans || {};
    if (p.made) box.appendChild(el("p", "hint why", t("usePlans", fmtN(p.made), fmtN(p.reached || 0), fmtN(p.missed || 0), fmtN(p.dropped || 0))));
    if (u.generals) box.appendChild(el("p", "hint", t("useGenerals", fmtN(u.generals))));
    if (p.subgoal_made) box.appendChild(el("p", "hint why", t("useSubgoals", fmtN(p.subgoal_made), fmtN(p.subgoal_reached || 0))));
    const g = u.goals || {};
    if (g.made || g.now) box.appendChild(el("p", "hint why", t("useGoals", fmtN(g.made || 0), fmtN(g.reached || 0), g.now)));
    if (u.pending) box.appendChild(el("p", "hint", t("usePending", fmtN(u.pending))));
    const rel = u.relation_words || [];
    if (rel.length) {
      box.appendChild(el("p", "hint why", t("relWordsHow")));
      box.appendChild(el("p", "hint", rel.map((r) => t("relWordRow", r)).join(sep("items"))));
    }
    const rr = u.reading_rules || {};
    if (Object.keys(rr).length) {
      box.appendChild(el("p", "hint why", t("readRulesHow")));
      for (const [form, r] of Object.entries(rr)) box.appendChild(el("p", "hint", t("readRuleRow", form, r)));
      if ((u.frame_words || []).length) box.appendChild(el("p", "hint", t("readFrameHow") + " " + u.frame_words.join(sep("list"))));
    }
    const fm = u.forms || {};
    if ((fm.pre || []).length || (fm.suf || []).length) box.appendChild(el("p", "hint", t("formsHow") + " " +
      [...(fm.pre || []).map(([a, e]) => `${a}… (${e})`), ...(fm.suf || []).map(([a, e]) => `…${a} (${e})`)].join(sep("items"))));
    const nw = u.number_words || [];
    if (nw.length) box.appendChild(el("p", "hint", t("numWordsHow") + " " + nw.map((r) => `${t("quoted", r.word)} = ${r.value}`).join(sep("items"))));
    if (u.frames && u.frames.believed) box.appendChild(el("p", "hint", t("framesHow", u.frames)));
    const opw = u.op_words || [];
    if (opw.length) box.appendChild(el("p", "hint", t("opWordsHow") + " " + opw.map((r) => `${t("quoted", r.word)} = ${t("op_" + r.op)} (${r.digits})`).join(sep("items"))));
    const rw = u.read_ways || {};
    if (Object.keys(rw).length) box.appendChild(el("p", "hint why", t("readWaysHow")));
    for (const [name, w] of Object.entries(rw)) {
      const opts = (w.options || []).map((o) => (o.value === w.now ? "★ " : "") + fmtN(o.value) + (o.n ? ` (${t("readWayDid", fmtN(o.n), o.mean)})` : ""));
      box.appendChild(el("p", "hint", t("rway_" + name) + ": " + opts.join(sep("items"))));
    }
    const wb = $("#itsWays");
    if (!wb) return;
    clear(wb);
    wb.appendChild(el("p", "hint why", t("waysHow", fmtN(u.judged || 0))));
    for (const [name, w] of Object.entries(u.ways || {})) {
      const opts = w.options.map((o) => {
        const shown = has("wayv_" + o.value) ? t("wayv_" + o.value) : o.value;
        const how = o.n ? t("wayDid", fmtN(o.presses), fmtN(o.n), o.ok == null ? null : fmtN(o.ok)) : t("wayNot");
        return (o.value === w.now ? "★ " : "") + shown + " (" + how + ")";
      });
      wb.appendChild(el("p", "hint", t("way_" + name) + ": " + opts.join(sep("items"))));
    }
  }

  function mind(shapes) {
    const svg = $("#donut"), list = $("#mindList");
    if (!svg || !shapes) return;
    const kinds = ["cycle", "torus", "gear", "crt", "invented", "general", "circuit", "topic", "seen"];
    const total = kinds.reduce((a, k) => a + (shapes[k] || 0), 0);
    const NS = "http://www.w3.org/2000/svg";
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    const R = 46, CIRC = 2 * Math.PI * R;
    const bg = document.createElementNS(NS, "circle");
    bg.setAttribute("cx", 60); bg.setAttribute("cy", 60); bg.setAttribute("r", R);
    bg.setAttribute("fill", "none"); bg.setAttribute("stroke", "var(--card-2)"); bg.setAttribute("stroke-width", 14);
    svg.appendChild(bg);
    let off = 0;
    for (const k of kinds) {
      const v = shapes[k] || 0;
      if (!v || !total) continue;
      const len = (v / total) * CIRC;
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", 60); c.setAttribute("cy", 60); c.setAttribute("r", R);
      c.setAttribute("fill", "none"); c.setAttribute("stroke", C[k]); c.setAttribute("stroke-width", 14);
      c.setAttribute("stroke-dasharray", `${Math.max(0, len - 1.5)} ${CIRC}`);
      c.setAttribute("stroke-dashoffset", String(-off));
      c.setAttribute("transform", "rotate(-90 60 60)");
      svg.appendChild(c);
      off += len;
    }
    const num = document.createElementNS(NS, "text");
    num.setAttribute("x", 60); num.setAttribute("y", 60); num.setAttribute("text-anchor", "middle");
    num.setAttribute("fill", "var(--text)"); num.setAttribute("font-size", "22"); num.setAttribute("font-weight", "750");
    num.textContent = fmtN(total);
    const lab = document.createElementNS(NS, "text");
    lab.setAttribute("x", 60); lab.setAttribute("y", 78); lab.setAttribute("text-anchor", "middle");
    lab.setAttribute("fill", "var(--muted)"); lab.setAttribute("font-size", "11");
    lab.textContent = t("cellsTotal");
    svg.append(num, lab);
    if (!list.children.length || list.dataset.lang !== LANG || list.dataset.theme !== String(C.light)) {
      clear(list);
      list.dataset.lang = LANG;
      list.dataset.theme = String(C.light);
      for (const k of kinds) {
        const row = el("div", "mindrow");
        row.dataset.k = k;
        const cv = el("canvas");
        cv.width = cv.height = 22;
        const bar = el("div", "bar"), i = el("i");
        i.style.background = C[k];
        bar.appendChild(i);
        row.append(cv, el("span", null, t("t_" + k)), el("b", null, "0"), bar);
        list.appendChild(row);
        iconCanvas(cv, k, Object.assign({}, sampleOf(k), { animate: false, symbol: "" }));
      }
    }
    for (const row of list.children) {
      const v = shapes[row.dataset.k] || 0;
      row.querySelector("b").textContent = fmtN(v);
      row.querySelector(".bar i").style.width = (total ? (100 * v) / total : 0) + "%";
    }
  }

  /* ---------- its story so far, in one paragraph made of its own numbers ---------- */
  function story(stats, counts, born) {
    const box = $("#story");
    if (!box || !stats) return;
    clear(box);
    const parts = t("story", {
      age: born ? age(born) : "—", worlds: fmtN(stats.senses_known || 0), cells: fmtN((stats.cells || 0) + (stats.seen || 0)),
      kinds: t("kindsList", counts), articles: fmtN(stats.articles), anything: fmtN(stats.anything), words: fmtN(stats.words),
      meanings: fmtN(stats.meanings), assoc: fmtN(stats.assoc), types: fmtN(stats.types),
      n: { worlds: stats.senses_known || 0, cells: (stats.cells || 0) + (stats.seen || 0), articles: stats.articles, anything: stats.anything,
        words: stats.words, meanings: stats.meanings, assoc: stats.assoc, types: stats.types },
    });
    parts.forEach((p, i) => box.appendChild(i % 2 ? el("b", null, p) : document.createTextNode(p)));
  }

  /* ---------- what it knows ---------- */
  function knowledge(k) {
    const box = $("#knows");
    clear(box);
    $("#knowsN").textContent = fmtN((k.means || []).length);
    if (!(k.means || []).length) box.appendChild(el("div", "empty", t("noKnows")));
    for (const m of k.means || []) {
      const b = el("button", "lk" + (m.taught ? " taught" : ""));
      b.type = "button";
      const i = el("i");
      i.style.background = C.word;
      b.append(i, el("bdi", null, m.word), document.createTextNode(" = "), el("bdi", "mono", m.cell),
        el("small", null, m.taught ? t("taughtShort") : String(m.strength)));
      const key = m.key || m.word;
      b.addEventListener("click", () => Brain.focus(Brain.get("w:" + key) ? "w:" + key : m.id));
      box.appendChild(b);
    }
    const pairs = $("#pairs");
    clear(pairs);
    $("#pairsN").textContent = fmtN(k.assoc || 0);
    if (!(k.links || []).length) pairs.appendChild(el("div", "empty", t("none")));
    for (const l of k.links || []) {
      const b = el("button", "lk");
      b.type = "button";
      const i = el("i");
      i.style.background = C.assoc;
      b.append(i, el("bdi", null, `${l.a} · ${l.b}`), el("small", null, String(l.e)));
      b.addEventListener("click", () => Brain.focus("w:" + (l.ka || l.a)));
      pairs.appendChild(b);
    }
  }

  /* ---------- the details of one cell ---------- */
  function lk(item, label, extra, color, cls) {
    const b = el("button", "lk" + (cls ? " " + cls : ""));
    b.type = "button";
    const i = el("i");
    i.style.background = color;
    b.append(i, el("bdi", null, label));
    if (extra != null) b.append(el("small", null, extra));
    b.addEventListener("click", () => Brain.focus(item.id));
    return b;
  }
  function colorOfId(id) {
    const n = Brain.get(id);
    if (n) return C[n.type];
    return id && id.startsWith("w:") ? C.word : id && id.startsWith("s:") ? C.seen : C.cycle;
  }

  function takeBack(label, onTake) {
    const b = el("button", "lk taught untake");
    b.type = "button";
    b.title = t("untaughtTip");
    b.append(el("bdi", null, label), svgIcon("close", "ico"));
    b.addEventListener("click", () => { b.disabled = true; onTake(); });
    return b;
  }
  function section(box, title, items) {
    if (!items || !items.length) return;
    box.appendChild(el("div", "sect", title));
    const l = el("div", "links");
    items.forEach((x) => l.appendChild(x));
    box.appendChild(l);
  }
  function inspector(info, actions) {
    const box = $("#insp");
    const old = box.querySelector(".ib");
    const keep = old && box.dataset.id === info.id ? old.scrollTop : 0;
    box.dataset.id = info.id;
    clear(box);
    const n = Brain.get(info.id);
    const type = n ? n.type : typeOf(info);
    const head = el("div", "ih");
    const cv = el("canvas");
    head.appendChild(cv);
    const who = el("div", "who");
    const kind = el("div", "kind", t("t_" + type));
    kind.style.color = C[type];
    const h2 = el("h2");
    h2.appendChild(el("bdi", null, info.kind === "word" ? info.label : (info.symbol || info.label || "")));
    if (info.kind !== "word" && info.word) h2.appendChild(el("small", null, t("quoted", info.word)));
    who.append(kind, h2);
    const x = el("button", "btn icon x");
    x.type = "button";
    x.title = t("close");
    x.appendChild(svgIcon("close"));
    x.addEventListener("click", () => Brain.select(null));
    head.append(who, x);
    box.appendChild(head);
    const ib = el("div", "ib");
    box.appendChild(ib);
    if (keep) requestAnimationFrame(() => { ib.scrollTop = keep; });
    iconCanvas(cv, type, { cycles: info.cycles || (n && n.cycles), T: info.T || (n && n.T), symbol: info.symbol, img: n && n.img, means: n && n.means, nature: info.nature || (n && n.nature), animate: true, rate: 1.2 });
    if (info.kind === "gone") { ib.appendChild(el("p", "desc", t("gone"))); return; }
    if (Brain.isCurrent(info.id)) ib.appendChild(el("span", "tag new", t("inWorldNow")));
    let desc = t("d_" + type);
    if (type === "seen" && info.origin) desc += " — " + t("o_" + info.origin);
    ib.appendChild(el("p", "desc", desc));
    const kv = el("div", "kv");
    const cell = (k, v) => { const d = el("div"); d.append(el("small", null, k), el("b", null, v)); kv.appendChild(d); };
    if (info.kind === "word") {
      cell(t("means"), (info.means || []).length ? info.means.map((m) => m.cell).join(", ") : "—");
      cell(t("sources"), fmtN(info.sources || 0));
      cell(t("heard"), fmtN(info.heard || 0));
      cell(t("lookedUp"), info.looked ? "✓" : "—");
      ib.appendChild(kv);
      section(ib, t("means"), (info.means || []).map((m) => lk(m, m.label !== m.cell ? `${m.cell} · ${m.label}` : m.cell, `${m.strength}` + (m.taught ? " · " + t("taughtByYou") : ""), colorOfId(m.id), m.taught ? "taught" : "")));
      for (const m of info.means || []) {
        if (m.taught) continue;
        if (m.of && m.articles >= 4)
          ib.appendChild(el("p", "hint why", t("whyMeaning", info.label, m.cell, m.articles, m.of, pct(m.chance), m.strength)));
        if ((m.topics || []).length)
          ib.appendChild(el("p", "hint why", t(m.general ? "generalT" : "topicalT", info.label, m.cell, m.topics.length, m.topics.join(" | "))));
        if ((m.seen || []).length)
          ib.appendChild(el("p", "hint why", t("seenIn", info.label, m.cell, m.seen.join(" · "))));
        if (actions.forget) {
          const f = el("button", "btn small forget", null);
          f.type = "button";
          f.title = t("forgetTip");
          f.append(svgIcon("scissors"), el("span", null, t("forgetBtn", m.cell)));
          f.addEventListener("click", () => { f.disabled = true; actions.forget(m.cell, info.id.slice(2), info.label); });
          ib.appendChild(f);
        }
      }
      if (actions.unname) {
        const key = info.id.slice(2);
        section(ib, t("youNamed"), (info.means || []).filter((m) => m.taught)
          .map((m) => takeBack(`${info.label} = ${m.cell}`, () => actions.unname(m.cell, key))));
      }
      section(ib, t("goesWith"), (info.with || []).map((w) => lk(w, w.word, `${w.evidence}`, C.assoc)));
      section(ib, t("related"), (info.related || []).map((w) => lk(w, w.word, null, C.rel)));
      if ((info.near || []).length) {
        ib.appendChild(el("div", "sect", t("near")));
        for (const m of info.near) {
          const row = el("div");
          row.style.margin = "6px 0";
          const top = el("div", "links");
          top.appendChild(lk(m, m.label !== m.cell ? `${m.cell} · ${m.label}` : m.cell, `${m.evidence} ${t("digits")} · ${m.articles} ${t("articles")}`, colorOfId(m.id)));
          const bar = el("div", "evbar"), i = el("i"), u = el("u");
          const need = info.needs || 6;
          i.style.width = Math.min(100, (100 * m.evidence) / (need * 1.4)) + "%";
          u.style.insetInlineStart = (100 / 1.4) + "%";
          bar.append(i, u);
          row.append(top, bar);
          ib.appendChild(row);
        }
        ib.appendChild(el("p", "hint", t("needs", info.needs || 6)));
      }
    } else if (info.kind === "topic") {
      cell(t("topicArticles"), fmtN(info.articles || 0));
      ib.appendChild(kv);
      section(ib, t("topicWords"), (info.words || []).map((w) => lk(w, w.word, "", C.word)));
      section(ib, t("topicCells"), (info.cells || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, `${c.times}`, colorOfId(c.id))));
    } else if (info.kind === "circuit") {
      cell(t("bornAt"), ago(info.born));
      cell(t("circuitSize"), fmtN((info.members || []).length));
      ib.appendChild(kv);
      section(ib, t("circuitCells"), (info.members || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, "", colorOfId(c.id))));
      section(ib, t("lawsWith"), (info.laws || []).map((x) => lk(x.b, leads(leads(iso(x.a.cell), lawName("law:" + x.law)), iso(x.b.cell)), "", lawColor(x.law))));
    } else if (info.kind === "general") {
      cell(t("inWorlds"), `#${fmtN(info.world)}`);
      cell(t("itsWord"), info.word || t("noWord"));
      ib.appendChild(kv);
      ib.appendChild(el("p", "hint why", info.general === "part" ? t("genPartT", info.g, (info.members || []).length)
        : t("genLawT", t("gen_" + info.law), (info.members || []).length)));
      section(ib, t("itsKinds"), (info.members || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, "", colorOfId(c.id))));
      section(ib, t("wordsFor"), (info.words || []).map((w) => lk(w, w.word, `${w.strength}`, C.word)));
    } else if (info.kind === "thing") {
      cell(t("inWorlds"), fmtN(info.worlds || 0));
      if (info.life) cell(t("bornAt"), `${ago(info.life.born)} · #${fmtN(info.life.world)}`);
      cell(t("itsWord"), info.word || t("noWord"));
      ib.appendChild(kv);
      ib.appendChild(el("p", "hint why", t("d_thing")));
      section(ib, t("thingParts"), (info.parts || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, "", colorOfId(c.id))));
      section(ib, t("lawsWith"), (info.links || []).map(lawRow));
    } else if (info.kind === "odds") {
      cell(t("oddsIs"), t("oddsWhat", info.values, info.dwell));
      cell(t("inWorlds"), fmtN(info.worlds || 0));
      if (info.life) {
        cell(t("bornAt"), `${ago(info.life.born)} · #${fmtN(info.life.world)}`);
        cell(t("lastSeen"), `${ago(info.life.last)} · #${fmtN(info.life.last_world)}`);
      }
      cell(t("itsWord"), info.word || t("noWord"));
      cell(t("spoke"), fmtN(info.spoke || 0) + " " + t("times", info.spoke || 0));
      ib.appendChild(kv);
      ib.appendChild(el("p", "hint why", t("d_odds")));
      for (const lv of info.live || []) {
        ib.appendChild(el("div", "sect", t("oddsSense", lv.sense)));
        if (lv.verdict) ib.appendChild(el("p", "hint why", t("oddsVerdictT", lv.verdict)));
        for (const law of lv.laws || []) {
          ib.appendChild(el("p", "hint why", t("oddsLawT", law)));
          for (const u of law.unless || []) ib.appendChild(el("p", "hint", t("oddsUnless", u[1], u[2])));
          for (const u of law.especially || []) ib.appendChild(el("p", "hint", t("oddsEspecially", u[1], u[2])));
          if ((law.profile || []).length) ib.appendChild(el("p", "hint num", t("oddsProfile") + ": " + law.profile.map(([l, dg]) => `${l}:${dg}`).join("  ")));
          const cal = Object.entries(law.cal || {});
          if (cal.length) ib.appendChild(el("p", "hint num", t("oddsCal") + ": " + cal.map(([b, [n, k]]) => `${(+b / 10).toFixed(1)}→${n ? (k / n).toFixed(2) : "—"} (${fmtN(n)})`).join("  ")));
        }
      }
      for (const x of info.laws || []) ib.appendChild(el("p", "hint why", t("oddsLinkT", x)));
      section(ib, t("lawsWith"), (info.links || []).map(lawRow));
    } else if (info.kind === "invented") {
      cell(t("madeOf"), natureWords(info.nature));
      cell(t("inWorlds"), fmtN(info.worlds || 0));
      if (info.life) {
        cell(t("bornAt"), `${ago(info.life.born)} · #${fmtN(info.life.world)}`);
        cell(t("lastSeen"), `${ago(info.life.last)} · #${fmtN(info.life.last_world)}`);
      }
      cell(t("itsWord"), info.word || t("noWord"));
      cell(t("spoke"), fmtN(info.spoke || 0) + " " + t("times", info.spoke || 0));
      ib.appendChild(kv);
      if ((info.ops || []).length) ib.appendChild(el("p", "hint why", t("opsT", info.ops.map((o) => t("op_" + o)).join(sep("items")))));
      if (info.mechanism) ib.appendChild(el("p", "hint why", t("mechT", info.mechanism, info.evidence, fmtN(info.tried || 0))));
      if (info.machine) {
        const mc = info.machine;
        ib.appendChild(el("p", "hint why", t("madeT", mc.name, mc.states, fmtN(mc.things) + (mc.all ? "" : "+"), !!mc.group, !!mc.commute)));
        if (mc.sync) ib.appendChild(el("p", "hint why", t("syncT", pressWords(mc.sync))));
        if (mc.old) ib.appendChild(el("p", "hint why", t("oldT", mc.old)));
      }
      ib.appendChild(el("p", "hint why", t("usefulT", fmtN(info.worlds || 0), fmtN(info.foreseen || 0))));
      section(ib, t("lawsWith"), (info.links || []).map(lawRow));
      for (const law of info.laws || []) ib.appendChild(el("p", "hint why", lawText(law)));
      section(ib, t("wordsFor"), (info.words || []).map((w) => lk(w, w.word, `${w.strength}`, C.word)));
      section(ib, t("livedWith"), (info.lived || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, `${c.times}`, colorOfId(c.id))));
      const nb = el("form", "namebox");
      const inp = el("input");
      inp.placeholder = t("nameHint");
      inp.maxLength = 80;
      const go = el("button", "btn primary small", t("teach"));
      go.type = "submit";
      nb.append(inp, go);
      nb.addEventListener("submit", (ev) => { ev.preventDefault(); const w = inp.value.trim(); if (w) { actions.name(info.symbol, w); inp.value = ""; } });
      ib.appendChild(el("div", "sect", t("nameIt")));
      ib.appendChild(nb);
      if (actions.unname) section(ib, t("youNamed"), (info.taught || []).map((w) => takeBack(w, () => actions.unname(info.symbol, w))));
    } else {
      cell(t("cycles"), (info.cycles || []).join(type === "seen" ? "×" : type === "gear" ? "." : type === "crt" ? "x" : ","));
      if (info.kind === "idea") cell(t("inWorlds"), fmtN(info.worlds));
      else cell(t("seenTimes"), fmtN(info.times));
      if (info.life) {
        cell(t("bornAt"), `${ago(info.life.born)} · #${fmtN(info.life.world)}`);
        cell(t("lastSeen"), `${ago(info.life.last)} · #${fmtN(info.life.last_world)}`);
      }
      cell(t("itsWord"), info.word || t("noWord"));
      cell(t("spoke"), fmtN(info.spoke || 0) + " " + t("times", info.spoke || 0));
      ib.appendChild(kv);
      if (info.remembered) ib.appendChild(el("span", "tag new", t("remembered")));
      const cy = info.cycles || [];
      if (info.kind === "idea" && cy.length > 1) {
        const all = cy.reduce((a, b) => a * b, 1);
        const how = type === "gear" ? t("gearHow", cy[0], cy[1], all) : type === "crt" ? t("crtHow", cy[0], cy[1], all) : t("torusHow", cy.join(" × "), all);
        ib.appendChild(el("p", "hint why", how));
      }
      if ((info.moves || []).length) {
        const d = (info.cycles || [])[0];
        ib.appendChild(el("p", "hint why", t("movesT", info.moves.map((x) => "+" + x).join(sep("or")), d)));
        const cv = el("canvas", "lawview");
        ib.appendChild(cv);
        lawView(cv, d, info.T, info.moves, info.id);
      }
      if (info.kind === "seen" && cy.length) {
        ib.appendChild(el("p", "hint why", cy.length > 1 ? t("seenHow2", cy[0], cy[1]) : t("seenHow1", cy[0])));
      }
      if (info.kind === "seen") {
        const sub = el("div", "kv");
        const c2 = (k, v) => { const d = el("div"); d.append(el("small", null, k), el("bdi", null, v || "—")); d.lastChild.style.display = "block"; d.lastChild.style.overflow = "hidden"; d.lastChild.style.textOverflow = "ellipsis"; d.lastChild.style.whiteSpace = "nowrap"; d.lastChild.style.fontSize = "12.5px"; sub.appendChild(d); };
        c2(t("firstIn"), info.first);
        c2(t("lastIn"), info.last);
        ib.appendChild(sub);
        const u = imgEl(info.unit, "unitimg");
        if (u) { ib.appendChild(el("div", "sect", t("unit"))); ib.appendChild(u); }
      }
      section(ib, t("wordsFor"), (info.words || []).map((w) => lk(w, w.word, `${w.strength}`, C.word)));
      section(ib, t("livedWith"), (info.lived || []).map((c) => lk(c, c.label !== c.cell ? `${c.cell} · ${c.label}` : c.cell, `${c.times}`, colorOfId(c.id))));
      section(ib, t("readWith"), (info.read || []).map((c) => lk(c, c.cell, `${c.times}`, colorOfId(c.id))));
      section(ib, t("lawsWith"), (info.laws || []).map(lawRow));
      section(ib, t("sharesWith"), (info.kin || []).map((c) => lk(c, c.cell, c.numbers.join(","), colorOfId(c.id))));
      const nb = el("form", "namebox");
      const inp = el("input");
      inp.placeholder = t("nameHint");
      inp.maxLength = 80;
      const go = el("button", "btn primary small", t("teach"));
      go.type = "submit";
      nb.append(inp, go);
      nb.addEventListener("submit", (ev) => { ev.preventDefault(); const w = inp.value.trim(); if (w) { actions.name(info.symbol, w); inp.value = ""; } });
      ib.appendChild(el("div", "sect", t("nameIt")));
      ib.appendChild(nb);
      if (actions.unname) section(ib, t("youNamed"), (info.taught || []).map((w) => takeBack(w, () => actions.unname(info.symbol, w))));
    }
    const f = el("button", "btn small", null);
    f.type = "button";
    f.style.marginTop = "12px";
    f.append(svgIcon("focus"), el("span", null, t("focus")));
    f.addEventListener("click", () => Brain.focus(info.id));
    ib.appendChild(f);
  }

  function lawName(lt) {
    if (!String(lt).startsWith("law:")) return t("l_" + lt);
    const code = lt.slice(4);
    return has("law_" + code) ? t("law_" + code) : code;
  }
  function lawDesc(lt) {
    if (!String(lt).startsWith("law:")) return t("ld_" + lt);
    const code = lt.slice(4);
    return has("lawd_" + code) ? t("lawd_" + code) : t("lawGeneric", code);
  }
  function lawRow(x) {
    const name = lawName("law:" + x.law);
    return lk(x, x.out ? leads(name, iso(x.cell)) : leads(iso(x.cell), name), `${x.times}`, lawColor(x.law));
  }

  function natureWords(nature) {
    return String(nature || "").split("+").filter(Boolean)
      .map((p) => (p.startsWith("made:") ? t("nat_made", p.slice(5)) : t("nat_" + p))).join(" + ") || "—";
  }
  function pressWords(w) {
    return w ? String(w).split("").join(" ") : t("relNone");
  }
  function lawText(law) {
    if (law.law === "one") return t("lawOne", (law.sensors || []).join(t("join.and")), law.number);
    if (law.law === "rel") return t("lawRel", law.part, pressWords(law.lhs), pressWords(law.rhs));
    if (law.law !== "sum") return t("lawPart", lawName("law:" + law.law), law.from, law.to);
    const sum = (law.c || []).map((x, r) => (x ? `${x === 1 ? "" : x}n${r}` : "")).filter(Boolean).join(" + ");
    return t("lawSum", sum, law.total, !!law.proved);
  }

  const lawState = { key: null };
  function lawView(cv, d, T, moves, key) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const W = 220;
    cv.width = cv.height = W * dpr;
    const ctx = cv.getContext("2d");
    if (lawState.key !== key) {
      const now0 = performance.now();
      Object.assign(lawState, { key, pos: 0, from: 0, t0: now0, step: moves[0], next: now0 + 1100 });
    }
    const st = lawState;
    function frame(now) {
      if (!cv.isConnected) return;
      requestAnimationFrame(frame);
      if (now > st.next) { st.from = st.pos; st.step = moves[(Math.random() * moves.length) | 0]; st.pos = (st.pos + st.step) % d; st.t0 = now; st.next = now + 1100; }
      const { pos, from, t0, step } = st;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, W);
      const cx = W / 2, cy = W / 2, R = 84;
      ring(ctx, cx, cy, R, 16, d, T && T.length ? T : null, C.cycle, -Math.PI / 2);
      if (d <= 36) {
        for (let i = 0; i < d; i++) {
          const a = -Math.PI / 2 + ((i + 0.5) * TAU) / d;
          text(ctx, cx + (R + 17) * Math.cos(a), cy + (R + 17) * Math.sin(a), String(i), 9.5, C.muted, 600);
        }
      }
      const k = Math.min(1, (now - t0) / 450), e = ease(k);
      const cur = from + ((pos - from + d) % d) * e;
      const ang = -Math.PI / 2 + ((cur + 0.5) * TAU) / d;
      marker(ctx, cx, cy, R, ang, 6, C.cycle);
      text(ctx, cx, cy - 8, String(Math.round(cur) % d), 26, C.text, 750);
      ctx.globalAlpha = 1 - k * 0.6;
      text(ctx, cx, cy + 20, "+" + step, 15, C.ok, 750);
      ctx.globalAlpha = 1;
    }
    requestAnimationFrame(frame);
  }

  /* ---------- the legend, chips and guide (drawn with the same cells as the network) ---------- */
  function legend() {
    const b = $("#legendBody");
    clear(b);
    b.appendChild(el("h4", null, t("cellsLegend")));
    for (const ty of TYPES) {
      const r = el("div", "lg-row");
      const cv = el("canvas");
      cv.width = cv.height = 26;
      const tx = el("div");
      tx.append(el("b", null, t("t_" + ty)), el("span", null, t("d_" + ty).split(/[.—:]/)[0]));
      r.append(cv, tx);
      b.appendChild(r);
      iconCanvas(cv, ty, sampleOf(ty));
    }
    b.appendChild(el("p", "hint", t("sizeHint")));
    b.appendChild(el("h4", null, t("linksLegend")));
    for (const lt of [...LINKS, ...Brain.lawTypes()]) {
      const r = el("div", "lg-row");
      const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      linkIcon(s, lt);
      const tx = el("div");
      tx.append(el("b", null, lawName(lt)), el("span", null, lawDesc(lt)));
      r.append(s, tx);
      b.appendChild(r);
    }
  }
  function sampleOf(ty) {
    return {
      cycle: { cycles: [8], T: [0, 1, 2, 3, 4, 5, 6, 7], symbol: "8", animate: true, rate: 1.3 },
      torus: { cycles: [4, 6], symbol: "4,6", animate: true, rate: 1.3 },
      gear: { cycles: [4, 6], symbol: "4.6", animate: true, rate: 1.4 },
      crt: { cycles: [3, 5], symbol: "3x5", animate: true, rate: 1.2 },
      invented: { nature: "walls", symbol: "w[+1|-1]=", animate: true, rate: 1.2 },
      seen: { cycles: [4, 4], symbol: "", animate: true },
      word: { means: true },
    }[ty];
  }
  function chips(counts, onToggle) {
    const box = $("#chips");
    if (!box.children.length || box.dataset.lang !== LANG) {
      clear(box);
      box.dataset.lang = LANG;
      for (const ty of TYPES) {
        const c = el("button", "chip");
        c.type = "button";
        c.dataset.type = ty;
        const cv = el("canvas");
        cv.width = cv.height = 18;
        c.append(cv, el("span", null, t("tp_" + ty)), el("b", "num", "0"));
        c.addEventListener("click", () => onToggle(ty));
        box.appendChild(c);
        iconCanvas(cv, ty, Object.assign({}, sampleOf(ty), { animate: false, symbol: "" }));
      }
    }
    for (const c of box.children) {
      const ty = c.dataset.type;
      c.querySelector("b").textContent = fmtN(counts[ty] || 0);
      c.classList.toggle("off", !Brain.filters[ty]);
      c.title = t("d_" + ty);
    }
  }
  function guide(inbox) {
    const g = $("#p-guide");
    clear(g);
    const G = t("guide");
    g.appendChild(el("h2", null, G.title));
    g.appendChild(el("p", null, G.intro));
    g.appendChild(el("h3", null, G.cellsT));
    for (const ty of TYPES) {
      const row = el("div", "gt");
      const cv = el("canvas");
      cv.width = cv.height = 34;
      const tx = el("div");
      tx.append(el("b", null, t("t_" + ty)), el("p", null, t("d_" + ty)));
      row.append(cv, tx);
      g.appendChild(row);
      iconCanvas(cv, ty, sampleOf(ty));
    }
    g.appendChild(el("h3", null, G.linksT));
    const ul = el("ul");
    for (const lt of LINKS) { const li = el("li"); li.append(el("b", null, t("l_" + lt) + ": "), document.createTextNode(t("ld_" + lt))); ul.appendChild(li); }
    g.appendChild(ul);
    for (const [title, items] of G.sections) {
      g.appendChild(el("h3", null, title));
      const l = el("ul");
      items.forEach((s) => l.appendChild(el("li", null, s)));
      g.appendChild(l);
    }
    if (inbox) { const p = el("p"); p.append(document.createTextNode(G.inbox + " "), el("bdi", "mono", inbox)); g.appendChild(p); }
    const h = el("div", "honest");
    h.append(el("h3", null, G.honestT), el("p", null, G.honest));
    g.appendChild(h);
    g.appendChild(el("h3", null, G.keysT));
    const k = el("div", "keys");
    for (const [key, what] of G.keys) { k.append(el("kbd", null, key), el("span", null, what)); }
    g.appendChild(k);
  }

  /* ---------- its brains: every one alive, what each read and proved, and the ones it let go and why ---------- */
  function brains(live) {
    const box = $("#brains");
    if (!box) return;
    const list = live.brains || [];
    const alive = list.filter((b) => b.alive);
    $("#brainsN").textContent = t("brainsN", fmtN(Math.max(1, alive.length)));
    clear(box);
    const card = live.card;
    if (card) box.appendChild(el("p", "hint", t("cardLine", iso(card.name), fmtN(card.memory_gb), fmtN(card.kernels), fmtN(Math.round(card.items)), fmtN(card.seconds))));
    const inv = live.inventor_card;
    if (inv) box.appendChild(el("p", "hint", t("invLine", fmtK(inv.tried || 0), (+(inv.seconds || 0)).toFixed(1))));
    const ws = live.workshop;
    if (ws) box.appendChild(el("p", "hint", t("wsLine", fmtN(ws.worlds || 0), fmtN(ws.understood || 0), ws.level, fmtK(ws.pace || ws.per_second || 0))));
    if (alive.length <= 1 && list.length <= 1) { box.appendChild(el("p", "hint", t("brainsOnly"))); return; }
    for (const b of list) {
      const row = el("div", "brain" + (b.alive ? "" : " gone"));
      const head = el("div", "bh");
      head.append(el("b", "mono", b.name), el("small", null, b.alive ? (b.name === "Nova(1)" ? t("brainFirst") + " · " : "") + t("brainAlive", age(b.born))
        : t("brainGone", ago(b.gone))));
      row.appendChild(head);
      row.appendChild(el("p", "hint", b.alive ? t("brainDid", fmtN(b.pages || 0), fmtN(b.sites || 0), fmtN(b.ways || 0), fmtN(b.trusted || 0), fmtN(b.meanings || 0), fmtN(b.proved || 0), fmtN(b.waiting || 0))
        : brainWhy(b.why)));
      box.appendChild(row);
    }
  }

  /* ---------- how it asks the web: the ways it met in the pages it read, each a hypothesis it judges itself ---------- */
  function asks(rep) {
    const box = $("#asks");
    if (!box) return;
    const list = rep.asks || [];
    $("#asksN").textContent = t("asksCount", fmtN(rep.asks_met || list.length), fmtN(list.filter((w) => (w.trusted || []).length).length));
    clear(box);
    if (!list.length) { box.appendChild(el("p", "empty", t("asksNone"))); return; }
    for (const w of list) {
      const row = el("p", "hint" + ((w.trusted || []).length ? " ok" : ""), t("askRow", { how: askHow(w.how), site: iso(w.site), asked: fmtN(w.asked), answered: fmtN(w.answered) }));
      const more = [];
      if ((w.trusted || []).length) more.push(t("askTrusted", w.trusted.map(askKind).join(sep("list"))));
      if (w.taught) more.push(t("askTaught", iso(w.taught)));
      if (more.length) row.appendChild(el("small", null, " · " + more.join(" · ")));
      box.appendChild(row);
    }
  }

  /* ---------- small notes that come and go ---------- */
  function toast(icon, color, title, body, target) {
    const box = $("#toasts");
    const tst = el("div", "toast");
    const close = () => { tst.classList.add("out"); setTimeout(() => tst.remove(), 400); };
    if (target) tst.classList.add("link");
    tst.addEventListener("click", () => {
      const id = target && (typeof target === "function" ? target() : target);
      if (id) Brain.focus(id);
      close();
    });
    const ic = el("div", "ic");
    ic.style.background = rgba(color && color.startsWith("#") ? color : "#6ea8ff", 0.16);
    ic.style.color = color;
    ic.appendChild(svgIcon(icon));
    const tx = el("div");
    tx.append(el("b", null, title));
    if (body) tx.append(el("span", null, body));
    tst.append(ic, tx);
    box.appendChild(tst);
    while (box.children.length > 4) box.removeChild(box.firstChild);
    setTimeout(close, 5200);
  }

  /* ---------- its mind: how it thinks now, its workshop, its card, the space of its world, what it was born with ---------- */
  let spaceNow = null, spaceRaf = 0;
  function mindTab(live) {
    if (!$("#p-mind") || !$("#p-mind").classList.contains("on")) return;
    safely2(() => abilityView((live.self || {}).abilities));
    safely2(() => oneView(live.self, live.workshop));
    safely2(() => selfView(live.self));
    safely2(() => labView(live.lab));
    safely2(() => thinkNow(live));
    safely2(() => workshopView(live.workshop));
    safely2(() => gpuView(live));
    safely2(() => spaceView(live.space, (live.workshop || {}).space));
    safely2(() => innateView(live.innate || []));
    safely2(() => madeView(live.made_senses || [], live.senses || []));
  }

  function abilityView(ab) {
    const card = $("#abilityCard"), box = $("#abilityView");
    if (!card || !box) return;
    card.classList.toggle("hidden", !ab);
    clear(box);
    if (!ab) return;
    const aw = ab.aware || {}, s = aw.sure || [0, 0];
    box.appendChild(el("p", "hint", t("abilityAware", fmtN(aw.senses || 0), fmtN(aw.laws || 0), fmtN(s[0]), fmtN(s[0] + s[1]))));
    const cs = ab.causes || [];
    box.appendChild(el("p", "hint", cs.length ? t("abilityCauses", fmtN(cs.length)) : t("abilityCausesNone")));
    for (const c of cs) {
      const row = el("div", "self-row stack");
      row.append(el("b", null, `${c.act} → ${senseShort(c.sense)}`), el("small", "num", t("abilityCause", c.act, senseShort(c.sense), t(c.up ? "abilityUp" : "abilityDown"), c.q, c.change)));
      box.appendChild(row);
    }
    const f = ab.feel || {};
    box.appendChild(el("p", "hint", f.act ? t("abilityFeel", f.act, senseShort(f.sense), fmtN(f.came || 0), fmtN(f.broke || 0))
      : t("abilityFeelNone", fmtN(f.came || 0), fmtN(f.broke || 0))));
    const bySense = new Map();
    for (const b of f.brought || []) {
      if (!bySense.has(b.sense)) bySense.set(b.sense, []);
      bySense.get(b.sense).push(t("abilityBrought", b.act, fmtN(b.k), fmtN(b.n)));
    }
    if (bySense.size) box.appendChild(el("p", "hint", t("abilityBroughtT")));
    for (const [sense, parts] of bySense) {
      const row = el("div", "self-row stack");
      row.append(el("b", null, senseShort(sense)), el("small", "num", parts.join(" · ")));
      box.appendChild(row);
    }
  }

  function oneView(me, ws) {
    const card = $("#oneCard"), box = $("#oneView");
    if (!card || !box) return;
    card.classList.toggle("hidden", !me || !me.one);
    clear(box);
    if (!me || !me.one) return;
    const one = me.one, ep = me.episodes || {}, tw = (me.twins || {}).now, feel = ((me.abilities || {}).feel || {}).act;
    const lines = [
      t("onePairs", fmtN(one.pairs || 0)),
      t("oneClocks", fmtN((me.clocks || []).length)),
      t("oneEpisodes", fmtN(ep.cells || 0), fmtN((ep.trusted || []).length)),
      t("oneMade", fmtN(one.made || 0)),
      t("oneParts", fmtN(one.parts || 0), fmtN(one.kinds || 0)),
    ];
    if (ws && ws.worlds != null) lines.push(t("oneWorkshop", fmtN(ws.worlds || 0), fmtN(ws.understood || 0)));
    if (tw && tw.gene) lines.push(t("oneTwins", tw.gene, String(tw.to), fmtN(tw.acts || 0)));
    lines.push(feel ? t("oneDrive", feel) : t("oneDriveNone"));
    lines.push(t("oneBrains", fmtN(me.brains || 0)));
    for (const s of lines) box.appendChild(el("p", "hint", s));
  }

  function selfView(me) {
    const box = $("#selfView");
    clear(box);
    if (!me) return;
    $("#selfN").textContent = t("selfThink", fmtN(Math.round(me.think_ms_per_min || 0)));
    const top = Math.max(1, ...(me.parts || []).map((p) => p.share));
    for (const p of me.parts || []) {
      const row = el("div", "self-row");
      const bar = el("div", "bar"), i = el("i");
      i.style.width = Math.round((100 * p.share) / top) + "%";
      bar.appendChild(i);
      row.append(el("b", null, has("part_" + p.part) ? t("part_" + p.part) : p.part),
        el("small", "num", t("selfRow", p.share, fmtN(p.ms_per_min), fmtN(p.calls), p.longest_ms)), bar);
      box.appendChild(row);
    }
    const lines = [];
    const led = me.ledger || {};
    for (const tool of ["counts", "kind", "machine", "odds", "answer"]) {
      const s = led[`${tool}:sure`] || [0, 0, 0];
      const n = s[0] + s[1];
      if (n) lines.push(t("selfSure", t("tool_" + tool), fmtN(s[0]), fmtN(n)));
    }
    for (const [kind, b] of Object.entries(me.beliefs || {})) {
      const gone = Object.values(b.gone || {}).reduce((a, x) => a + x, 0);
      lines.push(t("selfBeliefs", has("belief_" + kind) ? t("belief_" + kind) : kind, fmtN(b.born), fmtN(b.held), fmtN(gone)));
    }
    if ((me.recalled || []).length) lines.push(t("selfRecalled", me.recalled.join(sep("list"))));
    const minds = Object.entries(me.minds || {});
    if (minds.length) lines.push(t("selfMinds", minds.map(([n, r]) => t("selfMind", n, fmtN(r.told), fmtN(r.held), fmtN(r.failed), r.trust)).join(sep("list"))));
    const ex = me.experiment;
    if (ex && (ex.left > 0 || ex.fair > 0)) lines.push(t("selfExperiment", "#" + (ex.button + 1), fmtN(Math.max(0, ex.left)), fmtN(ex.fair || 0)));
    lines.push(t("selfRuns", fmtN(Math.round((me.memory_bytes || 0) / 1024)), fmtN(me.brains || 0), fmtN(me.threads || 0)));
    for (const s of lines) box.appendChild(el("p", "hint", s));
    const code = me.code;
    if (code && code.print) {
      const p = el("p", code.changed || code.brains_other ? "hint code-warn" : "hint", t("selfCode", code.print, clock(code.began)));
      if (code.changed) p.append(" ", t("selfCodeChanged", code.disk));
      if (code.brains_other) p.append(" ", t("selfCodeBrains", fmtN(code.brains_other)));
      box.appendChild(p);
    }
  }

  const dur = (s) => (s < 90 ? t("unit.s", Math.round(s)) : s < 5400 ? t("unit.m", Math.round(s / 60)) : t("unit.h", Math.round(s / 3600)));
  const senseShort = (n) => {
    const [b, v] = String(n || "").split("@");
    const name = has("senseShort_" + b) ? t("senseShort_" + b) : b;
    return v ? t("senseVersion", name, v) : name;
  };
  function since(sv) {
    const card = $("#sinceCard"), box = $("#sinceView");
    if (!card || !box) return;
    card.classList.toggle("hidden", !sv);
    clear(box);
    if (!sv) return;
    const th = sv.this || {}, before = sv.before || [];
    $("#sinceN").textContent = t("sinceStarts", fmtN(before.length + 1));
    box.appendChild(el("p", "hint", t("sinceStart", clock(th.at), (th.recalled || []).length ? th.recalled.map(senseShort).join(sep("list")) : "—")));
    const names = [...new Set([...Object.keys(th.sure || {}), ...before.flatMap((s) => Object.keys(s.sure || {}))])];
    for (const name of names) {
      const now = (th.sure || {})[name];
      const prev = before.map((s) => (s.sure || {})[name]).filter((v) => v != null);
      const first = ((sv.first || {}).sure || {})[name];
      const row = el("div", "self-row");
      row.append(el("b", null, senseShort(name)),
        el("small", "num", (now != null ? dur(now) : t("sinceNotYet")) + (prev.length ? " " + t("sinceBefore", prev.slice(-3).map(dur).join(" · "), dur(first != null ? first : prev[0])) : "")));
      box.appendChild(row);
    }
    const born = Object.entries(th.born || {}).filter(([, n]) => n > 0);
    if (born.length) box.appendChild(el("p", "hint", t("sinceBorn", born.map(([k, n]) => `${fmtN(n)} ${has("born_" + k) ? t("born_" + k) : k}`).join(sep("list")))));
    const ch = sv.changed;
    if (ch) {
      const lw = ch.laws || {};
      if (lw.born) {
        box.appendChild(el("p", "hint", t("sinceLaws", fmtN(lw.born), fmtN(lw.held), fmtN(lw.gone))));
        for (const [kind, name, dig, at, held] of lw.top || []) {
          const label = has("belief_" + kind) ? t("belief_" + kind) : kind;
          box.appendChild(el("p", "hint", t(held ? "sinceLaw" : "sinceLawGone", label, senseShort(String(name || "")), dig == null ? "—" : dig, clock(at))));
        }
      }
      if ((ch.machines || []).length) box.appendChild(el("p", "hint", t("sinceMachines", ch.machines.map((m) => m[0]).join(sep("list")))));
      const g = ch.growth;
      if (g && g.meanings) box.appendChild(el("p", "hint", t("sinceGrowth", fmtN(g.meanings[0]), fmtN(g.meanings[1]), fmtN((g.words || [0, 0])[0]), fmtN((g.words || [0, 0])[1]), fmtN((g.read || [0, 0])[0]), fmtN((g.read || [0, 0])[1]))));
      const w = ch.workshop;
      if (w && w.worlds && w.worlds[0] != null) box.appendChild(el("p", "hint", t("sinceWorkshop", fmtN(w.worlds[1] - w.worlds[0]), fmtN((w.understood[1] || 0) - (w.understood[0] || 0)), "—")));
      const br = ch.brains || {};
      if ((br.born || []).length || (br.gone || []).length) box.appendChild(el("p", "hint", t("sinceBrains", (br.born || []).map((b) => b[0]).join(sep("list")) || "—", (br.gone || []).map((b) => b[0]).join(sep("list")) || "—")));
      for (const [gene, from, to] of ch.genes || []) box.appendChild(el("p", "hint", t("sinceGene", gene, from, to)));
      const c = ch.control;
      if (c && c.now) box.appendChild(el("p", "hint", t("sinceControl", fmtN(c.now.laws), fmtN(c.now.moments), fmtN(c.now.counts), fmtN(c.now.made), fmtN(c.now.machines), fmtN(c.clean), fmtN(c.starts))));
    }
    const fs = sv.forecasts || [];
    if (fs.length) {
      box.appendChild(el("p", "hint", t("sinceForecasts")));
      for (const f of fs.slice().reverse()) {
        const what = f.what === "moment" ? t("foreMoment", senseShort(f.name || ""), clock(f.due_at))
          : f.what === "gate" ? t("foreGate", senseShort(f.name || ""), clock(f.due_at))
          : f.what === "workshop" ? t("foreWorkshop", fmtN(f.world), clock(f.due_at))
          : f.what === "control" ? t("foreControl", fmtN(f.due))
          : t("foreInventor", clock(f.due_at));
        const mark = f.right == null ? (f.closed ? "·" : "…") : f.right ? "✓" : "✗";
        box.appendChild(el("p", "hint", `${mark} ${what}${f.sure ? "" : " " + t("foreGuess")}`));
      }
    }
    const fw = th.foresaw || {}, s1 = fw.sure || [0, 0], s0 = fw.guess || [0, 0];
    if (s1[0] + s1[1] + s0[0] + s0[1]) box.appendChild(el("p", "hint", t("sinceLedger", fmtN(s1[0]), fmtN(s1[0] + s1[1]), fmtN(s0[0]), fmtN(s0[0] + s0[1]))));
  }

  function labView(lab) {
    const box = $("#labView");
    clear(box);
    if (!lab) return;
    const changes = lab.changes || [];
    $("#labN").textContent = t("labCount", fmtN(changes.length));
    for (const [g, v] of Object.entries(lab.now || {})) {
      const born = (lab.genes || {})[g] ? lab.genes[g][0] : null;
      const row = el("div", "self-row");
      const tries = Object.entries(lab.trials || {}).filter(([k]) => k.startsWith(g + "=")).map(([k, r]) => t("labTry", k.split("=")[1], fmtN(r[1]), fmtN(r[0])));
      row.append(el("b", null, t("gene_" + g)), el("small", "num", t(String(v) === String(born) ? "labBorn" : "labChanged", String(v))));
      if (tries.length) row.append(el("small", "hint", tries.join(sep("items"))));
      box.appendChild(row);
    }
    for (const c of changes.slice().reverse()) box.appendChild(el("p", "hint why", t("labChange", t("gene_" + c.gene), String(c.from), String(c.to), fmtN(c.wins), fmtN(c.n), c.digits, c.bar)));
    const last = (lab.lab || []).slice(-4).reverse();
    for (const r of last) box.appendChild(el("p", "hint", t("labRow", r.k, t("gene_" + r.gene), r.value, fmtN(r.as_is), r.ok, fmtN(r.changed), r.ok2)));
    if (!changes.length && !last.length) box.appendChild(el("p", "empty", t("labNone")));
  }

  function thinkNow(live) {
    const box = $("#thinkNow");
    clear(box);
    const sure = (live.goal || []).filter((g) => g.sure).length;
    box.appendChild(el("p", "hint why", t("thinkWorld", live.real ? t("thinkReal") : fmtN(live.world), fmtN(live.steps || 0), fmtN(sure), fmtN((live.goal || []).length))));
    for (const g of live.goal || []) {
      const row = el("div", "think-row" + (g.sure ? " ok" : ""));
      row.append(el("b", "mono", "#" + g.sensor), el("span", null, t("thinkTool_" + g.tool) + (g.of ? " · " + t("thinkMapped", fmtN(g.mapped), fmtN(g.of)) : "")),
        el("small", null, g.sure ? t("thinkSure") : t("thinkOpen")));
      box.appendChild(row);
    }
    const why = (live.why || []).slice(0, 6);
    if (why.length) box.appendChild(el("div", "sect", t("thinkLately")));
    for (const d of why) box.appendChild(el("p", "hint", `${clock(d.t)} · ${whyText(d)}`));
  }

  function workshopView(ws) {
    const box = $("#workshop");
    clear(box);
    if (!ws) { $("#wsN").textContent = ""; box.appendChild(el("p", "empty", t("wsNone"))); return; }
    $("#wsN").textContent = t("wsCount", fmtN(ws.understood || 0), fmtN(ws.worlds || 0));
    const minis = el("div", "minis");
    for (const [k, v] of [["wsLevel", ws.level], ["wsPace", fmtK(ws.pace || ws.per_second || 0)], ["wsActs", fmtK(ws.acts || 0)]]) {
      const m = el("div", "mini");
      m.append(el("small", null, t(k)), el("b", null, String(v ?? "—")));
      minis.appendChild(m);
    }
    box.appendChild(minis);
    const made = ws.made || {};
    box.appendChild(el("p", "hint why", t("wsNow", fmtN(ws.world || 0), madeWords(made), fmtN(ws.now || 0))));
    const list = el("div", "wslist");
    for (const r of (ws.recent || []).slice().reverse()) {
      const row = el("div", "wsrow" + (r.ok ? " ok" : " bad"));
      row.append(el("b", "mono", "#" + r.k), el("span", null, madeWords(r.made || {})),
        el("small", null, t(r.ok ? "wsDidOk" : "wsDidNot", fmtN(r.acts), r.s, r.thought || 0)));
      list.appendChild(row);
    }
    box.appendChild(list);
  }

  function madeWords(made) {
    const kinds = (made.kinds || []).map((k) => t("wsKind_" + k[0], k[1] ?? ""));
    const extra = [];
    if (made.pile) extra.push(t("wsPile"));
    if (made.chance) extra.push(t("wsChance"));
    return [...kinds, ...extra].join(" + ") || "—";
  }

  function gpuView(live) {
    const box = $("#gpuUse");
    clear(box);
    const c = live.card, inv = live.inventor_card, ws = (live.workshop || {}).card;
    if (!c && !inv && !ws) { box.appendChild(el("p", "empty", t("gpuNone"))); return; }
    const name = (c || inv || ws).name;
    box.appendChild(el("p", "hint why", t("gpuName", iso(name), fmtN((c || inv || ws).memory_gb), fmtN((c || inv || ws).sms || 0))));
    const rows = [["gpuLife", c], ["gpuWorkshop", ws], ["gpuInventor", inv]];
    for (const [k, u] of rows) {
      if (!u) continue;
      const row = el("div", "gpurow");
      row.append(el("b", null, t(k)), el("span", "num", t(k === "gpuInventor" ? "gpuTried" : "gpuItems", fmtK(u.kernels || 0), fmtK(Math.round(u.tried ?? u.items ?? 0)), (+(u.seconds || 0)).toFixed(2))));
      box.appendChild(row);
    }
    if (inv && inv.steps) box.appendChild(el("p", "hint", t("gpuSteps", fmtK(inv.steps), fmtK(inv.simulated || 0), inv.seconds ? fmtK(Math.round(inv.steps / Math.max(inv.seconds, 1e-3))) : "—")));
  }

  let spaceOf = null;
  function spaceView(life, shop) {
    const n = (s) => (s ? s.n ?? ((s.dims || []).length + (s.machines || []).reduce((a, m) => a + (m.dims || []).length, 0)) : -1);
    const pick = spaceOf || (n(shop) > n(life) ? "workshop" : "life");
    const sp = pick === "workshop" && shop ? shop : life;
    spaceNow = sp || null;
    const dials = $("#spaceDials");
    clear(dials);
    const seg = el("div", "seg");
    for (const [k, s] of [["life", life], ["workshop", shop]]) {
      if (!s) continue;
      const b = el("button", (sp === s ? "on" : ""), t("spaceOf_" + k, fmtN(Math.max(0, n(s)))));
      b.type = "button";
      b.addEventListener("click", () => { spaceOf = k; spaceView(life, shop); });
      seg.appendChild(b);
    }
    if (seg.children.length > 1) dials.appendChild(seg);
    if (!sp) { $("#spaceN").textContent = ""; return; }
    const all = [...(sp.dims || []).map((d) => Object.assign({ from: "laws" }, d))];
    for (const m of sp.machines || []) for (const d of m.dims || []) all.push(Object.assign({ from: m.name }, d));
    $("#spaceN").textContent = t("spaceCount", fmtN(all.length), fmtN(sp.most || all.length));
    if (!all.length) dials.appendChild(el("p", "empty", t("spaceNone", fmtN(sp.senses || 0), fmtN(sp.of || 0))));
    all.forEach((d, i) => {
      const box = el("div", "dial");
      const cv = el("canvas");
      cv.width = cv.height = 54;
      box.append(cv, el("small", null, (d.kind === "line" || d.kind === "free" ? "∞" : fmtN(d.size)) + " · " + t("spaceKind_" + d.kind)));
      dials.appendChild(box);
      drawDial(cv, d, C.light ? "#2b3a67" : "#e9edfa", colorOf(i % 2 ? "accent" : "ok"));
    });
    if (!spaceRaf) spaceRaf = requestAnimationFrame(paintSpace);
  }

  function drawDial(cv, d, ink, col) {
    const ctx = cv.getContext("2d"), r = 21, cx = 27, cy = 27;
    ctx.clearRect(0, 0, 54, 54);
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(132,156,230,.28)";
    ctx.beginPath();
    if (d.kind === "walls" || d.kind === "line" || d.kind === "free") { ctx.moveTo(6, cy); ctx.lineTo(48, cy); }
    else ctx.arc(cx, cy, r, 0, 2 * Math.PI);
    ctx.stroke();
    const at = d.at == null ? 0 : +d.at;
    let x = cx, y = cy;
    if (d.kind === "walls") { x = 6 + 42 * (d.size > 1 ? at / (d.size - 1) : 0.5); }
    else if (d.kind === "line" || d.kind === "free") { x = cx + 21 * Math.tanh(at / 8); }
    else { const a = -Math.PI / 2 + 2 * Math.PI * (d.size ? (at % d.size) / d.size : 0); x = cx + r * Math.cos(a); y = cy + r * Math.sin(a); }
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(x, y, 5, 0, 2 * Math.PI); ctx.fill();
    ctx.fillStyle = ink;
    ctx.font = "10px " + getComputedStyle(document.body).fontFamily;
    ctx.textAlign = "center";
    ctx.fillText(d.at == null ? "—" : String(d.at), cx, d.kind === "walls" || d.kind === "line" || d.kind === "free" ? cy + 16 : cy + 4);
  }

  function paintSpace(time) {
    spaceRaf = 0;
    const cv = $("#spaceCanvas");
    if (!cv || !$("#p-mind").classList.contains("on") || !spaceNow) return;
    const W = cv.width, H = cv.height, ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, W, H);
    const dims = [...(spaceNow.dims || [])];
    for (const m of spaceNow.machines || []) for (const d of m.dims || []) dims.push(d);
    const n = dims.length;
    if (!n) return;
    const coords = (vals) => {
      const out = [];
      dims.forEach((d, i) => {
        const v = vals[i] == null ? 0 : +vals[i];
        if (d.kind === "cycle" || d.kind === "made" || d.kind === "bit") {
          const a = 2 * Math.PI * ((d.size ? v % d.size : 0) / (d.size || 1));
          out.push(Math.cos(a), Math.sin(a));
        } else if (d.kind === "walls") out.push(2 * (d.size > 1 ? v / (d.size - 1) : 0.5) - 1, 0);
        else out.push(Math.tanh(v / 8), 0);
      });
      return out;
    };
    const D = 2 * n, t0 = (time || 0) / 9000;
    const ax = [], ay = [];
    for (let i = 0; i < D; i++) {
      ax.push(Math.cos(t0 * (1 + 0.37 * i) + i * 1.7));
      ay.push(Math.sin(t0 * (0.8 + 0.29 * i) + i * 2.3));
    }
    const norm = (v) => { const s = Math.hypot(...v) || 1; return v.map((x) => x / s); };
    const X = norm(ax), Yr = ay.map((y, i) => y - X[i] * ay.reduce((s, q, k) => s + q * X[k], 0)), Y = norm(Yr);
    const scale = Math.min(W, H) * 0.42 / Math.sqrt(Math.max(1, n / 2));
    const proj = (vals) => { const c = coords(vals); let x = 0, y = 0; for (let i = 0; i < D; i++) { x += c[i] * X[i]; y += c[i] * Y[i]; } return [W / 2 + scale * x, H / 2 + scale * y]; };
    const per = Math.max(2, Math.floor(Math.pow(3000, 1 / n)));
    const counts = dims.map((d) => (d.kind === "cycle" || d.kind === "made" || d.kind === "bit" ? Math.min(d.size || 1, per) : Math.min(per, 9)));
    const total = counts.reduce((a, b) => a * b, 1);
    ctx.fillStyle = "rgba(166,129,255,.28)";
    for (let i = 0; i < total; i++) {
      let r = i;
      const vals = dims.map((d, k) => {
        const c = counts[k], s = r % c;
        r = Math.floor(r / c);
        if (d.kind === "cycle" || d.kind === "made" || d.kind === "bit") return (d.size || 1) * s / c;
        if (d.kind === "walls") return (d.size - 1) * s / Math.max(1, c - 1);
        return -16 + 32 * s / Math.max(1, c - 1);
      });
      const [px, py] = proj(vals);
      ctx.fillRect(px - 1, py - 1, 2, 2);
    }
    ctx.strokeStyle = "rgba(132,156,230,.16)";
    ctx.lineWidth = 1;
    dims.forEach((d, i) => {
      ctx.beginPath();
      const steps = d.kind === "cycle" || d.kind === "made" || d.kind === "bit" ? 48 : 2;
      for (let s = 0; s <= steps; s++) {
        const vals = dims.map(() => 0);
        vals[i] = d.kind === "cycle" || d.kind === "made" || d.kind === "bit" ? (d.size || 1) * s / steps : d.kind === "walls" ? (d.size - 1) * s / steps : -24 + 48 * s / steps;
        const [x, y] = proj(vals);
        s ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    });
    const lawDims = (spaceNow.dims || []).length;
    const now = dims.map((d) => d.at);
    const trail = (spaceNow.trail || []).map((tr) => [...tr, ...now.slice(lawDims)]);
    ctx.lineWidth = 2;
    for (let i = 1; i < trail.length; i++) {
      const [x0, y0] = proj(trail[i - 1]), [x1, y1] = proj(trail[i]);
      ctx.strokeStyle = `rgba(110,168,255,${0.08 + 0.7 * i / trail.length})`;
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    }
    const [x, y] = proj(now);
    const g = ctx.createRadialGradient(x, y, 0, x, y, 14);
    g.addColorStop(0, "rgba(255,255,255,.95)"); g.addColorStop(0.35, "rgba(110,168,255,.85)"); g.addColorStop(1, "rgba(110,168,255,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, 14, 0, 2 * Math.PI); ctx.fill();
    spaceRaf = requestAnimationFrame(paintSpace);
  }

  function innateView(list) {
    const box = $("#innate");
    clear(box);
    for (const a of list) {
      const row = el("div", "innate-row");
      const nums = [];
      if (a.now != null) nums.push(t("innNow", fmtN(a.now)));
      if (a.all != null) nums.push(t("innAll_" + a.key, fmtN(a.all)));
      if (a.tried) nums.push(t("innTried", fmtK(a.tried)));
      row.append(el("b", null, t("inn_" + a.key)), el("span", "hint", t("innWhat_" + a.key)), el("small", "num", nums.join(" · ")));
      box.appendChild(row);
    }
  }

  function madeView(list, senses) {
    const box = $("#madeSenses");
    clear(box);
    $("#madeN").textContent = fmtN(list.length);
    if (!list.length) { box.appendChild(el("p", "empty", t("madeNone"))); return; }
    const nameOf = (i) => (senses[i] != null ? senses[i] : "#" + (+i + 1));
    for (const s of list) {
      if (s.kind === "made") {
        const parts = s.parts.map(([i, r, c]) => t("madePart", nameOf(i), r, c)).join(" , ");
        box.appendChild(el("p", "hint", t("madeRow", nameOf(s.of), has("madeWay_" + s.way) ? t("madeWay_" + s.way) : s.way, parts, fmtN(s.right || 0), fmtN(s.n || 0))));
      } else {
        box.appendChild(el("p", "hint", t("madePair", s.name, s.parts.map(([l, a, v]) => `${a}=${v}` + (l ? ` (${t("madeLag", l)})` : "")).join(" & "))));
      }
    }
  }

  return { refeed, wantNames, note, discover, paintDiscoveries, mind, use, story, rhythm, sensorAt, sensorTip, sensorCell, currentCells, cellStates, since, knowledge, worlds, targetOf, now, readingFrom, world, paintStrip, paintSensorCards, message, chatEmpty, reading, tryRow, feed, setFeedFilter, setFeedPaused, growth, spark, inspector, legend, chips, guide, toast, mindTab, SERIES };
})();

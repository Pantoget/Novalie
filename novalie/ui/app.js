/* Novalie's page: it asks the model what is happening, many times a second, and shows it. */
"use strict";
let lastLaws = "";

(() => {
  const api = {
    async get(path) {
      const c = new AbortController();
      const tm = setTimeout(() => c.abort(), 7000);
      try {
        const r = await fetch(path, { cache: "no-store", signal: c.signal, headers: { "X-Novalie": "1" } });
        if (!r.ok) throw new Error(String(r.status));
        return await r.json();
      } finally { clearTimeout(tm); }
    },
    post(path, body, headers) {
      return fetch(path, { method: "POST", body, cache: "no-store", headers: Object.assign({ "X-Novalie": "1" }, headers || {}) });
    },
  };

  const S = {
    lastEvent: 0, nextMsg: 0, firstEvents: true, firstMsgs: true, online: null, fails: 0, erased: false,
    stats: {}, history: [], tab: "now", unread: 0, inbox: "", live: null,
  };
  try { S.tab = localStorage.getItem("novalie.tab") || "now"; } catch (e) {  }

  /* ---------- the numbers at the top, counting up as it learns ---------- */
  const KPIS = [
    ["cells", "k_cells", (s) => (s.cells || 0) + (s.seen || 0) + (s.generals || 0) + (s.circuits || 0) + (s.topics || 0) + (s.chance || 0) + (s.things || 0), "ideas", "cycle"],
    ["senses", "k_senses", (s) => s.senses_known, "senses", "ok"],
    ["words", "k_words", (s) => s.words, "words", "word"],
    ["meanings", "k_meanings", (s) => s.meanings, "meanings", "word"],
    ["assoc", "k_assoc", (s) => s.assoc, "links", "assoc"],
    ["articles", "k_articles", (s) => s.articles, "articles", "gear"],
    ["anything", "k_anything", (s) => s.anything, "read", "seen"],
    ["types", "k_types", (s) => s.types, "types", "seen"],
    ["steps", "k_steps", (s) => s.steps, "steps", "accent"],
  ];
  const kpiState = new Map();

  const KPI_GO = { cells: ["growth", "#donut"], senses: ["now", "#worlds"], words: ["growth", "#knows"], meanings: ["growth", "#knows"],
    assoc: ["growth", "#pairs"], articles: ["reading", "#readHist"], anything: ["reading", "#lastRead"], types: ["reading", "#types"], steps: ["growth", "#charts"] };
  function goKpi(key) {
    const go = KPI_GO[key];
    if (!go) return;
    setTab(go[0]);
    setTimeout(() => { const it = $(go[1]), card = it && (it.closest(".card") || it); if (card) { card.scrollIntoView({ block: "start", behavior: "smooth" }); card.classList.add("hi"); setTimeout(() => card.classList.remove("hi"), 1600); } }, 60);
  }
  function buildKpis() {
    const box = $("#kpis");
    clear(box);
    for (const [key, label, , , col] of KPIS) {
      const k = el("div", "kpi");
      k.dataset.key = key;
      k.dataset.col = col;
      const v = el("div", "v num", kpiState.has(key) ? fmtK(kpiState.get(key).shown) : "—");
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      k.append(v, el("div", "l", t(label)), el("span", "delta"), svg);
      k.title = t("kd_" + key) + " · " + t("kpiClick");
      k.tabIndex = 0;
      k.setAttribute("role", "button");
      k.addEventListener("click", () => goKpi(key));
      k.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); goKpi(key); } });
      box.appendChild(k);
    }
    sparkKpis();
  }
  function setKpis(stats) {
    for (const [key, , get] of KPIS) {
      const v = +get(stats) || 0;
      let st = kpiState.get(key);
      if (!st) {
        st = { shown: v, from: v, to: v, t0: 0 };
        kpiState.set(key, st);
        const box = $(`.kpi[data-key="${key}"] .v`);
        if (box) box.textContent = fmtK(v);
      }
      if (v !== st.to) {
        const box = $(`.kpi[data-key="${key}"]`);
        if (box && v > st.to && st.to > 0) {
          const d = box.querySelector(".delta");
          d.textContent = "+" + fmtK(v - st.to);
          box.classList.add("up", "flash");
          clearTimeout(st.timer);
          st.timer = setTimeout(() => box.classList.remove("up", "flash"), 2600);
        }
        st.from = st.shown;
        st.to = v;
        st.t0 = performance.now();
      }
    }
  }
  function tweenKpis(now) {
    for (const [key, st] of kpiState) {
      if (st.shown === st.to) continue;
      const s = Math.min(1, (now - st.t0) / 800);
      st.shown = s >= 1 ? st.to : st.from + (st.to - st.from) * ease(s);
      const v = $(`.kpi[data-key="${key}"] .v`);
      if (v) v.textContent = fmtK(st.shown);
    }
  }
  function sparkKpis() {
    if (S.history.length < 2) return;
    const recent = S.history.slice(-90);
    for (const [key, , , hkey, col] of KPIS) {
      const svg = $(`.kpi[data-key="${key}"] svg`);
      if (svg) Panels.spark(svg, recent.map((p) => +p[hkey] || 0), colorOf(col), 100, 14);
    }
  }

  function safely(what, f) {
    try { f(); } catch (err) { console.warn("[novalie] " + what, err); }
  }

  /* ---------- connection ---------- */

  function pace(ms) {
    return S.online === false ? Math.min(15000, ms * Math.pow(2, Math.min(S.fails || 1, 4))) : ms;
  }

  function online(ok) {
    if (S.erased) return;
    if (ok) {
      S.fails = 0;
      if (S.online !== true) {
        S.online = true;
        $("#offline").classList.add("hidden");
        $("#live").classList.remove("off");
        $("#live .lbl").textContent = t("live");
      }
      return;
    }
    S.fails++;
    if (S.fails >= 3 && S.online !== false) {
      S.online = false;
      $("#offline").classList.remove("hidden");
      $("#live").classList.add("off");
      $("#live .lbl").textContent = t("offline");
    }
  }

  /* ---------- what happens, as it happens ---------- */
  function handleEvents(evs, last) {
    if (last != null && last < S.lastEvent) { S.lastEvent = 0; S.firstEvents = true; }
    const fresh = (evs || []).filter((e) => e.id > S.lastEvent);
    if (!fresh.length) return;
    S.lastEvent = fresh[fresh.length - 1].id;
    const old = S.firstEvents;
    S.firstEvents = false;
    for (const e of fresh) safely("event " + e.k, () => {
      if (e.k === "try") { Panels.tryRow(e); return; }
      if (e.k === "reading") Panels.readingFrom(e.source);
      Panels.feed(e);
      Panels.discover(e, !old);
      if (old) return;
      Brain.effect(e);
      notify(e);
      talkNote(e);
      if (e.k === "read-any") soon("reading", 300);
      if (e.k === "born" || e.k === "meaning" || e.k === "linked" || e.k === "understood") soon("graph", 250);
      if (e.k === "understood") soon("worlds", 300);
    });
  }
  let bornNote = null;
  function notify(e) {
    const target = () => Panels.targetOf(e);
    if (e.k === "born") {
      const seen = String(e.s).includes("×"), now = Date.now();
      if (bornNote && now - bornNote.at < 2500 && bornNote.el.isConnected) {
        bornNote.more++;
        bornNote.el.querySelector("span").textContent = `${bornNote.first} · ${t("moreBorn", bornNote.more)}`;
        return;
      }
      Panels.toast("spark", seen ? C.seen : C.cycle, t(seen ? "bornSeen" : "bornIdea"), e.s, target);
      const box = $("#toasts");
      bornNote = { el: box.lastElementChild, at: now, more: 0, first: e.s };
    } else if (e.k === "meaning") {
      Panels.toast("key", C.word, t("learnedMeaning"), `${t("quoted", e.shown || e.word)} = ${e.s} · ${e.e} ${t("digits")}`, target);
    } else if (e.k === "read-any" && e.readable !== false) {
      if ((e.types || []).length) Panels.toast("spark", C.seen, t("newType"), e.types.join(" · "), target);
      else if (e.new_way) Panels.toast("key", C.gear, t("newWayT"), (e.chain || []).join(" → "));
    } else if (e.k === "pointed") {
      Panels.toast(e.ok ? "link" : "warn", e.ok ? C.accent : C.warn, evText(e));
    } else if (e.k === "trouble") {
      Panels.toast("warn", C.warn, t("trouble"), e.what);
    } else if (e.k === "spoke" && S.tab !== "talk") {
      Panels.toast("talk", C.accent, t("spokeT"), e.text, target);
    }
  }
  const timers = {};
  function soon(what, ms) {
    clearTimeout(timers[what]);
    timers[what] = setTimeout(() => (what === "graph" ? pollGraph(true) : what === "worlds" ? pollWorlds(true) : pollReading(true)), ms);
  }

  /* ---------- asking the model ---------- */
  async function pollLive() {
    if (S.erased) return;
    let live = null;
    try {
      live = await api.get("/live?since=" + S.lastEvent);
      online(true);
    } catch (e) { online(false); }
    if (live && live.world != null) {
      S.live = live;
      S.paused = !!live.paused;
      S.offline = !!live.offline;
      S.gentle = !!live.gentle;
      handleEvents(live.events, live.last);
      safely("now", () => { Panels.now(live); Brain.current = Panels.currentCells(); });
      $("#sps").textContent = fmtK(live.sps);
      $("#live .lbl").textContent = t(S.paused ? "paused" : "live");
      safely("think", () => {
        const ws = live.workshop || {};
        const tried = ((live.inventor_card || {}).tried || 0) + ((ws.inventor_card || {}).tried || 0);
        $("#thinkPill").classList.toggle("hidden", !(ws.pace || tried));
        $("#wsPace").textContent = fmtK(Math.round(ws.pace || ws.per_second || 0));
        $("#cardRate").textContent = fmtK(tried);
      });
      safely("since", () => Panels.since((live.self || {}).since));
    }
    setTimeout(pollLive, pace(document.hidden ? 3000 : 700));
  }
  let msgBusy = false;
  async function pollMsgs(once) {
    if (S.erased) return;
    if (!msgBusy) {
      msgBusy = true;
      try { await fetchMsgs(); } catch (e) {  }
      msgBusy = false;
    }
    if (!once) setTimeout(pollMsgs, pace(document.hidden ? 4000 : 1200));
  }
  async function fetchMsgs() {
      const r = await api.get("/poll?since=" + S.nextMsg);
      if (r.count != null && r.count < S.nextMsg) { S.nextMsg = 0; clear($("#msgs")); }
      else {
        for (const m of r.messages || []) {
          if (m.id != null && m.id < S.nextMsg) continue;
          safely("message", () => Panels.message(m, openName));
          if (m.id != null) S.nextMsg = m.id + 1;
          if (m.who !== "me" && !S.firstMsgs && S.tab !== "talk") S.unread++;
        }
        S.firstMsgs = false;
        Panels.chatEmpty();
        const b = $("#talkBadge");
        b.textContent = S.unread > 9 ? "9+" : String(S.unread);
        b.classList.toggle("hidden", !S.unread);
        if (r.inbox && r.inbox !== S.inbox) {
          S.inbox = r.inbox;
          $("#inboxPath").textContent = r.inbox;
          $("#inboxPath").title = r.inbox;
          if (S.tab === "guide") Panels.guide(S.inbox);
        }
      }
  }
  let graphBusy = false;
  async function pollGraph(once) {
    if (S.erased) return;
    if (!graphBusy) {
      graphBusy = true;
      try {
        const g = await api.get("/graph");
        if (g && g.nodes) {
          safely("network", () => Brain.update(g));
          const laws = Brain.lawTypes().join(",");
          if (laws !== lastLaws) { lastLaws = laws; safely("legend", () => Panels.legend()); }
          $("#emptyStage").classList.toggle("hidden", g.nodes.length > 0);
          S.stats = g.stats || {};
          safely("numbers", () => setKpis(S.stats));
          safely("chips", () => Panels.chips(chipCounts(), toggleType));
          safely("story", () => Panels.story(S.stats, S.stats.shapes || Brain.counts(), S.live && S.live.born));
          safely("names", () => Panels.wantNames(g.nodes.filter((n) => n.group === "cell" && (!n.label || n.label === n.symbol))
            .map((n) => ({ id: n.id, symbol: n.symbol, asked: n.asked || 0, w: n.w || 0, type: Brain.get(n.id) ? Brain.get(n.id).type : (n.shape === "seen" ? "seen" : "cycle") }))
            .sort((a, b) => b.asked - a.asked || b.w - a.w)
            .filter((n, i, all) => all.findIndex((m) => m.symbol === n.symbol) === i).slice(0, 8), openName));
          if (S.tab === "growth") safely("mind", () => { Panels.mind(S.stats.shapes || Brain.counts()); Panels.use(S.stats.use); });
        }
      } catch (e) {  }
      graphBusy = false;
    }
    if (!once) setTimeout(pollGraph, pace(document.hidden ? 8000 : 2500));
  }
  async function pollReading(once) {
    if (S.erased) return;
    try {
      const r = await api.get("/reading");
      if (r && "count" in r) safely("reading", () => Panels.reading(r));
    } catch (e) {  }
    if (!once) setTimeout(pollReading, pace(document.hidden ? 15000 : 6000));
  }
  async function pollWorlds(once) {
    if (S.erased) return;
    try {
      const w = await api.get("/worlds");
      if (Array.isArray(w)) safely("worlds", () => Panels.worlds(w));
    } catch (e) {  }
    if (!once) setTimeout(pollWorlds, pace(document.hidden ? 20000 : 8000));
  }
  async function pollKnowledge(once) {
    if (S.erased) return;
    if (S.tab === "growth" || once === true) {
      try {
        const k = await api.get("/knowledge");
        if (k && k.means) safely("knowledge", () => Panels.knowledge(k));
      } catch (e) {  }
    }
    if (once !== true) setTimeout(pollKnowledge, pace(8000));
  }
  let span = "2h";
  let dayHist = [], dayAt = 0;
  async function showGrowth(fresh) {
    if (span === "day") {
      if (fresh || Date.now() - dayAt > 55000) {
        try { dayHist = await api.get("/history?span=day"); dayAt = Date.now(); } catch (e) {  }
      }
      safely("growth", () => Panels.growth(dayHist, "day"));
    } else safely("growth", () => Panels.growth(S.history, "2h"));
    $("#histCsv").setAttribute("href", span === "day" ? "/history.csv?span=day" : "/history.csv");
  }
  for (const b of $$("#spanSel button")) b.addEventListener("click", () => {
    span = b.dataset.span;
    for (const o of $$("#spanSel button")) o.classList.toggle("on", o === b);
    showGrowth(true);
  });
  async function pollHistory() {
    if (S.erased) return;
    try {
      const h = await api.get("/history");
      if (Array.isArray(h)) {
        S.history = h;
        safely("sparklines", sparkKpis);
        if (S.tab === "growth") showGrowth();
      }
    } catch (e) {  }
    setTimeout(pollHistory, pace(10000));
  }

  /* ---------- the details of a cell ---------- */
  let inspTimer = null;
  let shownId = null;
  async function showCell(id, force) {
    clearTimeout(inspTimer);
    const box = $("#insp");
    if (!force) shownId = null;
    if (!id) { box.classList.remove("on"); return; }
    if (force) shownId = id;
    try {
      const info = await api.get("/cell?id=" + encodeURIComponent(id));
      if (Brain.selected !== id && shownId !== id) return;
      safely("details", () => Panels.inspector(info, { name: teach, unname: unteach, forget: forgetMeaning }));
      box.classList.add("on");
    } catch (e) {  }
    inspTimer = setTimeout(() => { if (Brain.selected === id && !box.contains(document.activeElement)) showCell(id); }, 5000);
  }
  Brain.on("select", showCell);

  const tip = $("#tip");
  Brain.on("hover", (n, sx, sy) => {
    if (!n) { tip.classList.remove("on"); return; }
    clear(tip);
    const tt = el("div", "tt");
    const sw = el("i");
    sw.style.background = C[n.type];
    tt.append(sw, el("span", null, t("t_" + n.type)), el("bdi", "muted", n.type === "word" ? n.label : n.symbol));
    tip.appendChild(tt);
    if (n.type !== "word" && n.label !== n.symbol) tip.appendChild(el("p", null, t("quoted", n.label)));
    let d = t("d_" + n.type).split(new RegExp("(?<=[.:—" + sep("semi").trim() + "])\\s"))[0];
    if (n.type === "seen" && n.origin) d = t("o_" + n.origin);
    tip.appendChild(el("p", null, d));
    const stage = $("#stage").getBoundingClientRect();
    const w = 300;
    let x = sx + 16, y = sy + 14;
    if (x + w > stage.width - 8) x = sx - w - 16;
    if (y + 110 > stage.height) y = sy - 110;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = Math.max(8, y) + "px";
    tip.classList.add("on");
  });

  /* ---------- teaching it words ---------- */
  async function teach(symbol, word) {
    try {
      const r = await api.post("/name", JSON.stringify({ symbol, word }), { "Content-Type": "application/json" });
      if (r.ok) { Panels.toast("check", C.ok, t("taughtToast", symbol, word)); soon("graph", 400); setTimeout(() => pollMsgs(true), 300); }
    } catch (e) {  }
  }
  Brain.on("teach", (symbol, word) => teach(symbol, word));
  async function forgetMeaning(symbol, word, shown) {
    try {
      const r = await api.post("/forget", JSON.stringify({ symbol, word }), { "Content-Type": "application/json" });
      const res = r.ok ? await r.json() : {};
      if (res.done) {
        Panels.toast("scissors", C.dim, t("forgotToast", shown || word, symbol));
        soon("graph", 300);
        if (Brain.selected || shownId) setTimeout(() => showCell(Brain.selected || shownId, !Brain.selected), 350);
      }
    } catch (e) {  }
  }
  async function unteach(symbol, word) {
    try {
      const r = await api.post("/unname", JSON.stringify({ symbol, word }), { "Content-Type": "application/json" });
      const res = r.ok ? await r.json() : {};
      if (res.done) {
        Panels.toast("close", C.dim, t("untaughtToast", symbol, word));
        soon("graph", 300);
        if (Brain.selected || shownId) setTimeout(() => showCell(Brain.selected || shownId, !Brain.selected), 350);
      }
    } catch (e) {  }
  }

  const pop = $("#namePop");
  let popSym = null;
  function openName(sym, anchor) {
    popSym = sym;
    $("#nameSym").textContent = sym;
    pop.classList.remove("hidden");
    const r = anchor.getBoundingClientRect();
    const w = 250;
    let x = dir() === "rtl" ? r.right - w : r.left;
    x = Math.max(8, Math.min(window.innerWidth - w - 8, x));
    let y = r.bottom + 8;
    if (y + 110 > window.innerHeight) y = r.top - 110;
    pop.style.left = x + "px";
    pop.style.top = y + "px";
    $("#nameIn").value = "";
    $("#nameIn").focus();
  }
  pop.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const w = $("#nameIn").value.trim();
    if (w && popSym) teach(popSym, w);
    pop.classList.add("hidden");
  });
  document.addEventListener("pointerdown", (ev) => { if (!pop.classList.contains("hidden") && !pop.contains(ev.target) && !ev.target.closest(".sym")) pop.classList.add("hidden"); });

  $("#compose").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const inp = $("#sayIn");
    const text = inp.value.trim();
    if (!text) return;
    inp.value = "";
    try { await api.post("/say", text, { "Content-Type": "text/plain;charset=utf-8" }); heardFromYou(text); } catch (e) { inp.value = text; }
    setTimeout(() => pollMsgs(true), 150);
  });

  /* ---------- in the talk, what it does with your words: it goes to read about one it does not know ---------- */
  const asked = new Map();
  const fold = (w) => String(w).normalize("NFD").replace(/[\u0300-\u036f\u064b-\u065f\u0670\u0640]/g, "").toLowerCase();
  function heardFromYou(text) {
    const now = Date.now();
    for (const tok of text.split(/\s+/)) if (tok && !/^https?:/.test(tok)) for (const w of tok.split(/\p{P}+/u)) if (w) asked.set(fold(w), now);
    for (const [w, at] of asked) if (now - at > 30 * 60000) asked.delete(w);
  }
  function talkNote(e) {
    if (e.k === "reading" && asked.has(fold(e.title))) {
      Panels.note(t("noteAsking", e.title));
    } else if (e.k === "read" && e.word && asked.has(fold(e.word))) {
      asked.delete(fold(e.word));
      Panels.note(e.title ? t("noteRead", e.title, (e.concepts || []).join(" ")) : t("noteNotFound", e.word));
    }
  }

  /* ---------- giving it files ---------- */
  async function give(file) {
    const big = file.size > 64e6;
    const name = file.name + (big ? " [0–64 MB]" : "");
    try {
      const r = await api.post("/give", big ? file.slice(0, 64e6) : file, { "X-Name": encodeURIComponent(name), "Content-Type": "application/octet-stream" });
      if (r.ok) Panels.toast("file", C.accent, t("given", name), fmtBytes(Math.min(file.size, 64e6)));
      else Panels.toast("warn", C.warn, r.status === 429 ? t("tooMany") : t("giveFail"), file.name);
    } catch (e) { Panels.toast("warn", C.warn, t("giveFail"), file.name); }
  }
  const drop = $("#drop");
  let dragDepth = 0;
  const hasFiles = (ev) => ev.dataTransfer && [...(ev.dataTransfer.types || [])].includes("Files");
  window.addEventListener("dragenter", (ev) => { if (!hasFiles(ev)) return; dragDepth++; drop.classList.remove("hidden"); });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) drop.classList.add("hidden"); });
  window.addEventListener("dragover", (ev) => { if (hasFiles(ev)) ev.preventDefault(); });
  window.addEventListener("drop", (ev) => {
    if (!hasFiles(ev)) return;
    ev.preventDefault();
    dragDepth = 0;
    drop.classList.add("hidden");
    [...ev.dataTransfer.files].slice(0, 20).forEach(give);
  });
  const dz = $("#dz");
  dz.addEventListener("click", () => $("#fileIn").click());
  dz.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); $("#fileIn").click(); } });
  $("#fileIn").addEventListener("change", (ev) => { [...ev.target.files].slice(0, 20).forEach(give); ev.target.value = ""; });
  $("#openFolder").addEventListener("click", () => api.post("/open-inbox", "").catch(() => {}));
  $("#copyPath").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(S.inbox);
      const s = $("#copyPath span");
      s.textContent = t("copied");
      setTimeout(() => (s.textContent = t("copy")), 1400);
    } catch (e) {  }
  });

  /* ---------- pausing it, and its reading of the internet ---------- */
  async function setSwitch(path, on) {
    try {
      await api.post(path, JSON.stringify({ on }), { "Content-Type": "application/json" });
      setTimeout(pollLiveOnce, 120);
    } catch (e) {  }
  }
  async function pollLiveOnce() {
    try {
      const live = await api.get("/live?since=" + S.lastEvent);
      if (live && live.world != null) { S.paused = !!live.paused; S.offline = !!live.offline; S.gentle = !!live.gentle; handleEvents(live.events, live.last); Panels.now(live); $("#live .lbl").textContent = t(S.paused ? "paused" : "live"); }
    } catch (e) {  }
  }
  /* ---------- the world it lives in: the real one, or one of the worlds folder ---------- */
  const worldSel = $("#worldSel");
  async function worldList() {
    try {
      const got = await api.get("/world-list");
      const have = [...worldSel.options].map((o) => o.value).join("|");
      const want = got.worlds.map((w) => w.name).join("|");
      if (have !== want) {
        worldSel.textContent = "";
        for (const w of got.worlds) {
          const o = document.createElement("option");
          o.value = w.name;
          o.textContent = w.title;
          o.title = w.about || "";
          worldSel.appendChild(o);
        }
      }
      if (document.activeElement !== worldSel) worldSel.value = got.now;
    } catch (e) {  }
  }
  worldSel.addEventListener("change", async () => {
    await api.post("/world", JSON.stringify({ name: worldSel.value }), { "Content-Type": "application/json" });
    setTimeout(worldList, 1500);
  });
  worldList();
  setInterval(worldList, 10000);

  $("#pauseBtn").addEventListener("click", () => setSwitch("/pause", !S.paused));
  $("#learnTog").addEventListener("click", () => setSwitch("/pause", !S.paused));
  $("#netTog").addEventListener("click", () => setSwitch("/offline", !S.offline));
  $("#paceTog").addEventListener("click", () => setSwitch("/gentle", !S.gentle));

  /* ---------- turning it off: it keeps everything it learned, and goes on from there at its next start ---------- */
  const quitModal = $("#quitModal");
  $("#quitBtn").addEventListener("click", () => { quitModal.classList.remove("hidden"); $("#quitYes").focus(); });
  $("#quitCancel").addEventListener("click", () => quitModal.classList.add("hidden"));
  quitModal.addEventListener("click", (ev) => { if (ev.target === quitModal) quitModal.classList.add("hidden"); });
  $("#quitYes").addEventListener("click", async () => {
    $("#quitYes span").textContent = t("quitting");
    S.erased = true;
    try { await api.post("/quit", ""); } catch (e) {  }
    quitModal.classList.add("hidden");
    $("#offline").classList.add("hidden");
    $("#quitted").classList.remove("hidden");
    $("#live").classList.add("off");
    setTimeout(function back() {
      fetch("/live?since=0", { cache: "no-store", headers: { "X-Novalie": "1" } })
        .then((r) => (r.ok ? location.reload() : setTimeout(back, 3000)))
        .catch(() => setTimeout(back, 3000));
    }, 4000);
  });

  /* ---------- the stop button: hold to erase ---------- */
  const modal = $("#stopModal"), hold = $("#holdBtn");
  let holdTimer = null;
  $("#stopBtn").addEventListener("click", () => { modal.classList.remove("hidden"); $("#stopCancel").focus(); });
  $("#stopCancel").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (ev) => { if (ev.target === modal) modal.classList.add("hidden"); });
  const startHold = () => {
    if (holdTimer) return;
    hold.classList.add("go");
    holdTimer = setTimeout(erase, 1600);
  };
  const stopHold = () => { clearTimeout(holdTimer); holdTimer = null; hold.classList.remove("go"); };
  hold.addEventListener("pointerdown", (ev) => {
    ev.preventDefault();
    startHold();
    try { hold.setPointerCapture(ev.pointerId); } catch (e) {  }
  });
  hold.addEventListener("pointerup", stopHold);
  hold.addEventListener("pointercancel", stopHold);
  hold.addEventListener("lostpointercapture", stopHold);
  hold.addEventListener("keydown", (ev) => { if ((ev.key === "Enter" || ev.key === " ") && !ev.repeat) { ev.preventDefault(); startHold(); } });
  hold.addEventListener("keyup", (ev) => { if (ev.key === "Enter" || ev.key === " ") stopHold(); });
  async function erase() {
    holdTimer = null;
    $("#holdBtn span").textContent = t("erasing");
    S.erased = true;
    try { localStorage.removeItem("novalie.welcomed"); } catch (e) {  }
    try { await api.post("/stop", ""); } catch (e) {  }
    modal.classList.add("hidden");
    $("#offline").classList.add("hidden");
    $("#erased").classList.remove("hidden");
    $("#live").classList.add("off");
    setTimeout(function back() {
      fetch("/live?since=0", { cache: "no-store", headers: { "X-Novalie": "1" } })
        .then((r) => (r.ok ? location.reload() : setTimeout(back, 3000)))
        .catch(() => setTimeout(back, 3000));
    }, 4000);
  }

  /* ---------- tabs, search, tools, language, theme ---------- */
  function setTab(name) {
    S.tab = name;
    try { localStorage.setItem("novalie.tab", name); } catch (e) {  }
    $$(".tab").forEach((b) => { const on = b.dataset.tab === name; b.classList.toggle("on", on); b.setAttribute("aria-selected", on); });
    $$(".pane").forEach((p) => p.classList.toggle("on", p.id === "p-" + name));
    if (name === "talk") {
      S.unread = 0;
      $("#talkBadge").classList.add("hidden");
      const m = $("#msgs");
      m.scrollTop = m.scrollHeight;
    }
    if (name === "growth") { showGrowth(); pollKnowledge(true); Panels.mind(S.stats.shapes || Brain.counts()); Panels.use(S.stats.use); }
    if (name === "guide") Panels.guide(S.inbox);
    if (name === "events") Panels.rhythm();
    if (name === "mind" && S.live) Panels.mindTab(S.live);
  }
  setInterval(() => { if (S.tab === "events") safely("rhythm", Panels.rhythm); }, 3000);
  $$(".tab").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));

  function buildFilters() {
    const box = $("#filters");
    clear(box);
    for (const f of ["all", "world", "words", "reading", "web", "brains", "speech", "cells", "trouble"]) {
      const b = el("button", "fbtn" + (f === "all" ? " on" : ""), t("f_" + f));
      b.type = "button";
      b.dataset.f = f;
      b.addEventListener("click", () => Panels.setFeedFilter(f));
      box.appendChild(b);
    }
    const p = el("button", "btn small", t("pause"));
    p.type = "button";
    p.addEventListener("click", () => {
      const paused = p.dataset.p !== "1";
      p.dataset.p = paused ? "1" : "0";
      p.textContent = t(paused ? "resume" : "pause");
      Panels.setFeedPaused(paused);
    });
    box.appendChild(p);
    if (!$("#feed").children.length) $("#feed").appendChild(el("div", "empty", t("noEvents")));
  }

  function chipCounts() {
    const c = Object.assign(Brain.counts(), (S.stats && S.stats.shapes) || {});
    if (S.stats && S.stats.words != null) c.word = S.stats.words;
    return c;
  }

  function toggleType(ty) {
    Brain.setFilter(ty, !Brain.filters[ty]);
    Panels.chips(chipCounts(), toggleType);
  }

  const q = $("#q"), results = $("#results");
  let sel = 0, found = [], remote = [], findTimer = null;
  function renderResults() {
    clear(results);
    if (!q.value.trim()) { results.classList.add("hidden"); return; }
    const drawn = Brain.search(q.value).map((n) => ({ id: n.id, type: n.type, drawn: true,
      label: n.type === "word" ? n.label : n.symbol + (n.label !== n.symbol ? " · " + n.label : "") }));
    const have = new Set(drawn.map((x) => x.id));
    found = drawn.concat(remote.filter((r) => !have.has(r.id)).map((r) => ({ id: r.id, type: r.kind, drawn: false,
      label: r.label + (r.word ? " · " + r.word : "") }))).slice(0, 14);
    if (!found.length) results.appendChild(el("div", "empty", t("noMatch")));
    found.forEach((n, i) => {
      const b = el("button", i === sel ? "sel" : "");
      b.type = "button";
      const sw = el("i", "sw");
      sw.style.background = C[n.type] || C.accent;
      b.append(sw, el("bdi", null, n.label), el("small", null, t("t_" + n.type) + (n.drawn ? "" : " · " + t("notDrawn"))));
      b.addEventListener("mousedown", (ev) => { ev.preventDefault(); pickResult(i); });
      results.appendChild(b);
    });
    results.classList.remove("hidden");
  }
  function pickResult(i) {
    const n = found[i];
    if (!n) return;
    if (n.drawn && Brain.get(n.id)) Brain.focus(n.id);
    else { Brain.select(null); showCell(n.id, true); }
    q.value = "";
    q.blur();
    results.classList.add("hidden");
  }
  q.addEventListener("input", () => {
    sel = 0;
    renderResults();
    Brain.highlight(q.value.trim() ? found.filter((n) => n.drawn).map((n) => n.id) : null);
    clearTimeout(findTimer);
    const asked = q.value.trim();
    findTimer = setTimeout(async () => {
      if (!asked) { remote = []; return; }
      try { remote = await api.get("/find?q=" + encodeURIComponent(asked)); } catch (e) { remote = []; }
      if (q.value.trim() === asked) renderResults();
    }, 220);
  });
  q.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowDown") { sel = Math.min(found.length - 1, sel + 1); renderResults(); ev.preventDefault(); }
    else if (ev.key === "ArrowUp") { sel = Math.max(0, sel - 1); renderResults(); ev.preventDefault(); }
    else if (ev.key === "Enter") { pickResult(sel); ev.preventDefault(); }
    else if (ev.key === "Escape") { q.value = ""; renderResults(); q.blur(); }
  });
  q.addEventListener("blur", () => setTimeout(() => { results.classList.add("hidden"); Brain.highlight(null); }, 120));

  $("#fitBtn").addEventListener("click", () => Brain.fit());
  $("#labelBtn").addEventListener("click", (ev) => { Brain.labels = !Brain.labels; ev.currentTarget.classList.toggle("on", Brain.labels); savePrefs(); });
  $("#motionBtn").addEventListener("click", (ev) => { Brain.motion = !Brain.motion; ev.currentTarget.classList.toggle("on", Brain.motion); motionIcon(); savePrefs(); });
  $("#solidBtn").classList.toggle("on", Brain.solid);
  $("#solidBtn").addEventListener("click", (ev) => { Brain.solid = !Brain.solid; ev.currentTarget.classList.toggle("on", Brain.solid); });
  $("#fullBtn").addEventListener("click", () => {
    const st = $("#stage");
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else (st.requestFullscreen ? st.requestFullscreen() : Promise.reject()).catch(() => {});
  });
  function motionIcon() { $("#motionBtn use").setAttribute("href", Brain.motion ? "#i-motion" : "#i-play"); }

  function networkPicture() {
    const src = Brain.picture(2);
    const out = document.createElement("canvas");
    out.width = src.width;
    out.height = src.height;
    const g = out.getContext("2d");
    const css = getComputedStyle(document.documentElement);
    const v = (name, d) => css.getPropertyValue(name).trim() || d;
    const W = out.width, H = out.height, k = W / Math.max(1, $("#brain").clientWidth);
    const font = getComputedStyle(document.body).fontFamily;
    g.fillStyle = v("--bg", "#05070f");
    g.fillRect(0, 0, W, H);
    for (const [x, y, c] of [[0.2, 0.1, v("--bg-glow-1", "transparent")], [0.85, 0.95, v("--bg-glow-2", "transparent")]]) {
      const grd = g.createRadialGradient(W * x, H * y, 0, W * x, H * y, Math.max(W, H) * 0.6);
      grd.addColorStop(0, c);
      grd.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = grd;
      g.fillRect(0, 0, W, H);
    }
    g.drawImage(src, 0, 0);
    const rtl = dir() === "rtl", pad = 18 * k, sgn = rtl ? -1 : 1;
    g.direction = dir();
    g.textAlign = rtl ? "right" : "left";
    g.textBaseline = "middle";
    const x0 = rtl ? W - pad : pad;
    g.font = `750 ${16 * k}px ${font}`;
    g.fillStyle = v("--text", "#e8ecf8");
    g.fillText(t("pageTitle"), x0, pad + 6 * k);
    const s = S.stats || {};
    g.font = `500 ${12 * k}px ${font}`;
    g.fillStyle = v("--muted", "#9aa3b8");
    const when = new Date().toLocaleString(locale(), { dateStyle: "medium", timeStyle: "short", numberingSystem: "latn" });
    g.fillText(`${when} · ${t("shotCaption", s)}`, x0, pad + 28 * k);
    let x = x0;
    const y = H - pad - 4 * k;
    g.font = `600 ${12 * k}px ${font}`;
    for (const [ty, n] of Object.entries(chipCounts())) {
      if (!n || !C[ty]) continue;
      const label = `${t("t_" + ty)} ${fmtN(n)}`;
      g.fillStyle = C[ty];
      g.beginPath();
      g.arc(x + sgn * 5 * k, y, 5 * k, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = v("--text", "#e8ecf8");
      g.fillText(label, x + sgn * 15 * k, y);
      x += sgn * (g.measureText(label).width + 34 * k);
    }
    return out;
  }
  $("#shotBtn").addEventListener("click", (ev) => {
    const btn = ev.currentTarget;
    if (btn.classList.contains("busy")) return;
    let pic;
    try { pic = networkPicture(); } catch (e) { console.warn("[novalie] picture", e); return; }
    btn.classList.add("busy");
    btn.setAttribute("aria-busy", "true");
    pic.toBlob((blob) => {
      btn.classList.remove("busy");
      btn.removeAttribute("aria-busy");
      if (!blob) return;
      const d = new Date(), z = (n) => String(n).padStart(2, "0");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `novalie-network-${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      Panels.toast("camera", C.ok, t("shotSaved"), a.download);
    }, "image/png");
  });
  $("#legendBtn").addEventListener("click", () => { $("#legend").classList.toggle("closed"); savePrefs(); });
  function savePrefs() {
    try { localStorage.setItem("novalie.prefs", JSON.stringify({ labels: Brain.labels, motion: Brain.motion, legend: !$("#legend").classList.contains("closed") })); } catch (e) {  }
  }
  try {
    const p = JSON.parse(localStorage.getItem("novalie.prefs") || "{}");
    if (p.labels === false) { Brain.labels = false; $("#labelBtn").classList.remove("on"); }
    if (p.motion === false) { Brain.motion = false; $("#motionBtn").classList.remove("on"); }
    if (p.legend === false || (p.legend == null && (innerHeight < 820 || innerWidth < 1300))) $("#legend").classList.add("closed");
  } catch (e) {  }
  motionIcon();

  function redrawAll() {
    readColors();
    setFont();
    buildKpis();
    Panels.legend();
    $("#chips").dataset.lang = "";
    Panels.chips(chipCounts(), toggleType);
    buildFilters();
    if (S.live) Panels.now(S.live);
    if (S.stats) safely("story", () => Panels.story(S.stats, S.stats.shapes || Brain.counts(), S.live && S.live.born));
    Panels.refeed();
    if (S.tab === "growth") showGrowth();
    if (S.tab === "guide") Panels.guide(S.inbox);
    Panels.paintDiscoveries();
    $("#live .lbl").textContent = t(S.online === false ? "offline" : S.paused ? "paused" : "live");
    if (Brain.selected) showCell(Brain.selected);
  }
  window.addEventListener("langchange", redrawAll);
  function themeIcon() { $("#themeBtn use").setAttribute("href", document.documentElement.dataset.theme === "light" ? "#i-moon" : "#i-sun"); }
  $("#themeBtn").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("novalie.theme", next); } catch (e) {  }
    themeIcon();
    redrawAll();
  });

  document.addEventListener("keydown", (ev) => {
    const typing = /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
    if (ev.key === "Escape") {
      if (!$("#welcome").classList.contains("hidden")) { $("#welOk").click(); return; }
      if (!modal.classList.contains("hidden")) { modal.classList.add("hidden"); stopHold(); return; }
      if (!pop.classList.contains("hidden")) { pop.classList.add("hidden"); return; }
      if (Brain.selected || $("#insp").classList.contains("on")) { Brain.select(null); return; }
    }
    if (typing || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "/") { ev.preventDefault(); q.focus(); }
    else if (ev.key === "f" || ev.key === "F") Brain.fit();
    else if (ev.key === "l" || ev.key === "L") $("#labelBtn").click();
    else if (ev.key === "m" || ev.key === "M") $("#motionBtn").click();
    else if (ev.key === "p" || ev.key === "P") $("#pauseBtn").click();
    else if (/^[1-6]$/.test(ev.key)) setTab(["now", "talk", "reading", "events", "growth", "guide"][+ev.key - 1]);
    else if (ev.key === "?") setTab("guide");
  });

  const strip = $("#stripCanvas");
  strip.addEventListener("pointermove", (ev) => {
    const hit = Panels.sensorAt(ev.offsetX);
    if (!hit) { tip.classList.remove("on"); strip.style.cursor = ""; return; }
    const [head, body] = Panels.sensorTip(hit.s, hit.i);
    clear(tip);
    const tt = el("div", "tt");
    const sw = el("i");
    sw.style.background = hit.s.known ? C.word : hit.s.sure ? C.ok : C.cycle;
    tt.append(sw, el("span", null, head));
    tip.append(tt, el("p", null, body));
    const st = $("#stage").getBoundingClientRect(), r = strip.getBoundingClientRect();
    tip.style.left = Math.max(8, Math.min(st.width - 300, r.left - st.left + hit.cx - 60)) + "px";
    tip.style.top = (r.top - st.top - 74) + "px";
    tip.classList.add("on");
    strip.style.cursor = Panels.sensorCell(hit.s) ? "pointer" : "";
  });
  strip.addEventListener("pointerleave", () => tip.classList.remove("on"));
  strip.addEventListener("click", (ev) => {
    const hit = Panels.sensorAt(ev.offsetX);
    const id = hit && Panels.sensorCell(hit.s);
    if (id) Brain.focus(id);
  });

  let frameErrors = 0;
  Brain.onFrame = (time) => {
    try {
      Panels.paintStrip(time);
      if (S.tab === "now") Panels.paintSensorCards(time);
      tweenKpis(performance.now());
    } catch (err) { if (frameErrors++ < 3) console.warn("[novalie] frame", err); }
  };
  new ResizeObserver(() => { Brain.bottom = $("#strip").offsetHeight + 24; }).observe($("#strip"));

  /* ---------- the first time: what is what ---------- */
  let welcomed = false;
  try { welcomed = localStorage.getItem("novalie.welcomed") === "1"; } catch (e) { welcomed = true; }
  if (!welcomed) $("#welcome").classList.remove("hidden");
  $("#welOk").addEventListener("click", () => {
    $("#welcome").classList.add("hidden");
    try { localStorage.setItem("novalie.welcomed", "1"); } catch (e) {  }
  });

  /* ---------- while you were away: what it did, in one note when you come back ---------- */
  let away = null;
  document.addEventListener("visibilitychange", async () => {
    if (document.hidden) { away = S.stats && S.stats.cells != null ? { at: Date.now(), stats: Object.assign({}, S.stats) } : null; return; }
    const was = away;
    away = null;
    if (!was || Date.now() - was.at < 60000 || S.erased) return;
    await pollGraph(true);
    const s = S.stats || {}, b = was.stats;
    const d = (k) => Math.max(0, (+s[k] || 0) - (+b[k] || 0));
    const parts = t("awayParts", { cells: d("cells") + d("seen"), words: d("words"), meanings: d("meanings"), articles: d("articles") });
    if (parts.length) Panels.toast("spark", C.accent, t("awayT", age(was.at / 1000)), parts.join(" · "));
  });

  /* ---------- the tab's title: what is waiting for you ---------- */
  function title() {
    const base = t("pageTitle");
    document.title = (S.unread ? `(${S.unread}) ` : "") + (S.paused ? "⏸ " : "") + base;
  }
  setInterval(title, 1500);

  $("#kpis").addEventListener("wheel", (ev) => {
    const k = ev.currentTarget;
    if (k.scrollWidth <= k.clientWidth || Math.abs(ev.deltaX) > Math.abs(ev.deltaY)) return;
    ev.preventDefault();
    k.scrollLeft += (dir() === "rtl" ? -1 : 1) * ev.deltaY;
  }, { passive: false });

  (() => {
    const handle = $("#resizer"), root = document.documentElement;
    const apply = (w) => {
      w = Math.max(300, Math.min(Math.round(innerWidth * 0.55), w));
      root.style.setProperty("--side", w + "px");
      return w;
    };
    try { const w = +localStorage.getItem("novalie.side"); if (w) apply(w); } catch (e) {  }
    let start = null;
    handle.addEventListener("pointerdown", (ev) => {
      start = { x: ev.clientX, w: $(".side").getBoundingClientRect().width };
      handle.classList.add("on");
      try { handle.setPointerCapture(ev.pointerId); } catch (e) {  }
      ev.preventDefault();
    });
    handle.addEventListener("pointermove", (ev) => {
      if (!start) return;
      const dx = ev.clientX - start.x;
      apply(start.w + dx);
    });
    const done = () => {
      if (!start) return;
      start = null;
      handle.classList.remove("on");
      try { localStorage.setItem("novalie.side", parseInt(getComputedStyle(root).getPropertyValue("--side"), 10)); } catch (e) {  }
    };
    handle.addEventListener("pointerup", done);
    handle.addEventListener("pointercancel", done);
    handle.addEventListener("dblclick", () => { root.style.removeProperty("--side"); try { localStorage.removeItem("novalie.side"); } catch (e) {  } });
  })();

  /* ---------- start: its words in the language chosen, then everything else ---------- */
  readColors();
  setFont();
  loadLang().catch((e) => console.warn("labels", e)).then(() => {
    applyLang();
    themeIcon();
    buildKpis();
    Panels.legend();
    Panels.chips(chipCounts(), toggleType);
    buildFilters();
    setTab(S.tab);
    Panels.chatEmpty();
    pollLive();
    pollMsgs();
    pollGraph();
    pollReading();
    pollHistory();
    pollWorlds();
    pollKnowledge();
  });
})();

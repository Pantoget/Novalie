/* Novalie's page: how its labels are filled. */
"use strict";

const fmtN = (n) => (n == null || isNaN(n)) ? "—" : Math.round(n).toLocaleString("en-US");
const fmtK = (n) => {
  if (n == null || isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
  if (a >= 1e4) return (n / 1e3).toFixed(a >= 1e5 ? 0 : 1) + "k";
  return fmtN(n);
};
const fmtBytes = (b) => b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : b >= 1024 ? Math.round(b / 1024) + " KB" : b + " B";
const pct = (x) => (x == null ? "—" : Math.round(x * 100) + "%");
const iso = (x) => "⁦" + x + "⁩";

let LANG = "en";
let PACK = { meta: {}, t: {}, nouns: {}, sep: {} };
let BACK = PACK;

function fill(tmpl, args) {
  if (typeof tmpl !== "string") return tmpl;
  const named = args.length && args[0] && typeof args[0] === "object" && !Array.isArray(args[0]) ? args[0] : null;
  return tmpl.replace(/\{([A-Za-z0-9_]+)\}/g, (m, k) => /^\d+$/.test(k) ? (args[+k] ?? "") : (named && k in named ? named[k] ?? "" : m));
}
function plural(forms, n) {
  const cat = new Intl.PluralRules(locale()).select(Math.round(Math.abs(+n || 0)));
  return forms[cat] ?? forms.other ?? forms.many ?? Object.values(forms)[0];
}
const isForms = (v) => v && typeof v === "object" && !Array.isArray(v) && ("other" in v || "one" in v);
function raw(key) { return PACK.t[key] ?? BACK.t[key]; }
const ACTIVE = new Set();
function t(key, ...args) {
  const f = TX[key];
  if (f && !ACTIVE.has(key)) {
    ACTIVE.add(key);
    try { return f(...args); } catch (e) { return key; } finally { ACTIVE.delete(key); }
  }
  let v = raw(key);
  if (v == null) return key;
  if (isForms(v)) v = plural(v, args[0]);
  return fill(v, args);
}
function has(key) { return key in TX || raw(key) != null; }
function noun(name, n) { const f = PACK.nouns[name] || BACK.nouns[name]; return f ? plural(f, n) : name; }
function sep(name) { return PACK.sep[name] ?? BACK.sep[name] ?? ""; }
function dir() { return PACK.meta.dir || "ltr"; }
function locale() { return PACK.meta.locale || "en-GB"; }
function evText(e) {
  const k = "ev." + e.k;
  try { return has(k) ? t(k, e) : e.k; } catch (err) { return e.k; }
}

async function getJSON(name) {
  const r = await fetch("/ui/" + name, { cache: "no-store" });
  if (!r.ok) throw new Error(name + ": " + r.status);
  return r.json();
}
async function loadLang() {
  PACK = BACK = await getJSON("text.en.json");
}
function applyLang() {
  document.documentElement.lang = LANG;
  document.documentElement.dir = dir();
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll("[data-t-title]").forEach((el) => { el.title = t(el.dataset.tTitle); el.setAttribute("aria-label", t(el.dataset.tTitle)); });
  document.querySelectorAll("[data-t-ph]").forEach((el) => { el.placeholder = t(el.dataset.tPh); });
  document.querySelectorAll("[data-t-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.tAria)); });
  document.title = t("pageTitle");
}
async function setLang() {
  await loadLang();
  applyLang();
  window.dispatchEvent(new CustomEvent("langchange"));
}

function condWords(c) {
  const [l, what, v] = c || [];
  const s = String(what || "");
  const thing = s === "act" ? t("cond.act", v) : t("cond.sense", { i: +s.slice(1) + 1, v });
  const when = !l ? t("cond.now") : t("cond.before", { l, acts: noun("act", l) });
  return t("cond.text", { thing, when });
}

function ruleWords(r) {
  r = r || {};
  if (r.mode === "count") return t("rule.count", Object.entries(r.does || {}).map(([w, e]) => t(e > 0 ? "rule.count.up" : "rule.count.down", w)).join(sep("list")));
  if (r.mode === "ways") return t("rule.ways", Object.entries(r.back || {}).filter(([a, b]) => a < b).map(([a, b]) => t("rule.ways.pair", { a, b })).join(sep("list")));
  if (r.mode === "chain") return t("rule.chain", { yes: r.yes, no: r.no });
  if (r.mode === "before") return t("rule.before", (r.order || []).join(t("rule.before.glue")));
  if (r.mode === "frame") return t("rule.frame", (r.frame || []).map(([n, d]) => t("rule.frame.slot", { n: n >= 0 ? n + 1 : n, d: d > 0 ? "+" + d : d })).join(sep("list")));
  const steps = r.then ? (r.then.then ? 3 : 2) : 1;
  const parts = [t("rule.steps", steps)];
  if (r.mode === "same") parts.push(t("rule.same", { yes: r.yes, no: r.no }));
  if ((r.stand || []).length) parts.push(t("rule.stand", r.stand.join(" ")));
  if ((r.turn || []).length) parts.push(t("rule.turn", r.turn.join(" ")));
  return parts.join(sep("semi"));
}

function brainWhy(w) {
  w = w || {};
  return has("brainWhy_" + w.code) ? t("brainWhy_" + w.code, Object.assign({}, w, { who: iso(w.who || "") })) : "";
}
const askHow = (h) => has("ask_" + h) ? t("ask_" + h) : h;
const askKind = (k) => has("askKind_" + k) ? t("askKind_" + k) : has("script_" + k) ? t("script_" + k) : k;

const TX = {
  "kindsList": (c) => ["cycle", "torus", "gear", "crt", "invented", "seen"].filter((k) => c[k]).map((k) => `${fmtN(c[k])} ${noun(k, c[k])}`).join(sep("list")) || "—",
  "savedAgo": (s) => t("savedAgo.t", s),
  "genPartT": (g, n) => t("genPartT.t", g, n),
  "genLawT": (law, n) => t("genLawT.t", law, n),
  "opsT": (s) => t("opsT.t", s),
  "mechT": (m, e, n) => t("mechT.t", m, e, n),
  "lawOne": (s, num) => t("lawOne.t", s, num),
  "lawSum": (law, total, proved) => t(proved ? "lawSum.proved" : "lawSum.seen", law, total),
  "realFor": (n) => t("realFor.t", n),
  "sense_second": (x) => t("sense_second.t", x),
  "sense_minute": (x) => t("sense_minute.t", x),
  "sense_hour": (x) => t("sense_hour.t", x),
  "sense_busy": (x) => t("sense_busy.t", x),
  "sense_load": (x) => t("sense_load.t", x),
  "sense_inventing": (x) => t("sense_inventing.t", x),
  "sense_workshop": (x) => t("sense_workshop.t", x),
  "sense_learned": (x) => t("sense_learned.t", x),
  "sense_reading": (x) => t("sense_reading.t", x),
  "sense_control": (x) => t("sense_control.t", x),
  "cycleOf": (n) => t("cycleOf.t", n),
  "sensorN": (n) => t("sensorN.t", n),
  "fromMem": (a, b) => t("fromMem.t", a, b),
  "taughtToast": (s, w) => t("taughtToast.t", s, w),
  "untaughtToast": (s, w) => t("untaughtToast.t", s, w),
  "inboxCount": (n, r) => t("inboxCount.t", n, r),
  "given": (n) => t("given.t", n),
  "needs": (n) => t("needs.text", n),
  "whyMeaning": (w, c, k, n, p, e) => t("whyMeaning.text", { w, c, k, n, times: noun("time", n), p, e }),
  "seenIn": (w, c, s) => t("seenIn.text", { w, c, s }),
  "lawGeneric": (code) => t("lawGeneric.text", code),
  "useInvent": (n, k) => t("useInvent.text", { n, k }),
  "useInventFirst": (n, k) => t("useInventFirst.text", { n, k }),
  "useRow": (tool, sure, r, w, nn, n) => t(sure ? "useRow.sure" : "useRow.unsure", { tool, r, w, nn, n }),
  "pr_said": (a, w, b, law, v) => t("pr_said.text", { a, w, b, law, verdict: t(v === "true" ? "pr_said.true" : v === "backwards" ? "pr_said.backwards" : "pr_said.unknown") }),
  "pr_reckon": (x, op, y, z, w, said) => t("pr_reckon.text", { x, op, y, z, w, tail: said == null ? "" : said === z ? t("pr_reckon.asSaid") : t("pr_reckon.notSaid", said) }),
  "pr_read_rule": (f, s, w, r, n, d, two) => t("pr_read_rule.text", { f, s, w, r, n, d, two: two ? t("pr_read_rule.twoSteps") : "" }),
  "pr_odds_law": (a, law, b, lag, d, q, p, dg) => t("pr_odds_law.text", { a, law, b, lag, d, q, p, dg }),
  "pr_analogy": (c, like, w) => t("pr_analogy.text", { c, like, w }),
  "dec_odds": (s, c, d, up, q, p, dg, n, known) => t("dec_odds.text", { s, cond: condWords(c), dir: t(up === false ? "dec_odds.lowers" : "dec_odds.raises"), d, q, p, dg, n: fmtN(n), known: known ? t("dec_odds.known") : "" }),
  "dec_odds_goal": (s, y) => t("dec_odds_goal.text", { s, goal: Array.isArray(y.goal) ? t("dec_odds_goal.range", { lo: y.goal[0], hi: y.goal[y.goal.length - 1] }) : y.goal, H: y.H }),
  "dec_thing": (name, w) => t("dec_thing.text", { name, senses: (w.senses || []).join(sep("and")) }),
  "dec_wish": (s, w) => t(w.code === "flees" ? "dec_wish.flees" : "dec_wish.seeks", { s, what: w.what }),
  "readRuleRow": (f, r) => t("readRuleRow.text", { f, rule: ruleWords(r.rule), right: r.right, of: r.of, digits: r.digits }),
  "dec_reading_rule": (f, r) => t("dec_reading_rule.text", { f, rule: ruleWords(r.rule), right: r.right, of: r.of, chance: r.chance, digits: r.digits }),
  "framesHow": (f) => t("framesHow.text", { k: f.k, n: f.n, digits: f.digits }),
  "dec_numberword": (w, r) => t("dec_numberword.text", { w, value: r.value, how: r.from === "counting" ? t("dec_numberword.counted") : t("dec_numberword.heard", { k: r.k, n: r.n }), digits: r.digits }),
  "dec_frames": (r) => t("dec_frames.text", { k: r.k, n: r.n, digits: r.digits }),
  "dec_opword": (w, r) => t("dec_opword.text", { w, op: t("op_" + r.op), k: r.k, n: r.n, p: r.p, digits: r.digits }),
  "relWordRow": (r) => t(r.way === "<" ? "relWordRow.back" : "relWordRow.same", { word: r.word, law: t("law_" + r.kind), digits: r.digits }),
  "dec_relword": (w, r) => t(r.way === "<" ? "dec_relword.back" : "dec_relword.same", { word: w, law: t("law_" + r.kind), k: r.k, n: r.n, p: r.p, digits: r.digits }),
  "dec_grain": (s, g, lv, n) => t("dec_grain.text", s, g, lv, fmtN(n)),
  "dec_lawless": (s, lift, rate, rows) => t("dec_lawless.text", s, lift, rate, fmtN(rows)),
  "dec_odds_revised": (s, c, after, came) => t("dec_odds_revised.text", s, condWords(c), fmtN(after), fmtN(came)),
  "oddsWhat": (v, dw) => t("oddsWhat.text", v, dw),
  "oddsSense": (s) => t("oddsSense.text", s),
  "oddsLawT": (w) => t(w.up === false ? "oddsLawT.down" : "oddsLawT.up", { cond: condWords([w.lag, w.attr, w.value]), d: w.d, q: w.q, p: w.p, base: w.base, digits: w.digits, tests: fmtN(w.tests), came: fmtN(w.came), after: fmtN(w.after) }),
  "oddsUnless": (c, q) => t("oddsUnless.text", condWords(c), q),
  "oddsEspecially": (c, q) => t("oddsEspecially.text", condWords(c), q),
  "oddsVerdictT": (v) => t("oddsVerdictT.text", { rows: fmtN(v.rows), of: fmtN(v.of), lift: v.lift, rate: v.rate }),
  "oddsLinkT": (x) => t(x.code === "cause" ? "oddsLinkT.cause" : "oddsLinkT.fore", { a: x.a, b: x.b, lag: x.lag, act: noun("act", x.lag), d: x.d, q: x.q, p: x.p }),
  "dec_read_way": (n, v, k) => t("dec_read_way.text", n, v, k),
  "readWayDid": (n, m) => t("readWayDid.text", n, m),
  "useSubgoals": (m, r) => t("useSubgoals.text", m, r),
  "useGoals": (m, r, now) => t(now ? "useGoals.now" : "useGoals.text", m, r, now),
  "usePending": (n) => t("usePending.text", n),
  "pr_foresee": (s, n, v, c) => t(c ? "pr_foresee.cell" : "pr_foresee.text", s, n, v == null ? t("pr_foresee.none") : v, c),
  "pr_law": (a, l, b, n) => t("pr_law.text", a, l, b, n),
  "pr_through": (p) => t("pr_through.text", p),
  "pr_kindof_": (a, b) => t("pr_kindof_.text", a, b),
  "pr_sense": (c, s) => t("pr_sense.text", c, s),
  "pr_unknown": (w) => t(w ? "pr_unknown.some" : "pr_unknown.none", w),
  "pr_nochain": (a, b) => t("pr.nochain", a, b),
  "pr_alone": (c) => t("pr.alone", c),
  "dec_answer": (a, q, n) => t("dec.answer", a, q, n),
  "dec_goal": (w, k, c, e) => t(has("dec.goal." + k) ? "dec.goal." + k : "dec.goal.meaning", w, c, e),
  "dec_goal_step": (w, i, n, g) => t("dec.goal_step", w, i, n, g),
  "dec_replan": (w, n) => t("dec.replan", w, n),
  "dec_recognize": (d, f, n) => t("dec.recognize", d, t(has("dec.recognize.from." + f) ? "dec.recognize.from." + f : "dec.recognize.from.lived"), n),
  "usePlans": (m, r, x, d) => t("use.plans", m, r, x, d),
  "useGenerals": (n) => t("use.generals", n),
  "goalHead": (d, n, s, p) => t("goal.head", d, n, s, p),
  "goalRow": (j, sure, tool, known, plan) => t("goal.row", j, t(sure ? "goal.row.closed" : "goal.row.open"), tool, known, plan ? t("goal.row.plan") : ""),
  "goalOf": (a, b) => t("goal.of", a, b),
  "goalMapped": (a) => t("goal.mapped", a),
  "dec_ways": (s) => t("dec.ways", s),
  "dec_pursue": (js, how) => t("dec.pursue", js, how),
  "dec_invent": (js, s, way) => t("dec.invent", js, s, way),
  "dec_plan": (g, n, seen, m) => t("dec.plan", g, n, seen, m),
  "dec_adapt": (m, s) => t("dec.adapt", m, s),
  "dec_experiment": (js, b, n) => t("dec.experiment", js, b, n),
  "waysHow": (n) => t("ways.how", n),
  "wayDid": (p, n, ok) => t("way.did", p, n, ok == null ? "" : t("way.did.ok", ok)),
  "grammarClasses": (sc, cl) => t("grammarClasses.t", sc, cl),
  "grammarLaw": (forms, by, e, n) => t("grammarLaw.t", forms, by, e, noun("digit", e), n, noun("source", n)),
  "nat_made": (x) => t("nat_made.t", x),
  "lawRel": (part, l, r) => t("lawRel.t", part, l, r),
  "lawPart": (name, a, b) => t("lawPart.t", name, a, b),
  "madeT": (name, n, things, group, commute) => t("madeT.t", name, n, noun("state", n), things, t(group ? "madeT.undo" : "madeT.noUndo"), t(commute ? "madeT.anyOrder" : "madeT.order")),
  "syncT": (w) => t("syncT.t", w),
  "oldT": (x) => t("oldT.t", x),
  "generalT": (w, c, n, s) => t("generalT.t", w, c, n, s),
  "topicalT": (w, c, n, s) => t("topicalT.t", w, c, n, s),
  "usefulT": (w, f) => t("usefulT.t", w, f),
  "gearHow": (a, b, n) => t("gearHow.t", a, b, n, noun("step", a), noun("state", n)),
  "crtHow": (a, b, n) => t("crtHow.t", a, b, n, noun("step", n)),
  "torusHow": (c, n) => t("torusHow.t", c, n, noun("state", n)),
  "seenHow2": (a, b) => t("seenHow2.t", a, b),
  "seenHow1": (a) => t("seenHow1.t", a, noun("step", a)),
  "moreBorn": (n) => t("moreBorn.t", n),
  "forgetBtn": (s) => t("forgetBtn.t", s),
  "forgotToast": (w, s) => t("forgotToast.t", w, s),
  "spokeOf": (n) => t("spokeOf.t", n, noun("time", n)),
  "noteRead": (title, cs) => t(cs ? "noteRead.found" : "noteRead.none", title, cs),
  "noteNotFound": (w) => t("noteNotFound.t", w),
  "dMeaning": (w, s) => t("dMeaning.text", w, s),
  "dBorn": (s) => t("dBorn.text", s),
  "dSeen": (s) => t("dSeen.text", s),
  "dType": (x) => t("dType.text", x),
  "dWay": (x) => t("dWay.text", x),
  "awayT": (a) => t("awayT.text", a),
  "movesT": (m, d) => t("movesT.text", m, d),
  "times": (n) => noun("time", n),
  "ev.world": (e) => e.real ? t("ev.world.real", e) : t("ev.world.sim", { world: e.world, sensors: e.sensors, size: fmtN(e.size) }),
  "ev.understood": (e) => t(e.real ? "ev.understood.real" : "ev.understood.sim",
  { sensor: e.sensor, world: e.world, steps: fmtN(e.steps), accuracy: e.accuracy, symbols: (e.symbols || []).join(" ") }),
  "ev.born": (e) => t("ev.born.text", e),
  "ev.recognized": (e) => e.how === "length"
  ? t(e.known === "read" ? "ev.recognized.length.read" : e.known === "general" ? "ev.recognized.length.general" : "ev.recognized.length.world", e)
  : t("ev.recognized.memory", e),
  "ev.goal": (e) => t(e.what === "asked" ? "ev.goal.asked" : "ev.goal.prove", e),
  "ev.goal_reached": (e) => t("ev.goal_reached.text", { word: e.word, means: (e.means || []).map((x) => t("isoItem", x)).join(" ") }),
  "ev.goal_dropped": (e) => t("ev.goal_dropped.text", e),
  "ev.answered": (e) => t("ev.answered.text", e),
  "ev.foretold": (e) => t(e.right ? "ev.foretold.right" : "ev.foretold.wrong", e),
  "ev.invented": (e) => e.new ? t("ev.invented.new", { s: e.s, evidence: e.evidence, tried: fmtN(e.tried) }) : t("ev.invented.library", e),
  "ev.inventing": (e) => t(e.real ? "ev.inventing.real" : "ev.inventing.sim", e),
  "ev.invention_failed": (e) => t("ev.invention_failed.text", e),
  "ev.surprise": (e) => t(e.tool === "self" ? "ev.surprise.self" : e.tool === "machine" ? "ev.surprise.machine" : e.tool === "kind" ? "ev.surprise.kind" : "ev.surprise.counts", e),
  "ev.plan": (e) => t("ev.plan.text", e),
  "ev.plan_dropped": (e) => t("ev.plan_dropped", e.s),
  "ev.general": (e) => t("ev.general", e.s, (e.members || []).map(iso).join(" ")),
  "ev.circuit": (e) => t("ev.circuit", (e.members || []).map(iso).join(" " + sep("arrow") + " ")),
  "ev.new_way": (e) => { const k = "ev.new_way.way." + e.way; return t("ev.new_way", has(k) ? t(k) : e.way, e.value, e.best); },
  "ev.grammar": (e) => { const k = "ev.grammar.script." + e.script; return t("ev.grammar", has(k) ? t(k) : e.script, (e.classes || []).map(([a, b]) => (a === b ? a : t("ev.grammar.range", a, b))).join(t("ev.grammar.bar")), e.laws); },
  "ev.law": (e) => { const k = "ev.law.code." + e.code; return t("ev.law", e.a, has(k) ? t(k) : e.code, e.b); },
  "ev.odds": (e) => t("ev.odds", e.sensor, condWords(e.cond), t(e.up === false ? "ev.odds.lowers" : "ev.odds.raises"), e.d, e.q, e.p, e.digits, fmtN(e.tests)),
  "ev.thing": (e) => t("ev.thing", e.s),
  "ev.numberword": (e) => t("ev.numberword", e.shown || e.word, e.value, e.digits),
  "ev.opword": (e) => t("ev.opword", e.shown || e.word, t("op_" + e.op), e.digits),
  "ev.relword": (e) => t(e.way === "<" ? "ev.relword.reversed" : "ev.relword", e.shown || e.word, t("law_" + e.link), e.digits),
  "ev.grain": (e) => t("ev.grain", e.grain, e.sensor, e.levels),
  "ev.lawless": (e) => t("ev.lawless", e.sensor, fmtN(e.rows), e.rate),
  "ev.odds_revised": (e) => t("ev.odds_revised", e.sensor, condWords(e.cond), fmtN(e.came), fmtN(e.after)),
  "ev.heard": (e) => t("ev.heard", (e.words || []).join(" ")),
  "ev.spoke": (e) => t("ev.spoke", e.text),
  "ev.linked": (e) => t("ev.linked", e.sa || e.a, e.sb || e.b, e.e),
  "ev.read": (e) => e.source ? t("ev.read.source", e.title || e.word, e.source) : t("ev.read", e.title || e.word),
  "ev.reading": (e) => t(e.source ? "ev.reading.src" : "ev.reading.title", e.title, e.source),
  "ev.read-any": (e) => e.readable === false ? t("ev.read-any.none", e.source)
  : t(e.found ? "ev.read-any.found" : "ev.read-any.opened", iso(e.source), (e.chain || []).map(iso).join(" " + sep("arrow") + " "), (e.found || []).join(" ")),
  "ev.connected": (e) => t("ev.connected.site", e.site),
  "ev.disconnected": (e) => { const n = (e.sites || []).length; return t("ev.disconnected.round", e.round, n, noun("site", n), e.pages, noun("page", e.pages)); },
  "ev.pruned": (e) => t("ev.pruned.n", e.n),
  "ev.given": (e) => t("ev.given.file", e.name, fmtBytes(e.size)),
  "ev.try": (e) => t("ev.try.chain", (e.chain || []).map(iso).join(" " + sep("arrow") + " ")),
  "ev.paused": (e) => t(e.on ? "ev.paused.on" : "ev.paused.off"),
  "ev.pointed": (e) => t(e.ok ? "ev.pointed.ok" : "ev.pointed.no", e.url),
  "ev.offline": (e) => t(e.on ? "ev.offline.on" : "ev.offline.off"),
  "ev.unnamed": (e) => t("ev.unnamed.word", e.word, e.s),
  "ev.forgot": (e) => t("ev.forgot.word", e.shown || e.word, e.s),
  "ev.gentle": (e) => t(e.on ? "ev.gentle.on" : "ev.gentle.off"),
  "evg.recognized": (xs) => t("evg.recognized.n", xs.length, xs.join(sep("list"))),
  "evg.read": (xs) => t("evg.read.n", xs.length, xs.slice(0, 5).map((x) => t("quoted", x)).join(sep("list")), xs.length > 5 ? t("ellipsis") : ""),
  "evg.connected": (xs) => t("evg.connected.n", xs.length, xs.join(sep("list"))),
  "evg.born": (xs) => t("evg.born.n", xs.length, xs.join(" ")),
  "evg.curious": (xs) => t("evg.curious.list", xs.map((x) => t("quoted", x)).join(sep("list"))),
  "evg.linked": (xs) => t("evg.linked.n", xs.length, xs.slice(0, 4).join(sep("list")), xs.length > 4 ? t("ellipsis") : ""),
  "ev.brain_made": (e) => t("ev.brain_made", { name: iso(e.name), why: brainWhy(e.why), living: e.living }),
  "ev.brain_gone": (e) => t("ev.brain_gone", { name: iso(e.name), why: brainWhy(e.why), living: e.living }),
  "ev.way_met": (e) => t("ev.way_met", { site: iso(e.site), how: askHow(e.how) }),
  "ev.way_trusted": (e) => t("ev.way_trusted", { site: iso(e.site), how: askHow(e.how), kind: askKind(e.words), answered: fmtN(e.answered), asked: fmtN(e.asked) }),
  "ev.way_dropped": (e) => t("ev.way_dropped", { site: iso(e.site), how: askHow(e.how), asked: fmtN(e.asked) }),
  "ev.concept": (e) => t("ev.concept", { sensor: e.sensor, classes: (e.classes || []).length, tells: e.tells, digits: e.digits }),
  "ev.made": (e) => t("ev.made", { sensor: e.sensor, parts: (e.parts || []).map((p) => iso(Array.isArray(p) ? p[0] : p)).join(sep("list")), digits: e.digits }),
  "ev.made_gone": (e) => t("ev.made_gone", { sensor: e.sensor, parts: (e.parts || []).map((p) => iso(Array.isArray(p) ? p[0] : p)).join(sep("list")) }),
  "ev.moment": (e) => t("ev.moment", { sensor: e.sensor, cond: Object.entries(e.cond || {}).map(([k, v]) => iso(k + " = " + v)).join(sep("list")), d: e.d, proof: e.proof }),
  "ev.odds_drift": (e) => t("ev.odds_drift", { sensor: e.sensor, cond: condWords(e.cond), laws: Array.isArray(e.laws) ? e.laws.length : e.laws }),
  "dec_way": (d) => { const c = d.choice, y = d.why || {};
    if (d.what === "brain_made" || d.what === "brain_gone") return t("dec_" + d.what, { name: iso(c), why: brainWhy(y), living: (y.living || []).map(iso).join(sep("list")) });
    if (d.what === "way_trusted") return t("dec_way_trusted", { site: iso(c), how: askHow(y.kind), kind: askKind(y.words), answered: fmtN(y.answered), asked: fmtN(y.asked), digits: y.digits });
    return t("dec_way_dropped", { site: iso(c), how: askHow(y.kind), asked: fmtN(y.asked), chance: y.chance }); },
  "ev.trouble": (e) => t(has("ev.trouble." + e.where) ? "ev.trouble." + e.where : "ev.trouble.reading", e.what),
  "story": (v) => [t("story.age", v.age), v.worlds, t("story.worlds", noun("sense", v.n.worlds)), v.cells, t("story.cells", noun("cell", v.n.cells)), v.kinds,
    t("story.kinds"), v.articles, t("story.articles", noun("article", v.n.articles)), v.anything, t("story.anything", noun("thing", v.n.anything)),
    v.words, t("story.words", noun("word", v.n.words)), v.meanings, t("story.meanings", noun("meaning", v.n.meanings)), v.assoc,
    t("story.assoc", noun("link", v.n.assoc)), v.types, t("story.types", noun("type", v.n.types))],
  "shotCaption": (s) => t("shotCaption.t", fmtN((s.cells || 0) + (s.seen || 0)), fmtN(s.words || 0), fmtN(s.meanings || 0), fmtN(s.senses_known || 0)),
  "awayParts": (d) => [
    d.cells && t("awayParts.cells", fmtN(d.cells), noun("cell", d.cells)),
    d.words && t("awayParts.words", fmtN(d.words), noun("word", d.words)),
    d.meanings && t("awayParts.meanings", fmtN(d.meanings), noun("meaning", d.meanings)),
    d.articles && t("awayParts.articles", fmtN(d.articles), noun("article", d.articles)),
  ].filter(Boolean),
  "ev.frames": (e) => t("ev.frames", e.got ?? e.k, e.n, e.digits),
  "ev.curious": (e) => e.s != null ? t("ev.curious", e.shown || e.word, e.s) : t("ev.curious.word", e.shown || e.word || (e.titles || [])[0] || ""),
  "ev.meaning": (e) => t(e.council ? "ev.meaning.council" : "ev.meaning", e.shown || e.word, e.s, e.e),
};

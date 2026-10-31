/* Novalie's page: its network, alive. */
"use strict";

const Brain = (() => {
  const cv = document.getElementById("brain");
  let ctx = cv.getContext("2d");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let W = 1, H = 1, dpr = 1;
  const nodes = new Map();
  let edges = [], visEdges = [], adj = new Map(), pair = new Map(), wmax = {};
  const pulses = [], ripples = [], floats = [], bubbles = [];
  const view = { x: 0, y: 0, k: 0.8, tx: 0, ty: 0, tk: 0.8, auto: true };
  const S = { hover: null, sel: null, labels: true, motion: !reduce, alpha: 1, t: 0, R: { idea: 120, seen: 230, word: 340, ni: 0, ns: 0, nw: 0 }, ambientAt: 0, lastFit: 0, bottom: 104, solid: true, solids: 0 };
  try { S.solid = localStorage.getItem("novalie.solid") !== "0"; } catch (e) {  }
  const filters = {};
  TYPES.forEach((k) => (filters[k] = true));
  LINKS.forEach((k) => (filters[k] = true));
  try { Object.assign(filters, JSON.parse(localStorage.getItem("novalie.filters") || "{}")); } catch (e) {  }
  const on = { select: [], hover: [], teach: [] };
  let dragNode = null, panStart = null, downAt = null, pinch = null, turnStart = null;
  const pointers = new Map();
  const widths = new Map();

  const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
  const isIdea = (type) => type === "cycle" || type === "torus" || type === "gear" || type === "crt" || type === "invented" || type === "circuit";
  const visible = (n) => filters[n.type];
  const backOut = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

  function resize() {
    const r = cv.getBoundingClientRect();
    dpr = Math.min(2, window.devicePixelRatio || 1);
    W = Math.max(1, r.width);
    H = Math.max(1, r.height);
    cv.width = Math.round(W * dpr);
    cv.height = Math.round(H * dpr);
  }
  new ResizeObserver(resize).observe(cv);
  resize();

  const toScreen = (x, y) => [W / 2 + (x - view.x) * view.k, H / 2 + (y - view.y) * view.k];
  const toWorld = (sx, sy) => [view.x + (sx - W / 2) / view.k, view.y + (sy - H / 2) / view.k];
  const toWorldT = (sx, sy) => [view.tx + (sx - W / 2) / view.tk, view.ty + (sy - H / 2) / view.tk];

  /* ---------- its space: every cell has a place in three dimensions ----------
     X, Y, Z are where a cell is; x, y where it falls on the screen's plane through a camera that turns
     around the middle (yaw, pitch) with perspective. Drag the empty space to turn it; it turns slowly
     by itself while nobody touches it. Nearer cells are larger and brighter. */
  const cam = { yaw: 0.6, pitch: -0.32, f: 900, spin: 0.05 };
  let cYaw = Math.cos(cam.yaw), sYaw = Math.sin(cam.yaw), cPit = Math.cos(cam.pitch), sPit = Math.sin(cam.pitch);
  function turn(dyaw, dpitch) {
    cam.yaw += dyaw;
    cam.pitch = Math.max(-1.45, Math.min(1.45, cam.pitch + dpitch));
    cYaw = Math.cos(cam.yaw); sYaw = Math.sin(cam.yaw); cPit = Math.cos(cam.pitch); sPit = Math.sin(cam.pitch);
  }
  function project(n) {
    const x1 = n.X * cYaw + n.Z * sYaw, z1 = -n.X * sYaw + n.Z * cYaw;
    const y1 = n.Y * cPit - z1 * sPit, z2 = n.Y * sPit + z1 * cPit;
    const p = cam.f / Math.max(80, cam.f + z2);
    n.x = x1 * p; n.y = y1 * p; n.ps = p; n.pz = z2;
  }
  function unproject(n, wx, wy) {
    const p = n.ps || 1, x1 = wx / p, y1 = wy / p, z2 = n.pz || 0;
    n.Y = y1 * cPit + z2 * sPit;
    const z1 = -y1 * sPit + z2 * cPit;
    n.X = x1 * cYaw - z1 * sYaw;
    n.Z = x1 * sYaw + z1 * cYaw;
  }
  const depthLight = (n) => Math.max(0.35, Math.min(1, 0.62 + 0.38 * ((n.ps || 1) - 0.82) / 0.36));
  const sphere = (h, R) => {
    const u = ((h % 10007) / 10007) * 2 - 1, a = (((h >>> 7) % 9973) / 9973) * TAU, s = Math.sqrt(1 - u * u);
    return [R * s * Math.cos(a), R * u, R * s * Math.sin(a)];
  };

  function targetR(n) {
    if (n.type === "word") return Math.min(13, 4.6 + 2.3 * Math.log2(1 + Math.max(0, (n.w || 1) - 1))) + (n.means ? 1.6 : 0);
    if (n.type === "seen") return Math.min(30, 12 + 5 * Math.log10(1 + (n.n || n.w || 1)));
    return Math.min(40, 13 + 6.2 * Math.log10(1 + (n.n || n.w || 1)));
  }

  function orbits() {
    let ni = 0, ns = 0, nw = 0;
    for (const n of nodes.values()) {
      if (!visible(n) || n.gone) continue;
      if (isIdea(n.type)) ni++; else if (n.type === "seen") ns++; else nw++;
    }
    const idea = 60 + 34 * Math.sqrt(ni);
    const seen = idea + 70 + 14 * Math.sqrt(ns);
    const word = (ns ? seen : idea) + 100 + 10 * Math.sqrt(nw);
    S.R = { idea, seen, word, ni, ns, nw };
  }

  function lawTypes() {
    const out = new Set();
    for (const e of edges) if (!LINKS.includes(e.t)) out.add(e.t);
    return [...out].sort();
  }

  function rebuild() {
    adj = new Map();
    pair = new Map();
    visEdges = [];
    for (const e of edges) {
      if (!adj.has(e.a.id)) adj.set(e.a.id, new Set());
      if (!adj.has(e.b.id)) adj.set(e.b.id, new Set());
      adj.get(e.a.id).add(e.b.id);
      adj.get(e.b.id).add(e.a.id);
      pair.set(e.a.id + "|" + e.b.id, e);
      pair.set(e.b.id + "|" + e.a.id, e);
      if ((filters[e.t] ?? true) && visible(e.a) && visible(e.b)) visEdges.push(e);
    }
  }

  function place(n) {
    const nb = [...(adj.get(n.id) || [])].map((id) => nodes.get(id)).find((m) => m && !m.isNew && (m.X || m.Y || m.Z));
    if (nb) {
      const [dx, dy, dz] = sphere(hash(n.id + "near"), nb.r + n.tr + 28);
      n.X = nb.X + dx; n.Y = nb.Y + dy; n.Z = nb.Z + dz;
    } else {
      const R = isIdea(n.type) ? S.R.idea * (0.25 + 0.6 * ((hash(n.id + "r") % 1000) / 1000))
        : n.type === "seen" ? S.R.seen : S.R.word;
      [n.X, n.Y, n.Z] = sphere(hash(n.id), R);
    }
    project(n);
  }

  function update(g) {
    const t = S.t;
    const seen = new Set();
    let added = 0;
    for (const raw of g.nodes || []) {
      seen.add(raw.id);
      let n = nodes.get(raw.id);
      if (!n) {
        n = { id: raw.id, x: 0, y: 0, X: 0, Y: 0, Z: 0, vx: 0, vy: 0, vz: 0, ps: 1, pz: 0, r: 0.5, born: t, boost: 0.7, act: 0, tick: 0, phase: (hash(raw.id) % 1000) / 1000, isNew: true };
        nodes.set(raw.id, n);
        added++;
      }
      n.gone = null;
      n.type = typeOf(raw);
      n.label = String(raw.label ?? "");
      n.symbol = String(raw.symbol || (raw.group === "word" ? "" : raw.id.slice(2)));
      n.group = raw.group;
      n.w = +raw.w || 1;
      n.n = raw.n;
      n.tact = +raw.act || 0;
      n.cycles = raw.cycles || [];
      n.T = raw.T || null;
      n.origin = raw.origin || "";
      n.means = !!raw.means;
      n.nature = raw.nature || "";
      if (raw.unit && typeof raw.unit === "string" && /^[A-Za-z0-9+/=]+$/.test(raw.unit)) {
        if (n.unitKey !== raw.unit.length) {
          const im = new Image();
          im.src = "data:image/png;base64," + raw.unit;
          n.img = im;
          n.unitKey = raw.unit.length;
        }
      }
      n.tr = targetR(n);
    }
    for (const n of nodes.values()) if (!seen.has(n.id) && !n.gone) n.gone = t;
    edges = [];
    wmax = {};
    for (const e of g.edges || []) {
      const a = nodes.get(e.a), b = nodes.get(e.b);
      if (!a || !b || a === b) continue;
      const h = hash(e.a + "|" + e.b);
      edges.push({ a, b, t: e.t, w: +e.w || 1, n: e.n, bend: (h & 1 ? 1 : -1) * (0.06 + (h % 97) / 1200) });
      wmax[e.t] = Math.max(wmax[e.t] || 0, +e.w || 1);
    }
    edges = backbone(edges);
    rebuild();
    orbits();
    const fresh = [...nodes.values()].filter((n) => n.isNew);
    fresh.sort((a, b) => (isIdea(b.type) - isIdea(a.type)) || (b.w - a.w));
    for (const n of fresh) { place(n); n.isNew = false; }
    if (added && added === nodes.size) {              // its first picture: settled at once, out of sight
      for (const n of fresh) { n.r = n.tr; }
      settle(added > 60 ? 320 : 180);
      if (view.auto) { computeFit(); view.x = view.tx; view.y = view.ty; view.k = view.tk; }
    } else if (added) {                               // a few new cells: they find their place near their kin,
      S.alpha = Math.max(S.alpha, 0.18);              // gently, and the rest hardly moves
    }
    if (S.sel && !nodes.has(S.sel)) select(null);
  }

  const BACKBONE = { lived: 4, read: 3, kin: 2 };
  function backbone(list) {
    const keep = new Set(), per = new Map();
    for (const e of list) {
      if (!BACKBONE[e.t]) { keep.add(e); continue; }
      for (const n of [e.a, e.b]) {
        let m = per.get(n);
        if (!m) per.set(n, (m = {}));
        (m[e.t] = m[e.t] || []).push(e);
      }
    }
    for (const m of per.values()) {
      for (const ty in m) {
        m[ty].sort((x, y) => y.w - x.w);
        m[ty].slice(0, BACKBONE[ty]).forEach((e) => keep.add(e));
      }
    }
    return list.filter((e) => keep.has(e));
  }

  function settle(n) {
    let a = 0.9;
    for (let i = 0; i < n; i++) { physics(a); a = Math.max(0.05, a * 0.985); }
    for (const m of nodes.values()) { m.vx = 0; m.vy = 0; m.vz = 0; project(m); }
  }

  const SPRING = { lived: [64, 0.011], read: [84, 0.007], kin: [120, 0.0016], kindof: [70, 0.01], part: [46, 0.02], about: [58, 0.008], means: [34, 0.03], assoc: [42, 0.015], rel: [50, 0.008] };

  function physics(alpha) {
    const list = [];
    for (const n of nodes.values()) if (visible(n) && !n.gone) list.push(n);
    for (const n of list) { n.fx = 0; n.fy = 0; n.fz = 0; }
    for (let i = 0; i < list.length; i++) {
      const a = list[i];
      const ma = a.type === "word" ? 0.6 : a.type === "seen" ? 1.15 : 1.4;
      for (let j = i + 1; j < list.length; j++) {
        const b = list[j];
        let dx = b.X - a.X, dy = b.Y - a.Y, dz = b.Z - a.Z;
        let d2 = dx * dx + dy * dy + dz * dz;
        if (d2 > 300000) continue;
        if (d2 < 0.01) {
          dx = ((hash(a.id) % 7) - 3) * 0.1 || 0.1; dy = ((hash(b.id) % 7) - 3) * 0.1 || 0.1;
          dz = ((hash(a.id + b.id) % 7) - 3) * 0.1 || 0.1; d2 = dx * dx + dy * dy + dz * dz;
        }
        const d = Math.sqrt(d2);
        const mb = b.type === "word" ? 0.6 : b.type === "seen" ? 1.15 : 1.4;
        let f = (2100 * ma * mb) / (d2 + 120);
        const min = a.r + b.r + (a.type === "word" && b.type === "word" ? 6 : 12);
        if (d < min) f += (min - d) * 0.5;
        const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
        a.fx -= fx; a.fy -= fy; a.fz -= fz;
        b.fx += fx; b.fy += fy; b.fz += fz;
      }
    }
    for (const e of visEdges) {
      if (e.a.gone || e.b.gone) continue;
      const sp = SPRING[e.t] || [70, 0.006];
      const a = e.a, b = e.b;
      const dx = b.X - a.X, dy = b.Y - a.Y, dz = b.Z - a.Z;
      const d = Math.hypot(dx, dy, dz) || 0.01;
      const norm = wmax[e.t] ? Math.min(1, e.w / wmax[e.t]) : 0.5;
      const f = (d - (sp[0] + a.r + b.r)) * sp[1] * (0.55 + norm);
      const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
      a.fx += fx; a.fy += fy; a.fz += fz;
      b.fx -= fx; b.fy -= fy; b.fz -= fz;
    }
    const R = S.R;
    for (const n of list) {
      const d = Math.hypot(n.X, n.Y, n.Z) || 0.01;
      if (isIdea(n.type)) {
        const k = d > R.idea ? 0.012 : 0.0035;
        n.fx -= n.X * k; n.fy -= n.Y * k; n.fz -= n.Z * k;
      } else {
        const target = n.type === "seen" ? R.seen : R.word;
        const k = n.type === "seen" ? 0.02 : n.means ? 0.005 : 0.012;
        const f = (target - d) * k;
        n.fx += (n.X / d) * f; n.fy += (n.Y / d) * f; n.fz += (n.Z / d) * f;
      }
    }
    for (const n of list) {
      if (n === dragNode) { n.vx = n.vy = n.vz = 0; continue; }
      n.vx = (n.vx + n.fx * alpha) * 0.7;
      n.vy = (n.vy + n.fy * alpha) * 0.7;
      n.vz = (n.vz + n.fz * alpha) * 0.7;
      const sp = Math.hypot(n.vx, n.vy, n.vz);
      if (sp > 16) { n.vx *= 16 / sp; n.vy *= 16 / sp; n.vz *= 16 / sp; }
      n.X += n.vx; n.Y += n.vy; n.Z += n.vz;
      if (!Number.isFinite(n.X) || !Number.isFinite(n.Y) || !Number.isFinite(n.Z)) {
        [n.X, n.Y, n.Z] = sphere(hash(n.id), 60);
        n.vx = n.vy = n.vz = 0;
      }
    }
  }

  function computeFit() {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, any = false;
    for (const n of nodes.values()) {
      if (!visible(n) || n.gone) continue;
      any = true;
      x0 = Math.min(x0, n.x - n.r - 30); x1 = Math.max(x1, n.x + n.r + 30);
      y0 = Math.min(y0, n.y - n.r - 24); y1 = Math.max(y1, n.y + n.r + 30);
    }
    if (!any) { view.tx = 0; view.ty = 0; view.tk = 1; return; }
    const top = 56, bottom = S.bottom, side = 60;
    const k = Math.max(0.18, Math.min((W - side * 2) / Math.max(1, x1 - x0), (H - top - bottom) / Math.max(1, y1 - y0), 1.9));
    if (k < view.tk * 0.97 || k > view.tk * 1.15) view.tk = k;   // (a calm camera: it zooms out at once when cells
    const tx = (x0 + x1) / 2, ty = (y0 + y1) / 2 - ((top - bottom) / 2) / view.tk;   // would leave the screen, in only
    if (Math.hypot(tx - view.tx, ty - view.ty) * view.tk > 24) { view.tx = tx; view.ty = ty; }   // when clearly room)
  }

  const fadeOf = (n) => n.gone ? Math.max(0, 1 - (S.t - n.gone) / 0.7) : Math.min(1, (S.t - n.born) / 0.35);
  const mid = { X: 0, Y: 0, Z: 0 };
  function ctrl(e) {
    const a = e.a, b = e.b;
    let mx = (a.X + b.X) / 2, my = (a.Y + b.Y) / 2, mz = (a.Z + b.Z) / 2;
    const len = Math.hypot(b.X - a.X, b.Y - a.Y, b.Z - a.Z) || 1, m = Math.hypot(mx, my, mz);
    const out = Math.abs(e.bend) * 2.2 * len;
    if (m > 1e-3) { mx += (mx / m) * out; my += (my / m) * out; mz += (mz / m) * out; }
    else { my -= out; }
    mid.X = mx; mid.Y = my; mid.Z = mz;
    project(mid);
    return [mid.x, mid.y];
  }
  function bez(e, s) {
    const [cx, cy] = ctrl(e), u = 1 - s;
    return [u * u * e.a.x + 2 * u * s * cx + s * s * e.b.x, u * u * e.a.y + 2 * u * s * cy + s * s * e.b.y];
  }

  /* ---------- drawing ---------- */
  const probe = { X: 0, Y: 0, Z: 0 };
  function ring3D(R, plane, color, alpha) {
    ctx.beginPath();
    for (let i = 0; i <= 72; i++) {
      const a = (i / 72) * TAU, c = Math.cos(a) * R, s = Math.sin(a) * R;
      if (plane === 0) { probe.X = c; probe.Y = 0; probe.Z = s; }
      else if (plane === 1) { probe.X = c; probe.Y = s; probe.Z = 0; }
      else { probe.X = 0; probe.Y = c; probe.Z = s; }
      project(probe);
      if (i === 0) ctx.moveTo(probe.x, probe.y); else ctx.lineTo(probe.x, probe.y);
    }
    ctx.strokeStyle = rgba(color, alpha);
    ctx.stroke();
  }
  function drawOrbits() {
    const R = S.R;
    drawGlow(ctx, 0, 0, R.idea * 1.7, C.accent, C.light ? 0.16 : 0.26);
    ctx.setLineDash([3 / view.k, 8 / view.k]);
    ctx.lineWidth = 1 / view.k;
    const a = C.light ? 0.26 : 0.22;
    for (let p = 0; p < 3; p++) {
      if (R.ni) ring3D(R.idea, p, C.accent, a * 0.8);
      if (R.ns && filters.seen) ring3D(R.seen, p, C.seen, a);
      if (R.nw && filters.word) ring3D(R.word, p, C.word, a * 0.85);
    }
    ctx.setLineDash([]);
  }
  function drawOrbitLabels() {
    S.orbitRects = [];
    if (view.k > 1.7) return;
    const R = S.R;
    const rows = [];
    if (R.ni) rows.push([R.idea + 14, C.accent, t("orbitIdeas")]);
    if (R.ns && filters.seen) rows.push([R.seen, C.seen, t("orbitSeen")]);
    if (R.nw && filters.word) rows.push([R.word, C.word, t("orbitWords")]);
    for (const [r, col, s] of rows) {
      const [sx, sy] = toScreen(0, -r);
      if (sy < 30) continue;
      ctx.font = `650 10.5px ${FONT}`;
      const mk = ctx.font + "|" + s;
      let tw = widths.get(mk);
      if (tw == null) { tw = ctx.measureText(s).width; widths.set(mk, tw); }
      S.orbitRects.push([sx - tw / 2 - 6, sy - 19, tw + 12, 18]);
      ctx.globalAlpha = 0.75;
      text(ctx, sx, sy - 10, s, 10.5, rgba(col, 0.9), 650);
    }
    ctx.globalAlpha = 1;
  }

  function drawEdges() {
    const focus = S.sel || S.hover;
    for (const type of [...LINKS, ...lawTypes()]) {
      if (!(filters[type] ?? true)) continue;
      const st = linkStyle(type), law = String(type).startsWith("law:");
      ctx.setLineDash(st.dash);
      for (const e of visEdges) {
        if (e.t !== type) continue;
        const norm = wmax[type] ? Math.min(1, e.w / wmax[type]) : 0.5;
        const la = depthLight(e.a), lb = depthLight(e.b);
        let a = (st.base + 0.42 * norm) * Math.min(fadeOf(e.a), fadeOf(e.b));
        let lw = st.width * (0.7 + 1.5 * norm) * ((e.a.ps || 1) + (e.b.ps || 1)) / 2;
        if (focus) {
          const hit = e.a.id === focus || e.b.id === focus;
          a = hit ? Math.min(1, a * 2.4 + 0.3) : a * 0.15;
          if (hit) lw += 0.9;
        }
        if (a < 0.01) continue;
        const [cx, cy] = ctrl(e);
        ctx.beginPath();
        ctx.moveTo(e.a.x, e.a.y);
        ctx.quadraticCurveTo(cx, cy, e.b.x, e.b.y);
        if (focus || law) {                           // (its halo, and its light near to far, where the eye is)
          ctx.strokeStyle = rgba(st.color, a * 0.1 * (la + lb));
          ctx.lineWidth = lw * 3.4;
          ctx.stroke();
          const g = ctx.createLinearGradient(e.a.x, e.a.y, e.b.x, e.b.y);
          g.addColorStop(0, rgba(st.color, a * la));
          g.addColorStop(1, rgba(st.color, a * lb));
          ctx.strokeStyle = g;
        } else {
          ctx.strokeStyle = rgba(st.color, a * (la + lb) / 2);
        }
        ctx.lineWidth = lw;
        ctx.stroke();
        if (law && S.motion) {
          const len = Math.hypot(e.b.x - e.a.x, e.b.y - e.a.y) + 1, ph = (S.t * 0.45 + Math.abs(e.bend) * 7) % 1;
          ctx.save();
          ctx.setLineDash([len * 0.14, len * 1.3]);
          ctx.lineDashOffset = -ph * len * 1.44;
          ctx.lineCap = "round";
          ctx.strokeStyle = `rgba(255,255,255,${(0.6 * a).toFixed(3)})`;
          ctx.lineWidth = lw * 1.1;
          ctx.stroke();
          ctx.restore();
        }
        if (type === "means") {
          const len = Math.hypot(e.b.x - e.a.x, e.b.y - e.a.y) || 1;
          const p = bez(e, Math.max(0, 1 - (e.b.r + 2.5) / len));
          ctx.fillStyle = rgba(st.color, Math.min(1, a + 0.25));
          ctx.beginPath(); ctx.arc(p[0], p[1], 2.4, 0, TAU); ctx.fill();
        }
      }
    }
    ctx.setLineDash([]);
  }

  function pointAlong(p, s) {
    s = Math.max(0, Math.min(1, s));
    if (p.e) return p.e.a === p.a ? bez(p.e, s) : bez(p.e, 1 - s);
    return [p.a.x + (p.b.x - p.a.x) * s, p.a.y + (p.b.y - p.a.y) * s];
  }
  function drawPulses() {
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i];
      const s = (S.t - p.t0) / p.dur;
      if (s >= 1 || !nodes.has(p.a.id) || !nodes.has(p.b.id)) { pulses.splice(i, 1); continue; }
      if (s < 0) continue;
      const es = ease(s);
      for (let k = 4; k >= 0; k--) {
        const q = pointAlong(p, es - k * 0.035);
        const a = p.s * (1 - k / 5);
        if (k === 0) drawGlow(ctx, q[0], q[1], 16, p.color, a);
        ctx.fillStyle = k === 0 ? "#fff" : rgba(p.color, a * 0.8);
        ctx.beginPath(); ctx.arc(q[0], q[1], k === 0 ? 2.3 : 1.6, 0, TAU); ctx.fill();
      }
      if (s > 0.92 && !p.hit) { p.hit = true; p.b.boost = Math.min(1.5, p.b.boost + 0.25 * p.s); }
    }
  }

  function drawNodes(t, dt) {
    S.solids = 0;
    const focus = S.sel || S.hover;
    const nbr = S.hl || (focus ? adj.get(focus) : null);
    const list = [];
    for (const n of nodes.values()) if (visible(n)) list.push(n);
    list.sort((a, b) => ((a.id === focus) - (b.id === focus)) || (b.pz - a.pz));
    const here = typeof Panels !== "undefined" && Panels.cellStates ? Panels.cellStates() : {};
    for (const n of list) {
      const fade = fadeOf(n);
      if (fade <= 0) continue;
      const [sx, sy] = toScreen(n.x, n.y), m = n.r * (n.ps || 1) * view.k * 2.5 + 24;
      if (sx < -m || sy < -m || sx > W + m || sy > H + m) continue;
      const age = t - n.born;
      const scale = age < 0.9 ? Math.max(0.05, backOut(Math.min(1, age / 0.9))) : 1;
      const dim = (S.hl ? !S.hl.has(n.id) : focus && n.id !== focus && !(nbr && nbr.has(n.id))) ? 0.22 : 1;
      const heat = Math.min(1.5, n.act * 0.9 + n.boost);
      const breathe = S.motion ? 1 + 0.03 * Math.sin(t * 1.6 + n.phase * TAU) * (0.3 + heat) : 1;
      const r = Math.max(0.5, n.r * scale * breathe * (n.ps || 1));
      n.tick += dt * (S.motion ? 0.55 + 2.4 * Math.min(1, heat) : 0);
      const col = C[n.type];
      const px = r * view.k;
      ctx.globalAlpha = fade * dim * depthLight(n);
      if (px < 2.4) {
        drawSphere(ctx, n.x, n.y, r, col, 1);
      } else {
        drawGlow(ctx, n.x, n.y, r * (2.1 + heat * 1.2), col, (C.light ? 0.22 : 0.3) * (0.3 + heat));
        const deep = S.solid && solid(n.type) && px >= 6 && S.solids < 160;
        if (deep) {
          S.solids++;
          drawSphere(ctx, n.x, n.y, r * 0.98, col, C.light ? 0.28 : 0.34);
          drawCell3D(ctx, n.type, n.x, n.y, r, { cycles: n.cycles, T: n.T, t: n.tick, rate: 1, act: Math.min(1, heat), img: n.img, symbol: n.symbol, means: n.means, nature: n.nature, px, fr: n.tr * scale, phase: n.phase, at: here[n.id] || null });
        } else if (S.solid) {
          drawSphere(ctx, n.x, n.y, r, col, 0.95);
        } else {
          drawCell(ctx, n.type, n.x, n.y, r, { cycles: n.cycles, T: n.T, t: n.tick, rate: 1, act: Math.min(1, heat), img: n.img, symbol: n.symbol, means: n.means, nature: n.nature, px, fr: n.tr * scale, phase: n.phase, at: here[n.id] || null });
        }
      }
      if (n.id === S.target) {
        ctx.save();
        ctx.strokeStyle = rgba(C.word, 0.95);
        ctx.lineWidth = 2.6 / view.k;
        ctx.setLineDash([6 / view.k, 4 / view.k]);
        ctx.lineDashOffset = -t * 20 / view.k;
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 7 + 4 / view.k, 0, TAU); ctx.stroke();
        ctx.restore();
      }
      if (S.current && S.current.has(n.id)) {
        ctx.save();
        ctx.setLineDash([2 / view.k, 5 / view.k]);
        ctx.lineDashOffset = t * 10 / view.k;
        ctx.strokeStyle = rgba(C.ok, 0.85);
        ctx.lineWidth = 1.6 / view.k;
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 3 + 6 / view.k, 0, TAU); ctx.stroke();
        ctx.restore();
      }
      if (n.id === S.sel) {
        ctx.save();
        ctx.setLineDash([5 / view.k, 4 / view.k]);
        ctx.lineDashOffset = -t * 14 / view.k;
        ctx.strokeStyle = rgba(col, 0.95);
        ctx.lineWidth = 1.8 / view.k;
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 5 + 3 / view.k, 0, TAU); ctx.stroke();
        ctx.restore();
      } else if (n.id === S.hover) {
        ctx.strokeStyle = rgba(col, 0.75);
        ctx.lineWidth = 1.3 / view.k;
        ctx.beginPath(); ctx.arc(n.x, n.y, r + 4, 0, TAU); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  function drawRipples() {
    for (let i = ripples.length - 1; i >= 0; i--) {
      const p = ripples[i];
      const s = (S.t - p.t0) / p.dur;
      if (s >= 1 || !nodes.has(p.n.id)) { ripples.splice(i, 1); continue; }
      const r = p.n.r * (p.n.ps || 1) + 4 + ease(s) * p.size;
      ctx.strokeStyle = rgba(p.color, (1 - s) * 0.9);
      ctx.lineWidth = (2.4 * (1 - s) + 0.4) / Math.sqrt(view.k);
      ctx.beginPath(); ctx.arc(p.n.x, p.n.y, r, 0, TAU); ctx.stroke();
    }
  }

  function drawLabels() {
    const focus = S.sel || S.hover;
    const nbr = focus ? adj.get(focus) : null;
    const cands = [];
    for (const n of nodes.values()) {
      if (!visible(n)) continue;
      const word = n.type === "word";
      const named = !word && n.label && n.label !== n.symbol;
      if (!word && !named) continue;
      const [sx, sy] = toScreen(n.x, n.y);
      if (sx < -80 || sy < -40 || sx > W + 80 || sy > H + 40) continue;
      let pri = (n.act + n.boost) * 3 + (word ? Math.log2(1 + n.w) * 0.7 + (n.means ? 1.6 : 0) : 3.5);
      if (focus) pri += n.id === focus ? 100 : nbr && nbr.has(n.id) ? 20 : -3;
      if (n.id === S.hover) pri += 50;
      const need = !S.labels ? 19 : view.k > 1.6 ? -99 : view.k > 1.05 ? 0.9 : view.k > 0.7 ? 1.7 : 2.6;
      if (pri < need) continue;
      const size = word ? (n.means ? 12.5 : 11.5) : 12;
      cands.push({ n, sx, sy: sy + n.r * (n.ps || 1) * view.k + size * 0.8 + 3, s: n.label, pri, size, bold: n.means || !word });
    }
    cands.sort((a, b) => b.pri - a.pri);
    const placed = (S.orbitRects || []).slice();
    for (const c of cands.slice(0, 180)) {
      ctx.font = `${c.bold ? 650 : 520} ${c.size}px ${FONT}`;
      const s = c.s.length > 28 ? c.s.slice(0, 27) + "…" : c.s;
      const mk = ctx.font + "|" + s;
      let tw = widths.get(mk);
      if (tw == null) { tw = ctx.measureText(s).width; if (widths.size > 3000) widths.clear(); widths.set(mk, tw); }
      const w = tw + 12, h = c.size + 7;
      const x = c.sx - w / 2, y = c.sy - h / 2;
      if (placed.some((p) => x < p[0] + p[2] && x + w > p[0] && y < p[1] + p[3] && y + h > p[1])) continue;
      placed.push([x, y, w, h]);
      ctx.globalAlpha = fadeOf(c.n) * (focus && c.pri < 15 ? 0.4 : 1);
      ctx.fillStyle = C.light ? "rgba(255,255,255,.86)" : "rgba(6,9,20,.7)";
      roundRect(ctx, x, y, w, h, h / 2);
      ctx.fill();
      ctx.strokeStyle = rgba(C.word, c.n.type === "word" ? 0.28 : 0.45);
      ctx.lineWidth = 1;
      ctx.stroke();
      text(ctx, c.sx, c.sy, s, c.size, c.n.type === "word" ? C.text : C.word, c.bold ? 650 : 520);
    }
    ctx.globalAlpha = 1;
  }

  function drawFloats() {
    for (let i = floats.length - 1; i >= 0; i--) {
      const f = floats[i];
      const s = (S.t - f.t0) / f.dur;
      if (s >= 1 || !nodes.has(f.n.id)) { floats.splice(i, 1); continue; }
      const [sx, sy] = toScreen(f.n.x, f.n.y);
      ctx.globalAlpha = s < 0.15 ? s / 0.15 : 1 - Math.max(0, (s - 0.6) / 0.4);
      text(ctx, sx, sy - f.n.r * (f.n.ps || 1) * view.k - 12 - s * 26, f.s, 17, f.color, 800);
    }
    ctx.globalAlpha = 1;
  }

  function placeBubbles() {
    for (let i = bubbles.length - 1; i >= 0; i--) {
      const b = bubbles[i];
      const n = nodes.get(b.id);
      if (S.t - b.t0 > b.dur || !n) {
        b.el.classList.add("out");
        if (S.t - b.t0 > b.dur + 0.6 || !n) { b.el.remove(); bubbles.splice(i, 1); }
        if (!n) continue;
      }
      const [sx, sy] = toScreen(n.x, n.y - n.r * (n.ps || 1));
      b.el.style.left = sx + "px";
      b.el.style.top = sy + "px";
    }
  }

  function ambient(t) {
    if (!S.motion || t < S.ambientAt) return;
    S.ambientAt = t + 0.3;
    let best = null, bestHeat = 0.65;
    for (let tries = 0; tries < 24 && visEdges.length; tries++) {
      const e = visEdges[(Math.random() * visEdges.length) | 0];
      if (e.t === "kin") continue;
      const h = e.a.act + e.a.boost + e.b.act + e.b.boost;
      if (h > bestHeat) { best = e; bestHeat = h; }
    }
    if (!best) return;
    const fwd = best.a.act + best.a.boost >= best.b.act + best.b.boost;
    pulse(fwd ? best.a.id : best.b.id, fwd ? best.b.id : best.a.id, linkStyle(best.t).color, Math.min(0.8, 0.3 + bestHeat * 0.2));
  }

  const perf = { physics: 0, draw: 0, n: 0 };
  let lastInput = 0, lastDrawn = 0;
  function frame(now) {
    requestAnimationFrame(frame);

    const quiet = !S.motion && now - lastInput > 8000 && !dragNode && !pulses.length && !ripples.length && !floats.length;   // (while it turns: every frame, or the turn steps)
    if (now - lastDrawn < (quiet ? 38 : 12)) return;
    lastDrawn = now;
    const p0 = performance.now();
    const t = now / 1000;
    const dt = Math.min(0.05, Math.max(0, t - (S.t || t)));
    S.t = t;
    if (S.alpha > 0.021 || dragNode) { physics(S.alpha); S.alpha = Math.max(0.02, S.alpha * 0.988); }
    if (S.motion && !downAt && now - lastInput > 4000) turn(cam.spin * dt, 0);
    for (const n of nodes.values()) project(n);
    const p1 = performance.now();
    let removed = false;
    for (const [id, n] of nodes) {
      n.r += ((n.gone ? 0.3 : 1) * n.tr - n.r) * 0.1;
      n.act += (n.tact - n.act) * 0.04;
      n.boost *= Math.pow(0.4, dt);
      if (n.gone && t - n.gone > 0.75) { nodes.delete(id); removed = true; if (S.hover === id) setHover(null); }
    }
    if (removed) { edges = edges.filter((e) => nodes.has(e.a.id) && nodes.has(e.b.id)); rebuild(); orbits(); }
    if (view.auto && t - S.lastFit > 0.4) { computeFit(); S.lastFit = t; }
    const f = Math.min(1, dt * 7);
    view.x += (view.tx - view.x) * f;
    view.y += (view.ty - view.y) * f;
    view.k += (view.tk - view.k) * f;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.setTransform(dpr * view.k, 0, 0, dpr * view.k, dpr * (W / 2 - view.x * view.k), dpr * (H / 2 - view.y * view.k));
    drawOrbits();
    drawEdges();
    drawPulses();
    drawNodes(t, dt);
    drawRipples();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawOrbitLabels();
    drawLabels();
    drawFloats();
    placeBubbles();
    ambient(t);
    tickIcons(t);
    if (Brain.onFrame) Brain.onFrame(t, dt);
    const p2 = performance.now();
    perf.physics = perf.physics * 0.95 + (p1 - p0) * 0.05;
    perf.draw = perf.draw * 0.95 + (p2 - p1) * 0.05;
    perf.n++;
  }

  /* ---------- what happens in it, shown where it happens ---------- */
  function idOf(sym) {
    sym = String(sym);
    if (nodes.has("c:" + sym)) return "c:" + sym;
    if (nodes.has("s:" + sym)) return "s:" + sym;
    if (nodes.has("i:" + sym)) return "i:" + sym;
    if (nodes.has("o:" + sym)) return "o:" + sym;
    if (nodes.has("b:" + sym)) return "b:" + sym;
    if (nodes.has("g:" + sym)) return "g:" + sym;
    if (nodes.has("w:" + sym)) return "w:" + sym;
    return null;
  }
  function boost(id, x) { const n = id && nodes.get(id); if (n) n.boost = Math.min(1.6, n.boost + x); }
  function ripple(id, color, size) { const n = id && nodes.get(id); if (n && filters[n.type]) ripples.push({ n, t0: S.t, dur: 1.1, color, size: size || 34 }); }
  function float(id, s, color) { const n = id && nodes.get(id); if (n && filters[n.type]) floats.push({ n, s, color, t0: S.t, dur: 1.6 }); }
  function pulse(aId, bId, color, s) {
    const a = nodes.get(aId), b = nodes.get(bId);
    if (!a || !b || !S.motion || !filters[a.type] || !filters[b.type]) return;
    const e = pair.get(aId + "|" + bId) || null;
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    pulses.push({ a, b, e, color, s: s == null ? 1 : s, t0: S.t + Math.random() * 0.15, dur: 0.7 + len / 520 });
    if (pulses.length > 160) pulses.splice(0, pulses.length - 160);
  }
  function bubble(id, s) {
    const n = id && nodes.get(id);
    if (!n) return;
    const el = document.createElement("div");
    el.className = "bubble";
    el.textContent = s;
    document.getElementById("stage").appendChild(el);
    bubbles.push({ el, id, t0: S.t, dur: 6 });
    if (bubbles.length > 3) { const b = bubbles.shift(); b.el.remove(); }
  }

  function effect(e) {
    switch (e.k) {
      case "understood": {
        const ids = (e.symbols || []).map(idOf).filter(Boolean);
        ids.forEach((id) => { boost(id, 0.9); ripple(id, C.lived, 26); });
        for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) { pulse(ids[i], ids[j], C.lived, 0.9); pulse(ids[j], ids[i], C.lived, 0.6); }
        break;
      }
      case "born": { const id = idOf(e.s); if (id) { boost(id, 1.2); ripple(id, C[nodes.get(id).type] || C.accent, 60); } break; }
      case "recognized": { const id = idOf(e.s); boost(id, 0.8); ripple(id, C.ok, 30); float(id, "✓", C.ok); break; }
      case "invented": { const id = idOf(e.s); boost(id, 1.2); ripple(id, C.invented, 60); float(id, "✦", C.invented); break; }
      case "law": { const a = idOf(e.a), b = idOf(e.b); boost(a, 0.8); boost(b, 0.8); if (a && b) pulse(a, b, lawColor(e.code), 1.4); break; }
      case "heard": {
        (e.words || []).forEach((w) => boost("w:" + w, 1));
        (e.symbols || []).map(idOf).forEach((id) => { boost(id, 1); ripple(id, C.word, 26); });
        (e.words || []).forEach((w) => (e.symbols || []).forEach((s) => pulse("w:" + w, idOf(s), C.means, 1)));
        break;
      }
      case "spoke": {
        const ids = (e.symbols || []).map(idOf).filter(Boolean);
        ids.forEach((id) => boost(id, 1.2));
        if (ids.length) bubble(ids[0], e.text);
        break;
      }
      case "meaning": { const c = idOf(e.s); boost("w:" + e.word, 1.2); boost(c, 0.8); pulse("w:" + e.word, c, C.means, 1); ripple(c, C.means, 40); float("w:" + e.word, "★", C.word); break; }
      case "linked": pulse("w:" + e.a, "w:" + e.b, C.assoc, 1); boost("w:" + e.a, 0.8); boost("w:" + e.b, 0.8); break;
      case "curious": float("w:" + e.word, "?", C.word); ripple("w:" + e.word, C.word, 22); break;
      case "read": (e.concepts || []).forEach((s) => { const id = idOf(s); boost(id, 0.5); }); break;
      case "read-any": (e.found || []).forEach((s) => { const id = nodes.has("s:" + s) ? "s:" + s : idOf(s); boost(id, 1); ripple(id, C.seen, 40); }); break;
      default: break;
    }
  }

  /* ---------- you, looking at it ---------- */
  function pick(sx, sy, skip) {
    const [wx, wy] = toWorld(sx, sy);
    let best = null, bd = Infinity;
    for (const n of nodes.values()) {
      if (!visible(n) || n.gone || n === skip) continue;
      const d = Math.hypot(n.x - wx, n.y - wy) - n.r * (n.ps || 1) - 3 / view.k;
      if (d < 0 && d < bd) { best = n; bd = d; }
    }
    return best;
  }
  function setHover(n, sx, sy) {
    const id = n ? n.id : null;
    if (id !== S.hover) { S.hover = id; cv.classList.toggle("pointing", !!n); }
    on.hover.forEach((f) => f(n, sx, sy));
  }
  function select(id) {
    S.sel = id && nodes.has(id) ? id : null;
    on.select.forEach((f) => f(S.sel));
  }
  function focusOn(id) {
    const n = nodes.get(id);
    if (!n) return;
    if (!filters[n.type]) setFilter(n.type, true);
    view.auto = false;
    view.tx = n.x;
    view.ty = n.y + 40 / Math.max(1.3, view.tk);
    view.tk = Math.max(view.tk, 1.35);
    select(id);
    boost(id, 0.6);
    ripple(id, C[n.type], 40);
  }
  function zoomAt(sx, sy, k) {
    k = Math.max(0.15, Math.min(5, k));
    const [wx, wy] = toWorldT(sx, sy);
    view.tk = k;
    view.tx = wx - (sx - W / 2) / k;
    view.ty = wy - (sy - H / 2) / k;
    view.auto = false;
  }
  function fit() { view.auto = true; S.lastFit = 0; }

  for (const k of ["pointerdown", "pointermove", "wheel"]) cv.addEventListener(k, () => { lastInput = performance.now(); }, { passive: true });
  cv.addEventListener("pointerdown", (ev) => {
    try { cv.setPointerCapture(ev.pointerId); } catch (e) {  }
    pointers.set(ev.pointerId, [ev.offsetX, ev.offsetY]);
    if (pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      pinch = { d: Math.hypot(p[0] - q[0], p[1] - q[1]) || 1, k: view.tk };
      dragNode = null; panStart = null; downAt = null;
      return;
    }
    downAt = [ev.offsetX, ev.offsetY, performance.now()];
    const n = pick(ev.offsetX, ev.offsetY);
    if (n) dragNode = n;
    else if (ev.shiftKey || ev.button === 2) panStart = [ev.offsetX, ev.offsetY, view.tx, view.ty];
    else turnStart = [ev.offsetX, ev.offsetY];
    cv.classList.add("dragging");
  });
  cv.addEventListener("pointermove", (ev) => {
    if (pointers.has(ev.pointerId)) pointers.set(ev.pointerId, [ev.offsetX, ev.offsetY]);
    if (pinch && pointers.size === 2) {
      const [p, q] = [...pointers.values()];
      zoomAt((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (pinch.k * Math.hypot(p[0] - q[0], p[1] - q[1])) / pinch.d);
      return;
    }
    const moved = downAt && Math.hypot(ev.offsetX - downAt[0], ev.offsetY - downAt[1]) > 4;
    if (turnStart && moved) {
      turn(-(ev.offsetX - turnStart[0]) * 0.006, (ev.offsetY - turnStart[1]) * 0.006);
      turnStart = [ev.offsetX, ev.offsetY];
      return;
    }
    if (dragNode && moved) {
      const [wx, wy] = toWorld(ev.offsetX, ev.offsetY);
      unproject(dragNode, wx, wy);
      project(dragNode);
      S.alpha = Math.max(S.alpha, 0.22);
      view.auto = false;
      setHover(dragNode, ev.offsetX, ev.offsetY);
      if (dragNode.type === "word") {
        const under = pick(ev.offsetX, ev.offsetY, dragNode);
        S.target = under && under.type !== "word" ? under.id : null;
      }
      return;
    }
    if (panStart && moved) {
      view.tx = panStart[2] - (ev.offsetX - panStart[0]) / view.k;
      view.ty = panStart[3] - (ev.offsetY - panStart[1]) / view.k;
      view.x = view.tx; view.y = view.ty;
      view.auto = false;
      return;
    }
    if (!downAt) { const n = pick(ev.offsetX, ev.offsetY); setHover(n, ev.offsetX, ev.offsetY); }
  });
  const end = (ev) => {
    pointers.delete(ev.pointerId);
    if (pointers.size < 2) pinch = null;
    if (dragNode && S.target && ev.type === "pointerup") {
      const cell = nodes.get(S.target);
      if (cell) {
        on.teach.forEach((f) => f(cell.symbol, dragNode.label, cell.id));
        ripple(cell.id, C.word, 46);
        pulse(dragNode.id, cell.id, C.means, 1);
      }
    }
    S.target = null;
    if (downAt && Math.hypot(ev.offsetX - downAt[0], ev.offsetY - downAt[1]) <= 4 && performance.now() - downAt[2] < 600) {
      const n = pick(ev.offsetX, ev.offsetY);
      select(n ? n.id : null);
    }
    dragNode = null; panStart = null; downAt = null; turnStart = null;
    cv.classList.remove("dragging");
  };
  cv.addEventListener("contextmenu", (ev) => ev.preventDefault());
  cv.addEventListener("pointerup", end);
  cv.addEventListener("pointercancel", end);
  cv.addEventListener("pointerleave", () => { if (!downAt) setHover(null); });
  cv.addEventListener("wheel", (ev) => { ev.preventDefault(); zoomAt(ev.offsetX, ev.offsetY, view.tk * Math.exp(-ev.deltaY * 0.0015)); }, { passive: false });
  cv.addEventListener("dblclick", (ev) => { const n = pick(ev.offsetX, ev.offsetY); n ? focusOn(n.id) : fit(); });

  function setFilter(k, v) {
    filters[k] = v;
    try { localStorage.setItem("novalie.filters", JSON.stringify(filters)); } catch (e) {  }
    rebuild();
    orbits();
    S.alpha = Math.max(S.alpha, 0.5);
    if (S.sel && nodes.get(S.sel) && !filters[nodes.get(S.sel).type]) select(null);
  }
  function counts() {
    const c = {};
    TYPES.forEach((k) => (c[k] = 0));
    for (const n of nodes.values()) if (!n.gone) c[n.type]++;
    return c;
  }
  function search(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    const out = [];
    for (const n of nodes.values()) {
      if (n.gone) continue;
      const a = n.label.toLowerCase(), b = n.symbol.toLowerCase();
      const score = a === q || b === q ? 3 : a.startsWith(q) || b.startsWith(q) ? 2 : a.includes(q) || b.includes(q) ? 1 : 0;
      if (score) out.push({ n, score });
    }
    out.sort((x, y) => y.score - x.score || (y.n.w || 0) - (x.n.w || 0));
    return out.slice(0, 12).map((x) => x.n);
  }

  function picture(scale) {
    const keepCtx = ctx, keepDpr = dpr;
    const k = Math.min(Math.max(dpr, scale || 3), Math.sqrt(16e6 / (W * H)));
    const out = document.createElement("canvas");
    out.width = Math.round(W * k);
    out.height = Math.round(H * k);
    ctx = out.getContext("2d");
    dpr = k;
    try {
      ctx.setTransform(dpr * view.k, 0, 0, dpr * view.k, dpr * (W / 2 - view.x * view.k), dpr * (H / 2 - view.y * view.k));
      drawOrbits();
      drawEdges();
      drawPulses();
      drawNodes(S.t || 0, 0);
      drawRipples();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawOrbitLabels();
      drawLabels();
      drawFloats();
    } finally {
      ctx = keepCtx;
      dpr = keepDpr;
    }
    return out;
  }

  requestAnimationFrame(frame);
  return {
    picture,
    update, effect, select, focus: focusOn, fit, setFilter, filters, counts, search, idOf, toScreen, lawTypes,
    get: (id) => nodes.get(id), neighbours: (id) => adj.get(id) || new Set(),
    on: (k, f) => on[k].push(f),
    get selected() { return S.sel; },
    highlight(ids) { S.hl = ids && ids.length ? new Set(ids) : null; },
    set current(ids) { S.current = new Set(ids || []); },
    isCurrent: (id) => !!(S.current && S.current.has(id)),
    set labels(v) { S.labels = v; }, get labels() { return S.labels; },
    set motion(v) { S.motion = v; }, get motion() { return S.motion; },
    set solid(v) { S.solid = v; try { localStorage.setItem("novalie.solid", v ? "1" : "0"); } catch (e) {  } },
    get solid() { return S.solid; },
    set bottom(v) { S.bottom = v; },
    get size() { return nodes.size; },
    get perf() { return { physics: +perf.physics.toFixed(2), draw: +perf.draw.toFixed(2), alpha: +S.alpha.toFixed(3), edges: visEdges.length, frames: perf.n }; },
    onFrame: null,
  };
})();

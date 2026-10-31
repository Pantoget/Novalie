/* Novalie's page: how each kind of cell is drawn. */
"use strict";

const TAU = Math.PI * 2;
const TYPES = ["cycle", "torus", "gear", "crt", "invented", "general", "circuit", "topic", "odds", "thing", "seen", "word"];
const LINKS = ["lived", "read", "kin", "kindof", "part", "about", "means", "assoc", "rel"];

const C = {};
function readColors() {
  const cs = getComputedStyle(document.documentElement);
  const get = (n) => cs.getPropertyValue(n).trim();
  C.light = document.documentElement.dataset.theme === "light";
  for (const k of TYPES) C[k] = get("--c-" + k);
  Object.assign(C, {
    text: get("--text"), muted: get("--muted"), dim: get("--dim"), line: get("--line"), accent: get("--accent"),
    ok: get("--ok"), warn: get("--warn"), bad: get("--bad"),
    body: C.light ? "#ffffff" : "#0b1122", body2: C.light ? "#eef2fb" : "#121a33",
    lived: get("--c-cycle"), read: get("--c-gear"), kin: C.light ? "#7d88a8" : "#7c87ab", kindof: get("--c-general"),
    means: get("--c-word"), assoc: C.light ? "#d9822b" : "#ffad5c", rel: C.light ? "#b08a3c" : "#d7b06a",
    part: get("--c-circuit"), about: get("--c-topic"),
  });
  glowCache.clear();
  styleCache.clear();
}
const styleCache = new Map();

const rgbCache = new Map();
function hexToRgb(hex) {
  let v = rgbCache.get(hex);
  if (v) return v;
  let h = (hex || "#888").replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const n = parseInt(h, 16);
  v = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  rgbCache.set(hex, v);
  return v;
}
const rgbaCache = new Map();                          // (the same colour strings, asked thousands of times a frame)
function rgba(hex, a) {
  const q = Math.round(a * 200) / 200, key = hex + q;
  let s = rgbaCache.get(key);
  if (s === undefined) {
    const [r, g, b] = hexToRgb(hex);
    s = `rgba(${r},${g},${b},${q})`;
    if (rgbaCache.size > 20000) rgbaCache.clear();
    rgbaCache.set(key, s);
  }
  return s;
}
function classColor(i) {
  if (i == null || i < 0) return C.light ? "#c3c9da" : "#36405e";
  return `hsl(${(i * 137.508 + 195) % 360}, ${C.light ? 70 : 80}%, ${C.light ? 46 : 63}%)`;
}

function typeOf(n) {
  if (n.group === "word" || n.kind === "word") return "word";
  const shape = n.shape || (n.kind === "seen" ? "seen" : "flat");
  if (shape === "seen" || n.kind === "seen") return "seen";
  if (shape === "gear") return "gear";
  if (shape === "crt") return "crt";
  if (shape === "invented") return "invented";
  if (shape === "general") return "general";
  if (shape === "circuit" || n.kind === "circuit") return "circuit";
  if (shape === "topic" || n.kind === "topic") return "topic";
  if (shape === "odds" || n.kind === "odds") return "odds";
  if (shape === "thing" || n.kind === "thing") return "thing";
  return (n.cycles || []).length > 1 ? "torus" : "cycle";
}

const glowCache = new Map();
function glowSprite(color) {
  let s = glowCache.get(color);
  if (s) return s;
  s = document.createElement("canvas");
  s.width = s.height = 128;
  const g = s.getContext("2d");
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, rgba(color, 0.55));
  grd.addColorStop(0.35, rgba(color, 0.22));
  grd.addColorStop(1, rgba(color, 0));
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  glowCache.set(color, s);
  return s;
}
function drawGlow(ctx, x, y, r, color, alpha) {
  if (alpha <= 0.01) return;
  ctx.save();
  ctx.globalAlpha *= Math.min(1, alpha);
  ctx.globalCompositeOperation = C.light ? "source-over" : "lighter";
  ctx.drawImage(glowSprite(color), x - r, y - r, r * 2, r * 2);
  ctx.restore();
}

const sphereCache = new Map();
function sphereSprite(color) {
  let s = sphereCache.get(color);
  if (s) return s;
  s = document.createElement("canvas");
  s.width = s.height = 96;
  const g = s.getContext("2d");
  const grd = g.createRadialGradient(34, 30, 3, 48, 48, 48);
  grd.addColorStop(0, "rgba(255,255,255,0.95)");
  grd.addColorStop(0.18, rgba(color, 0.95));
  grd.addColorStop(0.72, rgba(color, 0.55));
  grd.addColorStop(0.97, "rgba(0,0,0,0.55)");
  grd.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grd;
  g.beginPath(); g.arc(48, 48, 48, 0, TAU); g.fill();
  sphereCache.set(color, s);
  return s;
}
function drawSphere(ctx, x, y, r, color, alpha) {
  if (alpha <= 0.01) return;
  const ga = ctx.globalAlpha;
  ctx.globalAlpha = ga * Math.min(1, alpha);
  ctx.drawImage(sphereSprite(color), x - r, y - r, r * 2, r * 2);
  ctx.globalAlpha = ga;
}

const ease = (x) => x * x * (3 - 2 * x);

function tickPos(ticks) {
  const whole = Math.floor(ticks);
  return whole + ease(Math.min(1, (ticks - whole) * 3));
}

function hexPath(ctx, x, y, r) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + i * TAU / 6;
    const px = x + r * Math.cos(a), py = y + r * Math.sin(a);
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.closePath();
}
function diamondPath(ctx, x, y, r) {
  ctx.beginPath();
  ctx.moveTo(x, y - r);
  ctx.lineTo(x + r, y);
  ctx.lineTo(x, y + r);
  ctx.lineTo(x - r, y);
  ctx.closePath();
}
function gearPath(ctx, x, y, r, teeth, rot) {
  const inner = r * 0.84, step = TAU / teeth;
  ctx.beginPath();
  for (let i = 0; i < teeth; i++) {
    const a = rot + i * step;
    const pts = [[a, inner], [a + step * 0.12, r], [a + step * 0.44, r], [a + step * 0.56, inner]];
    for (const [ang, rad] of pts) {
      const px = x + rad * Math.cos(ang), py = y + rad * Math.sin(ang);
      i === 0 && ang === a ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.arc(x, y, inner, a + step * 0.56, a + step, false);
  }
  ctx.closePath();
}

function ringStyle(ctx, n, T, color, rot) {
  const key = n + "|" + (T && T.length ? T.join(",") : color) + "|" + rot.toFixed(3);
  let g = styleCache.get(key);
  if (g) return g;
  g = ctx.createConicGradient(rot, 0, 0);
  for (let i = 0; i < n; i++) {
    const ci = T && T.length ? T[Math.floor((i * T.length) / n)] : null;
    const c = ci != null ? classColor(ci) : rgba(color, i % 2 ? 0.75 : 0.42);
    g.addColorStop(i / n, c);
    g.addColorStop(Math.min(1, (i + 1) / n - 1e-6), c);
  }
  if (styleCache.size > 600) styleCache.clear();
  styleCache.set(key, g);
  return g;
}
function ring(ctx, x, y, rad, width, d, T, color, rot) {
  const n = Math.max(1, Math.min(d, 96));
  ctx.save();
  ctx.translate(x, y);
  ctx.lineWidth = width;
  ctx.lineCap = "butt";
  ctx.strokeStyle = ringStyle(ctx, n, T, color, rot);
  if (n > 1) {
    const L = (rad * TAU) / n, g = Math.min(L * 0.24, rad * 0.08);
    ctx.setLineDash([L - g, g]);
    ctx.lineDashOffset = -g / 2;
  }
  ctx.beginPath();
  ctx.arc(0, 0, rad, rot, rot + TAU);
  ctx.stroke();
  ctx.restore();
}
function ticks(ctx, x, y, rad, d, color, alpha, len) {
  const n = Math.min(d, 60);
  ctx.strokeStyle = rgba(color, alpha);
  ctx.lineWidth = Math.max(0.6, len * 0.35);
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + (i * TAU) / n;
    ctx.moveTo(x + (rad - len) * Math.cos(a), y + (rad - len) * Math.sin(a));
    ctx.lineTo(x + rad * Math.cos(a), y + rad * Math.sin(a));
  }
  ctx.stroke();
}
function marker(ctx, x, y, rad, ang, size, color) {
  const px = x + rad * Math.cos(ang), py = y + rad * Math.sin(ang);
  drawGlow(ctx, px, py, size * 4, color, 0.9);
  ctx.fillStyle = "#fff";
  ctx.beginPath();
  ctx.arc(px, py, size, 0, TAU);
  ctx.fill();
}
function body(ctx, x, y, rad, color) {
  const key = "body|" + color;
  let g = styleCache.get(key);
  if (!g) {
    g = ctx.createRadialGradient(-0.3, -0.35, 0.1, 0, 0, 1);
    g.addColorStop(0, C.light ? rgba(color, 0.22) : rgba(color, 0.34));
    g.addColorStop(1, C.light ? rgba(color, 0.07) : C.body);
    styleCache.set(key, g);
  }
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(rad, rad);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, 1, 0, TAU);
  ctx.fill();
  ctx.restore();
}
let FONT = "Segoe UI, system-ui, sans-serif";
function setFont() { FONT = getComputedStyle(document.body).fontFamily || FONT; }
function text(ctx, x, y, s, size, color, weight, align) {
  ctx.fillStyle = color;
  ctx.font = `${weight || 700} ${size}px ${FONT}`;
  ctx.textAlign = align || "center";
  ctx.textBaseline = "middle";
  ctx.fillText(s, x, y + size * 0.04);
}

function drawCell(ctx, type, x, y, r, o) {
  const t = o.t || 0, rate = o.rate == null ? 0.8 : o.rate, col = C[type] || C.accent;
  const big = (k) => (o.px != null ? o.px > k * 0.75 : !o.small || r > k);
  const fine = o.px == null || o.px > 7;
  const cyc = (o.cycles && o.cycles.length ? o.cycles : [6]).map((v) => Math.max(1, v | 0));
  const sym = o.symbol || "";

  const R = o.fr || r;
  const fs = Math.round(2 * Math.max(6, Math.min(R * 0.62, R * 2.1 / Math.max(2, sym.length)))) / 2;
  if (type === "cycle") {
    const d = cyc[0];
    body(ctx, x, y, r * 0.8, col);
    ring(ctx, x, y, r * 0.9, r * 0.17, d, o.T, col, -Math.PI / 2);
    if (big(10)) text(ctx, x, y, sym || String(d), fs, C.text, 750);
    const p = tickPos(t * rate) % d;
    marker(ctx, x, y, r * 0.9, -Math.PI / 2 + ((p + 0.5) * TAU) / d, Math.max(1.4, r * 0.1), col);
  } else if (type === "torus") {
    const rs = [0.92, 0.7, 0.5].slice(0, Math.min(3, cyc.length));
    body(ctx, x, y, r * 0.84, col);
    rs.forEach((k, i) => {
      const d = cyc[i];
      ctx.strokeStyle = rgba(col, 0.25);
      ctx.lineWidth = r * 0.1;
      ctx.beginPath(); ctx.arc(x, y, r * k, 0, TAU); ctx.stroke();
      if (fine) ticks(ctx, x, y, r * k + r * 0.05, d, col, 0.8, r * 0.1);
      const p = tickPos((t * rate) / (i + 1)) % d;
      marker(ctx, x, y, r * k, -Math.PI / 2 + (p * TAU) / d, Math.max(1.2, r * 0.075), col);
    });
    if (big(12)) text(ctx, x, y, sym || cyc.join(","), fs * 0.8, C.text, 750);
  } else if (type === "gear") {
    const d1 = cyc[0], d2 = cyc[1] || cyc[0];
    const inner = tickPos(t * rate * 1.6);
    const carried = Math.floor(inner / d1);
    const frac = inner / d1 - carried;
    const outerStep = carried + (frac > 0.92 ? ease((frac - 0.92) / 0.08) : 0);
    const teeth = Math.max(6, Math.min(20, d2));
    gearPath(ctx, x, y, r, teeth, -Math.PI / 2 + (outerStep * TAU) / d2);
    ctx.fillStyle = C.light ? rgba(col, 0.12) : rgba(col, 0.16);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.06);
    ctx.stroke();
    body(ctx, x, y, r * 0.62, col);
    ring(ctx, x, y, r * 0.56, r * 0.12, d1, null, col, -Math.PI / 2);
    marker(ctx, x, y, r * 0.56, -Math.PI / 2 + ((inner % d1) * TAU) / d1, Math.max(1.2, r * 0.08), col);
    if (big(12)) text(ctx, x, y, sym || `${d1}.${d2}`, fs * 0.72, C.text, 750);
  } else if (type === "crt") {
    const d1 = cyc[0], d2 = cyc[1] || cyc[0], off = r * 0.34, rr = r * 0.64;
    const p = tickPos(t * rate);
    [[x - off, d1], [x + off, d2]].forEach(([cx, d], i) => {
      ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.13);
      ctx.beginPath(); ctx.arc(cx, y, rr, 0, TAU); ctx.fill();
      ctx.strokeStyle = rgba(col, 0.9);
      ctx.lineWidth = Math.max(0.8, r * 0.07);
      ctx.beginPath(); ctx.arc(cx, y, rr, 0, TAU); ctx.stroke();
      if (fine) ticks(ctx, cx, y, rr, d, col, 0.7, r * 0.09);
      marker(ctx, cx, y, rr, -Math.PI / 2 + ((p % d) * TAU) / d, Math.max(1.2, r * 0.075), col);
    });
    if (big(12)) {
      ctx.fillStyle = C.light ? "rgba(255,255,255,.85)" : "rgba(8,12,26,.72)";
      const w = Math.max(fs * 1.6, (sym || "").length * fs * 0.52 + 8);
      roundRect(ctx, x - w / 2, y - fs * 0.62, w, fs * 1.24, fs * 0.5);
      ctx.fill();
      text(ctx, x, y, sym || `${d1}x${d2}`, fs * 0.72, C.text, 750);
    }
  } else if (type === "general") {
    const k = Math.max(2, Math.min(8, o.n || 3)), ga = ctx.globalAlpha;
    ctx.beginPath(); ctx.arc(x, y, r * 0.92, 0, TAU);
    ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.18);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.08);
    ctx.setLineDash([Math.max(2, r * 0.22), Math.max(1.5, r * 0.12)]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = rgba(col, 0.92);
    for (let i = 0; i < k; i++) {
      const a = -Math.PI / 2 + (TAU * i) / k + t * rate * 0.15;
      ctx.beginPath(); ctx.arc(x + r * 0.62 * Math.cos(a), y + r * 0.62 * Math.sin(a), Math.max(1.2, r * 0.1), 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = ga * 0.9;
    ctx.beginPath(); ctx.arc(x, y, Math.max(1.6, r * 0.2), 0, TAU); ctx.fill();
    ctx.globalAlpha = ga;
  } else if (type === "invented") {
    const nat = o.nature || "", k = r * 0.9, ga = ctx.globalAlpha;
    roundRect(ctx, x - k, y - k, 2 * k, 2 * k, r * 0.32);
    const g = ctx.createLinearGradient(x, y - r, x, y + r);
    g.addColorStop(0, C.light ? rgba(col, 0.16) : rgba(col, 0.32));
    g.addColorStop(1, C.light ? rgba(col, 0.05) : rgba(C.body, 0.95));
    ctx.fillStyle = g;
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.08);
    ctx.stroke();
    const sw = Math.sin(t * rate * Math.PI), ph = ((t * rate * 0.5) % 1 + 1) % 1;
    ctx.fillStyle = rgba(col, 0.92);
    ctx.lineWidth = Math.max(1, r * 0.09);
    ctx.lineCap = "round";
    if (nat.startsWith("made")) {
      const k = 5, rr = r * 0.48, pts = [];
      for (let i = 0; i < k; i++) {
        const a = -Math.PI / 2 + (TAU * i) / k;
        pts.push([x + rr * Math.cos(a), y + rr * Math.sin(a)]);
      }
      ctx.globalAlpha = ga * 0.5;
      ctx.beginPath();
      for (let i = 0; i < k; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[(i * 2 + 1) % k];
        ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
      }
      ctx.stroke();
      ctx.globalAlpha = ga;
      for (const [px, py] of pts) { ctx.beginPath(); ctx.arc(px, py, Math.max(1.2, r * 0.08), 0, TAU); ctx.fill(); }
      const [qx, qy] = pts[(Math.floor(t * rate * 1.2) * 2 + 1) % k];
      ctx.beginPath(); ctx.arc(qx, qy, Math.max(1.8, r * 0.15), 0, TAU); ctx.fill();
    } else if (nat.includes("pile")) {
      for (let i = 0; i < 3; i++) {
        const w = r * (1.15 - i * 0.2), yy = y + r * 0.42 - i * r * 0.3;
        ctx.globalAlpha = ga * (i === 2 ? 0.3 + 0.7 * Math.abs(sw) : 1);
        roundRect(ctx, x - w / 2, yy - r * 0.11, w, r * 0.22, r * 0.06);
        ctx.fill();
      }
      ctx.globalAlpha = ga;
    } else if (nat.includes("bit")) {
      ctx.beginPath(); ctx.arc(x, y, r * 0.48, 0, TAU); ctx.stroke();
      const dir = sw >= 0 ? 1 : -1, a = t * rate * 1.6 * dir;
      ctx.beginPath(); ctx.arc(x + r * 0.48 * Math.cos(a), y + r * 0.48 * Math.sin(a), Math.max(1.5, r * 0.11), 0, TAU); ctx.fill();
      ctx.beginPath(); ctx.arc(x, y, r * 0.13, 0, TAU);
      if (dir > 0) ctx.fill(); else ctx.stroke();
    } else if (nat.includes("+")) {
      const h = r * 0.62, f = 0.5 + 0.5 * sw;
      roundRect(ctx, x - r * 0.6, y + r * 0.42 - h * f - 1, r * 0.4, h * f + 1, r * 0.05); ctx.fill();
      roundRect(ctx, x + r * 0.2, y + r * 0.42 - h * (1 - f) - 1, r * 0.4, h * (1 - f) + 1, r * 0.05); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x - r * 0.3, y - r * 0.5); ctx.lineTo(x + r * 0.3, y - r * 0.5); ctx.stroke();
    } else if (nat.startsWith("walls")) {
      ctx.beginPath();
      ctx.moveTo(x - r * 0.6, y - r * 0.38); ctx.lineTo(x - r * 0.6, y + r * 0.38);
      ctx.moveTo(x + r * 0.6, y - r * 0.38); ctx.lineTo(x + r * 0.6, y + r * 0.38);
      ctx.moveTo(x - r * 0.6, y); ctx.lineTo(x + r * 0.6, y);
      ctx.stroke();
      ctx.beginPath(); ctx.arc(x + r * 0.46 * sw, y, Math.max(1.5, r * 0.13), 0, TAU); ctx.fill();
    } else {
      ctx.beginPath(); ctx.moveTo(x - r * 0.62, y); ctx.lineTo(x + r * 0.5, y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + r * 0.66, y); ctx.lineTo(x + r * 0.42, y - r * 0.18); ctx.lineTo(x + r * 0.42, y + r * 0.18);
      ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.arc(x - r * 0.62 + r * 1.0 * ph, y, Math.max(1.5, r * 0.11), 0, TAU); ctx.fill();
    }
    ctx.lineCap = "butt";
  } else if (type === "circuit") {
    const k = Math.max(2, Math.min(5, (o.members || []).length || o.n || 2)), ga = ctx.globalAlpha;
    ctx.beginPath(); ctx.arc(x, y, r * 0.92, 0, TAU);
    ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.16);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.07);
    ctx.stroke();
    const span = r * 1.16, x0 = x - span / 2, step = span / (k - 1), rr = Math.max(1.3, Math.min(r * 0.17, step * 0.32));
    ctx.lineWidth = Math.max(0.7, r * 0.06);
    ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x0 + span, y); ctx.stroke();
    for (let i = 0; i < k; i++) {
      ctx.beginPath(); ctx.arc(x0 + i * step, y, rr, 0, TAU);
      ctx.fillStyle = C.light ? "#ffffff" : C.body;
      ctx.fill(); ctx.stroke();
    }
    const ph = ((t * rate * 0.35) % 1 + 1) % 1;
    ctx.fillStyle = rgba(col, 0.95);
    ctx.beginPath(); ctx.arc(x0 + ph * span, y, Math.max(1.1, rr * 0.55), 0, TAU); ctx.fill();
    ctx.globalAlpha = ga;
  } else if (type === "topic") {
    const k = Math.max(3, Math.min(7, o.n || 3)), ga = ctx.globalAlpha;
    ctx.beginPath(); ctx.arc(x, y, r * 0.9, 0, TAU);
    ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.15);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.9);
    ctx.lineWidth = Math.max(0.7, r * 0.06);
    ctx.setLineDash([Math.max(1.5, r * 0.1), Math.max(1.5, r * 0.1)]);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = rgba(col, 0.92);
    for (let i = 0; i < k; i++) {
      const a = -Math.PI / 2 + (TAU * i) / k - t * rate * 0.05, rad = r * (0.36 + 0.12 * (i % 3));
      diamondPath(ctx, x + rad * Math.cos(a), y + rad * Math.sin(a), Math.max(1, r * 0.11));
      ctx.fill();
    }
    ctx.globalAlpha = ga;
  } else if (type === "odds") {
    const vals = Math.max(2, Math.min(6, cyc[0] || 2)), dwell = Math.max(1, cyc[1] || 2), ga = ctx.globalAlpha;
    roundRect(ctx, x - r * 0.8, y - r * 0.8, r * 1.6, r * 1.6, r * 0.3);
    ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.14);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.07);
    ctx.setLineDash([Math.max(2, r * 0.18), Math.max(1.5, r * 0.1)]);
    ctx.stroke();
    ctx.setLineDash([]);
    const face = Math.floor((t * rate * 3) / dwell);
    const shown = 1 + ((face * 7 + 3) % vals);
    const P = [[0, 0], [-1, -1], [1, 1], [-1, 1], [1, -1], [-1, 0], [1, 0]];
    const pips = { 1: [0], 2: [1, 2], 3: [1, 0, 2], 4: [1, 2, 3, 4], 5: [1, 2, 3, 4, 0], 6: [1, 2, 3, 4, 5, 6] }[shown];
    ctx.fillStyle = rgba(col, 0.95);
    for (const i of pips) {
      const [dx, dy] = P[i];
      ctx.beginPath(); ctx.arc(x + dx * r * 0.42, y + dy * r * 0.42, Math.max(1.1, r * 0.11), 0, TAU); ctx.fill();
    }
    ctx.globalAlpha = ga;
  } else if (type === "thing") {
    const k = Math.max(2, Math.min(5, cyc[0] || 2)), ga = ctx.globalAlpha;
    ctx.beginPath(); ctx.arc(x, y, r * 0.92, 0, TAU);
    ctx.fillStyle = C.light ? rgba(col, 0.1) : rgba(col, 0.15);
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.08);
    ctx.stroke();
    const sway = Math.sin(t * rate * 0.9) * r * 0.06;
    for (let i = 0; i < k; i++) {
      const a = -Math.PI / 2 + (TAU * i) / k;
      ctx.beginPath(); ctx.arc(x + r * 0.34 * Math.cos(a) + sway, y + r * 0.34 * Math.sin(a), r * 0.36, 0, TAU);
      ctx.strokeStyle = rgba(col, 0.8);
      ctx.lineWidth = Math.max(0.7, r * 0.06);
      ctx.stroke();
    }
    ctx.globalAlpha = ga;
  } else if (type === "seen") {
    hexPath(ctx, x, y, r);
    const g = ctx.createLinearGradient(x, y - r, x, y + r);
    g.addColorStop(0, C.light ? rgba(col, 0.16) : rgba(col, 0.32));
    g.addColorStop(1, C.light ? rgba(col, 0.06) : rgba(C.body, 0.95));
    ctx.fillStyle = g;
    ctx.fill();
    ctx.save();
    hexPath(ctx, x, y, r * 0.8);
    ctx.clip();
    if (o.img && o.img.complete && o.img.naturalWidth) {
      ctx.globalAlpha *= 0.92;
      ctx.imageSmoothingEnabled = false;
      const n = cyc.length > 1 ? 2 : 1;
      const s = (r * 1.6) / n;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) ctx.drawImage(o.img, x - r * 0.8 + i * s, y - r * 0.8 + j * s, s, s);
    } else {
      lattice(ctx, x, y, r * 0.8, cyc, col, t);
    }
    ctx.restore();
    hexPath(ctx, x, y, r);
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.8, r * 0.07);
    ctx.stroke();
    if (big(13)) {
      const s = sym || cyc.join("×");
      const f = Math.round(2 * Math.max(6, Math.min(R * 0.42, (R * 2.2) / Math.max(3, s.length)))) / 2;
      ctx.fillStyle = C.light ? "rgba(255,255,255,.88)" : "rgba(8,12,26,.78)";
      const w = s.length * f * 0.58 + 8;
      roundRect(ctx, x - w / 2, y + r * 0.42 - f * 0.62, w, f * 1.24, f * 0.5);
      ctx.fill();
      text(ctx, x, y + r * 0.42, s, f, C.text, 750);
    }
  } else {
    diamondPath(ctx, x, y, r);
    ctx.fillStyle = rgba(col, C.light ? 0.25 + 0.5 * (o.act || 0) : 0.2 + 0.6 * (o.act || 0));
    ctx.fill();
    ctx.strokeStyle = rgba(col, 0.95);
    ctx.lineWidth = Math.max(0.7, r * 0.18);
    ctx.stroke();
    if (o.means) {
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(x, y, r * 0.32, 0, TAU); ctx.fill();
    }
  }
}

/* ---------- cells in three dimensions: each one the shape its laws give it ----------
   A cell's dimensions are what its laws found: a cycle is a ring of its places, two cycles a torus (a carry from one
   into the other a gear, two that turn together a knot that visits every place), more than two a cloud of all its
   places; a cell of chance a sphere of its values; a machine it invented the parts it is made of. Each is a body in
   space, made of lit faces, tubes and beads drawn far to near (its near side hides its far side), turning slowly so
   its depth shows; where it is now (its place on each of its dimensions) is the light on it. Drawn on the page's
   canvas with no library, and the same every time (no chance). */
const D3 = { tilt: 0.55, persp: 0.28 };
const LIGHT = (() => { const v = [-0.45, -0.65, -0.62], l = Math.hypot(v[0], v[1], v[2]); return v.map((x) => x / l); })();
function rot3(p, yaw, tilt) {
  const [x, y, z] = p, cy = Math.cos(yaw), sy = Math.sin(yaw), ct = Math.cos(tilt), st = Math.sin(tilt);
  const x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
  return [x1, y * ct - z1 * st, y * st + z1 * ct];
}
function proj3(cx, cy, r, p) {
  const f = 1 / (1 + D3.persp * p[2]);
  return [cx + r * p[0] * f, cy + r * p[1] * f, f, p[2]];
}
const unit3 = (v) => { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };
const nearOf = (z) => Math.max(0, Math.min(1, 0.5 - 0.5 * z));

let SCN = null;
function put(z, f) { if (SCN) SCN.push({ z, f }); else f(); }
function flush3() {
  const s = SCN;
  SCN = null;
  if (!s) return;
  s.sort((a, b) => b.z - a.z);
  for (const q of s) q.f();
}

function tube3(ctx, a, b, col, width) {
  const z = (a[3] + b[3]) / 2, near = nearOf(z);
  put(z, () => {
    const w = Math.max(0.5, width * (0.5 + 0.75 * near) * (a[2] + b[2]) / 2);
    ctx.strokeStyle = rgba(col, 0.22 + 0.73 * near);
    ctx.lineWidth = w;
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    if (w > 1.5) {
      const o = w * 0.2;
      ctx.strokeStyle = `rgba(255,255,255,${(0.08 + 0.32 * near).toFixed(3)})`;
      ctx.lineWidth = w * 0.3;
      ctx.beginPath(); ctx.moveTo(a[0] - o, a[1] - o); ctx.lineTo(b[0] - o, b[1] - o); ctx.stroke();
    }
  });
}
function line3(ctx, pts, col, width, closed) {
  for (let i = 0; i < pts.length - (closed ? 0 : 1); i++) tube3(ctx, pts[i], pts[(i + 1) % pts.length], col, width);
}
function dot3(ctx, p, rad, col, glow) {
  put(p[3] - 0.002, () => {
    const s = Math.max(0.6, rad * p[2]);
    if (glow) drawGlow(ctx, p[0], p[1], s * 4.2, col, 0.6);
    if (s < 1.6) {
      ctx.fillStyle = glow ? "#fff" : rgba(col, 0.35 + 0.6 * nearOf(p[3]));
      ctx.beginPath(); ctx.arc(p[0], p[1], s, 0, TAU); ctx.fill();
      return;
    }
    drawSphere(ctx, p[0], p[1], s, col, glow ? 1 : 0.45 + 0.55 * nearOf(p[3]));
    if (glow) {
      ctx.fillStyle = "rgba(255,255,255,.92)";
      ctx.beginPath(); ctx.arc(p[0] - s * 0.15, p[1] - s * 0.15, s * 0.42, 0, TAU); ctx.fill();
    }
  });
}
function face3(ctx, pts, n, col, alpha, glow) {
  let z = 0;
  for (const p of pts) z += p[3];
  z = z / pts.length + 0.001;
  put(z, () => {
    const front = n[2] < 0, lam = Math.max(0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]);
    ctx.fillStyle = glow ? rgba(col, 0.95) : shade(col, Math.round(lam * 24), front ? Math.round(alpha * 20) : Math.round(alpha * 5.6), front);
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath(); ctx.fill();
    if (glow) drawGlow(ctx, (pts[0][0] + pts[2][0]) / 2, (pts[0][1] + pts[2][1]) / 2, Math.hypot(pts[0][0] - pts[2][0], pts[0][1] - pts[2][1]) * 1.6, col, 0.7);
  });
}
const shades = new Map();
function shade(col, l24, a20, front) {
  const key = col + "|" + l24 + "|" + a20 + "|" + front;
  let s = shades.get(key);
  if (s) return s;
  const lam = l24 / 24, k = 0.3 + 0.7 * lam, sp = front ? Math.pow(lam, 12) * 150 : 0, [r0, g0, b0] = hexToRgb(col);
  const c = (v) => Math.min(255, Math.round(v * k + sp));
  s = `rgba(${c(r0)},${c(g0)},${c(b0)},${(a20 / 20).toFixed(2)})`;
  if (shades.size > 20000) shades.clear();
  shades.set(key, s);
  return s;
}
function box3(ctx, P, N, c, h, col, alpha) {
  const at = (s) => P([c[0] + s[0] * h[0], c[1] + s[1] * h[1], c[2] + s[2] * h[2]]);
  for (const f of BOX) face3(ctx, f[0].map(at), N(f[1]), col, alpha);
}
const BOX = [
  [[[1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]], [1, 0, 0]],
  [[[-1, -1, -1], [-1, -1, 1], [-1, 1, 1], [-1, 1, -1]], [-1, 0, 0]],
  [[[-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]], [0, 1, 0]],
  [[[-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1]], [0, -1, 0]],
  [[[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], [0, 0, 1]],
  [[[-1, -1, -1], [-1, 1, -1], [1, 1, -1], [1, -1, -1]], [0, 0, -1]],
];
function disc3(ctx, P, N, x, rad, col, alpha) {
  const pts = [];
  for (let i = 0; i < 14; i++) { const u = (i / 14) * TAU; pts.push(P([x, rad * Math.cos(u), rad * Math.sin(u)])); }
  face3(ctx, pts, N([Math.sign(x) || 1, 0, 0]), col, alpha);
}
const torusPt = (a, b, R, rr) => [(R + rr * Math.cos(b)) * Math.cos(a), rr * Math.sin(b), (R + rr * Math.cos(b)) * Math.sin(a)];
function torusFaces(ctx, P, N, R, rr, m1, m2, col, alpha, lit, xf) {
  const f = xf || ((v) => v);
  for (let i = 0; i < m1; i++) for (let j = 0; j < m2; j++) {
    const a0 = (i / m1) * TAU, a1 = ((i + 1) / m1) * TAU, b0 = (j / m2) * TAU, b1 = ((j + 1) / m2) * TAU;
    const am = (a0 + a1) / 2, bm = (b0 + b1) / 2;
    face3(ctx, [P(f(torusPt(a0, b0, R, rr))), P(f(torusPt(a1, b0, R, rr))), P(f(torusPt(a1, b1, R, rr))), P(f(torusPt(a0, b1, R, rr)))],
      N(f([Math.cos(bm) * Math.cos(am), Math.sin(bm), Math.cos(bm) * Math.sin(am)])), col, alpha, !!lit && lit[0] === i && lit[1] === j);
  }
}
const aboutX = (q) => { const c = Math.cos(q), s = Math.sin(q); return (v) => [v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c]; };
const fibPt = (i, n, R) => {
  const z = 1 - (2 * (i + 0.5)) / n, rad = Math.sqrt(1 - z * z), a = i * 2.399963;
  return [R * rad * Math.cos(a), R * z, R * rad * Math.sin(a)];
};
const OCTA = [[0, -0.85, 0], [0.62, 0, 0], [0, 0, 0.62], [-0.62, 0, 0], [0, 0, -0.62], [0, 0.85, 0]];
const OCTA_F = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 1], [5, 2, 1], [5, 3, 2], [5, 4, 3], [5, 1, 4]];

function solid(type) {
  return ["cycle", "torus", "gear", "crt", "odds", "invented", "thing", "circuit", "general", "topic", "seen",
    "word"].includes(type);
}

function drawCell3D(ctx, type, x, y, r, o) {
  if (!solid(type) || (o.px != null && o.px < 6)) return drawCell(ctx, type, x, y, r, o);
  const t = o.t || 0, rate = o.rate == null ? 0.8 : o.rate, col = C[type] || C.accent;
  const at = Array.isArray(o.at) && o.at.length ? o.at.map((v) => Math.max(0, v | 0)) : null;
  const moving = !at && !Object.prototype.hasOwnProperty.call(o, "at");
  const place = (i, d) => (at && at[i] != null ? at[i] % d : 0);
  const cyc = (o.cycles && o.cycles.length ? o.cycles : [6]).map((v) => Math.max(1, v | 0));
  const yaw = (o.phase || 0) * TAU + t * 0.35, tilt = D3.tilt;
  const tip = aboutX(0.45 + 0.5 * (o.phase || 0));
  const P = (p) => proj3(x, y, r, rot3(tip(p), yaw, tilt)), N = (v) => rot3(tip(v), yaw, tilt);
  const fine = (o.px == null ? 2 * r : o.px) > 22;
  const lw = Math.max(0.7, r * 0.05);
  ctx.save();
  ctx.lineCap = "round";
  drawGlow(ctx, x, y, r * 1.05, col, C.light ? 0.08 : 0.14);
  SCN = [];
  if (type === "cycle") {
    const d = cyc[0], n = Math.min(d, fine ? 48 : 24), R = 0.8;
    torusFaces(ctx, P, N, R, 0.075, fine ? 40 : 18, fine ? 6 : 3, col, 0.85);
    for (let i = 0; i < n; i++) { const a = ((i + 0.5) / n) * TAU; dot3(ctx, P([R * Math.cos(a), 0, R * Math.sin(a)]), r * (n > 24 ? 0.07 : 0.1), col); }
    line3(ctx, [P([0, -0.38, 0]), P([0, 0.38, 0])], col, lw, false);
    const p = moving ? tickPos(t * rate) % d : place(0, d), a = ((p + 0.5) / d) * TAU;
    dot3(ctx, P([R * Math.cos(a), 0, R * Math.sin(a)]), r * 0.14, col, true);
  } else if (type === "torus" || type === "gear" || type === "crt") {
    const d1 = cyc[0], d2 = cyc[1] || cyc[0], R0 = 0.58, rr = 0.28;
    if (cyc.length >= 3 && type === "torus") {
      cloud3D(ctx, x, y, r, cyc, col, t, moving ? rate : 0, P, lw, at);
    } else {
      let a, b;
      const tick = tickPos(t * rate * (type === "gear" ? 1.6 : 1));
      if (type === "gear") {
        a = ((tick % d1) / d1) * TAU;
        b = ((Math.floor(tick / d1) % d2) / d2) * TAU;
      } else {
        a = ((tick % d1) / d1) * TAU;
        b = (((type === "crt" ? tick : tick / 3) % d2) / d2) * TAU;
      }
      if (!moving) {
        a = (place(0, d1) / d1) * TAU;
        b = (place(1, d2) / d2) * TAU;
      }
      const m1 = Math.min(d1, fine ? 16 : 8), m2 = Math.min(d2, fine ? 10 : 5);
      torusFaces(ctx, P, N, R0, rr, m1, m2, col, 0.6, [Math.floor((a / TAU) * m1 + 1e-6) % m1, Math.floor((b / TAU) * m2 + 1e-6) % m2]);
      if (type === "gear") {
        for (let i = 0; i < m1; i++) {
          const u = ((i + 0.5) / m1) * TAU;
          line3(ctx, [P(torusPt(u, 0, R0, rr)), P(torusPt(u, 0, R0 + 0.16, rr))], col, lw * 2.2, false);
        }
      } else if (type === "crt") {
        const L = Math.min(d1 * d2, fine ? 240 : 120), knot = [];
        for (let k = 0; k <= L; k++) { const s = (k / L) * d1 * d2; knot.push(P(torusPt((s / d1) * TAU, (s / d2) * TAU, R0, rr * 1.08))); }
        line3(ctx, knot, col, lw * 1.2, false);
      }
      dot3(ctx, P(torusPt(a, b, R0, rr * 1.12)), r * 0.1, col, true);
    }
  } else if (type === "odds") {
    const vals = Math.max(2, Math.min(48, cyc[0] || 6)), dwell = Math.max(1, cyc[1] || 2);
    for (let i = 0; i < vals; i++) dot3(ctx, P(fibPt(i, vals, 0.8)), r * (vals > 24 ? 0.06 : 0.085), col);
    const ring = [];
    for (let i = 0; i <= 40; i++) { const a = (i / 40) * TAU; ring.push(P([0.84 * Math.cos(a), 0, 0.84 * Math.sin(a)])); }
    line3(ctx, ring, col, lw * 0.8, true);
    const face = Math.floor((t * rate * 3) / dwell), i = moving ? (face * 7 + 3) % vals : place(0, vals);
    dot3(ctx, P(fibPt(i, vals, 0.8)), r * 0.13, col, true);
  } else if (type === "thing") {
    const k = Math.max(2, Math.min(5, cyc[0] || 2)), c0 = P([0, 0, 0]);
    for (let i = 0; i < k; i++) {
      const a = (i / k) * TAU, c = P([0.55 * Math.cos(a), 0.25 * Math.sin(2 * a), 0.55 * Math.sin(a)]);
      line3(ctx, [c0, c], col, lw * 1.8, false);
      dot3(ctx, c, r * 0.17, col);
    }
    dot3(ctx, c0, r * 0.15, col, true);
  } else if (type === "circuit") {
    const k = Math.max(2, Math.min(6, (o.members || []).length || o.n || 3)), pts = [];
    const H = (u) => P([0.72 * Math.cos(u * TAU * 1.5), -0.7 + 1.4 * u, 0.72 * Math.sin(u * TAU * 1.5)]);
    for (let s = 0; s <= (fine ? 80 : 40); s++) pts.push(H(s / (fine ? 80 : 40)));
    line3(ctx, pts, col, lw * 1.8, false);
    for (let i = 0; i < k; i++) dot3(ctx, H(i / (k - 1)), r * 0.11, col);
    dot3(ctx, H(moving ? ((t * rate * 0.3) % 1 + 1) % 1 : 0), r * 0.12, col, true);
  } else if (type === "invented") {
    machine3D(ctx, o.nature || "", r, col, t, moving ? rate : 0, P, lw, N);
  } else if (type === "word") {
    const v = OCTA.map(P);
    for (const f of OCTA_F) face3(ctx, f.map((i) => v[i]), N(unit3([0, 1, 2].map((q) => OCTA[f[0]][q] + OCTA[f[1]][q] + OCTA[f[2]][q]))), col, o.means ? 0.82 : 0.62);
    if (o.means) dot3(ctx, P([0, 0, 0]), r * 0.13, col, true);
  } else if (type === "seen") {
    box3(ctx, P, N, [0, 0, 0], [0.58, 0.58, 0.58], col, 0.34);
    const k = Math.max(2, Math.min(4, cyc[0] || 3));
    for (let i = 0; i < k; i++) for (let j = 0; j < k; j++) {
      dot3(ctx, P([-0.58 + (1.16 * (i + 0.5)) / k, -0.58 + (1.16 * (j + 0.5)) / k, 0]), r * 0.07, col);
    }
  } else if (type === "topic") {
    for (let i = 0; i < 14; i++) dot3(ctx, P(fibPt(i, 14, 0.75)), r * 0.08, col);
    const ring = [];
    for (let i = 0; i <= 40; i++) { const a = (i / 40) * TAU; ring.push(P([0.8 * Math.cos(a), 0.24 * Math.sin(a), 0.8 * Math.sin(a)])); }
    line3(ctx, ring, col, lw * 1.2, true);
    dot3(ctx, P([0, 0, 0]), r * 0.12, col, true);
  } else if (type === "general") {
    for (let k = 0; k < 3; k++) torusFaces(ctx, P, N, 0.78, 0.055, fine ? 36 : 16, fine ? 5 : 3, col, 0.8, null, aboutX(Math.PI / 2 + (k / 3) * Math.PI));
    const d = cyc[0] || 12, p = moving ? tickPos(t * rate) % d : place(0, d), a = ((p + 0.5) / d) * TAU;
    dot3(ctx, P([0.78 * Math.cos(a), 0.78 * Math.sin(a), 0]), r * 0.12, col, true);
  }
  flush3();
  if (type === "seen" && o.img && o.img.complete && o.img.naturalWidth && r > 10) {
    const s = r * 0.55;
    ctx.globalAlpha *= 0.85;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(o.img, x - s / 2, y - s / 2, s, s);
  }
  ctx.restore();
  const sym = o.symbol || "";
  if (sym && (o.px == null || o.px > 13)) {
    const R = o.fr || r;
    const fs = Math.round(2 * Math.max(6, Math.min(R * 0.42, (R * 1.9) / Math.max(2, sym.length)))) / 2;
    ctx.fillStyle = C.light ? "rgba(255,255,255,.82)" : "rgba(8,12,26,.66)";
    const w = sym.length * fs * 0.58 + 8;
    roundRect(ctx, x - w / 2, y + r * 0.95 - fs * 0.62, w, fs * 1.24, fs * 0.5);
    ctx.fill();
    text(ctx, x, y + r * 0.95, sym, fs, C.text, 750);
  }
}

function cloud3D(ctx, x, y, r, cyc, col, t, rate, P, lw, at) {
  const k = cyc.length, dirs = [];
  for (let i = 0; i < 2 * k; i++) dirs.push(fibPt(i, 2 * k, 1));
  const place = (vals) => {
    const p = [0, 0, 0];
    vals.forEach((v, i) => {
      const a = (v / cyc[i]) * TAU, c = Math.cos(a), s = Math.sin(a);
      for (let q = 0; q < 3; q++) p[q] += (c * dirs[2 * i][q] + s * dirs[2 * i + 1][q]) * 0.8 / Math.sqrt(k);
    });
    return P(p);
  };
  const per = Math.max(2, Math.floor(Math.pow(400, 1 / k)));
  const counts = cyc.map((d) => Math.min(d, per)), total = counts.reduce((a, b) => a * b, 1);
  for (let n = 0; n < total; n++) {
    let rem = n;
    const vals = counts.map((c, i) => { const s = rem % c; rem = Math.floor(rem / c); return (s / c) * cyc[i]; });
    dot3(ctx, place(vals), r * 0.045, col);
  }
  const tick = tickPos(t * rate), now = at ? cyc.map((d, i) => (at[i] || 0) % d)
    : cyc.map((d, i) => Math.floor(tick / Math.pow(3, i)) % d);
  dot3(ctx, place(now), r * 0.11, col, true);
}

function machine3D(ctx, nat, r, col, t, rate, P, lw, N) {
  const sw = Math.sin(t * rate * Math.PI);
  if (nat.startsWith("made")) {
    const k = 6, pts = [];
    for (let i = 0; i < k; i++) pts.push(P(fibPt(i, k, 0.7)));
    for (let i = 0; i < k; i++) line3(ctx, [pts[i], pts[(i * 2 + 1) % k]], col, lw * 1.4, false);
    pts.forEach((p) => dot3(ctx, p, r * 0.1, col));
    dot3(ctx, pts[(Math.floor(t * rate * 1.2) * 2 + 1) % k], r * 0.13, col, true);
  } else if (nat.includes("pile")) {
    for (let i = 0; i < 4; i++) {
      if (i === 3 && Math.abs(sw) < 0.3) continue;
      const w = 0.7 - i * 0.1;
      box3(ctx, P, N, [0, 0.5 - i * 0.28, 0], [w, 0.09, w], col, i === 3 ? 0.4 + 0.5 * Math.abs(sw) : 0.72);
    }
  } else if (nat.includes("bit")) {
    const a = P([0, -0.7, 0]), b = P([0, 0.7, 0]);
    line3(ctx, [a, b], col, lw * 1.6, false);
    dot3(ctx, sw >= 0 ? b : a, r * 0.15, col, true);
    dot3(ctx, sw >= 0 ? a : b, r * 0.11, col);
  } else if (nat.startsWith("walls")) {
    disc3(ctx, P, N, -0.75, 0.36, col, 0.7);
    disc3(ctx, P, N, 0.75, 0.36, col, 0.7);
    line3(ctx, [P([-0.75, 0, 0]), P([0.75, 0, 0])], col, lw * 1.6, false);
    dot3(ctx, P([0.6 * sw, 0, 0]), r * 0.14, col, true);
  } else {
    line3(ctx, [P([-0.85, 0, 0]), P([0.7, 0, 0])], col, lw * 1.6, false);
    const tip = P([0.95, 0, 0]), base = [];
    for (let i = 0; i < 8; i++) { const u = (i / 8) * TAU; base.push([0.7, 0.14 * Math.cos(u), 0.14 * Math.sin(u)]); }
    for (let i = 0; i < 8; i++) {
      const p = base[i], q = base[(i + 1) % 8], um = ((i + 0.5) / 8) * TAU;
      face3(ctx, [tip, P(p), P(q)], N(unit3([0.5, Math.cos(um), Math.sin(um)])), col, 0.85);
    }
    const ph = ((t * rate * 0.5) % 1 + 1) % 1;
    dot3(ctx, P([-0.85 + 1.6 * ph, 0, 0]), r * 0.14, col, true);
  }
}

function lattice(ctx, x, y, r, cyc, col, t) {
  ctx.fillStyle = rgba(col, 0.85);
  if (cyc.length >= 2) {
    const a = Math.min(cyc[0], 6), b = Math.min(cyc[1], 6);
    for (let i = 0; i < a; i++) for (let j = 0; j < b; j++) {
      const px = x - r * 0.7 + (r * 1.4 * (i + 0.5)) / a, py = y - r * 0.75 + (r * 1.1 * (j + 0.5)) / b;
      ctx.beginPath(); ctx.arc(px, py, Math.max(0.8, r * 0.07), 0, TAU); ctx.fill();
    }
  } else {
    const n = Math.max(2, Math.min(cyc[0] || 4, 10));
    ctx.strokeStyle = rgba(col, 0.9);
    ctx.lineWidth = Math.max(0.8, r * 0.08);
    ctx.beginPath();
    for (let i = 0; i <= 40; i++) {
      const px = x - r * 0.8 + (r * 1.6 * i) / 40;
      const py = y - r * 0.18 + Math.sin((i / 40) * TAU * Math.min(n, 4) / 2 + t * 1.5) * r * 0.32;
      i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.stroke();
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

const icons = new Set();
const iconsSeen = new Set();                          // (icons on screen now: only they are painted)
const iconWatch = typeof IntersectionObserver !== "undefined"
  ? new IntersectionObserver((es) => es.forEach((e) => (e.isIntersecting ? iconsSeen.add(e.target) : iconsSeen.delete(e.target))))
  : null;
let iconsAt = 0;
function iconCanvas(cv, type, o) {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = cv.clientWidth || parseInt(cv.getAttribute("width") || "24", 10);
  cv.width = w * dpr;
  cv.height = w * dpr;
  const item = { cv, type, o: Object.assign({ small: true }, o || {}), w, dpr };
  paintIcon(item, 0);
  if (item.o.animate) { icons.add(item); if (iconWatch) iconWatch.observe(cv); }
  return item;
}
function paintIcon(item, t) {
  const { cv, type, o, w, dpr } = item;
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, w);
  const r = type === "word" ? w * 0.3 : w * 0.44;
  const deep = w >= 18 && solid(type);
  if (deep) drawSphere(ctx, w / 2, w / 2, r * 0.85, C[type] || C.accent, C.light ? 0.22 : 0.3);
  (deep ? drawCell3D : drawCell)(ctx, type, w / 2, w / 2, deep ? r * 0.85 : r, Object.assign({}, o, { t }));
}
function tickIcons(t) {
  if (t - iconsAt < 1 / 15) return;                   // (small icons: 15 frames a second is smooth enough)
  iconsAt = t;
  for (const item of icons) {
    if (!item.cv.isConnected) { icons.delete(item); iconsSeen.delete(item.cv); if (iconWatch) iconWatch.unobserve(item.cv); continue; }
    if (iconWatch && !iconsSeen.has(item.cv)) continue;   // (hidden or scrolled away: not painted)
    paintIcon(item, t);
  }
}

function lawColor(code) {
  let h = 0;
  for (const ch of String(code)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return `hsl(${(h * 47) % 360}, ${C.light ? 68 : 78}%, ${C.light ? 44 : 64}%)`;
}
function linkStyle(type) {
  if (type === "law:cause") return { color: C.odds, dash: [], base: 0.5, width: 2.0 };
  if (type === "law:fore") return { color: C.odds, dash: [], base: 0.42, width: 1.6 };
  if (type === "law:seeks" || type === "law:flees") return { color: C.thing, dash: type === "law:flees" ? [4, 3] : [], base: 0.5, width: 1.9 };
  if (String(type).startsWith("law:")) return { color: lawColor(type.slice(4)), dash: [], base: 0.4, width: 1.7 };
  switch (type) {
    case "lived": return { color: C.lived, dash: [], base: 0.16, width: 1.1 };
    case "read": return { color: C.read, dash: [], base: 0.18, width: 1.0 };
    case "kin": return { color: C.kin, dash: [], base: 0.12, width: 0.7 };
    case "kindof": return { color: C.kindof, dash: [], base: 0.3, width: 1.1 };
    case "part": return { color: C.part, dash: [], base: 0.36, width: 1.2 };
    case "about": return { color: C.about, dash: [], base: 0.2, width: 0.9 };
    case "means": return { color: C.means, dash: [], base: 0.42, width: 1.3 };
    case "assoc": return { color: C.assoc, dash: [], base: 0.24, width: 0.9 };
    default: return { color: C.rel, dash: [], base: 0.18, width: 0.8 };
  }
}
function linkIcon(svgEl, type) {
  const s = linkStyle(type);
  svgEl.setAttribute("viewBox", "0 0 26 26");
  while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", "M3 18 Q13 4 23 12");
  p.setAttribute("fill", "none");
  p.setAttribute("stroke", s.color);
  p.setAttribute("stroke-width", type === "means" ? "2.2" : "1.8");
  p.setAttribute("stroke-linecap", "round");
  if (s.dash.length) p.setAttribute("stroke-dasharray", s.dash.join(" "));
  svgEl.appendChild(p);
  if (type === "means") {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("cx", "23"); c.setAttribute("cy", "12"); c.setAttribute("r", "2.6"); c.setAttribute("fill", s.color);
    svgEl.appendChild(c);
  }
}

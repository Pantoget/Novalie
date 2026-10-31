# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's inventor on its graphics card."""
import array
import ctypes
import itertools
import math
import os
import time

from . import gpu as gpu

SRC = r"""
typedef unsigned long long u64;
#define NONEV (-2147483647 - 1)
#define MAXD 32
#define MAXM 64

__device__ __forceinline__ int moved(int nat, int n, int v, int d) {
    if (nat == 0) return v + d;
    if (nat == 1) { int x = (v + d) % n; return x < 0 ? x + n : x; }
    int x = v + d; return x < 0 ? 0 : (x > n - 1 ? n - 1 : x);
}

__device__ __forceinline__ void apply(const int* __restrict__ ops, int oi, const int* __restrict__ tables,
                                      const int* nat, const int* sz, int* regs, int* pile, int& ph) {
    const int* op = ops + 6 * oi;
    while (op[0] == 7) op = ops + 6 * (regs[op[1]] == 0 ? op[4] : op[5]);
    int a = op[1], b = op[2], d = op[3];
    switch (op[0]) {
    case 1: regs[a] = moved(nat[a], sz[a], regs[a], d); break;
    case 2: regs[a] = 0; break;
    case 3: regs[a] = 1 - regs[a]; break;
    case 4: if (regs[a] > 0 && moved(nat[b], sz[b], regs[b], 1) != regs[b]) { regs[a] -= 1; regs[b] += 1; } break;
    case 5: pile[ph++] = d; break;
    case 6: if (ph > 0) ph--; break;
    case 8: pile[ph++] = regs[a]; break;
    case 9: if (ph > 0) { regs[a] = pile[ph - 1]; ph--; } break;
    case 10: regs[b] = regs[a]; break;
    case 11: { int old = regs[a]; int nw = moved(nat[a], sz[a], old, d); regs[a] = nw;
               if ((d > 0 && nw < old) || (d < 0 && nw > old)) regs[b] = moved(nat[b], sz[b], regs[b], d > 0 ? 1 : -1); }
             break;
    case 12: { int v = regs[a]; regs[a] = (v == NONEV) ? NONEV : tables[op[4] + v]; } break;
    case 13: { int v = regs[a]; regs[a] = regs[b]; regs[b] = v; } break;
    default: break;
    }
}

__device__ __forceinline__ int see(const int* f, const int* regs, const int* pile, int ph) {
    int v;
    switch (f[0]) {
    case 0: return regs[f[1]];
    case 1: return regs[f[1]] == 0;
    case 2: v = regs[f[1]]; return (v > 0) - (v < 0);
    case 3: v = regs[f[1]] % f[2]; return v < 0 ? v + f[2] : v;
    case 4: return ph > 0 ? pile[ph - 1] : NONEV;
    case 5: return ph == 0;
    case 7: v = regs[f[1]] - regs[f[2]]; return (v > 0) - (v < 0);
    default: return ph;
    }
}

extern "C" __global__ void mech_dfs(
    const int* __restrict__ acts, const int* __restrict__ obs, const double* __restrict__ gain,
    const int* __restrict__ first, const int* __restrict__ kinds, const int* __restrict__ ops,
    const int* __restrict__ tables, const int* __restrict__ looks, const int* __restrict__ starts,
    const int* __restrict__ evb, const int* __restrict__ evt, const int* __restrict__ eva,
    const int* __restrict__ evf, const int* __restrict__ cfg, const u64* __restrict__ cfg64,
    unsigned char* st_dig, int* st_flag, int* st_from, u64* st_count,
    int* mstamp, short* msym, int* tstamp, int* pile_slab,
    u64* shared_cnt, u64* root_cnt,
    unsigned char* out_dig, u64* out_unit, double* out_ev, int* out_info, unsigned int* out_n,
    int* pending, u64* stats)
{
    // One step of one mechanism per turn of the loop, whatever each thread is doing: a thread whose mechanism has
    // failed takes the next one at once, and does not wait for the others of its warp to fail theirs.
    const int T = cfg[0], k = cfg[1], half = cfg[2], allowed = cfg[3], nregs = cfg[4], KEEPOP = cfg[5];
    const int S = cfg[6], D = cfg[7], P = cfg[8], VS = cfg[9], VLO = cfg[10], SM = cfg[11];
    const int REG = cfg[12], PS = cfg[13], DW = cfg[14], cap = cfg[15], budget = cfg[16];
    const u64 UPR = cfg64[0], u0 = cfg64[1], u1 = cfg64[2];
    const int tid = blockIdx.x * blockDim.x + threadIdx.x;
    const int nth = gridDim.x * blockDim.x;
    int* my_st = mstamp + (size_t)tid * REG;
    short* my_sy = msym + (size_t)tid * REG;
    int* pile = pile_slab + (size_t)tid * PS;
    int stamp = tstamp[tid];
    int nat[2] = {0, 0}, sz[2] = {1, 1};
    for (int i = 0; i < nregs; i++) { nat[i] = kinds[2 * i]; sz[i] = kinds[2 * i + 1]; }
    long long steps = 0, sims = 0;
    u64 counted = 0;
    unsigned char dig[MAXD];
    int opidx[MAXM];
    u64 u = u0 + tid, root = 0, cnt = 0;
    size_t ui = 0;
    int flag = 0, from = 0, li = 0, si = 0;
    const int* lk = looks;
    bool have = false, fresh = true;
    int t = 0, ph = 0, msum = 0, late = 0;
    int regs[2] = {0, 0};
    double ev = 0.0;
    while (true) {
        if (!have) {                                  // the next beginning of its own
            while (u < u1 && st_flag[(size_t)(u - u0)] >= 2) u += nth;
            if (u >= u1) break;
            if (steps >= budget) { atomicAdd(pending, 1); break; }
            ui = (size_t)(u - u0);
            flag = st_flag[ui];
            root = u / UPR;
            u64 pre = u % UPR;
            li = (int)(root / (u64)S); si = (int)(root % (u64)S);
            for (int e = P - 1; e >= 0; e--) { const u64 A = (u64)eva[e]; dig[e] = (unsigned char)(pre % A); pre /= A; }
            if (flag == 0) { for (int e = P; e < D; e++) dig[e] = 0; from = P; cnt = 0; }
            else { for (int e = P; e < D; e++) dig[e] = st_dig[ui * DW + (e - P)]; from = st_from[ui]; cnt = st_count[ui]; }
            lk = looks + (size_t)li * k * 3;
            have = true; fresh = true;
        }
        if (fresh) {                                  // a mechanism begins: where its hidden part starts, its symbols
            for (int e = 0; e < D; e++) opidx[evb[e]] = evf[e] ? (int)dig[e] : KEEPOP;
            stamp++;
            for (int i = 0; i < nregs; i++) regs[i] = starts[(size_t)si * nregs + i];
            ph = 0; msum = 0; late = 0; t = 0; ev = 0.0;
            bool over = false;
            for (int j = 0; j < k; j++) {
                const int v = see(lk + 3 * j, regs, pile, ph);
                const int s = (v == NONEV) ? VS - 1 : v - VLO;
                if (v != NONEV && (s < 0 || s >= VS - 1)) { over = true; break; }
                my_st[j * VS + s] = stamp; my_sy[j * VS + s] = (short)first[j]; msum++;
            }
            if (over) { st_flag[ui] = 3; atomicAdd(pending, 1 << 20); have = false; u += nth; continue; }
            fresh = false;
        }
        apply(ops, opidx[acts[t]], tables, nat, sz, regs, pile, ph);   // one press, and what it sees after it
        const int* o = obs + (size_t)t * k;
        int res = 0;
        for (int j = 0; j < k; j++) {
            const int v = see(lk + 3 * j, regs, pile, ph);
            const int s = (v == NONEV) ? VS - 1 : v - VLO;
            if (v != NONEV && (s < 0 || s >= VS - 1)) { res = 2; break; }
            const int idx = j * VS + s;
            if (my_st[idx] != stamp) {
                my_st[idx] = stamp; my_sy[idx] = (short)o[j]; msum++;
                if (t >= half && ++late > allowed) { res = 1; break; }
            } else if (my_sy[idx] != (short)o[j]) { res = 1; break; }
            else ev += gain[j * SM + o[j]];
        }
        steps++;
        if (res == 0 && ++t < T) continue;
        if (res == 2) { st_flag[ui] = 3; atomicAdd(pending, 1 << 20); have = false; u += nth; continue; }
        const int tf = (res == 1) ? t : T;            // this mechanism is over: it failed at tf, or saw it all
        sims++;
        if (tf == T && ev >= 6.0) {
            const unsigned int w = atomicAdd(out_n, 1u);
            if (w < (unsigned int)cap) {
                for (int e = 0; e < D; e++) out_dig[(size_t)w * D + e] = dig[e];
                out_unit[w] = u; out_ev[w] = ev; out_info[2 * w] = late; out_info[2 * w + 1] = msum;
            }
        }
        int q = -1;
        for (int e = 0; e < D; e++) { if (evt[e] <= tf) q = e; else break; }
        bool done = false;
        if (flag == 0) {
            flag = 1;
            for (int e = 0; e < P; e++) {
                if (evt[e] <= tf) atomicAdd(&shared_cnt[(size_t)root * P + e], 1ull); else break;
            }
            if (q < P) done = true;
        }
        if (!done) {
            for (int e = from; e <= q; e++) { cnt += (u64)eva[e]; counted += (u64)eva[e]; }
            int e2 = q;                               // the next mechanism, as its processor would take it
            while (e2 >= P && (int)dig[e2] + 1 >= eva[e2]) { dig[e2] = 0; e2--; }
            if (e2 < P) done = true;
            else {
                dig[e2]++;
                for (int e = e2 + 1; e < D; e++) dig[e] = 0;
                from = e2 + 1;
            }
        }
        if (done) {
            st_flag[ui] = 2; atomicAdd(&root_cnt[root], cnt);
            have = false; u += nth;
            continue;
        }
        if (steps >= budget) {                        // its turn is over: where it is, kept for the next launch
            st_flag[ui] = flag; st_from[ui] = from; st_count[ui] = cnt;
            for (int e = P; e < D; e++) st_dig[ui * DW + (e - P)] = dig[e];
            atomicAdd(pending, 1);
            break;
        }
        fresh = true;
    }
    tstamp[tid] = stamp;
    atomicAdd(&stats[0], (u64)steps);
    atomicAdd(&stats[1], (u64)sims);
    atomicAdd(&stats[2], counted);
}
"""

MAXD, MAXM, MAXK = 32, 64, 4
TARGET_UNITS = 1 << 16
BATCH = 1 << 20
STEPS = 1 << 20
OUT_CAP = 1 << 20
STATE = {"steps": 1 << 14}
USE = {"searches": 0, "tried": 0, "mechanisms": 0, "seconds": 0.0}


def memory_for(c, reg, ps):
    """Its threads' memory on the card."""
    slab = STATE.get("slab")
    if slab is not None and slab["reg"] >= reg and slab["ps"] >= ps and slab["uses"] < 1800:
        return slab
    if slab is not None:
        reg, ps = max(reg, slab["reg"]), max(ps, slab["ps"])
        c.free(slab["st"], slab["sy"], slab["ts"], slab["pile"])
        STATE.pop("slab", None)
    per = 6 * reg + 4 * ps + 4
    room = c.room()
    from . import invent as novalie_invent
    promised = novalie_invent.commit_gb()
    if promised:
        room = min(room, int(max(0.0, promised[1] - novalie_invent.reserve_gb(promised[0])) * 2 ** 30) // 2)
    threads = min(c.sms * 1024, room // per) // 128 * 128
    if threads < 128:
        return None
    try:
        st, sy = c.alloc(4 * threads * reg), c.alloc(2 * threads * reg)
        ts, pl = c.alloc(4 * threads), c.alloc(4 * threads * ps)
    except RuntimeError:
        return None
    c.clear(st, 4 * threads * reg)
    c.clear(ts, 4 * threads)
    slab = STATE["slab"] = {"st": st, "sy": sy, "ts": ts, "pile": pl, "reg": reg, "ps": ps, "threads": threads,
                            "uses": 0, "bytes": per * threads}
    return slab


def ready():
    """Its card and its compiler both here."""
    if "fn" in STATE:
        return STATE["fn"]
    STATE["fn"] = None
    c = gpu.card()
    if c is None:
        return None
    try:
        prog = c.program(SRC, ["mech_dfs"])
    except Exception as e:
        STATE["error"] = f"{type(e).__name__}: {e}"[:300]
        return None
    if prog:
        STATE["fn"] = prog["mech_dfs"]
    return STATE["fn"]


def encode_op(x, tables):
    """One operation of its alphabet as six numbers for the card."""
    k = x[0]
    if k == "keep":
        return [0, 0, 0, 0, 0, 0]
    if k == "add":
        return [1, x[1], 0, x[2], 0, 0]
    if k == "zero":
        return [2, x[1], 0, 0, 0, 0]
    if k == "flip":
        return [3, x[1], 0, 0, 0, 0]
    if k == "pass":
        return [4, x[1], x[2], 0, 0, 0]
    if k == "put":
        return [5, 0, 0, x[1], 0, 0]
    if k == "take":
        return [6, 0, 0, 0, 0, 0]
    if k == "push":
        return [8, x[1], 0, 0, 0, 0]
    if k == "pop":
        return [9, x[1], 0, 0, 0, 0]
    if k == "copy":
        return [10, x[1], x[2], 0, 0, 0]
    if k == "carry":
        return [11, x[1], x[2], x[3], 0, 0]
    if k == "go":
        at = len(tables)
        tables.extend(-2 ** 31 if v is None else v for v in x[2])
        return [12, x[1], 0, 0, at, 0]
    if k == "swap":
        return [13, x[1], x[2], 0, 0, 0]
    raise ValueError(k)


SIGHT = {"value": 0, "at zero": 1, "sign": 2, "mod": 3, "top": 4, "empty": 5, "height": 6, "cmp": 7}
NATURE = {"free": 0, "cycle": 1, "walls": 2, "bit": 3, "made": 4}


def value_range(shape, options, T):
    """The values its sensors could see, lowest and highest, for its memory of symbols on the card."""
    kinds, _ = shape
    big = 8 + 2 * T
    regs = []
    for kd in kinds:
        if kd[0] == "free":
            regs.append((-big, big))
        elif kd[0] == "bit":
            regs.append((0, 1))
        else:
            regs.append((0, kd[1] - 1))
    nums = [regs[r] for r, kd in enumerate(kinds) if kd[0] not in ("bit", "made")]
    pile = (min([0] + [lo for lo, _ in nums]), max([2] + [hi for _, hi in nums]))
    lo, hi = 0, 1
    for f in options:
        r = {"value": lambda: regs[f[1]], "at zero": lambda: (0, 1), "sign": lambda: (-1, 1),
             "mod": lambda: (0, f[2] - 1), "top": lambda: pile, "empty": lambda: (0, 1),
             "height": lambda: (0, T), "cmp": lambda: (-1, 1)}[f[0]]()
        lo, hi = min(lo, r[0]), max(hi, r[1])
    return lo, hi


def search(inv, stream, first, m, shape, sizes, ops, budget, seconds, enough=False, free=None, tried=0):
    """novalie_invent.search for one shape, on its card."""
    fn = ready()
    if fn is None:
        return None
    acts, obs, k = [a for a, _ in stream], [o for _, o in stream], len(first)
    T = len(acts)
    if T == 0 or k == 0 or k > MAXK or m > MAXM:
        return None
    alpha = inv.alphabet(shape, ops)
    if not alpha:
        return None
    pressed = []
    when = {}
    for t, a in enumerate(acts):
        if a not in when:
            when[a] = t
            pressed.append(a)
    D = len(pressed)
    if D > MAXD or len(alpha) > 255:
        return None
    options = inv.sights(shape, sizes)
    looks_all = sorted(itertools.product(options, repeat=k), key=lambda ls: sum(inv.cost(f) for f in ls))
    starts_all = inv.starts(shape)
    kinds, pile_on = shape
    nregs = len(kinds)
    if nregs > 2:
        return None
    t_start, tried_in = time.perf_counter(), tried
    deadline = time.time() + max(0.0, seconds)
    codes = [{} for _ in range(k)]
    every = [first] + obs
    for o in every:
        for j in range(k):
            codes[j].setdefault(o[j], len(codes[j]))
    SM = max(len(c) for c in codes)
    if SM >= 32767:
        return None
    gain = array.array("d", [0.0] * (k * SM))
    for j in range(k):
        cnt = {}
        for o in every:
            cnt[o[j]] = cnt.get(o[j], 0) + 1
        for s, n in cnt.items():
            gain[j * SM + codes[j][s]] = -math.log10(n / len(every))
    obs_c = array.array("i", [codes[j][o[j]] for o in obs for j in range(k)])
    first_c = array.array("i", [codes[j][first[j]] for j in range(k)])
    half = T // 2
    allowed = max(2, int(inv.NEW_AT_MOST * (T - half)))
    tables, rows = [], []

    def put_op(x):
        if x[0] == "if":
            row = [7, x[1], 0, 0, put_op(x[2]), put_op(x[3])]
        else:
            row = encode_op(x, tables)
        rows.append(row)
        return len(alpha) + len(rows)

    flat = []
    for x in alpha:
        flat.extend([7, x[1], 0, 0, put_op(x[2]), put_op(x[3])] if x[0] == "if" else encode_op(x, tables))
    keep_at = len(alpha)
    flat.extend([0] * 6)
    for row in rows:
        flat.extend(row)
    looks_c = array.array("i", [v for ls in looks_all for f in ls
                                for v in (SIGHT[f[0]], f[1] if len(f) > 1 else 0, f[2] if len(f) > 2 else 0)])
    starts_c = array.array("i", [v for regs, _ in starts_all for v in (list(regs) + [0] * (nregs - len(regs)))])
    if nregs == 0:
        starts_c = array.array("i", [0] * len(starts_all))
    kinds_c = array.array("i", [v for kd in kinds for v in (NATURE[kd[0]], kd[1] if len(kd) > 1 else 2)])
    evb = array.array("i", pressed)
    evt = array.array("i", [when[a] for a in pressed])
    evf = array.array("i", [1 if (free is None or a in free) else 0 for a in pressed])
    eva = array.array("i", [len(alpha) if f else 1 for f in evf])
    lo, hi = value_range(shape, options, T)
    VS = hi - lo + 2
    L, S = len(looks_all), len(starts_all)
    R = L * S
    if R == 0:
        return None
    P, UPR = 0, 1
    while P < D and R * UPR < TARGET_UNITS:
        UPR *= eva[P]
        P += 1
    NU = R * UPR
    c = gpu.card()
    with c.lock:
        c.bind()
        slab = memory_for(c, k * VS, T if pile_on else 1)
        if slab is None:
            return None
        threads, REG, PS = slab["threads"], slab["reg"], slab["ps"]
        consts = [c.put(a) for a in (array.array("i", acts), obs_c, gain, first_c, kinds_c or array.array("i", [0]),
                                     array.array("i", flat), array.array("i", tables or [0]), looks_c,
                                     starts_c or array.array("i", [0]), evb, evt, eva, evf)]
        DW = max(1, D - P)
        B = min(BATCH, NU)
        st_dig, st_flag = c.alloc(B * DW), c.alloc(4 * B)
        st_from, st_count = c.alloc(4 * B), c.alloc(8 * B)
        shared = c.alloc(8 * max(1, R * P))
        rootc = c.alloc(8 * R)
        out_dig, out_unit = c.alloc(OUT_CAP * max(1, D)), c.alloc(8 * OUT_CAP)
        out_ev, out_info = c.alloc(8 * OUT_CAP), c.alloc(8 * OUT_CAP)
        out_n, pending, stats = c.alloc(4), c.alloc(4), c.alloc(24)
        cfgp = c.alloc(4 * 17)
        cfg64p = c.alloc(8 * 3)
        c.clear(shared, 8 * max(1, R * P))
        c.clear(rootc, 8 * R)
        c.clear(out_n, 4)
        c.clear(stats, 24)
        U64 = ctypes.c_uint64
        complete, cut_at = True, NU
        args = [(U64, p) for p in consts] + [(U64, cfgp), (U64, cfg64p), (U64, st_dig), (U64, st_flag),
                                             (U64, st_from), (U64, st_count), (U64, slab["st"]), (U64, slab["sy"]),
                                             (U64, slab["ts"]), (U64, slab["pile"]), (U64, shared), (U64, rootc),
                                             (U64, out_dig), (U64, out_unit), (U64, out_ev), (U64, out_info),
                                             (U64, out_n), (U64, pending), (U64, stats)]
        try:
            u0 = 0
            while u0 < NU:
                u1 = min(NU, u0 + B)
                c.clear(st_flag, 4 * (u1 - u0))
                c64 = (ctypes.c_uint64 * 3)(UPR, u0, u1)
                c.ok(c.lib.cuMemcpyHtoD_v2(cfg64p, ctypes.cast(c64, ctypes.c_void_p), 24), "cfg64")
                blocks = (min(threads, u1 - u0) + 127) // 128
                while True:
                    cfg = array.array("i", [T, k, half, allowed, nregs, keep_at, S, D, P, VS, lo, SM, REG, PS, DW,
                                            OUT_CAP, STATE["steps"]])
                    c.ok(c.lib.cuMemcpyHtoD_v2(cfgp, cfg.buffer_info()[0], 4 * len(cfg)), "cfg")
                    c.clear(pending, 4)
                    t0 = time.perf_counter()
                    c.run(fn, blocks, 128, args)
                    dt = time.perf_counter() - t0
                    USE["launches"] = USE.get("launches", 0) + 1
                    USE["longest"] = max(USE.get("longest", 0.0), dt)
                    slab["uses"] += 1
                    left = c.get(pending, "i", 1)[0]
                    if left >= 1 << 20:
                        return None
                    if left == 0:
                        break
                    so_far = tried_in + R + c.get(stats, "Q", 3)[2]
                    if time.time() > deadline or so_far > budget:
                        complete, cut_at = False, u0
                        break
                if not complete:
                    break
                u0 = u1
                if u0 < NU and time.time() > deadline:
                    complete, cut_at = False, u0
                    break
            n_out = c.get(out_n, "I", 1)[0]
            if n_out > OUT_CAP:
                return None
            digs = c.get_bytes(out_dig, n_out * max(1, D))
            units = c.get(out_unit, "Q", n_out)
            evs = c.get(out_ev, "d", n_out)
            info = c.get(out_info, "i", 2 * n_out)
            root_counts = c.get(rootc, "Q", R)
            shared_counts = c.get(shared, "Q", max(1, R * P))
            st = c.get(stats, "Q", 3)
            USE["steps"] = USE.get("steps", 0) + st[0]
            USE["simulated"] = USE.get("simulated", 0) + st[1]
            counted = st[2]
        finally:
            c.free(*consts)
            c.free(st_dig, st_flag, st_from, st_count, shared, rootc, out_dig, out_unit, out_ev, out_info, out_n,
                   pending, stats, cfgp, cfg64p)
    found = {}
    for w in range(n_out):
        found.setdefault(units[w] // UPR, []).append((tuple(digs[w * D:(w + 1) * D]) if D else (), w))
    div = [1] * (P + 1)
    for e in range(P - 1, -1, -1):
        div[e] = div[e + 1] * eva[e]
    base_said = sum(inv.cost(x) for x in kinds) + pile_on
    passed = []
    KEEP = inv.KEEP

    def entry(root, dg, w):
        li, si = divmod(root, S)
        looks = looks_all[li]
        assign = [None] * m
        for e, a in enumerate(pressed):
            assign[a] = alpha[dg[e]] if evf[e] else ("keep",)
        said = base_said + sum(inv.cost(x) for x in assign if x) + sum(inv.cost(f) for f in looks) + info[2 * w + 1]
        return said, -evs[w], shape, assign, looks, starts_all[si], evs[w], info[2 * w]

    if complete:
        for root in range(R):
            tried += 1
            for e in range(P):
                tried += shared_counts[root * P + e] // div[e + 1]
            tried += root_counts[root]
            for dg, w in sorted(found.get(root, ())):
                passed.append(entry(root, dg, w))
                if len(passed) > 4 * KEEP:
                    passed.sort(key=lambda p: (p[0], p[1]))
                    del passed[KEEP:]
            if enough and any(p[6] >= inv.EVIDENCE + math.log10(max(1, tried)) for p in passed):
                break
    else:
        tried += R + counted
        for root in range(R):
            for e in range(P):
                tried += -(-shared_counts[root * P + e] // div[e + 1])
        for root in sorted(found):
            for dg, w in sorted(found[root]):
                passed.append(entry(root, dg, w))
    USE["searches"] += 1
    USE["tried"] += tried - tried_in
    USE["seconds"] += time.perf_counter() - t_start
    with gpu._USE_LOCK:
        gpu.USE["items"] += tried - tried_in
    need = inv.EVIDENCE + math.log10(max(1, tried))
    ok = [p for p in passed if p[6] >= need]
    if not ok:
        return None, tried, complete
    said, _, shape_, assign, looks, start, ev, late = min(ok, key=lambda p: (p[0], p[1]))
    got = replay(inv, stream, first, shape_, assign, looks, start)
    if (got is None or abs(got[2] - ev) > 1e-9 or got[3] != late
            or said != base_said + sum(inv.cost(x) for x in assign if x) + sum(inv.cost(f) for f in looks)
            + sum(len(x) for x in got[0])):
        STATE["disagreed"] = STATE.get("disagreed", 0) + 1
        return None
    maps, state, ev2, late2 = got
    USE["mechanisms"] += 1
    mech = inv.Mechanism(shape_, list(assign), list(looks), maps, state, ev2, tried, said, late2)
    mech.begin = start
    return mech, tried, complete


def replay(inv, stream, first, shape, assign, looks, start):
    """One mechanism followed on its processor through all it saw, as novalie_invent.search follows each."""
    acts, obs = [a for a, _ in stream], [o for _, o in stream]
    k = len(first)
    every = [first] + obs
    gain = []
    for j in range(k):
        cnt = {}
        for o in every:
            cnt[o[j]] = cnt.get(o[j], 0) + 1
        gain.append({s: -math.log10(n / len(every)) for s, n in cnt.items()})
    half = len(acts) // 2
    allowed = max(2, int(inv.NEW_AT_MOST * (len(acts) - half)))
    regs, pile = start
    kinds = shape[0]
    maps = [{inv.see(f, regs, pile): first[j]} for j, f in enumerate(looks)]
    ev, late = 0.0, 0
    for t, a in enumerate(acts):
        regs, pile = inv.act(assign[a], kinds, regs, pile)
        o = obs[t]
        for j, f in enumerate(looks):
            v = inv.see(f, regs, pile)
            s = maps[j].get(v, inv.MISSING)
            if s is inv.MISSING:
                maps[j][v] = o[j]
                if t >= half:
                    late += 1
                    if late > allowed:
                        return None
            elif s != o[j]:
                return None
            else:
                ev += gain[j][o[j]]
    return maps, (regs, pile), ev, late

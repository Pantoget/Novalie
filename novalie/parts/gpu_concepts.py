# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Every grouping of a sense's symbols scored at once on the graphics card."""
import array
import collections
import ctypes
import math
import sys


PTX = r"""
.version 7.0
.target sm_75
.address_size 64

// subset_kt: item = (subset mask m >= 1, (cell, grain) g). For each key q of g, in order (ks[g] .. ks[g+1]-1): its
// counts per outcome y, the sum over symbols j in m of cnt[off[q] + j*K + y]; KT's code (natural log, as a
// log-probability): sum_y (lgamma(c_y + 1/2) - lgamma(1/2)) + lgamma(K/2) - lgamma(N + K/2), from lg[x] = lgamma(x/2);
// added in that order into T[m*CG + g] when N > 0. (No atomics, the processor's own order: the very same doubles.)
.visible .entry subset_kt(
    .param .u64 p_cnt, .param .u64 p_off, .param .u64 p_kk, .param .u64 p_ks, .param .u64 p_lg, .param .u64 p_T,
    .param .u32 p_Q, .param .u32 p_M, .param .u32 p_n, .param .u32 p_CG)
{
    .reg .pred %p<8>;
    .reg .b32 %r<40>;
    .reg .b64 %rd<40>;
    .reg .f64 %fd<16>;

    ld.param.u64 %rd1, [p_cnt];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_off];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_kk];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_ks];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_lg];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u64 %rd6, [p_T];
    cvta.to.global.u64 %rd6, %rd6;
    ld.param.u32 %r1, [p_Q];
    ld.param.u32 %r2, [p_M];
    ld.param.u32 %r3, [p_n];
    ld.param.u32 %r4, [p_CG];
    mul.lo.u32 %r5, %r4, %r2;
    mov.u32 %r6, %ctaid.x;
    mov.u32 %r7, %ntid.x;
    mov.u32 %r8, %tid.x;
    mad.lo.u32 %r9, %r6, %r7, %r8;
    mov.u32 %r10, %nctaid.x;
    mul.lo.u32 %r10, %r10, %r7;
    ld.global.f64 %fd1, [%rd5+8];
S_LOOP:
    setp.ge.u32 %p1, %r9, %r5;
    @%p1 bra S_DONE;
    div.u32 %r26, %r9, %r2;
    rem.u32 %r12, %r9, %r2;
    add.u32 %r12, %r12, 1;
    mul.wide.u32 %rd21, %r26, 4;
    add.u64 %rd22, %rd4, %rd21;
    ld.global.u32 %r27, [%rd22];
    ld.global.u32 %r28, [%rd22+4];
    mov.f64 %fd6, 0d0000000000000000;
    mov.u32 %r11, %r27;
Q_LOOP:
    setp.ge.u32 %p6, %r11, %r28;
    @%p6 bra Q_DONE;
    mul.wide.u32 %rd7, %r11, 4;
    add.u64 %rd8, %rd2, %rd7;
    ld.global.u32 %r13, [%rd8];
    add.u64 %rd9, %rd3, %rd7;
    ld.global.u32 %r14, [%rd9];
    mov.u32 %r16, 0;
    mov.f64 %fd2, 0d0000000000000000;
    mov.u32 %r17, 0;
Y_LOOP:
    setp.ge.u32 %p2, %r17, %r14;
    @%p2 bra Y_DONE;
    mov.u32 %r18, 0;
    mov.u32 %r19, 0;
J_LOOP:
    setp.ge.u32 %p3, %r19, %r3;
    @%p3 bra J_DONE;
    shr.u32 %r20, %r12, %r19;
    and.b32 %r20, %r20, 1;
    setp.eq.u32 %p4, %r20, 0;
    @%p4 bra J_NEXT;
    mad.lo.u32 %r21, %r19, %r14, %r13;
    add.u32 %r21, %r21, %r17;
    mul.wide.u32 %rd11, %r21, 4;
    add.u64 %rd12, %rd1, %rd11;
    ld.global.u32 %r22, [%rd12];
    add.u32 %r18, %r18, %r22;
J_NEXT:
    add.u32 %r19, %r19, 1;
    bra J_LOOP;
J_DONE:
    add.u32 %r16, %r16, %r18;
    shl.b32 %r23, %r18, 1;
    add.u32 %r23, %r23, 1;
    mul.wide.u32 %rd13, %r23, 8;
    add.u64 %rd14, %rd5, %rd13;
    ld.global.f64 %fd3, [%rd14];
    sub.rn.f64 %fd3, %fd3, %fd1;
    add.rn.f64 %fd2, %fd2, %fd3;
    add.u32 %r17, %r17, 1;
    bra Y_LOOP;
Y_DONE:
    setp.eq.u32 %p5, %r16, 0;
    @%p5 bra Q_NEXT;
    mul.wide.u32 %rd15, %r14, 8;
    add.u64 %rd16, %rd5, %rd15;
    ld.global.f64 %fd4, [%rd16];
    add.rn.f64 %fd2, %fd2, %fd4;
    shl.b32 %r24, %r16, 1;
    add.u32 %r24, %r24, %r14;
    mul.wide.u32 %rd17, %r24, 8;
    add.u64 %rd18, %rd5, %rd17;
    ld.global.f64 %fd5, [%rd18];
    sub.rn.f64 %fd2, %fd2, %fd5;
    add.rn.f64 %fd6, %fd6, %fd2;
Q_NEXT:
    add.u32 %r11, %r11, 1;
    bra Q_LOOP;
Q_DONE:
    mad.lo.u32 %r25, %r12, %r4, %r26;
    mul.wide.u32 %rd19, %r25, 8;
    add.u64 %rd20, %rd6, %rd19;
    st.global.f64 [%rd20], %fd6;
    add.u32 %r9, %r9, %r10;
    bra S_LOOP;
S_DONE:
    ret;
}

// partition_score: item = grouping p, its classes as masks[p*n ...] (zero after the last). For each cell c (its
// (cell, grain)s are cs[c] .. cs[c+1]-1): the best over them of the sum over classes of T[mask*CG + cg]; summed over
// cells; plus sum over classes lgamma(|class|) - lgamma(n + 1) (alpha = 1); into out[p].
.visible .entry partition_score(
    .param .u64 p_masks, .param .u64 p_T, .param .u64 p_cs, .param .u64 p_lg, .param .u64 p_out,
    .param .u32 p_P, .param .u32 p_n, .param .u32 p_C, .param .u32 p_CG)
{
    .reg .pred %p<8>;
    .reg .b32 %r<40>;
    .reg .b64 %rd<40>;
    .reg .f64 %fd<16>;

    ld.param.u64 %rd1, [p_masks];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_T];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_cs];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_lg];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_out];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u32 %r1, [p_P];
    ld.param.u32 %r2, [p_n];
    ld.param.u32 %r3, [p_C];
    ld.param.u32 %r4, [p_CG];
    mov.u32 %r6, %ctaid.x;
    mov.u32 %r7, %ntid.x;
    mov.u32 %r8, %tid.x;
    mad.lo.u32 %r9, %r6, %r7, %r8;
    mov.u32 %r10, %nctaid.x;
    mul.lo.u32 %r10, %r10, %r7;
P_LOOP:
    setp.ge.u32 %p1, %r9, %r1;
    @%p1 bra P_DONE;
    mul.lo.u32 %r11, %r9, %r2;
    mov.f64 %fd1, 0d0000000000000000;
    mov.u32 %r12, 0;
C_LOOP:
    setp.ge.u32 %p2, %r12, %r3;
    @%p2 bra C_DONE;
    mul.wide.u32 %rd6, %r12, 4;
    add.u64 %rd7, %rd3, %rd6;
    ld.global.u32 %r13, [%rd7];
    ld.global.u32 %r14, [%rd7+4];
    mov.f64 %fd2, 0dFFF0000000000000;
    mov.u32 %r15, %r13;
G_LOOP:
    setp.ge.u32 %p3, %r15, %r14;
    @%p3 bra G_DONE;
    mov.f64 %fd3, 0d0000000000000000;
    mov.u32 %r16, 0;
K_LOOP:
    setp.ge.u32 %p4, %r16, %r2;
    @%p4 bra K_DONE;
    add.u32 %r17, %r11, %r16;
    mul.wide.u32 %rd8, %r17, 4;
    add.u64 %rd9, %rd1, %rd8;
    ld.global.u32 %r18, [%rd9];
    setp.eq.u32 %p5, %r18, 0;
    @%p5 bra K_DONE;
    mad.lo.u32 %r19, %r18, %r4, %r15;
    mul.wide.u32 %rd10, %r19, 8;
    add.u64 %rd11, %rd2, %rd10;
    ld.global.f64 %fd4, [%rd11];
    add.rn.f64 %fd3, %fd3, %fd4;
    add.u32 %r16, %r16, 1;
    bra K_LOOP;
K_DONE:
    max.f64 %fd2, %fd2, %fd3;
    add.u32 %r15, %r15, 1;
    bra G_LOOP;
G_DONE:
    add.rn.f64 %fd1, %fd1, %fd2;
    add.u32 %r12, %r12, 1;
    bra C_LOOP;
C_DONE:
    mov.u32 %r16, 0;
Q_LOOP:
    setp.ge.u32 %p4, %r16, %r2;
    @%p4 bra Q_DONE;
    add.u32 %r17, %r11, %r16;
    mul.wide.u32 %rd8, %r17, 4;
    add.u64 %rd9, %rd1, %rd8;
    ld.global.u32 %r18, [%rd9];
    setp.eq.u32 %p5, %r18, 0;
    @%p5 bra Q_DONE;
    popc.b32 %r20, %r18;
    shl.b32 %r20, %r20, 1;
    mul.wide.u32 %rd12, %r20, 8;
    add.u64 %rd13, %rd4, %rd12;
    ld.global.f64 %fd5, [%rd13];
    add.rn.f64 %fd1, %fd1, %fd5;
    add.u32 %r16, %r16, 1;
    bra Q_LOOP;
Q_DONE:
    shl.b32 %r21, %r2, 1;
    add.u32 %r21, %r21, 2;
    mul.wide.u32 %rd14, %r21, 8;
    add.u64 %rd15, %rd4, %rd14;
    ld.global.f64 %fd6, [%rd15];
    sub.rn.f64 %fd1, %fd1, %fd6;
    mul.wide.u32 %rd16, %r9, 8;
    add.u64 %rd17, %rd5, %rd16;
    st.global.f64 [%rd17], %fd1;
    add.u32 %r9, %r9, %r10;
    bra P_LOOP;
P_DONE:
    ret;
}
"""

MAX_N = 10
_STATE = {"module": None, "masks": {}}
USE = {"searches": 0, "groupings": 0, "subsets": 0, "seconds": 0.0, "cpu_searches": 0}


def card():
    """The card with these kernels loaded."""
    try:
        from . import gpu as g
    except Exception:
        return None
    c = g.card()
    if c is None:
        return None
    if "subset_kt" not in c.kernels:
        with c.lock:
            c.bind()
            mod = ctypes.c_void_p()
            log = ctypes.create_string_buffer(16384)
            opts = (ctypes.c_int * 2)(5, 6)
            vals = (ctypes.c_void_p * 2)(ctypes.cast(log, ctypes.c_void_p), ctypes.c_void_p(16384))
            r = c.lib.cuModuleLoadDataEx(ctypes.byref(mod), ctypes.c_char_p(PTX.encode()), 2, opts, vals)
            if r:
                raise RuntimeError("concept kernels did not compile: " + log.value.decode(errors="replace")[:600])
            _STATE["module"] = mod
            for k in ("subset_kt", "partition_score"):
                f = ctypes.c_void_p()
                c.ok(c.lib.cuModuleGetFunction(ctypes.byref(f), mod, k.encode()), k)
                c.kernels[k] = f
    return c


def rgs_all(n):
    out, a = [], [0] * n

    def rec(j, top):
        if j == n:
            out.append(tuple(a))
            return
        for c in range(top + 2):
            a[j] = c
            rec(j + 1, max(top, c))
    if n == 1:
        return [(0,)]
    if n:
        rec(1, 0)
    return out


def masks_of(n):
    """Every grouping of n symbols as class masks."""
    got = _STATE["masks"].get(n)
    if got is None:
        flat = array.array("I")
        groups = []
        for r in rgs_all(n):
            ms = [0] * (max(r) + 1)
            for j, c in enumerate(r):
                ms[c] |= 1 << j
            groups.append(tuple(ms))
            flat.extend(ms + [0] * (n - len(ms)))
        got = _STATE["masks"][n] = (flat, groups)
    return got


class Tables:
    """What the search scores, from a concept test's per-symbol counts."""

    def __init__(self, test, values):
        self.values = list(values)
        n = len(self.values)
        idx = {v: j for j, v in enumerate(self.values)}
        kinds = collections.defaultdict(set)
        for (cell, g), per in test.persym.items():
            for key, bys in per.items():
                for v, cnt in bys.items():
                    if v in idx:
                        kinds[cell].update(cnt)
        cgs = sorted(((cell, g) for (cell, g) in test.persym if len(kinds[cell]) >= 2), key=repr)
        self.cgs = cgs
        self.cells = []
        self.cs = array.array("I")
        last = object()
        for ci, (cell, g) in enumerate(cgs):
            if cell != last:
                self.cs.append(ci)
                self.cells.append(cell)
                last = cell
        self.cs.append(len(cgs))
        self.keys = []
        for ci, (cell, g) in enumerate(cgs):
            outs = sorted(kinds[cell], key=repr)
            at = {y: k for k, y in enumerate(outs)}
            K = len(outs)
            for key, bys in sorted(test.persym[(cell, g)].items(), key=lambda kv: repr(kv[0])):
                rows = [[0] * K for _ in range(n)]
                any_ = False
                for v, cnt in bys.items():
                    j = idx.get(v)
                    if j is None:
                        continue
                    for y, k in cnt.items():
                        rows[j][at[y]] += k
                        any_ = True
                if any_:
                    self.keys.append((ci, K, rows))
        self.ks = array.array("I")
        q = 0
        for ci in range(len(cgs) + 1):
            while q < len(self.keys) and self.keys[q][0] < ci:
                q += 1
            self.ks.append(q)
        self.maxN = max((sum(sum(r) for r in rows) for _, _, rows in self.keys), default=0)
        self.maxK = max((K for _, K, _ in self.keys), default=2)

    def T_of(self, mask):
        """Exactly, on the processor."""
        n = len(self.values)
        out = collections.defaultdict(float)
        lg = math.lgamma
        for ci, K, rows in self.keys:
            tot, s = 0, 0.0
            for y in range(K):
                c = 0
                for j in range(n):
                    if mask >> j & 1:
                        c += rows[j][y]
                tot += c
                s += lg(c + 0.5) - lg(0.5)
            if tot:
                out[ci] += s + lg(K / 2) - lg(tot + K / 2)
        return out

    def score(self, ms, cache):
        """A grouping's score exactly."""
        n = len(self.values)
        for mk in ms:
            if mk not in cache:
                cache[mk] = self.T_of(mk)
        tot = 0.0
        for c in range(len(self.cells)):
            best = -math.inf
            for ci in range(self.cs[c], self.cs[c + 1]):
                s = 0.0
                for mk in ms:
                    s += cache[mk].get(ci, 0.0)
                best = max(best, s)
            tot += best
        for mk in ms:
            tot += math.lgamma(bin(mk).count("1"))
        return tot - math.lgamma(n + 1)


def best_groupings(test, values, top=8, use_card=True, check=False):
    """The top groupings of values by their count-only score, ranked."""
    import time
    t0 = time.perf_counter()
    tb = Tables(test, values)
    n = len(tb.values)
    if n < 2 or not tb.keys:
        return []
    flat, groups = masks_of(n)
    c = card() if use_card else None
    cache = {}
    if c is None:
        scored = sorted(((tb.score(ms, cache), ms) for ms in groups), key=lambda x: (-x[0], x[1]))
        USE["cpu_searches"] += 1
    else:
        CG = len(tb.cgs)
        M = (1 << n) - 1
        cnt, off, kk = array.array("I"), array.array("I"), array.array("I")
        for ci, K, rows in tb.keys:
            off.append(len(cnt))
            kk.append(K)
            for r in rows:
                cnt.extend(r)
        L = 2 * tb.maxN + tb.maxK + 2 * n + 8
        lg = array.array("d", [0.0] + [math.lgamma(x / 2) for x in range(1, L)])
        with c.lock:
            c.bind()
            ptr = {}
            try:
                for name, arr in (("cnt", cnt), ("off", off), ("kk", kk), ("ks", tb.ks), ("lg", lg), ("masks", flat),
                                  ("cs", tb.cs)):
                    ptr[name] = c.put(arr)
                ptr["T"] = c.zeros(2 * (M + 1) * CG)
                Q = len(tb.keys)
                c.launch("subset_kt", M * CG, ("p", ptr["cnt"]), ("p", ptr["off"]), ("p", ptr["kk"]), ("p", ptr["ks"]),
                         ("p", ptr["lg"]), ("p", ptr["T"]), ("u", Q), ("u", M), ("u", n), ("u", CG))
                P = len(groups)
                ptr["out"] = c.alloc(8 * P)
                c.launch("partition_score", P, ("p", ptr["masks"]), ("p", ptr["T"]), ("p", ptr["cs"]), ("p", ptr["lg"]),
                         ("p", ptr["out"]), ("u", P), ("u", n), ("u", len(tb.cells)), ("u", CG))
                got = c.get(ptr["out"], "d", P)
            finally:
                c.free(*ptr.values())
        import heapq
        best = heapq.nsmallest(top, range(P), key=lambda p: (-got[p], groups[p]))
        scored = [(got[p], groups[p]) for p in best]
        if check:
            again = [(tb.score(ms, cache), ms) for _, ms in scored]
            USE["checked"] = USE.get("checked", 0) + len(again)
            USE["differ"] = USE.get("differ", 0) + sum(1 for (a, _), (b, _) in zip(scored, again) if a != b)
        USE["subsets"] += Q * M
        USE["groupings"] += P
    USE["searches"] += 1
    USE["seconds"] += time.perf_counter() - t0
    out = []
    for s, ms in scored[:top]:
        out.append((s, [[tb.values[j] for j in range(n) if mk >> j & 1] for mk in ms]))
    return out

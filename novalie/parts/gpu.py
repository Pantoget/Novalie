# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's graphics card, reached with nothing but the standard library."""
import array
import ctypes
import math
import os
import threading
import time

PTX = r"""
.version 7.0
.target sm_75
.address_size 64

// For every pair of conditions (a < b) that held together at one act, and every change d the sense could have made
// from where it was then (rate >= 0): how many such acts (nf), the sum of its odds of that change by itself there (e),
// and how many times it made it (k). One thread per (act, condition); the pairs are a, b in the act's sorted list.
.visible .entry pairs_accumulate(
    .param .u64 p_row, .param .u64 p_off, .param .u64 p_feat, .param .u64 p_ch, .param .u64 p_rate,
    .param .u64 p_k, .param .u64 p_nf, .param .u64 p_e,
    .param .u32 p_nnz, .param .u32 p_F, .param .u32 p_D)
{
    .reg .pred %p<4>;
    .reg .b32 %r<24>;
    .reg .b64 %rd<40>;
    .reg .f32 %f<4>;

    ld.param.u64 %rd1, [p_row];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_off];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_feat];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_ch];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_rate];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u64 %rd6, [p_k];
    cvta.to.global.u64 %rd6, %rd6;
    ld.param.u64 %rd7, [p_nf];
    cvta.to.global.u64 %rd7, %rd7;
    ld.param.u64 %rd8, [p_e];
    cvta.to.global.u64 %rd8, %rd8;
    ld.param.u32 %r1, [p_nnz];
    ld.param.u32 %r2, [p_F];
    ld.param.u32 %r3, [p_D];
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r7, %r4, %r5, %r6;
    mov.u32 %r8, %nctaid.x;
    mul.lo.u32 %r8, %r8, %r5;
    cvt.u64.u32 %rd17, %r2;
    cvt.u64.u32 %rd22, %r3;
G_LOOP:
    setp.ge.u32 %p1, %r7, %r1;
    @%p1 bra G_DONE;
    mul.wide.u32 %rd9, %r7, 4;
    add.u64 %rd10, %rd1, %rd9;
    ld.global.u32 %r9, [%rd10];
    add.u32 %r10, %r9, 1;
    mul.wide.u32 %rd11, %r10, 4;
    add.u64 %rd12, %rd2, %rd11;
    ld.global.u32 %r11, [%rd12];
    add.u64 %rd13, %rd3, %rd9;
    ld.global.u32 %r12, [%rd13];
    mul.wide.u32 %rd14, %r9, 4;
    add.u64 %rd15, %rd4, %rd14;
    ld.global.s32 %r13, [%rd15];
    cvt.u64.u32 %rd16, %r12;
    mul.lo.u64 %rd18, %rd16, %rd17;
    add.u64 %rd19, %rd16, 1;
    mul.lo.u64 %rd19, %rd19, %rd16;
    shr.u64 %rd19, %rd19, 1;
    sub.u64 %rd18, %rd18, %rd19;
    sub.u64 %rd18, %rd18, %rd16;
    sub.u64 %rd18, %rd18, 1;
    cvt.u64.u32 %rd36, %r9;
    mul.lo.u64 %rd36, %rd36, %rd22;
    shl.b64 %rd20, %rd36, 2;
    add.u64 %rd21, %rd5, %rd20;
    add.u32 %r15, %r7, 1;
J_LOOP:
    setp.ge.u32 %p2, %r15, %r11;
    @%p2 bra J_DONE;
    mul.wide.u32 %rd23, %r15, 4;
    add.u64 %rd24, %rd3, %rd23;
    ld.global.u32 %r16, [%rd24];
    cvt.u64.u32 %rd25, %r16;
    add.u64 %rd26, %rd18, %rd25;
    mul.lo.u64 %rd27, %rd26, %rd22;
    mov.u32 %r17, 0;
D_LOOP:
    setp.ge.u32 %p3, %r17, %r3;
    @%p3 bra D_DONE;
    mul.wide.u32 %rd28, %r17, 4;
    add.u64 %rd29, %rd21, %rd28;
    ld.global.f32 %f1, [%rd29];
    setp.lt.f32 %p1, %f1, 0f00000000;
    @%p1 bra D_NEXT;
    cvt.u64.u32 %rd30, %r17;
    add.u64 %rd31, %rd27, %rd30;
    shl.b64 %rd32, %rd31, 2;
    add.u64 %rd33, %rd7, %rd32;
    red.global.add.u32 [%rd33], 1;
    add.u64 %rd34, %rd8, %rd32;
    red.global.add.f32 [%rd34], %f1;
    setp.ne.s32 %p1, %r13, %r17;
    @%p1 bra D_NEXT;
    add.u64 %rd35, %rd6, %rd32;
    red.global.add.u32 [%rd35], 1;
D_NEXT:
    add.u32 %r17, %r17, 1;
    bra D_LOOP;
D_DONE:
    add.u32 %r15, %r15, 1;
    bra J_LOOP;
J_DONE:
    add.u32 %r7, %r7, %r8;
    bra G_LOOP;
G_DONE:
    ret;
}

// For every (pair, change) q: a first look at its evidence, its Chernoff digits in single precision (as
// novalie_app.kl_digits, each way), and q kept when they reach thr (or cannot be told: kept too).
.visible .entry pairs_select(
    .param .u64 p_k, .param .u64 p_nf, .param .u64 p_e, .param .u64 p_out, .param .u64 p_count,
    .param .u32 p_Q, .param .u32 p_cap, .param .f32 p_thr)
{
    .reg .pred %p<6>;
    .reg .b32 %r<16>;
    .reg .b64 %rd<16>;
    .reg .f32 %f<24>;

    ld.param.u64 %rd1, [p_k];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_nf];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_e];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_out];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_count];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u32 %r1, [p_Q];
    ld.param.u32 %r2, [p_cap];
    ld.param.f32 %f20, [p_thr];
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r7, %r4, %r5, %r6;
    mov.u32 %r8, %nctaid.x;
    mul.lo.u32 %r8, %r8, %r5;
Q_LOOP:
    setp.ge.u32 %p1, %r7, %r1;
    @%p1 bra Q_DONE;
    mul.wide.u32 %rd6, %r7, 4;
    add.u64 %rd7, %rd2, %rd6;
    ld.global.u32 %r9, [%rd7];
    setp.lt.u32 %p2, %r9, 2;
    @%p2 bra Q_NEXT;
    add.u64 %rd8, %rd1, %rd6;
    ld.global.u32 %r10, [%rd8];
    add.u64 %rd9, %rd3, %rd6;
    ld.global.f32 %f1, [%rd9];
    cvt.rn.f32.u32 %f2, %r9;
    cvt.rn.f32.u32 %f3, %r10;
    div.rn.f32 %f4, %f1, %f2;
    setp.gt.f32 %p3, %f3, %f1;
    @%p3 bra UP;
    sub.f32 %f3, %f2, %f3;
    mov.f32 %f5, 0f3F800000;
    sub.f32 %f4, %f5, %f4;
UP:
    mul.f32 %f6, %f2, %f4;
    setp.le.f32 %p4, %f3, %f6;
    @%p4 bra Q_NEXT;
    setp.ge.f32 %p4, %f4, 0f3F800000;
    @%p4 bra Q_NEXT;
    max.f32 %f4, %f4, 0f2B8CBCCC;
    div.rn.f32 %f7, %f3, %f2;
    div.rn.f32 %f8, %f7, %f4;
    lg2.approx.f32 %f8, %f8;
    mul.f32 %f9, %f7, %f8;
    mov.f32 %f10, 0f3F800000;
    sub.f32 %f11, %f10, %f7;
    setp.le.f32 %p5, %f11, 0f00000000;
    @%p5 bra SUM;
    sub.f32 %f12, %f10, %f4;
    div.rn.f32 %f13, %f11, %f12;
    lg2.approx.f32 %f13, %f13;
    fma.rn.f32 %f9, %f11, %f13, %f9;
SUM:
    mul.f32 %f14, %f2, %f9;
    mul.f32 %f14, %f14, 0f3E9A209B;
    setp.lt.f32 %p5, %f14, %f20;
    @%p5 bra Q_NEXT;
    atom.global.add.u32 %r11, [%rd5], 1;
    setp.ge.u32 %p5, %r11, %r2;
    @%p5 bra Q_NEXT;
    mul.wide.u32 %rd10, %r11, 4;
    add.u64 %rd11, %rd4, %rd10;
    st.global.u32 [%rd11], %r7;
Q_NEXT:
    add.u32 %r7, %r7, %r8;
    bra Q_LOOP;
Q_DONE:
    ret;
}
"""


COUNTS_PTX = r"""
.version 7.0
.target sm_75
.address_size 64

// Its laws of counts on the card. The hidden state (key) of moment t under a model: register j is the sum over buttons
// a of counts[t][a] * eff[a][j], reduced into [0, q) when the register is a cycle of q (mods[j] = q > 0), as
// novalie_mind.Model.step makes it press by press. A key is written as one number: register j shifted by lo[j] and
// weighed by stride[j] (exact: the host checks that every key fits). The table holds each key once with what was seen
// in it (open addressing; an empty slot is all ones).

// cc_range: for each register with no cycle, the least and the most it takes over the moments.
.visible .entry cc_range(
    .param .u64 p_counts, .param .u64 p_eff, .param .u64 p_mods, .param .u64 p_kmin, .param .u64 p_kmax,
    .param .u32 p_T, .param .u32 p_m, .param .u32 p_r)
{
    .reg .pred %p<4>;
    .reg .b32 %r<16>;
    .reg .b64 %rd<32>;

    ld.param.u64 %rd1, [p_counts];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_eff];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_mods];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_kmin];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_kmax];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u32 %r1, [p_T];
    ld.param.u32 %r2, [p_m];
    ld.param.u32 %r3, [p_r];
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r7, %r4, %r5, %r6;
    mov.u32 %r8, %nctaid.x;
    mul.lo.u32 %r8, %r8, %r5;
R_T:
    setp.ge.u32 %p1, %r7, %r1;
    @%p1 bra R_DONE;
    mul.lo.u32 %r9, %r7, %r2;
    mul.wide.u32 %rd6, %r9, 4;
    add.u64 %rd7, %rd1, %rd6;
    mov.u32 %r10, 0;
R_J:
    setp.ge.u32 %p2, %r10, %r3;
    @%p2 bra R_TNEXT;
    mul.wide.u32 %rd8, %r10, 8;
    add.u64 %rd9, %rd3, %rd8;
    ld.global.s64 %rd10, [%rd9];
    setp.ne.s64 %p3, %rd10, 0;
    @%p3 bra R_JNEXT;
    mov.u64 %rd11, 0;
    mov.u32 %r11, 0;
R_A:
    setp.ge.u32 %p2, %r11, %r2;
    @%p2 bra R_ADONE;
    mul.wide.u32 %rd12, %r11, 4;
    add.u64 %rd13, %rd7, %rd12;
    ld.global.s32 %r12, [%rd13];
    cvt.s64.s32 %rd14, %r12;
    mad.lo.u32 %r13, %r11, %r3, %r10;
    mul.wide.u32 %rd15, %r13, 8;
    add.u64 %rd16, %rd2, %rd15;
    ld.global.s64 %rd17, [%rd16];
    mad.lo.s64 %rd11, %rd14, %rd17, %rd11;
    add.u32 %r11, %r11, 1;
    bra R_A;
R_ADONE:
    add.u64 %rd18, %rd4, %rd8;
    atom.global.min.s64 %rd19, [%rd18], %rd11;
    add.u64 %rd20, %rd5, %rd8;
    atom.global.max.s64 %rd21, [%rd20], %rd11;
R_JNEXT:
    add.u32 %r10, %r10, 1;
    bra R_J;
R_TNEXT:
    add.u32 %r7, %r7, %r8;
    bra R_T;
R_DONE:
    ret;
}

// cc_insert: every moment's key into the table with what was seen then; stats[0] counts the keys (states), stats[1]
// becomes 1 when one key was seen with two different things (the model is refuted).
.visible .entry cc_insert(
    .param .u64 p_counts, .param .u64 p_colors, .param .u64 p_eff, .param .u64 p_mods, .param .u64 p_lo,
    .param .u64 p_stride, .param .u64 p_tkeys, .param .u64 p_tcols, .param .u64 p_stats,
    .param .u32 p_T, .param .u32 p_m, .param .u32 p_r, .param .u32 p_mask)
{
    .reg .pred %p<6>;
    .reg .b32 %r<24>;
    .reg .b64 %rd<48>;

    ld.param.u64 %rd1, [p_counts];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_colors];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_eff];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_mods];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_lo];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u64 %rd6, [p_stride];
    cvta.to.global.u64 %rd6, %rd6;
    ld.param.u64 %rd7, [p_tkeys];
    cvta.to.global.u64 %rd7, %rd7;
    ld.param.u64 %rd8, [p_tcols];
    cvta.to.global.u64 %rd8, %rd8;
    ld.param.u64 %rd9, [p_stats];
    cvta.to.global.u64 %rd9, %rd9;
    ld.param.u32 %r1, [p_T];
    ld.param.u32 %r2, [p_m];
    ld.param.u32 %r3, [p_r];
    ld.param.u32 %r14, [p_mask];
    mov.u64 %rd40, 0xFFFFFFFFFFFFFFFF;
    mov.u64 %rd41, 0x9E3779B97F4A7C15;
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r7, %r4, %r5, %r6;
    mov.u32 %r8, %nctaid.x;
    mul.lo.u32 %r8, %r8, %r5;
I_T:
    setp.ge.u32 %p1, %r7, %r1;
    @%p1 bra I_DONE;
    mul.lo.u32 %r9, %r7, %r2;
    mul.wide.u32 %rd10, %r9, 4;
    add.u64 %rd11, %rd1, %rd10;
    mov.u64 %rd30, 0;
    mov.u32 %r10, 0;
I_J:
    setp.ge.u32 %p2, %r10, %r3;
    @%p2 bra I_HASH;
    mov.u64 %rd12, 0;
    mov.u32 %r11, 0;
I_A:
    setp.ge.u32 %p2, %r11, %r2;
    @%p2 bra I_ADONE;
    mul.wide.u32 %rd13, %r11, 4;
    add.u64 %rd14, %rd11, %rd13;
    ld.global.s32 %r12, [%rd14];
    cvt.s64.s32 %rd15, %r12;
    mad.lo.u32 %r13, %r11, %r3, %r10;
    mul.wide.u32 %rd16, %r13, 8;
    add.u64 %rd17, %rd3, %rd16;
    ld.global.s64 %rd18, [%rd17];
    mad.lo.s64 %rd12, %rd15, %rd18, %rd12;
    add.u32 %r11, %r11, 1;
    bra I_A;
I_ADONE:
    mul.wide.u32 %rd19, %r10, 8;
    add.u64 %rd20, %rd4, %rd19;
    ld.global.s64 %rd21, [%rd20];
    setp.eq.s64 %p3, %rd21, 0;
    @%p3 bra I_PLACE;
    rem.s64 %rd12, %rd12, %rd21;
    setp.ge.s64 %p3, %rd12, 0;
    @%p3 bra I_PLACE;
    add.s64 %rd12, %rd12, %rd21;
I_PLACE:
    add.u64 %rd22, %rd5, %rd19;
    ld.global.s64 %rd23, [%rd22];
    sub.s64 %rd24, %rd12, %rd23;
    add.u64 %rd25, %rd6, %rd19;
    ld.global.u64 %rd26, [%rd25];
    mad.lo.u64 %rd30, %rd24, %rd26, %rd30;
    add.u32 %r10, %r10, 1;
    bra I_J;
I_HASH:
    mul.lo.u64 %rd31, %rd30, %rd41;
    shr.u64 %rd31, %rd31, 32;
    cvt.u32.u64 %r15, %rd31;
    and.b32 %r15, %r15, %r14;
I_PROBE:
    mul.wide.u32 %rd32, %r15, 8;
    add.u64 %rd33, %rd7, %rd32;
    atom.global.cas.b64 %rd34, [%rd33], %rd40, %rd30;
    setp.eq.u64 %p4, %rd34, %rd40;
    @%p4 bra I_NEW;
    setp.eq.u64 %p4, %rd34, %rd30;
    @%p4 bra I_COLOR;
    add.u32 %r15, %r15, 1;
    and.b32 %r15, %r15, %r14;
    bra I_PROBE;
I_NEW:
    red.global.add.u32 [%rd9], 1;
I_COLOR:
    mul.wide.u32 %rd35, %r7, 4;
    add.u64 %rd36, %rd2, %rd35;
    ld.global.s32 %r16, [%rd36];
    mul.wide.u32 %rd37, %r15, 4;
    add.u64 %rd38, %rd8, %rd37;
    atom.global.cas.b32 %r17, [%rd38], -1, %r16;
    setp.eq.s32 %p5, %r17, -1;
    @%p5 bra I_TNEXT;
    setp.eq.s32 %p5, %r17, %r16;
    @%p5 bra I_TNEXT;
    add.u64 %rd39, %rd9, 4;
    red.global.or.b32 [%rd39], 1;
I_TNEXT:
    add.u32 %r7, %r7, %r8;
    bra I_T;
I_DONE:
    ret;
}

// cc_quick: its quick test of many classes of candidates at once. For class c and sampled moment t: the key of t moved
// by the class's change (each register by cls[c][j], a cycle's reduced); when that state is in the table, the thing
// seen there must be what was seen at t: bad[c] = 1 at the first that is not, agree[c] counts those that are.
.visible .entry cc_quick(
    .param .u64 p_counts, .param .u64 p_colors, .param .u64 p_eff, .param .u64 p_mods, .param .u64 p_lo,
    .param .u64 p_stride, .param .u64 p_span, .param .u64 p_tkeys, .param .u64 p_tcols, .param .u64 p_sample,
    .param .u64 p_cls, .param .u64 p_bad, .param .u64 p_agree,
    .param .u32 p_NS, .param .u32 p_C, .param .u32 p_m, .param .u32 p_r, .param .u32 p_mask)
{
    .reg .pred %p<6>;
    .reg .b32 %r<32>;
    .reg .b64 %rd<64>;

    ld.param.u64 %rd1, [p_counts];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_colors];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_eff];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_mods];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_lo];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u64 %rd6, [p_stride];
    cvta.to.global.u64 %rd6, %rd6;
    ld.param.u64 %rd7, [p_span];
    cvta.to.global.u64 %rd7, %rd7;
    ld.param.u64 %rd8, [p_tkeys];
    cvta.to.global.u64 %rd8, %rd8;
    ld.param.u64 %rd9, [p_tcols];
    cvta.to.global.u64 %rd9, %rd9;
    ld.param.u64 %rd10, [p_sample];
    cvta.to.global.u64 %rd10, %rd10;
    ld.param.u64 %rd11, [p_cls];
    cvta.to.global.u64 %rd11, %rd11;
    ld.param.u64 %rd12, [p_bad];
    cvta.to.global.u64 %rd12, %rd12;
    ld.param.u64 %rd13, [p_agree];
    cvta.to.global.u64 %rd13, %rd13;
    ld.param.u32 %r1, [p_NS];
    ld.param.u32 %r2, [p_C];
    ld.param.u32 %r3, [p_m];
    ld.param.u32 %r4, [p_r];
    ld.param.u32 %r5, [p_mask];
    mov.u64 %rd60, 0xFFFFFFFFFFFFFFFF;
    mov.u64 %rd61, 0x9E3779B97F4A7C15;
    mul.lo.u32 %r6, %r1, %r2;
    mov.u32 %r7, %ctaid.x;
    mov.u32 %r8, %ntid.x;
    mov.u32 %r9, %tid.x;
    mad.lo.u32 %r10, %r7, %r8, %r9;
    mov.u32 %r11, %nctaid.x;
    mul.lo.u32 %r11, %r11, %r8;
Q_G:
    setp.ge.u32 %p1, %r10, %r6;
    @%p1 bra Q_DONE;
    div.u32 %r12, %r10, %r1;
    mul.lo.u32 %r13, %r12, %r1;
    sub.u32 %r13, %r10, %r13;
    mul.wide.u32 %rd14, %r13, 4;
    add.u64 %rd15, %rd10, %rd14;
    ld.global.u32 %r14, [%rd15];
    mul.lo.u32 %r15, %r14, %r3;
    mul.wide.u32 %rd16, %r15, 4;
    add.u64 %rd17, %rd1, %rd16;
    mov.u64 %rd40, 0;
    mov.u32 %r16, 0;
Q_J:
    setp.ge.u32 %p2, %r16, %r4;
    @%p2 bra Q_HASH;
    mad.lo.u32 %r17, %r12, %r4, %r16;
    mul.wide.u32 %rd18, %r17, 8;
    add.u64 %rd19, %rd11, %rd18;
    ld.global.s64 %rd20, [%rd19];
    mov.u32 %r18, 0;
Q_A:
    setp.ge.u32 %p2, %r18, %r3;
    @%p2 bra Q_ADONE;
    mul.wide.u32 %rd21, %r18, 4;
    add.u64 %rd22, %rd17, %rd21;
    ld.global.s32 %r19, [%rd22];
    cvt.s64.s32 %rd23, %r19;
    mad.lo.u32 %r20, %r18, %r4, %r16;
    mul.wide.u32 %rd24, %r20, 8;
    add.u64 %rd25, %rd3, %rd24;
    ld.global.s64 %rd26, [%rd25];
    mad.lo.s64 %rd20, %rd23, %rd26, %rd20;
    add.u32 %r18, %r18, 1;
    bra Q_A;
Q_ADONE:
    mul.wide.u32 %rd27, %r16, 8;
    add.u64 %rd28, %rd4, %rd27;
    ld.global.s64 %rd29, [%rd28];
    add.u64 %rd30, %rd5, %rd27;
    ld.global.s64 %rd31, [%rd30];
    setp.eq.s64 %p3, %rd29, 0;
    @%p3 bra Q_FREE;
    rem.s64 %rd20, %rd20, %rd29;
    setp.ge.s64 %p3, %rd20, 0;
    @%p3 bra Q_PLACE;
    add.s64 %rd20, %rd20, %rd29;
    bra Q_PLACE;
Q_FREE:
    setp.lt.s64 %p3, %rd20, %rd31;
    @%p3 bra Q_NEXT;
    sub.s64 %rd32, %rd20, %rd31;
    add.u64 %rd33, %rd7, %rd27;
    ld.global.u64 %rd34, [%rd33];
    setp.ge.u64 %p3, %rd32, %rd34;
    @%p3 bra Q_NEXT;
Q_PLACE:
    sub.s64 %rd35, %rd20, %rd31;
    add.u64 %rd36, %rd6, %rd27;
    ld.global.u64 %rd37, [%rd36];
    mad.lo.u64 %rd40, %rd35, %rd37, %rd40;
    add.u32 %r16, %r16, 1;
    bra Q_J;
Q_HASH:
    mul.lo.u64 %rd41, %rd40, %rd61;
    shr.u64 %rd41, %rd41, 32;
    cvt.u32.u64 %r21, %rd41;
    and.b32 %r21, %r21, %r5;
Q_PROBE:
    mul.wide.u32 %rd42, %r21, 8;
    add.u64 %rd43, %rd8, %rd42;
    ld.global.u64 %rd44, [%rd43];
    setp.eq.u64 %p4, %rd44, %rd60;
    @%p4 bra Q_NEXT;
    setp.eq.u64 %p4, %rd44, %rd40;
    @%p4 bra Q_FOUND;
    add.u32 %r21, %r21, 1;
    and.b32 %r21, %r21, %r5;
    bra Q_PROBE;
Q_FOUND:
    mul.wide.u32 %rd45, %r21, 4;
    add.u64 %rd46, %rd9, %rd45;
    ld.global.s32 %r22, [%rd46];
    mul.wide.u32 %rd47, %r14, 4;
    add.u64 %rd48, %rd2, %rd47;
    ld.global.s32 %r23, [%rd48];
    mul.wide.u32 %rd49, %r12, 4;
    setp.eq.s32 %p5, %r22, %r23;
    @%p5 bra Q_AGREE;
    add.u64 %rd50, %rd12, %rd49;
    red.global.or.b32 [%rd50], 1;
    bra Q_NEXT;
Q_AGREE:
    add.u64 %rd51, %rd13, %rd49;
    red.global.add.u32 [%rd51], 1;
Q_NEXT:
    add.u32 %r10, %r10, %r11;
    bra Q_G;
Q_DONE:
    ret;
}
"""


SINGLES_PTX = r"""
.version 7.0
.target sm_75
.address_size 64

// Its laws of odds of one condition (novalie_app.Novalie.judge_odds): for each (condition c, change d), over the values
// the sense was at when c held (CSR: off, vidx, cnt), where its chain gives odds of d from that value (rate >= 0):
// nf = the count (exact), e = the sum of count times odds (what it would have done by itself).
.visible .entry singles_sums(
    .param .u64 p_off, .param .u64 p_vidx, .param .u64 p_cnt, .param .u64 p_rate,
    .param .u64 p_nf, .param .u64 p_e, .param .u32 p_C, .param .u32 p_D)
{
    .reg .pred %p<4>;
    .reg .b32 %r<24>;
    .reg .b64 %rd<24>;
    .reg .f32 %f<8>;

    ld.param.u64 %rd1, [p_off];
    cvta.to.global.u64 %rd1, %rd1;
    ld.param.u64 %rd2, [p_vidx];
    cvta.to.global.u64 %rd2, %rd2;
    ld.param.u64 %rd3, [p_cnt];
    cvta.to.global.u64 %rd3, %rd3;
    ld.param.u64 %rd4, [p_rate];
    cvta.to.global.u64 %rd4, %rd4;
    ld.param.u64 %rd5, [p_nf];
    cvta.to.global.u64 %rd5, %rd5;
    ld.param.u64 %rd6, [p_e];
    cvta.to.global.u64 %rd6, %rd6;
    ld.param.u32 %r1, [p_C];
    ld.param.u32 %r2, [p_D];
    mul.lo.u32 %r3, %r1, %r2;
    mov.u32 %r4, %ctaid.x;
    mov.u32 %r5, %ntid.x;
    mov.u32 %r6, %tid.x;
    mad.lo.u32 %r7, %r4, %r5, %r6;
    mov.u32 %r8, %nctaid.x;
    mul.lo.u32 %r8, %r8, %r5;
S_LOOP:
    setp.ge.u32 %p1, %r7, %r3;
    @%p1 bra S_DONE;
    div.u32 %r9, %r7, %r2;
    mul.lo.u32 %r10, %r9, %r2;
    sub.u32 %r10, %r7, %r10;
    mul.wide.u32 %rd7, %r9, 4;
    add.u64 %rd8, %rd1, %rd7;
    ld.global.u32 %r11, [%rd8];
    ld.global.u32 %r12, [%rd8+4];
    mov.f32 %f1, 0f00000000;
    mov.u32 %r13, 0;
V_LOOP:
    setp.ge.u32 %p2, %r11, %r12;
    @%p2 bra V_DONE;
    mul.wide.u32 %rd9, %r11, 4;
    add.u64 %rd10, %rd2, %rd9;
    ld.global.u32 %r14, [%rd10];
    add.u64 %rd11, %rd3, %rd9;
    ld.global.u32 %r15, [%rd11];
    mad.lo.u32 %r16, %r14, %r2, %r10;
    mul.wide.u32 %rd12, %r16, 4;
    add.u64 %rd13, %rd4, %rd12;
    ld.global.f32 %f2, [%rd13];
    setp.lt.f32 %p3, %f2, 0f00000000;
    @%p3 bra V_NEXT;
    cvt.rn.f32.u32 %f3, %r15;
    fma.rn.f32 %f1, %f3, %f2, %f1;
    add.u32 %r13, %r13, %r15;
V_NEXT:
    add.u32 %r11, %r11, 1;
    bra V_LOOP;
V_DONE:
    mul.wide.u32 %rd14, %r7, 4;
    add.u64 %rd15, %rd5, %rd14;
    st.global.u32 [%rd15], %r13;
    add.u64 %rd16, %rd6, %rd14;
    st.global.f32 [%rd16], %f1;
    add.u32 %r7, %r7, %r8;
    bra S_LOOP;
S_DONE:
    ret;
}
"""


class _Card:
    """One graphics card, its context, and the kernels above."""

    def __init__(self):
        self.lib = ctypes.WinDLL("nvcuda.dll") if os.name == "nt" else ctypes.CDLL("libcuda.so.1")
        L = self.lib
        for name in ("cuMemAlloc_v2", "cuMemFree_v2", "cuMemcpyHtoD_v2", "cuMemcpyDtoH_v2", "cuMemsetD32_v2"):
            getattr(L, name).restype = ctypes.c_int
        L.cuMemAlloc_v2.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t]
        L.cuMemFree_v2.argtypes = [ctypes.c_uint64]
        L.cuMemcpyHtoD_v2.argtypes = [ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
        L.cuMemcpyDtoH_v2.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t]
        L.cuMemsetD32_v2.argtypes = [ctypes.c_uint64, ctypes.c_uint, ctypes.c_size_t]
        self.ok(L.cuInit(0), "cuInit")
        dev = ctypes.c_int()
        self.ok(L.cuDeviceGet(ctypes.byref(dev), 0), "cuDeviceGet")
        name = ctypes.create_string_buffer(256)
        L.cuDeviceGetName(name, 256, dev)
        mem, sms, major, minor = ctypes.c_size_t(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        L.cuDeviceTotalMem_v2(ctypes.byref(mem), dev)
        L.cuDeviceGetAttribute(ctypes.byref(sms), 16, dev)
        L.cuDeviceGetAttribute(ctypes.byref(major), 75, dev)
        L.cuDeviceGetAttribute(ctypes.byref(minor), 76, dev)
        self.name, self.memory, self.sms = name.value.decode(errors="replace"), mem.value, sms.value
        self.cc = 10 * major.value + minor.value
        self.ctx = ctypes.c_void_p()
        self.ok(L.cuDevicePrimaryCtxRetain(ctypes.byref(self.ctx), dev), "cuDevicePrimaryCtxRetain")
        self.lock = threading.RLock()
        self.bind()
        self.module = ctypes.c_void_p()
        log = ctypes.create_string_buffer(16384)
        opts = (ctypes.c_int * 2)(5, 6)
        vals = (ctypes.c_void_p * 2)(ctypes.cast(log, ctypes.c_void_p), ctypes.c_void_p(16384))
        r = L.cuModuleLoadDataEx(ctypes.byref(self.module), ctypes.c_char_p(PTX.encode()), 2, opts, vals)
        if r:
            raise RuntimeError("its card could not compile its kernels: " + log.value.decode(errors="replace")[:400])
        self.kernels = {}
        for k in ("pairs_accumulate", "pairs_select"):
            f = ctypes.c_void_p()
            self.ok(L.cuModuleGetFunction(ctypes.byref(f), self.module, k.encode()), k)
            self.kernels[k] = f
        self.counts_module = ctypes.c_void_p()
        r = L.cuModuleLoadDataEx(ctypes.byref(self.counts_module), ctypes.c_char_p(COUNTS_PTX.encode()), 2, opts, vals)
        if r:
            raise RuntimeError("its card could not compile its kernels: " + log.value.decode(errors="replace")[:400])
        for k in ("cc_range", "cc_insert", "cc_quick"):
            f = ctypes.c_void_p()
            self.ok(L.cuModuleGetFunction(ctypes.byref(f), self.counts_module, k.encode()), k)
            self.kernels[k] = f
        self.singles_module = ctypes.c_void_p()
        r = L.cuModuleLoadDataEx(ctypes.byref(self.singles_module), ctypes.c_char_p(SINGLES_PTX.encode()), 2, opts, vals)
        if r:
            raise RuntimeError("its card could not compile its kernels: " + log.value.decode(errors="replace")[:400])
        f = ctypes.c_void_p()
        self.ok(L.cuModuleGetFunction(ctypes.byref(f), self.singles_module, b"singles_sums"), "singles_sums")
        self.kernels["singles_sums"] = f
        L.cuMemcpyDtoD_v2.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_size_t]

    def ok(self, r, what):
        if r:
            s = ctypes.c_char_p()
            self.lib.cuGetErrorName(r, ctypes.byref(s))
            raise RuntimeError(f"its card: {what}: {s.value.decode() if s.value else r}")

    def bind(self):
        """Its context, current in the thread that asks."""
        self.ok(self.lib.cuCtxSetCurrent(self.ctx), "cuCtxSetCurrent")

    def free_memory(self):
        free, total = ctypes.c_size_t(), ctypes.c_size_t()
        self.lib.cuMemGetInfo_v2(ctypes.byref(free), ctypes.byref(total))
        return free.value

    def room(self):
        """What one more taker may hold on the card now."""
        return max(0, self.spare() // 2)

    def spare(self):
        """What is free on the card beyond the part it keeps for the screen and your programs."""
        self.bind()
        keep = 0.2 * self.memory
        return int(self.free_memory() - keep)

    def alloc(self, nbytes):
        p = ctypes.c_uint64()
        self.ok(self.lib.cuMemAlloc_v2(ctypes.byref(p), max(4, nbytes)), "cuMemAlloc")
        return p.value

    def put(self, arr):
        """An array.array copied to the card."""
        p = self.alloc(arr.itemsize * len(arr))
        if len(arr):
            addr, _ = arr.buffer_info()
            self.ok(self.lib.cuMemcpyHtoD_v2(p, addr, arr.itemsize * len(arr)), "cuMemcpyHtoD")
        return p

    def get(self, p, typecode, n):
        out = array.array(typecode, bytes(array.array(typecode).itemsize * n))
        if n:
            addr, _ = out.buffer_info()
            self.ok(self.lib.cuMemcpyDtoH_v2(addr, p, out.itemsize * n), "cuMemcpyDtoH")
        return out

    def zeros(self, nwords):
        p = self.alloc(4 * nwords)
        self.ok(self.lib.cuMemsetD32_v2(p, 0, nwords), "cuMemsetD32")
        return p

    def free(self, *ps):
        for p in ps:
            if p:
                self.lib.cuMemFree_v2(p)

    def launch(self, kernel, work, *args):
        """A kernel over work items, a grid that fills the card."""
        t0 = time.perf_counter()
        try:
            self._launch(kernel, work, *args)
        finally:
            with _USE_LOCK:
                USE["kernels"] += 1
                USE["items"] += work
                USE["seconds"] += time.perf_counter() - t0

    def _launch(self, kernel, work, *args):
        holders, ptrs = [], []
        for kind, v in args:
            h = (ctypes.c_uint64 if kind == "p" else ctypes.c_uint32 if kind == "u" else ctypes.c_float)(v)
            holders.append(h)
            ptrs.append(ctypes.cast(ctypes.byref(h), ctypes.c_void_p))
        argv = (ctypes.c_void_p * len(ptrs))(*ptrs)
        blocks = max(1, min(self.sms * 32, (work + 255) // 256))
        self.ok(self.lib.cuLaunchKernel(self.kernels[kernel], blocks, 1, 1, 256, 1, 1, 0, None, argv, None), kernel)
        self.ok(self.lib.cuCtxSynchronize(), kernel)

    def program(self, src, names):
        """Kernels written in CUDA C."""
        key = (src, tuple(names))
        got = self.__dict__.setdefault("programs", {})
        if key in got:
            return got[key]
        ptx = nvrtc_compile(src, self.cc)
        if ptx is None:
            got[key] = None
            return None
        module = ctypes.c_void_p()
        log = ctypes.create_string_buffer(16384)
        opts = (ctypes.c_int * 2)(5, 6)
        vals = (ctypes.c_void_p * 2)(ctypes.cast(log, ctypes.c_void_p), ctypes.c_void_p(16384))
        with self.lock:
            self.bind()
            r = self.lib.cuModuleLoadDataEx(ctypes.byref(module), ctypes.c_char_p(ptx), 2, opts, vals)
            if r:
                raise RuntimeError("its card could not load its program: " + log.value.decode(errors="replace")[:400])
            out = {}
            for n in names:
                f = ctypes.c_void_p()
                self.ok(self.lib.cuModuleGetFunction(ctypes.byref(f), module, n.encode()), n)
                out[n] = f
        got[key] = out
        return out

    def run(self, fn, blocks, threads, args, items=0):
        """One of its own programs' kernels."""
        holders = [t(v) for t, v in args]
        argv = (ctypes.c_void_p * len(holders))(*[ctypes.cast(ctypes.byref(h), ctypes.c_void_p) for h in holders])
        t0 = time.perf_counter()
        try:
            self.ok(self.lib.cuLaunchKernel(fn, blocks, 1, 1, threads, 1, 1, 0, None, argv, None), "launch")
            self.ok(self.lib.cuCtxSynchronize(), "run")
        finally:
            with _USE_LOCK:
                USE["kernels"] += 1
                USE["items"] += items
                USE["seconds"] += time.perf_counter() - t0

    def put_bytes(self, data):
        """Bytes copied to the card."""
        p = self.alloc(len(data))
        if data:
            buf = ctypes.create_string_buffer(bytes(data), len(data))
            self.ok(self.lib.cuMemcpyHtoD_v2(p, ctypes.cast(buf, ctypes.c_void_p), len(data)), "cuMemcpyHtoD")
        return p

    def get_bytes(self, p, n):
        buf = ctypes.create_string_buffer(max(1, n))
        if n:
            self.ok(self.lib.cuMemcpyDtoH_v2(ctypes.cast(buf, ctypes.c_void_p), p, n), "cuMemcpyDtoH")
        return buf.raw[:n]

    def clear(self, p, nbytes):
        """Zeros over nbytes at p."""
        self.ok(self.lib.cuMemsetD32_v2(p, 0, (nbytes + 3) // 4), "cuMemsetD32")


NVRTC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "novalie_libs", "nvrtc")
_NVRTC = [None, False]


def nvrtc():
    """NVIDIA's compiler of CUDA C for the card."""
    if _NVRTC[1]:
        return _NVRTC[0]
    _NVRTC[1] = True
    names = ("nvrtc64_120_0.dll",) if os.name == "nt" else ("libnvrtc.so.12", "libnvrtc.so")
    libs = os.path.dirname(NVRTC_DIR)
    for where in (NVRTC_DIR, os.path.join(libs, "nvidia", "cuda_nvrtc", "bin" if os.name == "nt" else "lib")):
        for n in names:
            path = os.path.join(where, n)
            if not os.path.exists(path):
                continue
            try:
                if os.name == "nt":
                    _NVRTC.append(os.add_dll_directory(where))
                    for f in sorted(os.listdir(where)):
                        if f.startswith("nvrtc-builtins") and f.endswith(".dll"):
                            _NVRTC.append(ctypes.WinDLL(os.path.join(where, f)))
                    lib = ctypes.WinDLL(path)
                else:
                    for f in sorted(os.listdir(where)):
                        if f.startswith("libnvrtc-builtins"):
                            _NVRTC.append(ctypes.CDLL(os.path.join(where, f), mode=ctypes.RTLD_GLOBAL))
                    lib = ctypes.CDLL(path)
            except OSError:
                continue
            lib.nvrtcGetErrorString.restype = ctypes.c_char_p
            _NVRTC[0] = lib
            return lib
    return None


def nvrtc_compile(src, cc):
    """CUDA C compiled to PTX for a card of compute capability cc."""
    lib = nvrtc()
    if lib is None:
        return None
    n = ctypes.c_int()
    arch = cc
    if lib.nvrtcGetNumSupportedArchs(ctypes.byref(n)) == 0 and n.value:
        archs = (ctypes.c_int * n.value)()
        lib.nvrtcGetSupportedArchs(archs)
        known = sorted(archs)
        arch = max([a for a in known if a <= cc] or known[:1])
    prog = ctypes.c_void_p()
    r = lib.nvrtcCreateProgram(ctypes.byref(prog), src.encode(), b"novalie.cu", 0, None, None)
    if r:
        raise RuntimeError("its compiler: " + lib.nvrtcGetErrorString(r).decode())
    try:
        opts = [f"--gpu-architecture=compute_{arch}".encode(), b"--std=c++17"]
        argv = (ctypes.c_char_p * len(opts))(*opts)
        r = lib.nvrtcCompileProgram(prog, len(opts), argv)
        size = ctypes.c_size_t()
        if r:
            lib.nvrtcGetProgramLogSize(prog, ctypes.byref(size))
            log = ctypes.create_string_buffer(size.value + 1)
            lib.nvrtcGetProgramLog(prog, log)
            raise RuntimeError("its compiler: " + log.value.decode(errors="replace")[:1500])
        lib.nvrtcGetPTXSize(prog, ctypes.byref(size))
        ptx = ctypes.create_string_buffer(size.value)
        lib.nvrtcGetPTX(prog, ptx)
        return ptx.raw
    finally:
        lib.nvrtcDestroyProgram(ctypes.byref(prog))


_CARD, _TRIED, _LOCK = None, False, threading.Lock()
USE, _USE_LOCK = {"kernels": 0, "items": 0, "seconds": 0.0}, threading.Lock()


def card():
    """Its graphics card, or None."""
    global _CARD, _TRIED
    with _LOCK:
        if not _TRIED:
            _TRIED = True
            if os.environ.get("NOVALIE_GPU", "1") != "0":
                try:
                    _CARD = _Card()
                except Exception:
                    _CARD = None
        return _CARD


def describe(ask=True):
    """Its card and what it did on it."""
    c = card() if ask else _CARD
    if c is None:
        return None
    with _USE_LOCK:
        used = dict(USE)
    return {"name": c.name, "memory_gb": round(c.memory / 2 ** 30, 2), "sms": c.sms, "kernels": used["kernels"],
            "items": used["items"], "seconds": round(used["seconds"], 3)}


def singles(items, rate_of, ds, screen=None):
    """Its laws of odds of one condition."""
    c = card()
    if c is None or not items or not ds:
        return None
    D = len(ds)
    vi, off, vidx, cnt = {}, array.array("I", [0]), array.array("I"), array.array("I")
    for _, row in items:
        for v, h in row[3].items():
            k = vi.get(v)
            if k is None:
                k = vi[v] = len(vi)
            vidx.append(k)
            cnt.append(int(h))
        off.append(len(vidx))
    rate = array.array("f", [-1.0]) * (max(1, len(vi)) * D)
    for v, k in vi.items():
        for di, d in enumerate(ds):
            r = rate_of(v, d)
            if r is not None:
                rate[k * D + di] = r
    where = {d: i for i, d in enumerate(ds)}
    C = len(items)
    Q = C * D
    K = array.array("I", bytes(4 * max(1, Q)))
    for ci, (_, row) in enumerate(items):
        for d, n in row[2].items():
            di = where.get(d)
            if di is not None:
                K[ci * D + di] = int(n)
    with c.lock:
        c.bind()
        ptr = []
        try:
            p_off, p_vidx = c.put(off), c.put(vidx if len(vidx) else array.array("I", [0]))
            p_cnt, p_rate, p_k = c.put(cnt if len(cnt) else array.array("I", [0])), c.put(rate), c.put(K)
            p_nf, p_e = c.zeros(Q), c.zeros(Q)
            ptr += [p_off, p_vidx, p_cnt, p_rate, p_k, p_nf, p_e]
            c.launch("singles_sums", Q, ("p", p_off), ("p", p_vidx), ("p", p_cnt), ("p", p_rate), ("p", p_nf),
                     ("p", p_e), ("u", C), ("u", D))
            nf = c.get(p_nf, "I", Q)
            kept = None
            if screen is not None:
                cap = 1 << 14
                while True:
                    p_count, p_out = c.zeros(1), c.alloc(4 * cap)
                    c.launch("pairs_select", Q, ("p", p_k), ("p", p_nf), ("p", p_e), ("p", p_out), ("p", p_count),
                             ("u", Q), ("u", cap), ("f", screen))
                    n = c.get(p_count, "I", 1)[0]
                    if n <= cap:
                        kept = c.get(p_out, "I", n)
                        c.free(p_count, p_out)
                        break
                    c.free(p_count, p_out)
                    cap = n
        finally:
            c.free(*ptr)
    return nf, kept, D


def pair_index(a, b, F):
    """The place of the pair a < b among the F*(F-1)/2 pairs of F conditions."""
    return a * F - a * (a + 1) // 2 + (b - a - 1)


def pair_of(p, F):
    """The pair a < b at place p."""
    lo, hi = 0, F - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid * F - mid * (mid + 1) // 2 <= p:
            lo = mid
        else:
            hi = mid - 1
    a = lo
    return a, p - (a * F - a * (a + 1) // 2) + a + 1


def pair_candidates(acts, F, changes, rates, D, thr, margin=1.0):
    """The pairs of conditions."""
    c = card()
    if c is None or not acts:
        return pair_candidates_plain(acts, F, changes, rates, D, thr)
    P = F * (F - 1) // 2
    Q = P * D
    need = 12 * Q + 64 * sum(len(x) for x in acts) + (1 << 20)
    if Q >= 2 ** 32 or need > c.room():
        return pair_candidates_plain(acts, F, changes, rates, D, thr)
    row, off, feat = array.array("I"), array.array("I", [0]), array.array("I")
    for t, ids in enumerate(acts):
        feat.extend(ids)
        row.extend([t] * len(ids))
        off.append(len(feat))
    ch = array.array("i", [int(x) for x in changes])
    rt = array.array("f", [float(r) for rs in rates for r in rs])
    with c.lock:
        c.bind()
        ptr = {}
        try:
            for name, arr in (("row", row), ("off", off), ("feat", feat), ("ch", ch), ("rate", rt)):
                ptr[name] = c.put(arr)
            ptr["k"], ptr["nf"], ptr["e"] = c.zeros(Q), c.zeros(Q), c.zeros(Q)
            c.launch("pairs_accumulate", len(feat), ("p", ptr["row"]), ("p", ptr["off"]), ("p", ptr["feat"]),
                     ("p", ptr["ch"]), ("p", ptr["rate"]), ("p", ptr["k"]), ("p", ptr["nf"]), ("p", ptr["e"]),
                     ("u", len(feat)), ("u", F), ("u", D))
            cap = 1 << 16
            while True:
                ptr["count"] = c.zeros(1)
                ptr["out"] = c.alloc(4 * cap)
                c.launch("pairs_select", Q, ("p", ptr["k"]), ("p", ptr["nf"]), ("p", ptr["e"]), ("p", ptr["out"]),
                         ("p", ptr["count"]), ("u", Q), ("u", cap), ("f", thr - margin))
                n = c.get(ptr["count"], "I", 1)[0]
                if n <= cap:
                    got = c.get(ptr["out"], "I", n)
                    break
                c.free(ptr.pop("count"), ptr.pop("out"))
                cap = n
        finally:
            c.free(*ptr.values())
    out = {}
    for q in sorted(got):
        p, d = divmod(q, D)
        out.setdefault(pair_of(p, F), set()).add(d)
    return out


INT64_MAX, INT64_MIN = 2 ** 63 - 1, -2 ** 63


class History:
    """A sense's history on the card, for its laws of counts."""

    def __init__(self, c, m):
        self.card, self.m = c, m
        self.n, self.cap = 0, 0
        self.counts = self.colors = 0
        self.codes = {}
        self.table = None

    def __del__(self):
        try:
            if self.card is not None:
                with self.card.lock:
                    self.card.bind()
                    self.drop_table()
                    self.card.free(self.counts, self.colors)
        except Exception:
            pass

    def drop_table(self):
        if self.table is not None:
            self.card.free(self.table[1], self.table[2], *self.table[4])
            self.table = None

    def sync(self, counts, colors):
        """What it lived since the last time, sent to the card."""
        with self.card.lock:
            self.card.bind()
            self._sync(counts, colors)

    def _sync(self, counts, colors):
        T = len(colors)
        if T <= self.n:
            return
        c, m = self.card, self.m
        if T > self.cap:
            cap = max(1024, 2 * T)
            pc, po = c.alloc(4 * m * cap), c.alloc(4 * cap)
            if self.n:
                c.ok(c.lib.cuMemcpyDtoD_v2(pc, self.counts, 4 * m * self.n), "cuMemcpyDtoD")
                c.ok(c.lib.cuMemcpyDtoD_v2(po, self.colors, 4 * self.n), "cuMemcpyDtoD")
            c.free(self.counts, self.colors)
            self.counts, self.colors, self.cap = pc, po, cap
        rows = array.array("i")
        for row in counts[self.n:T]:
            rows.extend(row)
        seen = array.array("i")
        codes = self.codes
        for o in colors[self.n:T]:
            k = codes.get(o)
            if k is None:
                k = codes[o] = len(codes)
            seen.append(k)
        addr, _ = rows.buffer_info()
        c.ok(c.lib.cuMemcpyHtoD_v2(self.counts + 4 * m * self.n, addr, 4 * len(rows)), "cuMemcpyHtoD")
        addr, _ = seen.buffer_info()
        c.ok(c.lib.cuMemcpyHtoD_v2(self.colors + 4 * self.n, addr, 4 * len(seen)), "cuMemcpyHtoD")
        self.n = T

    def place(self, eff, mods):
        """How each state of a model is written as one number."""
        c, m, r, T = self.card, self.m, len(mods), self.n
        lo, span = [0] * r, [q for q in mods]
        free = [j for j, q in enumerate(mods) if q == 0]
        e = array.array("q", [int(eff[a][j]) for a in range(m) for j in range(r)])
        q = array.array("q", [int(x) for x in mods])
        pe, pq = c.put(e), c.put(q)
        if free:
            pmin = c.put(array.array("q", [INT64_MAX] * r))
            pmax = c.put(array.array("q", [INT64_MIN] * r))
            c.launch("cc_range", T, ("p", self.counts), ("p", pe), ("p", pq), ("p", pmin), ("p", pmax),
                     ("u", T), ("u", m), ("u", r))
            kmin, kmax = c.get(pmin, "q", r), c.get(pmax, "q", r)
            c.free(pmin, pmax)
            for j in free:
                lo[j], span[j] = kmin[j], kmax[j] - kmin[j] + 1
        stride, total = [], 1
        for s in span:
            stride.append(total)
            total *= max(1, s)
        if total >= 2 ** 63 - 1:
            c.free(pe, pq)
            return None
        return pe, pq, c.put(array.array("q", lo)), c.put(array.array("Q", stride)), c.put(array.array("Q", [max(1, s) for s in span]))

    def check(self, key, eff, mods):
        """As Mind.check: how many states the model gives its moments, or None when one state was seen two ways."""
        with self.card.lock:
            self.card.bind()
            return self._check(key, eff, mods)

    def _check(self, key, eff, mods):
        c = self.card
        how = self.place(eff, mods)
        if how is None:
            return False
        T = self.n
        S = 1
        while S < 2 * T:
            S *= 2
        tk, tc = c.alloc(8 * S), c.alloc(4 * S)
        c.ok(c.lib.cuMemsetD32_v2(tk, 0xFFFFFFFF, 2 * S), "cuMemsetD32")
        c.ok(c.lib.cuMemsetD32_v2(tc, 0xFFFFFFFF, S), "cuMemsetD32")
        st = c.zeros(2)
        pe, pq, plo, pst, psp = how
        c.launch("cc_insert", T, ("p", self.counts), ("p", self.colors), ("p", pe), ("p", pq), ("p", plo), ("p", pst),
                 ("p", tk), ("p", tc), ("p", st), ("u", T), ("u", self.m), ("u", len(mods)), ("u", S - 1))
        got = c.get(st, "I", 2)
        c.free(st)
        self.drop_table()
        self.table = (key, tk, tc, S - 1, how, len(mods))
        return None if got[1] else got[0]

    def quick(self, key, classes, sample):
        """Its quick test of classes of candidates under the model whose table it holds."""
        if self.table is None or self.table[0] != key or not classes or not sample:
            return None
        with self.card.lock:
            self.card.bind()
            return self._quick(classes, sample)

    def _quick(self, classes, sample):
        c = self.card
        _, tk, tc, mask, how, r = self.table
        pe, pq, plo, pst, psp = how
        cls = array.array("q", [int(x) for cl in classes for x in cl])
        ps, pc = c.put(array.array("I", sample)), c.put(cls)
        bad, agree = c.zeros(len(classes)), c.zeros(len(classes))
        c.launch("cc_quick", len(sample) * len(classes), ("p", self.counts), ("p", self.colors), ("p", pe), ("p", pq),
                 ("p", plo), ("p", pst), ("p", psp), ("p", tk), ("p", tc), ("p", ps), ("p", pc), ("p", bad), ("p", agree),
                 ("u", len(sample)), ("u", len(classes)), ("u", self.m), ("u", r), ("u", mask))
        out = list(zip(c.get(bad, "I", len(classes)), c.get(agree, "I", len(classes))))
        c.free(ps, pc, bad, agree)
        return out


def history(m):
    """A sense's history on the card."""
    c = card()
    return None if c is None else History(c, m)


def kl_digits(n, k, p):
    """As novalie_app.kl_digits."""
    if n <= 0 or k <= n * p or p >= 1:
        return 0.0
    p, a = max(p, 1e-12), k / n
    d = a * math.log(a / p) + ((1 - a) * math.log((1 - a) / (1 - p)) if a < 1 else 0.0)
    return n * d / math.log(10)


def pair_candidates_plain(acts, F, changes, rates, D, thr):
    """The same search in plain Python."""
    k, nf, e = {}, {}, {}
    for t, ids in enumerate(acts):
        rs, c = rates[t], changes[t]
        ds = [d for d in range(D) if rs[d] >= 0]
        if not ds:
            continue
        for x in range(len(ids)):
            a = ids[x]
            for y in range(x + 1, len(ids)):
                key = (a, ids[y])
                for d in ds:
                    kd = key + (d,)
                    nf[kd] = nf.get(kd, 0) + 1
                    e[kd] = e.get(kd, 0.0) + rs[d]
                    if c == d:
                        k[kd] = k.get(kd, 0) + 1
    out = {}
    for kd, n in nf.items():
        if n < 2:
            continue
        kk, base = k.get(kd, 0), e[kd] / n
        quick = kl_digits(n, kk, base) if kk > e[kd] else kl_digits(n, n - kk, 1 - base)
        if quick >= thr:
            out.setdefault(kd[:2], set()).add(kd[2])
    return out


def made_up_acts(T, F, per, seed):
    """Acts for its checks, by a fixed rule."""
    x, acts, changes, rates = seed, [], [], []
    for t in range(T):
        ids = set()
        while len(ids) < per:
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
            ids.add((x >> 4) % F)
        ids = sorted(ids)
        acts.append(ids)
        x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        changes.append(0 if (3 in ids and 7 in ids) or (x >> 4) % 50 == 0 else -1)
        rates.append([0.05, -1.0])
    return acts, changes, rates


def self_check(T=3000, F=400, per=60, seed=7):
    """The card's search against the plain one."""
    import time
    acts, changes, rates = made_up_acts(T, F, per, seed)
    t0 = time.perf_counter()
    plain = pair_candidates_plain(acts, F, changes, rates, 2, 6.0)
    t1 = time.perf_counter()
    fast = pair_candidates(acts, F, changes, rates, 2, 6.0)
    t2 = time.perf_counter()
    agrees = all(k in fast and v <= fast[k] for k, v in plain.items())
    return agrees, (3, 7) in plain and (3, 7) in fast, round(t2 - t1, 3), round(t1 - t0, 3), (len(plain), len(fast))


def bench(T=20_000, F=3000, per=120, seed=11):
    """The card alone on a large search."""
    import time
    acts, changes, rates = made_up_acts(T, F, per, seed)
    t0 = time.perf_counter()
    got = pair_candidates(acts, F, changes, rates, 2, 6.0)
    return T * per * (per - 1) // 2, round(time.perf_counter() - t0, 3), len(got)


if __name__ == "__main__":
    print("card:", describe())
    print("self check (agrees, planted pair found, card s, plain s, (plain, card) candidates):", self_check())
    print("large search (pair occurrences, card s, candidates):", bench())

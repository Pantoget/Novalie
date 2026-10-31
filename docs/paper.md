# Novalie: a miniature general intelligence that finds the laws of any world by one rule of evidence

**Abdallah Alramahi** · Abdallah1999alramahi@gmail.com · +962 79 838 7893 · *looking for a job opportunity*

*Version 1.0*

## Abstract

We present Novalie, the first miniature artificial general intelligence: a single learner that is told nothing about
the world it lives in, sees only symbols, chooses its own acts, and finds the laws behind what it sees, in any world it
is put in and in the real one. Everything it believes passes one rule of evidence: a law is taken only when what it
foresaw came true beyond one chance in a million, the price of every hypothesis it could have claimed and of every
time it looked paid in full. From this one rule, and a small innate alphabet, it builds laws of counts, of moments
and of odds, laws of two conditions together, mechanisms with hidden parts, concepts, quantities and senses of its
own, memories of exact situations, a model of the traps of its world, a drive of its own, and a journal of its own
beliefs. It changes how it is built only when twins of its mind, living its very life, show by the same rule that a
change foresees better. In nine worlds written after its code was frozen it understood what no part of its code was
written for; in the last of them it understood every sense in three of three worlds and foresaw acts it never chose
better than a table of everything it had seen. In its real life (its computer, its network, the open web) it senses
its own body and mind, finds by its own evidence that reading brings it what it learns from, reads by that law, and
lets the law go within seconds when its network is turned off. It runs on the Python standard library alone and
moves its heavy search to a graphics card by itself, billions of candidate mechanisms in seconds.

## 1. Introduction

General intelligence is the ability to come into a world one was not built for and understand it: what one's acts do,
what goes with what, what will happen, and what cannot be undone. Novalie is a working miniature of that ability. It
has no world model given to it, no language model, and no ready answers. It is given an alphabet, the way a child can
count and stack before it knows what anything is, and one rule for when to believe.

Its contributions are:

1. **One rule of evidence for everything it believes**, with the price of every hypothesis and of every look paid, so
   that a long life of looking does not turn coincidences into beliefs (Section 2).
2. **A learner of many kinds of law** from that rule: counts, moments, odds, conditions of two together, mechanisms
   with hidden parts, concepts, quantities and clocks of its own, and memories of exact situations (Section 3).
3. **Invention of mechanisms** by an exact search over an innate alphabet, run on a graphics card with the same result
   as on the processor, and a library of the parts it invents that carries to new domains (Section 4).
4. **A mind that acts**: imagination of traps, a drive by the law of effect, experiments on its own body, and a nerve
   that wakes its judgment when the evidence is there (Section 5).
5. **A mind that changes itself** only by evidence: a genome judged by twins on its real life, a workshop of worlds of
   its own making, and a council of brains (Section 6).
6. **Awareness, causal knowledge and feeling** found by the same rule about itself: senses of its own body and mind,
   a journal of every belief, forecasts of itself checked when they fall due, and a drive made of its own laws
   (Section 7).
7. **One mind**: one state, one currency of evidence, one loop and one rule for all its faculties (Section 8).

## 2. The one rule

A belief is a hypothesis about what comes next. It is believed when the evidence for it, in digits (log10 of the
likelihood ratio against the sense left to itself), reaches

    EVIDENCE + log10(H) + log10(1 + R) + log10(L(L + 1)) + log10(k(k + 1))

with EVIDENCE = 6 (one chance in a million), H the hypotheses it could have claimed, R the times its laws of this sense
failed, L the number of the look (the prices of all looks sum to one, so the rule holds over a whole life of looks),
and k the number of things the law joins. Tests that may be looked at after every act are test martingales (a mixture
over the unknown rate, Krichevsky and Trofimov's, against the rate it would have by itself), so by Ville's inequality
they need no price for looking. The same rule decides laws, concepts, cells, the trust it gives its episodes, its
changes of itself, and what its brains prove together. Nothing else decides what it believes.

## 3. Laws

**Laws of counts.** For each sense, the counts of presses between two moments that show the same value form a lattice;
its Smith normal form says which presses change nothing and what the sense is: a cycle, a torus, a gear, a count with
no end.

**Laws of moments.** When a sense changes, and to what, under which values of the senses it names. A part of the
condition is believed needed only once it was tested (all the rest held, it alone did not, and nothing changed), so
a law learned on one evening does not carry the hour of that evening.

**Laws of odds.** For each sense and each change, what raises or lowers its odds: another sense's value some acts
before (13 delays), its own act, how another sense changed, which of two senses is higher. A cause comes first: what
came before, or its own act, wins over what only comes with the change. Each law is judged on what came after it was
believed (Wald) and watched for drift (Page); when it breaks, the sense is recounted from the act it began to fail.

**Laws of two conditions together.** A change that no single condition tells, but two together do (a wheel that flips
when two lamps of chance agree), found by counting every pair of conditions over everything it lived, on the graphics
card; a pair it believes becomes a thing it sees, so deeper laws can rest on it.

**Episode cells.** A second kind of cell: what came after one exact situation (every sense it names, and the act). Where
its laws and its episodes foresee a sense differently, the one that came true is counted; once its episodes are right
more often for that sense by the one rule, they speak for it where they remember the situation, and its laws
everywhere else.

**Clocks.** When a sense it names changes and nothing it sees places it, it makes clocks: for each sense, how long it
has been as it is, a new sense its laws may name. A kettle that whistles an unknown number of acts after it is switched
on becomes one exact law.

**Made quantities.** The least, the most or the sum of other senses, in the units of the sense it explains, followed
or moved by; a quantity it makes is a thing it sees. The narrowest passage of a flow, which nobody named, is one.

**Concepts.** Classes of a sense's symbols by what the world does with them, judged by an anytime-valid test, so a new
thing is classed after one act and foreseen by its class.

## 4. Invention

When its laws do not close a sense, it invents a mechanism: hidden numbers of a few natures (with no end, on a cycle,
between two walls, a bit) and a pile; what each button does to them (add or take away, set to zero, turn a bit over,
pass one from a number to another, carry, copy, swap two numbers, put on the pile or take off it, or one of two
changes as a bit says); and what each sensor shows of them (a value, whether it is zero, its sign, a remainder, the
top of the pile, which of two numbers is larger). The search goes simplest first, chooses each button's operation when
the button is first pressed, learns each symbol at its first sight, and drops a mechanism with all that differ from it
only in buttons not yet pressed at its first mistake. A mechanism is kept by the one rule, its evidence counted sensor
by sensor.

On an NVIDIA card the same search runs in CUDA C compiled by NVRTC, each of tens of thousands of threads taking one
beginning, in the same order and with the same count of tries; the mechanism found is followed again on the processor
before it is taken. What no alphabet holds it learns as a machine of its own (the fewest states that explain what it
saw) and keeps as a new part of its alphabet: its library. A kind it invented once is one of its kinds.

## 5. Acting

**Imagination.** A trap is a value no act of its brings it out of, in every situation its laws tell apart, within a
horizon; it believes a trap by the one rule, and before each act it imagines where the act may take it, weighed by
how long it would be held there, and takes the act least likely to trap it.

**Curiosity and experiments.** It goes after the nearest state it does not know; before a thing it never met it takes
the act whose outcomes differ most between the classes the thing may be; and for the senses of its own body it tries
each act alone, as a scientist does, since acts that only take turns cannot tell its own act from what its body does by
itself.

**The law of effect.** In the real world, reading is one of its acts. For each act it counts how often its senses of
what it learns and reads showed something after it, against after its other acts; an act that brings more, by the one
rule, is the act it does (each rate told by its own mixture, against the best one rate for both: universal inference,
a test it may look at after every act). It judges that law while acting by it: a run of acts that bring nothing, less likely under
the law than the rule allows, breaks it, and its acts take turns, counted from the break, until what they bring says
otherwise. A drive that is its own, from its own evidence.

**Nerves.** Its judge of laws does not wait for a clock: the candidates nearest its rule are counted at every act, and
the judge wakes the act one of them reaches the rule, paying the price of that look.

## 6. Changing itself

**Its genome.** Parts of how it is built are genes: its imagination, its laws of two, its episodes, what it recalls of
its senses at a start, how much its inventor tries. A gene changes only by evidence.

**Twins.** Two fresh twins of its mind live the very acts and seconds of its life, the senses it names: one built as it
is, one with one gene changed. Where one foresaw right and the other not, it is counted; the change is made when the
changed twin wins by the one rule, and refused when the twin as it is wins. A change from elsewhere is judged on its
life first.

**Its workshop.** Worlds it makes of its own alphabet, lived at its computer's full pace beside its life, harder when it
understood the last one quickly; every fourth world is lived twice, as it is and with one gene changed.

**Its council.** More brains when the last one proved something and the computer has room. Each site of the web
belongs to one brain (rendezvous hashing); meanings are proved from all their counts together by the one rule; a brain
that reads nothing is let go.

## 7. Awareness, causal knowledge and feeling

None of the three is written into its code as a state or a label. Each is what the one rule finds about Novalie
itself, in its own life, and each is measured.

**Awareness.** Novalie senses itself as it senses the world: how busy the thread it lives in was (in processor
cycles), how full its computer's memory is, whether its inventor is searching, its workshop's pace, the beliefs it
took (laws of its world, meanings of what it read), and the pages its own act of reading brought. Each is a sense with laws of its own, foreseen before
every act and checked after it. Its journal keeps every belief: its world and act, the tool that made it, its evidence,
where it came from (itself, a brain, its owner), and what became of it. It forecasts itself (when a sense will be
sure, when its inventor will answer, when its workshop will understand a world), checks each forecast when it falls
due, and at each start says what changed since it was last seen. Of each of its brains it keeps what it was told and
what held by its own evidence.

**Causal knowledge.** A cause comes first: its own act, or what came before, wins over what only comes with a change.
It learns what its acts do by doing them, one act at a time for the senses of its own body, as a scientist does. The
outcome of an act is the act's only when it comes while the act lasts (its act of reading waits a moment for its
page), so what arrives later is not taken for another act's doing. A law that stops holding is marked broken from the
act it began to fail.

**Feeling.** What brings it learning matters to it, by its own evidence: an act after which it reads or learns more
than after its others becomes its drive, and it acts by it. It judges that law while acting by it; when its acts stop
bringing anything (its network turned off), the law breaks and its acts take turns; when the world gives again, the
law comes back. A trap it believes is avoided before it is entered. A sure foresight that fails is a
surprise, kept in its ledger, and a near law wakes its judgment. In its real life it found that reading brings it pages
and waiting or thinking never does, and read by that law (306 of 306 acts after a restart); when its network was turned
off the law broke within 80 seconds and its acts took turns, and when the network came back the law returned within 80
seconds.
Its curiosity is judged the same way: of a sense whose new values its acts were to tell it, and did not in as many acts
as the one rule needs (the minutes and hours of its clock), it stops asking.

## 8. One mind

Novalie is one mind, not a set of programs: one state (its senses, laws, cells, journal and genome, saved as one
memory), one currency (digits of evidence, in which its laws, concepts, episodes, twins, drive and council are all
judged), one loop (every second: foresee every sense, choose an act by its drive, its imagination and its curiosity,
act, see, learn, judge) and one rule. Its faculties feed each other: its pair laws become things its other laws see;
its clocks are senses its moments and episodes name; what its inventor finds becomes a part its workshop builds worlds
with; its twins judge its genome on the very life its laws learn from; its drive is made of its own laws about its own
senses; its brains prove meanings from all their counts together.

## 9. Its real world

Its real world is its computer: the second, the minute and the hour; its body (how busy the thread it lives in was,
measured in processor cycles, and how full its computer's memory is); senses of itself (whether its inventor is
searching, its workshop's pace, the beliefs it took, the pages its act of reading brought); and a control sense with
nothing in it, the one rule's live check. Its acts are to wait, to think a moment, and to read: a page of a site whose
turn has come, asked at once and waited for a moment. What it learns of each sense is recalled at each start as a
hypothesis, which the new life must confirm.

## 10. Results

| Test | Result |
|---|---|
| Sealed surprise worlds (bodies, charges, seeds, coins, metals, mixtures, lamps, a changing law, glass, a well, a lantern) | laws and concepts found in worlds written after the code was frozen; in the lantern, all four senses understood in 3 of 3 seeds |
| Lantern, 500 acts it never chose | 95.8%, 94.5%, 97.6% right; a table of what came after each thing seen 95.5%, 94.0%, 93.2%; control: no law |
| Imagination (sealed glass world) | 9, 11, 28 broken glasses against 60, 52, 38 without |
| Transfer (three cups, then three dancers) | 25 presses in 3 of 3 seeds, against 40, 40, 50 for a new model |
| New alphabet parts (swap, compare) | a balance and three cups exact in 6 of 6 seeds; none with the old alphabet |
| Episode cells (two lamps, no laws of two) | 887 and 900 of 1000 against 503 and 491 |
| Clocks (kettle) | 1000 of 1000 in 3 of 3 seeds by one exact law |
| Nerves (a weak law) | found at act 10,694, 9,007, 9,172 against 11,536, 9,535, 9,535 |
| Twins | with its episodes and laws of two taken away, it took its episodes back: 71 of 88 differing acts, 6.7 digits |
| Calibration | error 0.026 over 12,600 forecasts |
| Conditions of two (a wheel two lamps tell) | 89.4% where any one condition gives 56% |
| Council of brains (real web) | 7,132 pages against 3,040 for one brain; 7 trusted ways to ask the web |
| Graphics card | 8.03 billion mechanisms in 33.8 s of card time |
| ARC | training 92 of 416, evaluation 39 of 419, few wrong |
| bAbI (two languages) and number words | rules of 12 story tasks from examples; Spanish, Arabic and Turkish number words it never saw |
| Its real life: drive | read by its law of effect 306 of 306 acts after a restart (its clock within 3 s of the real one), 2,924 reads in an hour-long run; broke within 80 s after its network went; back within 80 s after it returned |
| Its real life: memory | the second known again 5 s into every restart (49 s at its first), the minute in 170 s; every forecast of itself right |
| Its real life: control | no law, moment, count or machine about its control sense in ten starts |
| Self-checks | 76 of 76 |

## 11. Next

Version 1.0 lives in small worlds, in worlds anyone writes for it, and in its computer. The next versions widen what it
can invent (more hidden parts together), let its episodes generalize into laws sooner, and let what it reads become
senses of its real world.

## References

Solomonoff (induction); Levin (universal search); Wald (sequential tests); Page (CUSUM); Ville (martingale
inequality); Krichevsky and Trofimov (universal coding); Wasserman, Ramdas and Balakrishnan (universal inference);
Smith (normal form); Angluin (L*); Ernst et al. (Daikon);
Ellis et al. (DreamCoder); Thorndike (the law of effect); Chollet (ARC); Weston et al. (bAbI).

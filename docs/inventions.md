# Inventions in Novalie 1.0

*Inventor: Abdallah Alramahi (Abdallah1999alramahi@gmail.com)*

The methods below were invented for Novalie and are, to its author's knowledge, new. Each is described as a method
(what it takes, what it does, what makes it work), with where it lives in the code and how it was measured.

## 1. One evidence rule with priced hypotheses, looks and depth

A single acceptance rule for every belief of a learning system: a hypothesis is believed when its evidence in digits
(log10 of a likelihood ratio, or of a test martingale) reaches `E + log10(H) + log10(1 + R) + log10(L(L+1)) +
log10(k(k+1))`, where H counts the hypotheses that could have been claimed, R the failures of earlier beliefs about the
same quantity, L the index of the look (the prices of all looks sum to one, so the guarantee holds over an unbounded
life of looking), and k the number of things the belief joins (beliefs of one thing and of more share the budget).
*Code:* `novalie/evidence.py` (`odds_bar`, `paid`). *Effect:* zero laws in every control world, nine sealed worlds
understood.

## 2. Episode cells trusted by a sign-test martingale

A second kind of predictive cell beside general laws: the outcome counts after one exact situation. For each predicted
quantity, the disagreements between the episode and the law are scored (which one came true), and the episode speaks
for that quantity only once a Krichevsky-Trofimov mixture martingale against even odds passes the evidence rule; the
same test, reset, gives the law back its voice. Exceptions to laws are remembered without a threshold on counts and
without ever overriding a law on noise. *Code:* `novalie/mind/foresight.py`. *Effect:* 887 and 900 of 1000 against
503 and 491 where only two things together foretell the outcome.

## 3. Clocks made on demand

When a sensed quantity changes and nothing the learner sees places the change, it creates, for every sense it names,
a new sense: how long that sense has been as it is (exact up to 16 acts, then by doublings), available to its laws
only as a value from before the act. *Code:* `novalie/mind/odds.py`, `novalie/mind/living.py`. *Effect:* a delayed
event (a kettle's whistle after an unknown delay) foreseen 1000 of 1000 by one exact law.

## 4. Evidence nerves

The candidate laws that came closest to the acceptance rule at a judgment are counted act by act; the judgment wakes
at the act one of them reaches the rule as the next judgment would ask it (the next look's price and the current
number of hypotheses included), instead of on a fixed schedule. *Code:* `novalie/learner.py`. *Effect:* a weak law
found at act 10,694, 9,007 and 9,172 against 11,536, 9,535 and 9,535, with 6 to 10 wakes.

## 5. Twins: self-modification judged on the agent's own life

Two fresh copies of the learner live the very acts and observations of the running agent, one with one parameter of
its construction (a gene) changed. Wherever exactly one of them foresaw an observation correctly, it is counted; the
change is adopted when the changed twin wins by a sign-test martingale at the evidence rule, refused when the
unchanged twin wins, and a change proposed elsewhere (in simulated worlds) is judged on the live data first. *Code:*
`novalie/mind/twins.py`, `novalie/mind/shadow.py`. *Effect:* with two parts removed, it took back the one that mattered
(71 of 88 differing acts, 6.7 digits).

## 6. A law of effect judged by the evidence rule, with a run-length refutation

The outcome of an act is counted for the act only when it comes while the act lasts (its act of reading waits a moment
for its page), so in an asynchronous world no act is credited with what another brought. For each act the agent counts
how often its senses of its own learning showed something after it, against after its other acts; an act that brings
more by the evidence rule (every act and sense it could have claimed paid for) becomes its drive. It judges that law
while acting by it: when the run of acts with nothing coming has, under the law's own rate, a probability below the
evidence rule, the law is broken, its counts begin again, and the agent returns to a fair trial of its acts. *Code:*
`novalie/mind/acting.py` (`effect_act`, `effect_count`), `novalie/mind/asking.py` (`read_by_act`). *Effect:* see the
agenda, H1.

## 7. Exact mechanism synthesis, identical on a graphics card and a processor

Enumeration of hidden mechanisms (numbers of a few natures, a pile, operations per button chosen at first press, sights
learned at first sight) with prefix pruning: one wrong foresight discards every mechanism that differs only in buttons
not yet pressed. On the card, each thread takes one beginning and searches what follows it in the processor's order,
counting tries the same way, so the result and its evidence are the same on both. *Code:* `novalie/parts/invent.py`,
`novalie/parts/gpu_invent.py`. *Effect:* 8.03 billion mechanisms in 33.8 s of card time.

## 8. A library of invented parts that carries across domains

A mechanism no innate part can express is learned as a minimal machine and kept as a new part of the alphabet, tried
first in later searches. *Code:* `novalie/parts/prime.py`, `invent.keep`. *Effect:* a machine learned with three cups
found with three dancers after 25 presses in 3 of 3 seeds, against 40 to 50 for a learner without it.

## 9. Moment laws with tested conditions

A law of when a quantity changes keeps a part of its condition only once that part was shown necessary (all the rest
held, that part alone did not, and nothing changed); a change that comes with an untested part different drops that
part and keeps the evidence. *Code:* `novalie/learner.py` (`see_moment`). *Effect:* its clock laws survive the change
of the hour and are recalled across restarts.

## 10. Trap imagination believed by the evidence rule

A trap is a value no act brings it out of within a horizon, in every situation its laws distinguish, with nested
horizons priced as looks; each act is imagined and weighed by the probability of entering a believed trap times its
horizon. *Code:* `novalie/mind/acting.py`. *Effect:* 9, 11 and 28 broken glasses against 60, 52 and 38 without.

## 11. A council of brains with pooled evidence

Brains (processes) are born when the last one proved something by the rule and the computer has room, and let go when
they read nothing or memory is short; each source belongs to one brain by rendezvous hashing, and meanings are proved
from the counts of all brains together by the same rule. *Code:* `novalie/parts/council.py`. *Effect:* 7,132 pages
against 3,040 for one brain, 7 trusted ways to ask the web.

## 12. Curiosity judged by what it tells

Before a thing it never met, the agent takes the act whose outcomes differ most between the classes the thing may be
(Jensen-Shannon, in digits). Each such act was to tell it that many digits; of a sense whose things it asked about for
as many acts as their sum would have needed to make it sure of one by the evidence rule, and is sure of none, it asks
no more, until one of them is told. Curiosity that its acts cannot satisfy (the minutes of a clock) stops by the same
rule that decides its beliefs. *Code:* `novalie/mind/foresight.py` (`telling_act`). *Effect:* in its real life, 26
acts on its clock's minutes and 52 on its hours, then its drive.

## 13. Senses of itself with a live control

The agent senses its own body and mind (thread busy time in processor cycles, memory load, whether its inventor
searches, its workshop's pace, digits learned, what it read by its own act) as senses whose laws it learns, beside a
control sense that holds nothing; any belief about the control is counted as a live measure of the rule's error rate.
*Code:* `novalie/body.py`, `novalie/mind/real.py`.

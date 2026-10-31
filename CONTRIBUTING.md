# Contributing to Novalie

Thank you for helping. Anyone may open an issue or a pull request; every pull request is reviewed, and only the
maintainer, Abdallah Alramahi ([@PantomathX](https://github.com/PantomathX), Abdallah1999alramahi@gmail.com), merges.

## The principles a change must keep

1. **One rule of evidence.** Every belief (a law, a concept, a cell, a change of how it is built) is taken only when
   its evidence passes `EVIDENCE` digits plus the price of every hypothesis it could have claimed and every look it
   took (`novalie/evidence.py`). No other threshold decides what it believes.
2. **Nothing given.** No knowledge of a world, no word list, no ready-made sentence in what it says. What it says is
   made of its own symbols and the words it proved.
3. **Deterministic decisions.** The same experience gives the same beliefs.
4. **It only reads the web.** GET requests to public addresses, robots.txt obeyed, a gap per site; no forms, no
   logins, no posting, and it never runs code it reads.
5. **English only** in code, comments, documentation and the page.

## Adding to it

- A new world: one file in `worlds/` (see `worlds/README.md`).
- A new faculty of the mind: a module in `novalie/mind/` holding a class of methods, added to the bases of `Novalie`
  in `novalie/mind/__init__.py`.
- A new part of its inventor's alphabet: `novalie/parts/invent.py` (and its kernel in `gpu_invent.py`, so the card
  and the processor stay the same search).

## Before a pull request

- Start it with `Start Novalie.bat` (or `python -m novalie --port 8790 --state test_state`) and let it live a few
  minutes in the real world and in one of the worlds; say what you saw.
- Keep comments short: headings and what is not obvious.

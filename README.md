# Novalie

*By [Abdallah Alramahi](#author).*

**The first miniature AGI: version 1.0.** A small general learner that is told nothing about the world it lives in.
It sees symbols, chooses acts, and finds the laws behind them by one rule of evidence: it believes a law only when
what it foresaw came true beyond one chance in a million, paying for every law it could have claimed. It lives in the
real world (its computer's clock and its own body, and the open web it reads), and in any world you give it.

It runs on the Python standard library alone. On an NVIDIA graphics card it moves its heavy search there by itself.

## Run it

**Windows:** double-click `Start Novalie.bat`. Its page opens in your browser.

**Any system:**

```bash
python -m novalie
```

Python 3.8 or newer. Its memory is kept in `novalie_state/` beside the code; **Turn off** on its page keeps everything
it learned, **Erase everything** starts it from zero.

Nothing tells it where the web is: its reading begins where you point it. Write a link to it on its page (Talk), or put
a file of links (one per line) or any file in `novalie_inbox/`. From there it follows links by itself, and reading
becomes one of its acts.

Useful options (`python -m novalie --help` lists them):

| Option | What it does |
|---|---|
| `--port 8790` | its page on another port |
| `--state DIR` | another memory folder |
| `--inbox DIR` | another folder of files for it to read |
| `--memory-gb 16` | the most memory it may hold (no ceiling by default) |
| `--brains 4` | the most brains of its council at once (default: one per core) |
| `--no-browser`, `--headless 300` | no page opened; or run 300 s without a page |
| `--host 0.0.0.0` | its page reachable from other computers |
| `--gap 2`, `--ignore-robots`, `--private-network`, `--page-mb 64` | how it reads the web |

Optional libraries let it read more (files, pictures, sound, video) and use an NVIDIA card's compiler:

```bash
python -m pip install --target novalie_libs -r requirements.txt
```

## Put it in a world

The **World** menu at the top of its page lists the real world and every world in `worlds/`. Choose one and it moves
there at once; its laws are never told to it. **Anyone can write a world**: one Python file in `worlds/` with a class
`World` (its acts, its senses, `press`, `observe`). See [worlds/README.md](worlds/README.md). Build a world that
should be hard for it, choose it, and watch what it finds: every law, cell and decision is on its page, with its
evidence.

## What is inside

| Folder | |
|---|---|
| `novalie/mind/` | the mind, one faculty per module: laws of odds, concepts, foresight and episodes, made senses and clocks, goals, things and analogy, thought, acting (imagination, the law of effect), twins (how it is built, judged on its life), language, reading, its council, its page's views |
| `novalie/learner.py` | one sense's learner: laws of counts, of moments, of odds, and its nerve |
| `novalie/parts/` | its inventor and the machines it makes, the graphics card, the laws of counts, the reader of files, its grammar, its anytime-valid concepts, its council of brains, its workshop, its page server |
| `novalie/ui/` | its page: a brain of three dimensions, its senses, its journal, what it is doing and why, and (Mind tab) its awareness, causal knowledge and feeling, live, from its own laws |
| `worlds/` | worlds to put it in |
| `docs/` | [the paper](docs/paper.md), [the agenda](docs/agenda.md) and [its inventions](docs/inventions.md) |

## Contributing

Issues and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). Every change is reviewed and approved
by the maintainer before it is merged.

## Author

**Abdallah Alramahi** designed and built Novalie, and is looking for a job opportunity.

- Email: [Abdallah1999alramahi@gmail.com](mailto:Abdallah1999alramahi@gmail.com)
- Phone: +962 79 838 7893
- GitHub: [@PantomathX](https://github.com/PantomathX)

Copyright (c) 2026 Abdallah Alramahi. All rights reserved.

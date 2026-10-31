# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Words and scripts: tokens, folding, the writing system of a word."""

import collections
import functools
import re
import unicodedata

from .parts import senses


def unicode_marks(planes=0x30000):
    """What Unicode says of each character, the same in every script."""
    stops, ends, asks, commas, cuts, edges = set(), {"\n"}, set(), set(), set(), set()
    for cp in range(planes):
        ch = chr(cp)
        cat = unicodedata.category(ch)
        if cat[0] not in "PS":
            continue
        name = unicodedata.name(ch, "")
        if "INVERTED" not in name and cat[0] == "P":
            if "FULL STOP" in name:
                stops.add(ch)
            elif "QUESTION MARK" in name:
                asks.add(ch)
                ends.add(ch)
            elif any(k in name for k in ("EXCLAMATION MARK", "DANDA", "INTERROBANG")):
                ends.add(ch)
        if cat[0] == "P" and "COMMA" in name and "QUOTATION" not in name:
            commas.add(ch)
        elif (cat[0] == "P" and "SEMICOLON" in name) or "VERTICAL LINE" in name:
            cuts.add(ch)
        if (cat[0] == "P" and ch not in "%‰‱#-@&") or cat == "Sk" or (cat == "Sm" and ch not in "+−=±×÷∓"):
            edges.add(ch)
    return stops, ends, asks, commas, cuts, edges


def chars(cs):
    """A set of characters as the inside of a pattern's [...]."""
    return "".join(re.escape(c) for c in sorted(cs))


STOPS, ENDS, ASKS, COMMAS, CUTS, EDGE_MARKS = unicode_marks()
SENTENCE_END = re.compile(f"(?:[{chars(ENDS)}]|[{chars(STOPS)}](?!\\d)|(?<!\\d)[{chars(STOPS)}])+")
@functools.lru_cache(maxsize=100_000)
def fold(w):
    """A word with the case of its letters folded and its marks taken off, the same way in every script."""
    w = unicodedata.normalize("NFD", w.casefold())
    return unicodedata.normalize("NFC", "".join(ch for ch in w if not unicodedata.combining(ch)))


SEPARATORS = re.compile(f"[\\s{chars(CUTS)}]+|(?<=\\D)[{chars(COMMAS)}]|[{chars(COMMAS)}](?=\\D)")


EDGES = "".join(sorted(EDGE_MARKS))


def tokens(text):
    """The pieces of a sentence."""
    return [t.strip(EDGES) for t in SEPARATORS.split(text) if t]


NUMBERS_AND_SIGNS = re.compile(r"\d+(?:[.,]\d+)*|[^\w\s]")
ACT_REF = re.compile(r"#\d+")


def typed_tokens(text):
    """What you type, in pieces."""
    out = []
    for piece in text.split():
        if ACT_REF.fullmatch(piece):
            out.append(piece)
        elif any(ch.isalpha() for ch in piece):
            out += tokens(piece)
        elif any(ch.isdigit() for ch in piece) or all(is_sign(ch) or ch in "=?\u061f" for ch in piece):
            out += NUMBERS_AND_SIGNS.findall(piece)
        else:
            out += tokens(piece)
    return [t for t in out if t]


def is_sign(t):
    """One sign that can stand between two numbers."""
    return len(t) == 1 and not t.isalnum() and not t.isspace() and t not in "=?\u061f"


@functools.lru_cache(maxsize=50_000)
def script_of(w):
    """The writing system a word is written in."""
    for ch in w:
        if ch.isalpha():
            return unicodedata.name(ch, "?").split(" ")[0]
    return "?"


def column_heads(text, k):
    """The words written at the head of each of the k columns of a table of numbers, in the order its reader
    counts them."""
    def numbers(s):
        return senses.NUMBER.findall(s.replace(",", " ").replace(";", " "))

    def head(sep):
        fields = lines[i].split(sep)
        for h in range(i - 1, -1, -1):
            names = lines[h].split(sep)
            if len(names) == len(fields) and 2 * sum(any(ch.isalpha() for ch in x) for x in names) > len(names):
                return names, fields
        return None

    lines = text.splitlines()
    for i, line in enumerate(lines):
        if len(numbers(line)) == k and all(len(numbers(x)) == k for x in lines[i + 1:i + 4]):
            break
    else:
        return None
    for sep in (",", ";", "\t", None):
        if (sep is None or sep in lines[i]) and (got := head(sep)):
            names, fields = got
            break
    else:
        return None
    out = {}
    for name, field in zip(names, fields):
        for _ in numbers(field):
            out[len(out) + 1] = name
    return out if len(out) == k else None


def main_script(sentences):
    """The writing system most of an article's words are in."""
    seen = collections.Counter(script_of(w) for words in sentences for w in words[:200])
    return seen.most_common(1)[0][0] if seen else None

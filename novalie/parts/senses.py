# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Novalie's senses are not made for pictures, sounds, or any kind of file."""
import base64
import binascii
import bz2
import html.parser
import io
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
import zipfile
import zlib

LIBS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "novalie_libs")
if os.path.isdir(LIBS) and LIBS not in sys.path:
    sys.path.append(LIBS)
try:
    import numpy as np
except ImportError:
    np = None
try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 40_000_000
    import warnings
    warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)
except ImportError:
    Image = None

def _ffmpeg():
    """ffmpeg: this computer's own."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    folder = os.path.join(LIBS, "imageio_ffmpeg", "binaries")
    try:
        names = sorted(f for f in os.listdir(folder) if f.startswith("ffmpeg") and (f.endswith(".exe") or os.name != "nt"))
    except OSError:
        return None
    return os.path.join(folder, names[-1]) if names else None


FFMPEG = _ffmpeg()
MAX_OUT = 8_000_000
BIG_PICTURE = 40_000_000


def available():
    return np is not None


def _out(symbols, raw, kind, dims=None):
    return {"symbols": symbols, "raw": raw, "kind": kind, "dims": dims}


# -- as it is -------------------------------------------------------------------------------------------
def as_bytes(data):
    return [_out(np.frombuffer(data[:MAX_OUT], dtype=np.uint8).astype(np.int64), None, "values")]


# -- characters -----------------------------------------------------------------------------------------
def _printable(s):
    if not s:
        return 0.0
    good = sum(1 for ch in s if ch.isprintable() or ch in "\n\r\t")
    return good / len(s)


def as_text(data):
    """Bytes read as characters, in whichever encoding gives nearly only printable characters."""
    data = data[:MAX_OUT]
    tries = []
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        tries.append("utf-16")
    tries += ["utf-8", "utf-16-le", "utf-16-be", "cp1256"]
    for enc in tries:
        try:
            s = data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
        if len(s) >= 16 and _printable(s[:20000]) >= 0.97:
            return [_out(np.fromiter((ord(ch) for ch in s), dtype=np.int64, count=len(s)),
                         s.encode("utf-8"), "symbols")]
    return []


class _Visible(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def markup_text(data):
    """Text with tags (<...>) taken out."""
    out = as_text(data)
    if not out:
        return []
    s = out[0]["raw"].decode("utf-8")
    if s.count("<") < 10 or s.count("<") > 0.2 * len(s):
        return []
    p = _Visible()
    try:
        p.feed(s)
    except Exception:
        return []
    text = re.sub(r"\n\s*\n+", "\n", "".join(p.parts)).strip()
    if len(text) < 16:
        return []
    return [_out(np.fromiter((ord(ch) for ch in text), dtype=np.int64, count=len(text)),
                 text.encode("utf-8"), "symbols")]


NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def numbers_in(data):
    """The numbers written in a text, one after the other."""
    out = as_text(data)
    if not out:
        return []
    s = "".join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in out[0]["raw"].decode("utf-8"))
    rows = [[float(m) for m in NUMBER.findall(line.replace(",", " ").replace(";", " "))] for line in s.splitlines()]
    rows = [r for r in rows if r]
    if rows:
        counts = {}
        for r in rows:
            counts[len(r)] = counts.get(len(r), 0) + 1
        k, freq = max(counts.items(), key=lambda kv: kv[1])
        if freq >= 24 and freq >= 0.8 * len(rows) and k <= 64:
            table = np.asarray([r for r in rows if len(r) == k], dtype=np.float64)
            return [_out(table.ravel(), None, "values", (table.shape[0], k))]
    nums = [float(m) for m in NUMBER.findall(s.replace(",", ""))]
    if len(nums) < 24:
        return []
    return [_out(np.asarray(nums, dtype=np.float64), None, "values")]


# -- undoing compression ----------------------------------------------------------------------------
def _bounded(dec, data):
    """Undo as much as can be undone, a piece at a time, and keep it."""
    out, total = [], 0
    try:
        for i in range(0, len(data), 16384):
            piece = dec.decompress(data[i:i + 16384], MAX_OUT - total)
            out.append(piece)
            total += len(piece)
            if total >= MAX_OUT or getattr(dec, "eof", False):
                break
    except Exception:
        pass
    b = b"".join(out)
    return b if len(b) >= 64 else None


def inflate(data):
    """Undo deflate compression."""
    for wbits in (15, -15, 31):
        out = _bounded(zlib.decompressobj(wbits), data[:MAX_OUT])
        if out and len(out) > 1.05 * min(len(data), MAX_OUT):
            return [_out(None, out, "values")]
    return []


def inflate_inside(data):
    """Compressed blocks hidden inside the bytes."""
    found, total = [], 0
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[:MAX_OUT]):
        if len(found) >= 64 or total >= MAX_OUT:
            break
        out = _bounded(zlib.decompressobj(15), data[m.start():m.start() + MAX_OUT])
        if out:
            found.append(out)
            total += len(out)
    if not found or (len(found) == 1 and len(found[0]) < 128):
        return []
    return [_out(None, b"".join(found)[:MAX_OUT], "values")]


def bunzip(data):
    out = _bounded(bz2.BZ2Decompressor(), data[:MAX_OUT])
    return [_out(None, out, "values")] if out else []


def unxz(data):
    out = _bounded(lzma.LZMADecompressor(), data[:MAX_OUT])
    return [_out(None, out, "values")] if out else []


def from_base64(data):
    s = data[:MAX_OUT].strip()
    if len(s) < 64 or not re.fullmatch(rb"[A-Za-z0-9+/=\r\n]+", s[:4096]):
        return []
    try:
        out = base64.b64decode(re.sub(rb"\s+", b"", s), validate=True)
    except (binascii.Error, ValueError):
        return []
    return [_out(None, out, "values")] if len(out) >= 48 else []


def unpack(data):
    """The members of a container."""
    outs, total = [], 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist()[:40]:
                if info.is_dir() or info.file_size > MAX_OUT or total >= 4 * MAX_OUT:
                    continue
                try:
                    with z.open(info) as f:
                        b = f.read(min(MAX_OUT, 4 * MAX_OUT - total))
                except Exception:
                    continue
                total += len(b)
                if len(b) >= 32:
                    outs.append(_out(None, b, "values"))
        return outs
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError, ValueError):
        pass
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            for m in t.getmembers()[:40]:
                if not m.isfile() or m.size > MAX_OUT or total >= 4 * MAX_OUT:
                    continue
                try:
                    f = t.extractfile(m)
                    b = f.read(min(MAX_OUT, 4 * MAX_OUT - total)) if f else b""
                except Exception:
                    continue
                total += len(b)
                if len(b) >= 32:
                    outs.append(_out(None, b, "values"))
    except (tarfile.TarError, OSError, EOFError, ValueError):
        return []
    return outs


# -- the decoders on this computer, which give raw numbers and nothing else ---------------------------
def _plain(img, mode):
    """The decoder's picture as plain values."""
    if img.mode == "PA" or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    return img.convert(mode)


def pixels(data):
    """Let the picture decoder turn the bytes into raw colour values, one after another, with no width."""
    if Image is None:
        return []
    try:
        img = Image.open(io.BytesIO(data))
        img.seek(0)
        if img.width * img.height > BIG_PICTURE:
            img.draft("RGB", (320, 320))
            if img.width * img.height > BIG_PICTURE:
                return []
        rgb = _plain(img, "RGB")
        if max(rgb.size) > 320:
            rgb.thumbnail((320, 320), Image.Resampling.BOX)
        raw = rgb.tobytes()
    except Exception:
        return []
    return [_out(np.frombuffer(raw, dtype=np.uint8).astype(np.int64), None, "values",
                 (rgb.size[1], rgb.size[0], 3))]


def moving(data):
    """Let a decoder of moving pictures turn the bytes into raw light values, frame after frame."""
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(data))
            n = getattr(img, "n_frames", 1)
        except Exception:
            n = 1
        if n > 1 and img.width * img.height > BIG_PICTURE / 16:
            n = 1
        if n > 1:
            out = []
            for i in range(min(n, 240)):
                img.seek(i)
                out.append(_plain(img, "L").resize((96, 72), Image.Resampling.BOX).tobytes())
            raw = b"".join(out)
            return [_out(np.frombuffer(raw, dtype=np.uint8).astype(np.int64), None, "values", (len(out), 72, 96))]
    if not FFMPEG:
        return []
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-i", "pipe:0", "-vf", "fps=8,scale=96:72",
           "-frames:v", "240", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    try:
        run = subprocess.run(cmd, input=data[:40_000_000], capture_output=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if len(run.stdout) < 96 * 72 * 4:
        return []
    n = min(len(run.stdout), MAX_OUT) // (96 * 72)
    return [_out(np.frombuffer(run.stdout[:n * 96 * 72], dtype=np.uint8).astype(np.int64), None, "values",
                 (n, 72, 96))]


def sound(data):
    """Let the sound decoder turn the bytes into raw samples, one after another, with no rate."""
    if not FFMPEG:
        return []
    cmd = [FFMPEG, "-v", "error", "-nostdin", "-i", "pipe:0", "-vn", "-ac", "1", "-ar", "8000",
           "-t", "30", "-f", "s16le", "pipe:1"]
    try:
        run = subprocess.run(cmd, input=data[:40_000_000], capture_output=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if len(run.stdout) < 16000:
        return []
    return [_out(np.frombuffer(run.stdout[:MAX_OUT], dtype="<i2").astype(np.int64), None, "values")]


TOOLS = [
    ("text", as_text, False),
    ("markup", markup_text, False),
    ("numbers", numbers_in, False),
    ("inflate", inflate, False),
    ("inflate-inside", inflate_inside, False),
    ("bunzip", bunzip, False),
    ("unxz", unxz, False),
    ("base64", from_base64, False),
    ("unpack", unpack, False),
    ("pixels", pixels, True),
    ("frames", moving, True),
    ("sound", sound, True),
]

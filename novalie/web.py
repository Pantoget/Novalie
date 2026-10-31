# Novalie. Copyright (c) 2026 Abdallah Alramahi <Abdallah1999alramahi@gmail.com>
"""Its one door to the web: public addresses only, robots.txt, a gap per site, pages and links."""

import email.utils
import functools
import html.parser
import http.client
import http.server
import ipaddress
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

from . import config
from .config import AGENT, room


ROBOTS, AGENT_NAME = {}, "NovalieResearch"
ROBOTS_LOCK = threading.Lock()
READ_ANY = threading.Lock()
PAGES = threading.Lock()


def public(host):
    """Only the public internet."""
    try:
        addrs = {info[4][0].split("%")[0] for info in socket.getaddrinfo(host, None)}
        ips = [ipaddress.ip_address(a) for a in addrs]
    except (OSError, UnicodeError, ValueError):
        return False
    return bool(ips) and (config.PRIVATE_NETWORK or all(ip.is_global and not ip.is_multicast for ip in ips))


def safe_url(url):
    """An address it may ask."""
    try:
        u = urllib.parse.urlsplit(url)
        port = u.port
    except ValueError:
        return False
    return (u.scheme in ("http", "https") and bool(u.hostname) and u.username is None and u.password is None
            and port in (None, 80, 443) and len(url) <= 2000 and public(u.hostname))


class _Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise urllib.error.URLError("a redirect to a place it does not read")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _public_connect(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, *rest, **kw):
    """Connect only to a public address, checking the address it really connects to."""
    host, port = address[0], address[1]
    err = None
    for family, kind, proto, _, addr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        ip = ipaddress.ip_address(addr[0].split("%")[0])
        if not (ip.is_global or config.PRIVATE_NETWORK) or ip.is_multicast:
            raise OSError(f"{host} is not a public address")
        sock = socket.socket(family, kind, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            sock.connect(addr)
            return sock
        except OSError as e:
            err = e
            sock.close()
    raise err or OSError(f"no address for {host}")


class _PublicHTTP(http.client.HTTPConnection):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._create_connection = _public_connect


class _PublicHTTPS(http.client.HTTPSConnection):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._create_connection = _public_connect


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTP, req)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        kw = {"context": self._context}
        if hasattr(self, "_check_hostname"):
            kw["check_hostname"] = self._check_hostname
        return self.do_open(_PublicHTTPS, req, **kw)


OPENER = (urllib.request.build_opener(_Redirect, _PublicHTTPHandler, _PublicHTTPSHandler)
          if not urllib.request.getproxies() else urllib.request.build_opener(_Redirect))


HOSTS, HOSTS_LOCK = {}, threading.Lock()
READ_GATE = threading.Event()
READ_GATE.set()
OFFLINE = threading.Event()


def retry_after(told):
    """Seconds a site's Retry-After asks for."""
    told = (told or "").strip()
    if told.isdecimal():
        return float(told)
    try:
        when = email.utils.parsedate_to_datetime(told)
        return max(0.0, when.timestamp() - time.time())
    except (TypeError, ValueError, IndexError):
        return None


def polite(host, status, headers=None, delay=0.0):
    """How long it waits before it asks this site again, from what the site answered."""
    with HOSTS_LOCK:
        h = HOSTS.setdefault(host, {"next": 0.0, "gap": config.GAP_FLOOR, "good": 0, "bad": 0})
        base = max(config.GAP_FLOOR, delay)
        if status in (429, 503):
            told = retry_after(headers.get("Retry-After") if headers is not None else None)
            h["gap"], h["good"] = min(900.0, max(base, told if told is not None else 2 * h["gap"])), 0
            NET["silent"] = 0
        elif status == 0 and NET["silent"] >= 2:
            NET["silent"] += 1
            NET["until"] = time.time() + min(300.0, config.GAP_FLOOR * 2 ** min(5, NET["silent"] - 3))
        elif status == 0 or status >= 500:
            h["gap"], h["good"], h["bad"] = min(900.0, max(base, 2 * h["gap"])), 0, h["bad"] + 1
            h["owed"] = h.get("owed", 0) + 1
            NET["silent"] = NET["silent"] + 1 if status == 0 else 0
        else:
            NET["silent"], NET["until"] = 0, 0.0
            if h.get("owed"):
                h["gap"], h["owed"] = h["gap"] / 2, h["owed"] - 1
            h["good"], h["bad"] = h["good"] + 1, 0
            if h["good"] >= 10:
                h["gap"], h["good"] = h["gap"] * 0.8, 0
        h["gap"] = max(base, h["gap"])
        h["next"] = time.time() + h["gap"]
        return h["gap"]


NET = {"silent": 0, "until": 0.0}


def turn(host):
    """Seconds until it may ask this site again."""
    with HOSTS_LOCK:
        return max(0.0, HOSTS.get(host, {}).get("next", 0.0) - time.time())


def fetch(url, limit=None, robots=True):
    """The one door to the web, for every request it makes."""
    if not safe_url(url):
        return None, 0, "", None
    if robots and NET["until"] > time.time():
        return None, -1, "", None
    host, delay = site_of(url), 0.0
    if robots and config.OBEY_ROBOTS:
        ok, delay = allowed(url)
        if not ok:
            return None, -1 if ok is None else 403, "", None
    with HOSTS_LOCK:
        h = HOSTS.setdefault(host, {"next": 0.0, "gap": config.GAP_FLOOR, "good": 0, "bad": 0})
        if robots and h["next"] > time.time():
            return None, -1, "", None
        if robots:
            h["next"] = time.time() + max(h["gap"], delay)
    try:
        with OPENER.open(urllib.request.Request(url, headers=AGENT, method="GET"), timeout=20) as r:
            raw = r.read(limit or config.PAGE_BYTES)
            if robots:
                polite(host, r.status, r.headers, delay)
            return r.geturl(), r.status, r.headers.get_content_type(), raw
    except urllib.error.HTTPError as e:
        if robots:
            polite(host, e.code, e.headers, delay)
        return None, e.code, "", None
    except Exception:
        if robots:
            polite(host, 0, None, delay)
        return None, 0, "", None


def allowed(url):
    """What a site asks of automatic readers."""
    u = urllib.parse.urlsplit(url)
    site = f"{u.scheme}://{u.netloc}"
    rp, at = ROBOTS.get(site, (None, 0.0))
    if rp is None or time.time() - at > 86_400:
        rp = urllib.robotparser.RobotFileParser()
        _, status, _, raw = fetch(site + "/robots.txt", 300_000, robots=False)
        if status in (0, 429) or status >= 500:
            return None, 0.0
        if status in (401, 403):
            rp.disallow_all = True
        elif raw is None:
            rp.allow_all = True
        else:
            rp.parse(raw.decode("utf-8", errors="replace").splitlines())
        with ROBOTS_LOCK:
            ROBOTS[site] = (rp, time.time())
            while len(ROBOTS) > room(2000):
                del ROBOTS[next(iter(ROBOTS))]
    rate = rp.request_rate(AGENT_NAME)
    delay = max(float(rp.crawl_delay(AGENT_NAME) or 0), rate.seconds / max(1, rate.requests) if rate else 0.0)
    return rp.can_fetch(AGENT_NAME, url), delay


def robots_say(url):
    """What a site's robots.txt, already asked, says of this page."""
    u = urllib.parse.urlsplit(url)
    rp, _ = ROBOTS.get(f"{u.scheme}://{u.netloc}", (None, 0.0))
    return None if rp is None else rp.can_fetch(AGENT_NAME, url)


URL_IN = re.compile(r"https?://[^\s<>\"'()\[\]{}]+")
HOST_IN = re.compile(r"(?<![\w@./-])((?:[^\W_](?:[\w-]{0,61}[^\W_])?\.)+[^\W\d_]{2,63})(?![\w@/-])")
SLOT = "\x00"


def links_in(text, hosts=False):
    """The addresses written in a text."""
    found = [u.rstrip(".,;:!?") for u in URL_IN.findall(text or "")]
    if hosts:
        rest = URL_IN.sub(" ", text or "")
        found += [f"https://{h.lower()}/" for h in HOST_IN.findall(rest)]
    return list(dict.fromkeys(found))


class _Page(html.parser.HTMLParser):
    """The readable text of a page, its title, the addresses it links to."""
    SKIP = {"script", "style", "noscript", "svg", "nav", "header", "footer", "form", "aside", "button",
            "select", "template", "iframe", "canvas"}
    BLOCK = {"p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section",
             "article", "blockquote", "dd", "dt", "pre", "table", "ul", "ol", "main"}

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.skip, self.in_title, self.title, self.parts, self.links = base, 0, False, "", [], []
        self.texts, self.images, self.alts, self.forms, self.form, self.anchor = [], [], [], [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.form = {"action": urllib.parse.urljoin(self.base, (a.get("action") or "").strip() or self.base),
                         "method": (a.get("method") or "get").strip().lower(), "fields": [], "hidden": {}, "other": False}
        elif self.form is not None and tag in ("input", "textarea"):
            kind, name = (a.get("type") or ("text" if tag == "input" else "textarea")).strip().lower(), a.get("name")
            if kind == "hidden" and name:
                self.form["hidden"][name] = a.get("value") or ""
            elif kind in ("text", "search", "textarea") and name:
                self.form["fields"].append(name)
            elif kind in ("password", "file", "email", "tel"):
                self.form["other"] = True
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "a" and not self.skip:
            href = (a.get("href") or "").strip()
            if href and not href.startswith(("#", "mailto:", "javascript:", "tel:")):
                self.links.append(urllib.parse.urljoin(self.base, href).split("#")[0])
                self.texts.append("")
                self.anchor = len(self.links) - 1
        elif tag == "img" and not self.skip:
            src = (a.get("src") or "").strip()
            try:
                small = min(int(a.get("width") or 999), int(a.get("height") or 999)) < 64
            except ValueError:
                small = False
            if src and not src.startswith("data:") and not small:
                self.images.append(urllib.parse.urljoin(self.base, src).split("#")[0])
                self.alts.append(" ".join((a.get("alt") or "").split()))
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "form" and self.form is not None:
            f, self.form = self.form, None
            if f["method"] == "get" and len(f["fields"]) == 1 and not f["other"]:
                self.forms.append({"action": f["action"].split("#")[0].split("?")[0], "field": f["fields"][0],
                                   "hidden": f["hidden"]})
        elif tag == "a":
            self.anchor = None
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "title":
            self.in_title = False
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.anchor is not None:
            self.texts[self.anchor] += data
        if self.in_title:
            self.title += data
        elif not self.skip:
            self.parts.append(data)


def fetch_page(url):
    """One page of the open web through its one door."""
    final, status, kind, raw = fetch(url)
    if status == 403 and raw is None:
        return False, None
    if raw is None:
        return None, None
    return True, web_page(final, kind, raw)


def web_page(final, kind, raw):
    """What an address held, as a dict."""
    if kind not in ("text/html", "application/xhtml+xml"):
        return {"final": final, "title": "", "text": "", "links": [], "texts": [], "images": [], "alts": [],
                "forms": [], "bytes": raw}
    page = _Page(final)
    try:
        page.feed(raw.decode("utf-8", errors="replace"))
        page.close()
    except Exception:
        return None
    lines = (" ".join(line.split()) for line in "".join(page.parts).split("\n"))
    text = "\n".join(line for line in lines if len(line.split()) >= 6)[:30000]
    seen, links, texts = set(), [], []
    for u, t in zip(page.links, page.texts):
        if u not in seen:
            seen.add(u)
            links.append(u)
            texts.append(" ".join(t.split())[:120])
    return {"final": final, "title": " ".join(page.title.split())[:120], "text": text, "links": links,
            "texts": texts, "images": page.images, "alts": page.alts, "forms": page.forms, "bytes": None}


def link_end(url):
    """How a link ends: the last letters of its path after a dot."""
    try:
        ext = os.path.splitext(urllib.parse.urlsplit(url).path)[1].lower()
    except ValueError:
        return "/"
    return ext if 1 < len(ext) <= 6 and ext[1:].isalnum() else "/"


@functools.lru_cache(maxsize=65_536)
def site_of(url):
    try:
        return urllib.parse.urlsplit(url).hostname or ""
    except ValueError:
        return ""


def palette(T):
    """Its colours around a cycle as small numbers for the page."""
    seen = {}
    return [-1 if x is None else seen.setdefault(x, len(seen)) for x in T]

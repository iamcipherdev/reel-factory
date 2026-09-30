#!/usr/bin/env python3
"""AI Reel Factory — fetch article text from a URL.

Tries trafilatura first; falls back to urllib + basic HTML stripping.
"""
import re
import urllib.request
from html import unescape


def _fallback_extract(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; ReelFactory/1.0)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        html = r.read().decode("utf-8", errors="replace")
    html = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    paras = [p.strip() for p in text.split("\n") if len(p.strip().split()) > 8]
    return "\n\n".join(paras[:40])


def fetch_article(url):
    """Returns (title, text). Raises on failure."""
    try:
        import trafilatura
        dl = trafilatura.fetch_url(url)
        if dl:
            text = trafilatura.extract(
                dl, include_comments=False, include_tables=False)
            if text and len(text.split()) > 60:
                m = re.search(r"<title[^>]*>(.*?)</title>", dl,
                              re.I | re.S)
                title = unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
                    if m else url
                return title, text
    except Exception:
        pass
    # fallback
    text = _fallback_extract(url)
    if len(text.split()) < 60:
        raise RuntimeError("Could not extract enough article text "
                           "(paywall or fetch failed?). "
                           "Use --text to paste content directly.")
    return url, text

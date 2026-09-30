#!/usr/bin/env python3
"""AI Reel Factory — script format parser + naive auto-derivation.

Script file format:

    [// 01 — hook]
    badge: AGENT-GONE-ROGUE
    emoji: 😱
    stamp: OOPS.
    headline:
    An AI agent
    just deleted | y
    48,000 files. | y
    body: A Claude Code agent wiped 48,000 files — then apologized.
    visual: counter
    counter_value: 48000
    counter_label: files deleted

    [// 02 — what happened]
    ...

Fields (all optional except body):
  badge:        capsule badge text (default: section number)
  emoji:        emoji next to badge, and after last headline line
  stamp:        red stamp pill text (usually section 1 only)
  cta:          CTA pill text (usually last section, e.g. @createbycipher)
  headline:     block of headline lines; each may end with ` | y` or ` | p`
                for a yellow/pink marker, optionally followed by an emoji
  body:         narration text (one line) — also the TTS input
  visual:       counter | quote | chips | none  (auto-chosen if omitted)
  counter_value / counter_label: for visual: counter
  chips:        comma-separated chips for visual: chips

If `headline:` is missing, headlines are derived naively from the body:
first sentence split into short lines, numbers/ALL-CAPS lines highlighted.
"""
import re


class Section:
    def __init__(self, label):
        self.label = label            # e.g. "// 01 — hook"
        self.badge = ""
        self.emoji = None
        self.stamp = None
        self.cta = None
        self.headline = []            # list of (text, marker|None, emoji|None)
        self.body = ""
        self.visual = None            # counter | quote | chips | none
        self.counter_value = 0
        self.counter_label = ""
        self.chips = []

    def __repr__(self):
        return f"<Section {self.label!r} body={self.body[:40]!r}>"


_MARKERS = {"y": (255, 205, 40), "p": (235, 90, 120)}

_KNOWN_FIELDS = {"badge", "emoji", "stamp", "cta", "body", "visual",
                 "counter_value", "counter_label", "chips"}


def _parse_headline_line(line):
    text, mk, em = line.strip(), None, None
    if " | " in text:
        text, suffix = text.rsplit(" | ", 1)
        parts = suffix.strip().split(None, 1)
        if parts and parts[0] in _MARKERS:
            mk = _MARKERS[parts[0]]
            if len(parts) > 1:
                em = parts[1].strip()
    return text.strip(), mk, em


def parse_script(text):
    sections = []
    cur = None
    in_headline = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("[") and line.rstrip().endswith("]"):
            cur = Section(line.strip()[1:-1].strip())
            sections.append(cur)
            in_headline = False
            continue
        if cur is None:
            continue
        m = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if m and m.group(1) in _KNOWN_FIELDS and m.group(1) != "headline":
            in_headline = False
            key, val = m.group(1), m.group(2)
            if key == "badge":
                cur.badge = val
            elif key == "emoji":
                cur.emoji = val or None
            elif key == "stamp":
                cur.stamp = val or None
            elif key == "cta":
                cur.cta = val or None
            elif key == "body":
                cur.body = val
            elif key == "visual":
                cur.visual = val if val in ("counter", "quote", "chips", "none") else None
            elif key == "counter_value":
                cur.counter_value = int(re.sub(r"[^\d]", "", val) or 0)
            elif key == "counter_label":
                cur.counter_label = val
            elif key == "chips":
                cur.chips = [c.strip() for c in val.split(",") if c.strip()]
            continue
        if line.strip() == "headline:":
            in_headline = True
            continue
        if in_headline:
            cur.headline.append(_parse_headline_line(line))
    for s in sections:
        _finalize(s)
    return [s for s in sections if s.body]


def _strong_sentence(body):
    sents = re.split(r"(?<=[.!?])\s+", body.strip())
    sents = [s for s in sents if len(s.split()) > 3]
    return sents[0] if sents else body.strip()


def _derive_headline(body):
    sent = _strong_sentence(body)
    words = sent.split()
    lines, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))
    out = []
    for ln in lines[:4]:
        mk = None
        if re.search(r"\d", ln):
            mk = _MARKERS["y"]
        elif any(w.isupper() and len(w) > 2 and w.isalpha() for w in ln.split()):
            mk = _MARKERS["y"]
        out.append((ln, mk, None))
    return out


def _derive_visual(sec):
    if sec.visual:
        return
    m = re.search(r"(\d[\d,]*)", sec.body)
    if m and len(re.sub(r"\D", "", m.group(1))) >= 3:
        sec.visual = "counter"
        sec.counter_value = int(re.sub(r"\D", "", m.group(1)))
        # naive label: words right after the number, up to 3
        after = sec.body[m.end():].strip()
        words = re.findall(r"[A-Za-z]+", after)[:3]
        sec.counter_label = " ".join(words) or "counted"
    elif sec.chips:
        sec.visual = "chips"
    else:
        sec.visual = "quote"


def _finalize(sec):
    if not sec.badge:
        sec.badge = sec.label.split("—")[-1].strip().upper() or "REEL"
    if not sec.headline and sec.body:
        sec.headline = _derive_headline(sec.body)
    # attach section emoji to last headline line if none has one
    if sec.emoji and sec.headline and not any(h[2] for h in sec.headline):
        last = sec.headline[-1]
        sec.headline[-1] = (last[0], last[1], sec.emoji)
    _derive_visual(sec)

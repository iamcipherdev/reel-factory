#!/usr/bin/env python3
"""AI Reel Factory — generic section renderer.

Every section: badge row + optional visual module (counter/quote/chips) +
pop-in headline + optional stamp (first) / CTA pill (last).
"""
import os
from PIL import Image, ImageDraw
import style as S


def _quote_text(sec, limit=110):
    import re
    sents = re.split(r"(?<=[.!?])\s+", sec.body.strip())
    sents = [s for s in sents if len(s.split()) > 3]
    q = sents[0] if sents else sec.body.strip()
    return q if len(q) <= limit else q[:limit].rsplit(" ", 1)[0] + "…"


def draw_section(d, base, t, sec, is_first=False, is_last=False):
    S.badge(d, base, t, sec.label, sec.badge, sec.emoji)

    has_visual = sec.visual in ("counter", "quote", "chips")
    if sec.visual == "counter":
        S.stat_card(d, base, t, 0.4, sec.counter_value,
                    sec.counter_label or "counted", sec.emoji)
    elif sec.visual == "quote":
        S.quote_card(d, base, t, 0.4, _quote_text(sec))
    elif sec.visual == "chips" and sec.chips:
        S.chip_row(d, base, t, 0.4, sec.chips[:4])

    n = max(1, len(sec.headline))
    if has_visual:
        y_start, size, gap = 980, 108, 150
        S.warm_wash(base, 900, 1560)
    elif is_first or is_last:
        y_start, size, gap = 640, 122, 154
        S.warm_wash(base, 560, 1180)
    else:
        # no visual: vertically center the headline block
        gap = 152
        y_start = 960 - (n * gap) // 2
        size = 118
        S.warm_wash(base, y_start - 90, y_start + n * gap + 90)

    S.pop_headline(d, base, t, sec.headline, y_start,
                   t0=0.35, start_size=size, line_gap=gap)

    if is_first and sec.stamp and len(sec.headline) <= 3:
        S.stamp_pill(base, t, 1.7, S.W // 2, 1620, sec.stamp)
    if is_last and sec.cta:
        S.cta_pill(d, base, t, 1.7, sec.cta)


def render_section_frames(sec, idx, dur, out_dir, fps=S.FPS):
    os.makedirs(out_dir, exist_ok=True)
    n = int(dur * fps)
    is_first = idx == 0
    # is_last resolved by caller via total count; pass through attribute
    is_last = getattr(sec, "_is_last", False)
    for i in range(n):
        t = i / fps
        img = S.BG.copy()
        base = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        base.paste(img, (0, 0))
        draw_section(ImageDraw.Draw(base), base, t, sec,
                     is_first=is_first, is_last=is_last)
        base.convert("RGB").save(os.path.join(out_dir, f"f{i:04d}.png"))
    return n

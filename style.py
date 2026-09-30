#!/usr/bin/env python3
"""AI Reel Factory — shared visual system.

Cream dotted-grain background, mono `// NN — label` top-left, huge bold
headlines lower-left with yellow marker highlights, capsule badges, soft
shadows, warm gradient wash, emoji accents, bouncy pop-ins. No avatar.
Adapted from the tech-daily v2 motion-graphics pipeline.
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FPS = 30

CREAM = (252, 250, 244)
INK = (28, 28, 30)
MUTED = (150, 145, 132)
YELLOW = (255, 205, 40)
PINK = (235, 90, 120)
GREEN = (60, 170, 95)
RED = (220, 60, 60)
DARK = (24, 24, 26)
BLUE = (70, 140, 220)

FD = "/usr/share/fonts/truetype/dejavu/"
F_HEAD = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 104)
F_HEAD_S = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 88)
F_MONO = ImageFont.truetype(FD + "DejaVuSansMono.ttf", 34)
F_BADGE = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 34)
F_TERM = ImageFont.truetype(FD + "DejaVuSansMono.ttf", 30)
F_CAP = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 30)
F_CTA = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 44)
F_CARD = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 40)
F_STAT = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 120)

EMOJI_FONT = ImageFont.truetype(
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out_back(x):
    x = clamp01(x)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1 + c3 * math.pow(x - 1, 3) + c1 * math.pow(x - 1, 2)


def slide(t, t0, dur, dist=160.0):
    x = clamp01((t - t0) / dur)
    if x <= 0:
        return dist
    e = 1 + 2.2 * math.pow(x - 1, 3) + 1.2 * math.pow(x - 1, 2)
    return dist * (1 - e)


def make_bg():
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 16):
        for x in range(0, W, 16):
            d.ellipse([x, y, x + 2, y + 2], fill=(238, 234, 224))
    return img


BG = make_bg()

_emoji_cache = {}


def emoji_img(ch, size=84):
    key = (ch, size)
    if key not in _emoji_cache:
        img = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((20, 8), ch, font=EMOJI_FONT,
                                 embedded_color=True)
        bb = img.getbbox()
        img = img.crop(bb)
        s = size / max(img.width, img.height)
        img = img.resize((max(1, int(img.width * s)),
                          max(1, int(img.height * s))), Image.LANCZOS)
        _emoji_cache[key] = img
    return _emoji_cache[key]


_font_cache = {}


def fit_font(txt, start, max_w):
    key = (txt, start, max_w)
    if key not in _font_cache:
        size = start
        dd = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        while size > 40:
            f = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", size)
            if dd.textlength(txt, font=f) <= max_w:
                break
            size -= 6
        _font_cache[key] = ImageFont.truetype(
            FD + "DejaVuSans-Bold.ttf", size)
    return _font_cache[key]


def marker(d, x, y, w, h, color=YELLOW, rough=6):
    rnd = random.Random(int(x + y))
    pts = [(x + rnd.uniform(-rough, rough), y + rnd.uniform(-rough, rough)),
           (x + w + rnd.uniform(-rough, rough), y + rnd.uniform(-rough, rough)),
           (x + w + rnd.uniform(-rough, rough), y + h + rnd.uniform(-rough, rough)),
           (x + rnd.uniform(-rough, rough), y + h + rnd.uniform(-rough, rough))]
    d.polygon(pts, fill=color)
    d.rounded_rectangle([x + 4, y + 3, x + w - 4, y + h - 3],
                        radius=h // 2, fill=color)


_shadow_cache = {}


def _shadow_tile(w, h, radius=36, blur=22, alpha=55):
    key = (w, h, radius, blur, alpha)
    if key not in _shadow_cache:
        pad = blur * 3
        img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle(
            [pad, pad, pad + w, pad + h], radius=radius,
            fill=(45, 38, 28, alpha))
        _shadow_cache[key] = (img.filter(ImageFilter.GaussianBlur(blur)), pad)
    return _shadow_cache[key]


def shadow_card(base, x0, y0, x1, y1, radius=36, blur=22, alpha=55, dy=12):
    tile, pad = _shadow_tile(int(x1 - x0), int(y1 - y0), radius, blur, alpha)
    base.alpha_composite(tile, (int(x0) - pad, int(y0) + dy - pad))


_wash_cache = {}


def warm_wash(base, y0, y1, alpha=60):
    h = y1 - y0
    key = (h, alpha)
    if key not in _wash_cache:
        wash = Image.new("RGBA", (W, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(wash)
        for i in range(h):
            f = i / max(1, h - 1)
            a = int(alpha * math.sin(math.pi * min(1.0, f * 1.12)))
            dd.line([(0, i), (W, i)], fill=(255, 213, 150, max(0, a)))
        _wash_cache[key] = wash
    base.alpha_composite(_wash_cache[key], (0, y0))


def badge(d, base, t, section_label, badge_text, emoji=None, t0=0.0):
    y0 = 90 + slide(t, t0, 0.4)
    d.text((70, y0), section_label, font=F_MONO, fill=MUTED)
    tw = d.textlength(badge_text, font=F_BADGE)
    ew = 54 if emoji else 0
    bw = tw + 44 + ew
    bx1 = W - 70 - bw
    by = 74 + slide(t, t0, 0.4)
    shadow_card(base, bx1, by, bx1 + bw, by + 62, radius=31, blur=14,
                alpha=45, dy=8)
    d.rounded_rectangle([bx1, by, bx1 + bw, by + 62], radius=31,
                        fill=(255, 255, 255), outline=INK, width=2)
    d.text((bx1 + 22, by + 10), badge_text, font=F_BADGE, fill=INK)
    if emoji:
        base.alpha_composite(emoji_img(emoji, 40),
                             (int(bx1 + 22 + tw + 8), int(by + 11)))


def _text_layer(txt, font, marker_color):
    dd = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = dd.textlength(txt, font=font)
    asc, desc = font.getmetrics()
    th = asc + desc
    pad = 34
    layer = Image.new("RGBA", (int(tw) + pad * 2, th + pad * 2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(layer)
    if marker_color:
        marker(dd, pad - 16, pad - 10, tw + 32, th + 20, color=marker_color)
    dd.text((pad, pad), txt, font=font, fill=INK)
    return layer


def pop_headline(d, base, t, lines, y_start, t0=0.35, step=0.24,
                 start_size=120, max_w=940, line_gap=158, x=70):
    """lines: list of (text, marker_color|None, emoji|None)."""
    y = y_start
    for j, item in enumerate(lines):
        txt, mk = item[0], item[1]
        em = item[2] if len(item) > 2 else None
        lt = t0 + j * step
        if t >= lt:
            sc = ease_out_back((t - lt) / 0.5)
            font = fit_font(txt, start_size, max_w)
            layer = _text_layer(txt, font, mk)
            w2, h2 = int(layer.width * sc), int(layer.height * sc)
            if w2 > 2 and h2 > 2:
                rl = layer.resize((w2, h2), Image.LANCZOS)
                base.alpha_composite(
                    rl, (int(x - 34 * sc), int(y + layer.height / 2 - h2 / 2)))
            if em and (t - lt) / 0.5 >= 1.0:
                tw = d.textlength(txt, font=font)
                base.alpha_composite(emoji_img(em, 88),
                                     (int(x + tw + 16), int(y + 22)))
        y += line_gap


def stamp_pill(base, t, t0, cx, cy, text, size=40, color=RED, angle=-8):
    if t < t0:
        return
    sc = ease_out_back((t - t0) / 0.5)
    f = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", size)
    dd = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw = dd.textlength(text, font=f)
    layer = Image.new("RGBA", (int(tw) + 110, 112), (0, 0, 0, 0))
    dd = ImageDraw.Draw(layer)
    dd.rounded_rectangle([0, 0, layer.width - 1, 111], radius=56, fill=color)
    dd.text((55, 28), text, font=f, fill=(255, 255, 255))
    layer = layer.resize((max(2, int(layer.width * sc)),
                          max(2, int(layer.height * sc))), Image.LANCZOS)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(layer,
                         (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def cta_pill(d, base, t, t0, text):
    sc = ease_out_back((t - t0) / 0.5) if t >= t0 else 0
    if sc <= 0.01:
        return
    ctw = d.textlength(text, font=F_CTA)
    cw2, ch2 = int((ctw + 100) * sc), int(120 * sc)
    cx2, cy2 = W // 2 - cw2 // 2, 1450
    shadow_card(base, cx2, cy2, cx2 + cw2, cy2 + ch2, radius=60, blur=24,
                alpha=70, dy=14)
    cd = Image.new("RGBA", (cw2, ch2), (0, 0, 0, 0))
    ImageDraw.Draw(cd).rounded_rectangle([0, 0, cw2 - 1, ch2 - 1], radius=60,
                                         fill=INK)
    base.alpha_composite(cd, (cx2, cy2))
    d.text((W // 2 - ctw / 2, cy2 + 30), text, font=F_CTA, fill=(255, 255, 255))


def stat_card(d, base, t, t0, value, label, emoji=None):
    """Animated counting number card. value: int."""
    sc = ease_out_back((t - t0) / 0.5) if t >= t0 else 0
    if sc <= 0.01:
        return
    cw2, ch2 = int(940 * sc), int(380 * sc)
    cx, cy = W // 2, 520
    x0, y0 = int(cx - cw2 / 2), int(cy - ch2 / 2)
    shadow_card(base, x0, y0, x0 + cw2, y0 + ch2, radius=40, blur=24,
                alpha=60, dy=14)
    d.rounded_rectangle([x0, y0, x0 + cw2, y0 + ch2], radius=40,
                        fill=(255, 255, 255), outline=INK, width=2)
    xr = clamp01((t - t0 - 0.3) / 2.2)
    n = value * ease_out_back(xr) if xr < 1 else value
    txt = f"{max(0, int(n)):,}"
    tw = d.textlength(txt, font=F_STAT)
    d.text((cx - tw / 2, cy - 90), txt, font=F_STAT, fill=INK)
    lw = d.textlength(label, font=F_BADGE)
    d.text((cx - lw / 2, cy + 70), label, font=F_BADGE, fill=MUTED)
    if emoji:
        base.alpha_composite(emoji_img(emoji, 72), (int(cx + tw / 2 + 24),
                                                   int(cy - 120)))


def _wrap_lines(dd, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if dd.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def quote_card(d, base, t, t0, text, max_w=780):
    sc = ease_out_back((t - t0) / 0.5) if t >= t0 else 0
    if sc <= 0.01:
        return
    dd = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    size = 44
    lines = []
    while size > 26:
        font = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", size)
        lines = _wrap_lines(dd, "\u201c" + text + "\u201d", font, max_w)
        if len(lines) <= 4:
            break
        size -= 4
    font = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", size)
    asc, desc = font.getmetrics()
    line_h = asc + desc + 14
    widest = max(dd.textlength(ln, font=font) for ln in lines)
    cw2, ch2 = int((widest + 120) * sc), int((len(lines) * line_h + 90) * sc)
    cx, cy = W // 2, 520
    x0, y0 = int(cx - cw2 / 2), int(cy - ch2 / 2)
    shadow_card(base, x0, y0, x0 + cw2, y0 + ch2, radius=36, blur=22,
                alpha=55, dy=12)
    d.rounded_rectangle([x0, y0, x0 + cw2, y0 + ch2], radius=36,
                        fill=(255, 255, 255), outline=INK, width=2)
    ty = cy - (len(lines) * line_h) / 2 + 7
    for ln in lines:
        lw = dd.textlength(ln, font=font)
        d.text((W // 2 - lw / 2, ty), ln, font=font, fill=INK)
        ty += line_h


def chip_row(d, base, t, t0, chips):
    widths = [d.textlength(c, font=F_BADGE) + 100 for c in chips]
    total = sum(widths) + 30 * (len(chips) - 1)
    x = W // 2 - total / 2
    y = 440
    for j, (cn, w2) in enumerate(zip(chips, widths)):
        lt = t0 + j * 0.25
        if t >= lt:
            sc = ease_out_back((t - lt) / 0.4)
            if sc > 0.01:
                cw2, ch2 = int(w2 * sc), int(84 * sc)
                shadow_card(base, x, y, x + cw2, y + ch2, radius=42, blur=16,
                            alpha=50, dy=8)
                d.rounded_rectangle([x, y, x + cw2, y + ch2], radius=42,
                                    fill=(255, 255, 255), outline=INK, width=2)
                d.text((x + 50 * sc, y + 20 * sc), cn, font=F_BADGE, fill=INK)
        x += w2 + 30

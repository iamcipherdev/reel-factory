#!/usr/bin/env python3
"""AI Reel Factory — script generation via Google Gemini (free tier).

Requires GEMINI_API_KEY env var (get one free at https://aistudio.google.com).
"""
import os

MODEL = "gemini-2.0-flash"

PROMPT = """You write punchy tech-news explainer scripts for 9:16 Instagram reels.
Write ORIGINAL copy — do not copy sentences from the article below. Keep it
factual and grounded in the article; never invent numbers, quotes, or events.

Target: 140-160 words total, split into exactly 6 sections.
Section 1 is the hook (shocking, curiosity gap). Section 6 ends with a
follow CTA naming {cta}.

Use EXACTLY this format (no extra commentary):

[// 01 — hook]
badge: SHORT-BADGE
emoji: one emoji
stamp: 2-3 WORD STAMP
headline:
Line one
Line two | y
Line three | y
body: The full narration for this section, 20-30 words, spoken aloud.
visual: counter
counter_value: 48000
counter_label: files deleted

Rules for the other sections:
- badge: 1-3 word ALL-CAPS badge.
- emoji: one relevant emoji (also used beside the badge).
- headline: 2-4 SHORT lines (max ~5 words each). Append ` | y` to lines with
  the key number or punchline (yellow marker), ` | p` for a pink marker.
  Rarely: never more than 2 marked lines per section.
- body: 20-30 words of narration, conversational, no hashtags.
- visual: pick ONE per section, varied across sections:
    counter (needs counter_value as a plain integer and counter_label),
    quote (pulls the first sentence automatically — just set visual: quote),
    chips (needs chips: item one, item two, item three),
    none (headline-only section, good for the CTA).
- Section 6 must include: cta: {cta}
- Total across all 6 sections: 140-160 words of body text.

ARTICLE:
\"\"\"{article}\"\"\"
"""


def generate(article_text, cta="@createbycipher"):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set.\n"
            "Get a free key at https://aistudio.google.com (Google AI Studio),\n"
            "then run:  export GEMINI_API_KEY='your-key'\n"
            "Or skip auto-scripting with --script-file <file>.")
    from google import genai
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(article=article_text[:12000], cta=cta))
    text = resp.text.strip()
    if "[// 01" not in text:
        raise RuntimeError("Gemini did not return a valid script. Raw output:\n"
                           + text[:500])
    return text

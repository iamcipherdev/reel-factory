# 🎬 AI Reel Factory

Turn a URL or topic into a finished **motion-graphics reel** (1080×1920 MP4)
— the same cream-background, bold-headline, yellow-marker style as the
tech-daily videos. 100% free stack, no paid APIs.

## How it works

```
URL / topic / text
      → ① fetch article text (trafilatura)
      → ② write a 6-section reel script (Gemini, or --script-file)
      → ③ voiceover per section (edge-tts, gTTS fallback)
      → ④ render motion graphics (Pillow, 30fps)
      → ⑤ assemble with ffmpeg → output/reel-<slug>.mp4
```

## Install

```bash
cd ~/workspace/reel-factory
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

System deps: `ffmpeg`, `ffprobe` (already on most machines; `sudo apt install ffmpeg`).

## Usage

```bash
# From an article URL (script written by Gemini — needs API key)
./venv/bin/python factory.py --url https://example.com/some-ai-story

# From a topic (needs API key)
./venv/bin/python factory.py --topic "Claude Code deleted 48,000 files"

# From pasted text
./venv/bin/python factory.py --text "Paste the article text here..."

# Skip AI scripting — bring your own script file
./venv/bin/python factory.py --url <url> --script-file my-script.txt

# Options
--cta @yourhandle      # CTA pill on the last section (default: @createbycipher)
--tts edge|gtts|auto   # voice provider (default: auto → edge, fallback gtts)
--voice en-US-GuyNeural
--out my-slug          # output filename slug
--reuse-audio          # skip TTS on re-renders
--keep-frames          # keep PNG frames for debugging
```

Output: `output/reel-<slug>.mp4` (1080×1920, H264+AAC, Instagram-ready).

## Getting a free Gemini key

1. Go to **https://aistudio.google.com** (Google AI Studio)
2. Sign in → **Get API key** → create one (free tier)
3. `export GEMINI_API_KEY='your-key-here'`

Without the key, `--url`/`--topic`/`--text` auto-scripting exits with a clear
message; `--script-file` always works (that's how the test reel was made).

## Script file format

```ini
[// 01 — hook]
badge: AGENT-GONE-ROGUE
emoji: 😱
stamp: OOPS.
headline:
An AI agent
just deleted | y
48,000 files. | y
body: An AI coding agent was given file access and wiped out forty-eight thousand files.
visual: counter
counter_value: 48000
counter_label: files deleted

[// 02 — what happened]
...
```

- `headline:` lines support ` | y` / ` | p` suffixes for yellow/pink markers.
- `visual:` one of `counter` (needs `counter_value` + `counter_label`),
  `quote`, `chips` (needs `chips: a, b, c`), `none`.
- Omit `headline:` and it's derived naively from `body`
  (first sentence → short lines, numbers/ALL-CAPS highlighted).
- Omit `visual:` and it's guessed (big number → counter, else quote).
- Last section auto-gets the `--cta` pill if it has no `cta:` of its own.

## Project structure

```
reel-factory/
├── factory.py        # CLI orchestrator (fetch → script → TTS → render → assemble)
├── scriptgen.py      # Gemini script generation (google-genai SDK)
├── scriptparse.py    # script format parser + naive headline/visual derivation
├── fetch.py          # article extraction (trafilatura, urllib fallback)
├── tts.py            # edge-tts with automatic gTTS fallback
├── render.py         # generic section renderer
├── style.py          # visual system: palette, badges, markers, cards, emoji
├── requirements.txt
├── test-script-48k.txt   # example script (the test reel)
└── output/           # finished reels
```

## Limitations (honest)

- **Render time:** ~2–5 min per reel on CPU (~2000 frames at 1080×1920).
- **TTS needs internet.** edge-tts (best quality, natural voices) needs a
  WebSocket to Microsoft's servers; where that's blocked it auto-falls-back
  to gTTS (works everywhere, more robotic). Force with `--tts`.
- **Gemini free tier** has rate limits; big articles are truncated to ~12k chars.
- **Auto-derived visuals are naive** (regexes, first-sentence quotes) —
  hand-written `headline:`/`visual:` blocks look better.
- **No fact-checking:** the script generator is told to stay grounded in the
  article, but always skim the script before publishing.
- Tested on Linux with Python 3.12, ffmpeg 8, DejaVu + NotoColorEmoji fonts.

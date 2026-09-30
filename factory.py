#!/usr/bin/env python3
"""AI Reel Factory — URL/topic → motion-graphics reel (1080x1920 MP4).

Usage:
    python factory.py --url https://example.com/article
    python factory.py --topic "Claude Code deleted 48,000 files"
    python factory.py --text "pasted article text..."
    python factory.py --url ... --script-file script.txt   # skip AI scripting

Options:
    --cta @handle        CTA pill on last section (default: @createbycipher)
    --voice NAME         edge-tts voice (default: en-US-GuyNeural)
    --out NAME           output filename slug (default: auto)
    --keep-frames        don't delete PNG frames after render
"""
import argparse
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import scriptparse
import render
import tts as T
import fetch as F
import scriptgen

FPS = 30
TAIL = 0.7  # extra seconds after narration per section


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:40] or "reel"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def main():
    ap = argparse.ArgumentParser(description="AI Reel Factory")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Article URL to turn into a reel")
    src.add_argument("--topic", help="Topic to write a reel about (needs GEMINI_API_KEY)")
    src.add_argument("--text", help="Raw article text pasted directly")
    ap.add_argument("--script-file", help="Skip AI scripting; use this script file")
    ap.add_argument("--cta", default="@createbycipher")
    ap.add_argument("--voice", default="en-US-GuyNeural")
    ap.add_argument("--tts", default="auto", choices=["auto", "edge", "gtts"],
                    help="TTS provider (auto falls back to gtts if edge fails)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--reuse-audio", action="store_true",
                    help="reuse existing MP3s in work/<slug>/audio/")
    args = ap.parse_args()

    T.VOICE = args.voice

    # ---- 1. source text ----
    article = ""
    if args.url:
        print(f"[1/5] Fetching {args.url} ...", flush=True)
        try:
            title, article = F.fetch_article(args.url)
            print(f"      title: {title[:80]}", flush=True)
        except Exception as e:
            sys.exit(f"ERROR: fetch failed: {e}")
    elif args.text:
        article = args.text
    elif args.topic:
        article = f"Topic (use your own knowledge, stay factual): {args.topic}"

    # ---- 2. script ----
    if args.script_file:
        print("[2/5] Reading script file ...", flush=True)
        with open(args.script_file) as f:
            script_text = f.read()
    else:
        print("[2/5] Generating script with Gemini ...", flush=True)
        try:
            script_text = scriptgen.generate(article, cta=args.cta)
        except RuntimeError as e:
            sys.exit(f"ERROR: {e}")
        except Exception as e:
            sys.exit(f"ERROR: Gemini call failed: {e}")
    sections = scriptparse.parse_script(script_text)
    if not sections:
        sys.exit("ERROR: no sections parsed from script.")
    for i, s in enumerate(sections):
        s._is_last = (i == len(sections) - 1)
        if i == len(sections) - 1 and not s.cta:
            s.cta = args.cta
    words = sum(len(s.body.split()) for s in sections)
    print(f"      {len(sections)} sections, ~{words} words", flush=True)

    slug = args.out or slugify(args.topic or sections[0].body[:50])
    work = os.path.join(BASE, "work", slug)
    adir = os.path.join(work, "audio")
    fdir = os.path.join(work, "frames")
    os.makedirs(adir, exist_ok=True)

    # ---- 3. voiceover ----
    print("[3/5] Synthesizing voiceover (edge-tts) ...", flush=True)
    durs = []
    for i, s in enumerate(sections, 1):
        mp3 = os.path.join(adir, f"s{i}.mp3")
        if args.reuse_audio and os.path.exists(mp3):
            d = T.audio_duration(mp3) + TAIL
            print(f"      s{i}: reusing audio ({d - TAIL:.1f}s)", flush=True)
            durs.append(d)
            continue
        try:
            used = T.synthesize(s.body, mp3, provider=args.tts)
            d = T.audio_duration(mp3) + TAIL
        except Exception as e:
            sys.exit(f"ERROR: TTS failed on section {i}: {e}\n"
                     f"      (TTS needs internet access.)")
        durs.append(d)
        print(f"      s{i}: {d - TAIL:.1f}s audio", flush=True)

    # ---- 4. render ----
    print("[4/5] Rendering frames ...", flush=True)
    sec_mps = []
    for i, (s, d) in enumerate(zip(sections, durs), 1):
        sd = os.path.join(fdir, f"s{i}")
        n = render.render_section_frames(s, i - 1, d, sd)
        mp4 = os.path.join(work, f"s{i}.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
             "-i", os.path.join(sd, "f%04d.png"),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4])
        av = os.path.join(work, f"s{i}_av.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-i", mp4,
             "-i", os.path.join(adir, f"s{i}.mp3"),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-af", "apad", "-t", f"{d:.2f}", av])
        sec_mps.append(av)
        print(f"      s{i}: {n} frames", flush=True)

    # ---- 5. assemble ----
    print("[5/5] Assembling final MP4 ...", flush=True)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        for p in sec_mps:
            f.write(f"file '{p}'\n")
    outdir = os.path.join(BASE, "output")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"reel-{slug}.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", lst, "-c", "copy", out])
    total = sum(durs)

    if not args.keep_frames:
        import shutil
        shutil.rmtree(fdir, ignore_errors=True)

    with open(os.path.join(work, "script.txt"), "w") as f:
        f.write(script_text)

    print(f"\nDONE: {out}", flush=True)
    print(f"      {len(sections)} sections, {total:.1f}s, "
          f"1080x1920 H264+AAC", flush=True)


if __name__ == "__main__":
    main()

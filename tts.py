#!/usr/bin/env python3
"""AI Reel Factory — voiceover.

Primary: edge-tts (free, no API key, natural neural voices).
Fallback: gTTS (free, plain HTTPS) when edge-tts can't connect
(e.g. networks that block WebSocket upgrades).
"""
import asyncio
import os
import ssl
import subprocess

VOICE = "en-US-GuyNeural"   # edge-tts voice
RATE = "+0%"


def _patch_edge_ssl():
    """edge-tts pins certifi's CA bundle, which misses MITM egress proxies."""
    try:
        import edge_tts.communicate as _edge_comm
    except ImportError:
        return
    cafile = os.environ.get("SSL_CERT_FILE")
    if not cafile or not os.path.exists(cafile):
        for cand in ("/etc/ssl/certs/ca-certificates.crt",
                     "/etc/pki/tls/certs/ca-bundle.crt"):
            if os.path.exists(cand):
                cafile = cand
                break
    if cafile:
        _edge_comm._SSL_CTX = ssl.create_default_context(cafile=cafile)
    else:
        _edge_comm._SSL_CTX = ssl.create_default_context()


def _proxy():
    return (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            or None)


def _edge_synthesize(text, out_path):
    import edge_tts
    _patch_edge_ssl()

    async def _speak():
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, proxy=_proxy())
        await comm.save(out_path)

    asyncio.run(_speak())


def _gtts_synthesize(text, out_path):
    from gtts import gTTS
    gTTS(text, lang="en", tld="com").save(out_path)


def synthesize(text, out_path, provider="auto"):
    """provider: 'auto' | 'edge' | 'gtts'. Returns the provider used."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if provider in ("auto", "edge"):
        try:
            _edge_synthesize(text, out_path)
            return "edge-tts"
        except Exception as e:
            if provider == "edge":
                raise
            print(f"      (edge-tts unavailable: {type(e).__name__}; "
                  f"falling back to gTTS)", flush=True)
    _gtts_synthesize(text, out_path)
    return "gtts"


def audio_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True)
    return float(r.stdout.strip())

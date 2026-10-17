"""ElevenLabs calls: music from a composition plan, sound effects, and text-to-speech. Every call is logged.

The key comes from ELEVENLABS_API_KEY and is never printed. Each call appends a row to
<project>/takes/eleven-calls.jsonl (tools/spend_report.py reads it).

usage: python3 tools/eleven.py music <plan.json> <out.mp3> [--seed N] [--bpm 120]
       python3 tools/eleven.py sfx <text> <seconds> <out.mp3>
       python3 tools/eleven.py tts <voice_id> <text> <out.mp3> [--model eleven_multilingual_v2]
       add --project DIR (default .) and --dry-run (no key, no call: ffmpeg writes a placeholder of the right shape:
       a pulse on the --bpm grid for music, a noise burst for sfx, word-length tone bursts for tts).
Endpoints (docs read 2026-10-17): POST /v1/music (model music_v2_5, plan `chunks`), POST /v1/sound-generation,
POST /v1/text-to-speech/{voice_id}; auth header xi-api-key.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ensure_dir, ffmpeg, need_key, project, run  # noqa: E402

API = "https://api.elevenlabs.io/v1"
MUSIC_MODEL = "music_v2_5"


def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": need_key("ELEVENLABS_API_KEY"),
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs HTTP {e.code}: {e.read().decode()[:800]}")


def plan_seconds(plan):
    """Total length of a composition plan (music_v2/v2_5 `chunks`, or v1 `sections`), in seconds."""
    parts = plan.get("chunks") or plan.get("sections") or []
    return sum(p.get("duration_ms", p.get("duration", 0)) for p in parts) / 1000 or 10.0


def placeholder(expr, seconds, out):
    run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={seconds}",
         "-ac", "2", "-b:a", "192k", out])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["music", "sfx", "tts"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bpm", type=float, default=120.0, help="dry-run music only: the placeholder's beat grid")
    ap.add_argument("--model", default="eleven_multilingual_v2", help="tts model_id")
    ap.add_argument("--project", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run:
        need_key("ELEVENLABS_API_KEY")
    root = project(a.project)
    log_path = os.path.join(ensure_dir(os.path.join(root, "takes")), "eleven-calls.jsonl")

    if a.kind == "music":
        plan_path, out = a.args[:2]
        plan = json.load(open(os.path.join(root, plan_path)))
        entry = {"kind": "music", "plan": plan_path, "out": out, "seed": a.seed}
    elif a.kind == "sfx":
        text, seconds, out = a.args[0], float(a.args[1]), a.args[2]
        entry = {"kind": "sfx", "text": text, "duration": seconds, "out": out}
    else:
        voice, text, out = a.args[:3]
        entry = {"kind": "tts", "voice": voice, "model": a.model, "text": text, "out": out}
    dest = os.path.join(root, out)
    ensure_dir(os.path.dirname(dest))

    if a.dry_run:
        if a.kind == "music":
            beat = 60 / a.bpm  # a decaying low tone on every beat: beat_grid.py and onsets.py find the grid in it
            placeholder(f"0.6*sin(2*PI*90*t)*exp(-9*mod(t,{beat:.6f}))+0.08*sin(2*PI*330*t)", plan_seconds(plan), dest)
        elif a.kind == "sfx":
            placeholder("0.5*(random(0)*2-1)*exp(-12*t)", seconds, dest)
        else:
            words = max(1, len(text.split()))
            placeholder("0.4*sin(2*PI*220*t)*lt(mod(t,0.36),0.28)", round(words * 0.36, 2), dest)
        entry["dry_run"] = True
    else:
        if a.kind == "music":
            body = {"composition_plan": plan, "model_id": MUSIC_MODEL}
            if a.seed is not None:
                body["seed"] = a.seed
            audio = post("/music?output_format=mp3_48000_192", body)
        elif a.kind == "sfx":
            audio = post("/sound-generation?output_format=mp3_44100_128",
                         {"text": text, "duration_seconds": seconds, "prompt_influence": 0.6})
        else:
            audio = post(f"/text-to-speech/{voice}?output_format=mp3_44100_192",
                         {"text": text, "model_id": a.model,
                          "voice_settings": {"stability": 0.6, "similarity_boost": 0.8, "style": 0.0, "speed": 0.95}})
        with open(dest, "wb") as f:
            f.write(audio)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"{a.kind}: {dest}{' (dry run)' if a.dry_run else ''}")


if __name__ == "__main__":
    main()

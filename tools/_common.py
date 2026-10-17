"""Shared helpers for the fleet-video-lab tools: binaries from PATH, keys from env, project paths, the job log.

Every tool works on a PROJECT directory (default: the current directory) laid out as:
  stills/        start stills (GPT image)            takes/video/   Seedance takes (one file per job)
  audio/         music, VO, SFX (ElevenLabs)         takes/*.jsonl  the generation ledgers (every paid call)
  out/           renders and the master              frames/        contact sheets and proof frames
"""
import os
import shutil
import subprocess
import sys

FLEET_ROUTE = "fleet-ctl secret request {name} --dest env"


def binary(name, env=None, hint=""):
    """The path of an external binary: $<env> if set, else PATH; exits with one line when it is missing."""
    path = os.environ.get(env) if env else None
    path = path or shutil.which(name)
    if not path:
        sys.exit(f"{name} not found on PATH{(' (or set ' + env + ')') if env else ''}. {hint}".strip())
    return path


def ffmpeg():
    return binary("ffmpeg", "FFMPEG", "Install ffmpeg: brew install ffmpeg / apt-get install ffmpeg.")


def ffprobe():
    return binary("ffprobe", "FFPROBE", "Install ffmpeg (ffprobe ships with it).")


def need_key(name, extra=""):
    """The value of an API key env var; exits with a one-line 'set NAME' message when it is missing. Never printed."""
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"set {name} (export {name}=... or: {FLEET_ROUTE.format(name=name)}){extra}")
    return value


def project(path=None):
    return os.path.abspath(path or os.environ.get("VIDEO_LAB_PROJECT") or ".")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def run(cmd, **kw):
    """Run a command; on failure exit with its stderr tail (no tracebacks for tool users)."""
    kw.setdefault("text", True)
    r = subprocess.run(cmd, capture_output=True, **kw)
    if r.returncode:
        msg = r.stderr or r.stdout
        msg = msg.decode(errors="replace") if isinstance(msg, bytes) else msg
        sys.exit(f"{os.path.basename(cmd[0])} exit {r.returncode}: {msg.strip()[-1500:]}")
    return r


def duration(path):
    """Container duration in seconds (ffprobe)."""
    out = run([ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout
    return float(out.strip())

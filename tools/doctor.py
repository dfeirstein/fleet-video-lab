"""Check every external dependency fleet-video-lab uses and say exactly how to fix what is missing.

usage: python3 tools/doctor.py [--strict] [--offline]
Prints one row per check: status (ok / MISSING / optional), what was found, how to get it, and where to set it.
Report mode always exits 0, even with everything missing (so a new machine can see the whole list).
--strict exits 1 if anything a real (non-dry-run) film needs is missing.
--offline skips the Higgsfield login probe (it makes one network call to read the account status).
Keys are only checked for presence; no key value is ever printed.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

FLEET = "fleet-ctl secret request {} --dest env"
HF_INSTALL = "curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh (or npm i -g @higgsfield/cli)"
HYPERFRAMES_PIN = "0.8.169"


def sh(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def first_line(text):
    return text.splitlines()[0][:60] if text else ""


def checks(offline):
    """Yield (name, status, found, how_to_get, where_to_set, needed_for_real_film)."""
    py = sys.version_info
    yield ("python3 >= 3.10", "ok" if py >= (3, 10) else "MISSING", f"{py.major}.{py.minor}.{py.micro}",
           "python.org or your package manager", "PATH", True)

    ff = shutil.which(os.environ.get("FFMPEG") or "ffmpeg")
    found = first_line(sh([ff, "-version"])[1]) if ff else ""
    yield ("ffmpeg", "ok" if ff else "MISSING", found, "brew install ffmpeg / apt-get install ffmpeg",
           "PATH or FFMPEG=/path/to/ffmpeg", True)
    if ff:
        filters = sh([ff, "-hide_banner", "-filters"])[1]
        has = all(f" {name} " in filters for name in ("drawtext", "ebur128", "xstack", "zoompan"))
        yield ("ffmpeg filters (drawtext, ebur128, xstack, zoompan)", "ok" if has else "MISSING",
               "all present" if has else "a filter is missing", "an ffmpeg build with libfreetype (brew/apt builds have it)",
               "PATH or FFMPEG", True)
    fp = shutil.which(os.environ.get("FFPROBE") or "ffprobe")
    yield ("ffprobe", "ok" if fp else "MISSING", first_line(sh([fp, "-version"])[1]) if fp else "",
           "ships with ffmpeg", "PATH or FFPROBE=/path/to/ffprobe", True)

    try:
        import numpy  # noqa: F401
        np_status, np_found = "ok", numpy.__version__
    except ImportError:
        np_status, np_found = "optional", "not installed"
    yield ("numpy (vo_segments, audio_profile, fine_profile)", np_status, np_found, "pip install -r requirements.txt",
           "your Python environment", False)

    hf = shutil.which(os.environ.get("HIGGSFIELD") or "higgsfield")
    yield ("Higgsfield CLI (Seedance 2.5)", "ok" if hf else "MISSING",
           first_line(sh([hf, "version"])[1]) if hf else "", HF_INSTALL, "PATH or HIGGSFIELD=/path/to/higgsfield", True)
    if hf and not offline:
        code, out = sh([hf, "account", "status"], timeout=30)
        logged = code == 0 and re.search(r"[\d.,]+ credits", out)
        yield ("Higgsfield login", "ok" if logged else "MISSING", "logged in" if logged else "not logged in",
               "higgsfield auth login (browser OAuth; the token stays in the CLI's own credentials file)",
               "the Higgsfield CLI (no env var)", True)
    elif hf:
        yield ("Higgsfield login", "optional", "not probed (--offline)", "higgsfield auth login",
               "the Higgsfield CLI (no env var)", False)

    for name, use, how in (
            ("ELEVENLABS_API_KEY", "music, VO, SFX (tools/eleven.py)", "elevenlabs.io -> Developers -> API keys"),
            ("OPENAI_API_KEY", "start stills (tools/gpt_image.py)",
             "platform.openai.com -> API keys; OR make stills with the gpt-image MCP and skip this key")):
        present = bool(os.environ.get(name, "").strip())
        yield (f"{name} ({use})", "ok" if present else ("MISSING" if name != "OPENAI_API_KEY" else "optional"),
               "set" if present else "not set", how, f"env {name}; Fleet: {FLEET.format(name)}",
               name == "ELEVENLABS_API_KEY")

    node = shutil.which("node")
    ver = sh([node, "--version"])[1] if node else ""
    major = int(re.match(r"v(\d+)", ver).group(1)) if re.match(r"v(\d+)", ver) else 0
    yield ("node >= 22 (Hyperframes, tools/capture.mjs)", "ok" if major >= 22 else "MISSING", ver or "not found",
           "nodejs.org or nvm install 22", "PATH", True)
    hfr = shutil.which("hyperframes")
    yield (f"Hyperframes CLI (pin {HYPERFRAMES_PIN})", "ok" if (hfr or shutil.which("npx")) else "MISSING",
           "global install" if hfr else ("runs via npx on first use" if shutil.which("npx") else "no npx"),
           f"npx hyperframes@{HYPERFRAMES_PIN} --version (needs node >= 22 + ffmpeg)", "PATH (npx)", True)
    chrome = os.environ.get("CHROME") or next((p for p in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and os.path.exists(p)), "")
    yield ("Chrome (tools/capture.mjs proofs)", "ok" if chrome else "optional", "found" if chrome else "not found",
           "install Google Chrome or Chromium", "CHROME=/path/to/chrome", False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    rows = list(checks(a.offline))
    w = max(len(r[0]) for r in rows)
    print(f"{'check':<{w}}  {'status':<8}  found")
    print("-" * (w + 40))
    for name, status, found, how, where, _ in rows:
        print(f"{name:<{w}}  {status:<8}  {found}")
        if status != "ok":
            print(f"{'':<{w}}  {'':<8}  get it: {how}")
            print(f"{'':<{w}}  {'':<8}  set it: {where}")
    missing = [r[0] for r in rows if r[1] == "MISSING" and r[5]]
    print()
    if missing:
        print(f"{len(missing)} missing for a real film: " + "; ".join(missing))
        print("The keyless sample still runs: make demo-dry (needs python3 + ffmpeg only). See docs/SETUP.md.")
    else:
        print("everything a real film needs is present. Next: make demo (spends credits; it quotes first).")
    sys.exit(1 if a.strict and missing else 0)


if __name__ == "__main__":
    main()

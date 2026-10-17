"""One Seedance 2.5 take through the Higgsfield CLI, with spend guardrails.

Order: account status -> cost quote -> cap check -> create --wait -> account status -> log the delta -> download.
One job is one take; jobs run serially so every before/after delta belongs to one job. Seedance bills at submit and
a job can sit in_progress for 15+ minutes: never re-submit a pending job, poll `higgsfield --json generate list`.

usage: python3 tools/hf_shot.py <job> <start_still> <duration_s> <prompt> [--cap 1000] [--stop N] [--aspect 16:9]
                                [--ref still.png ...] [--project DIR] [--dry-run]
Writes <project>/takes/video/<job>.mp4 and appends one row to <project>/takes/hf-ledger.jsonl.
--dry-run calls nothing and spends nothing: it renders a slow push-in on the start still with ffmpeg as a stand-in take
and logs a 0-credit row marked dry_run, so the rest of the pipeline can be exercised without an account.
"""
import argparse
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import binary, ensure_dir, ffmpeg, project, run  # noqa: E402

MODEL = "seedance_2_5"
FPS = 24  # Seedance takes are 24 fps; render the cut at 24 too or it judders
HF_HINT = ("Install the Higgsfield CLI (curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh"
           " | sh, or npm install -g @higgsfield/cli), then run: higgsfield auth login")


def hf(*args):
    return run([binary("higgsfield", "HIGGSFIELD", HF_HINT), *args]).stdout.strip()


def credits():
    return float(re.search(r"([\d.,]+) credits", hf("account", "status")).group(1).replace(",", ""))


def spent_so_far(ledger):
    if not os.path.exists(ledger):
        return 0.0
    return sum(json.loads(row)["delta"] for row in open(ledger) if row.strip())


def dry_take(still, dur, dest):
    """A stand-in take: the still, scaled to 1280x720 and pushed in slowly, at 24 fps."""
    n = int(float(dur) * FPS)
    run([ffmpeg(), "-v", "error", "-y", "-loop", "1", "-i", still, "-vf",
         f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
         f"zoompan=z='1+0.1*on/{n}':d={n}:s=1280x720:fps={FPS},format=yuv420p",
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", dest])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job")
    ap.add_argument("still")
    ap.add_argument("duration")
    ap.add_argument("prompt")
    ap.add_argument("--cap", type=float, default=1000, help="refuse a job whose quote would take spend past this")
    ap.add_argument("--stop", type=float, default=None, help="hard stop: no jobs once spend reaches this")
    ap.add_argument("--aspect", default=None, help="e.g. 1:1 or 9:16 (default: the model's)")
    ap.add_argument("--ref", action="append", default=[], help="identity reference still (repeatable)")
    ap.add_argument("--resolution", default="1080p")
    ap.add_argument("--project", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = project(a.project)
    ledger = os.path.join(ensure_dir(os.path.join(root, "takes")), "hf-ledger.jsonl")
    dest = os.path.join(ensure_dir(os.path.join(root, "takes", "video")), f"{a.job}.mp4")
    still = os.path.join(root, a.still) if not os.path.isabs(a.still) else a.still
    if not os.path.exists(still):
        sys.exit(f"start still not found: {still}")

    if a.dry_run:
        dry_take(still, a.duration, dest)
        entry = {"job": a.job, "still": a.still, "duration": int(float(a.duration)), "quote": 0, "before": 0,
                 "after": 0, "delta": 0, "prompt": a.prompt, "dry_run": True}
        with open(ledger, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"{a.job}: DRY RUN, 0 credits; stand-in take {dest}")
        return

    params = [MODEL, "--mode", "omni_reference", "--start-image", still, "--prompt", a.prompt,
              "--duration", a.duration, "--resolution", a.resolution, "--generate_audio", "false"]
    if a.aspect:
        params += ["--aspect_ratio", a.aspect]
    for ref in a.ref:
        params += ["--image-references", ref]
    before = credits()
    quote = float(re.search(r"([\d.]+) credits", hf("generate", "cost", *params)).group(1))
    spent = spent_so_far(ledger)
    print(f"{a.job}: QUOTE {quote} credits; spent so far {spent} of cap {a.cap:g}", flush=True)
    if a.stop is not None and spent >= a.stop:
        sys.exit(f"STOPPED {a.job}: spent {spent} >= {a.stop:g}; report before any more jobs")
    if spent + quote > a.cap:
        sys.exit(f"REFUSED {a.job}: spent {spent} + quote {quote} > cap {a.cap:g}")
    out = hf("--json", "generate", "create", *params, "--wait", "--wait-timeout", "20m", "--wait-interval", "10s")
    after = credits()
    delta = round(before - after, 2)
    data = json.loads(out) if out.startswith(("{", "[")) else {"raw": out}
    urls = re.findall(r"https://[^\s\"']+\.mp4[^\s\"']*", out)
    entry = {"job": a.job, "still": a.still, "duration": int(float(a.duration)), "quote": quote, "before": before,
             "after": after, "delta": delta, "prompt": a.prompt, "urls": urls, "refs": a.ref}
    job = data[0] if isinstance(data, list) and data else data
    if isinstance(job, dict):
        entry["job_id"] = job.get("id") or job.get("job_id")
        entry["status"] = job.get("status")
    with open(ledger, "a") as f:
        f.write(json.dumps(entry) + "\n")
    if urls:
        urllib.request.urlretrieve(urls[0], dest)
        print("saved", dest)
    print(f"{a.job}: before {before}, after {after}, delta {delta}, total spent {spent + delta}")
    if not urls:
        print("NO URL FOUND; check `higgsfield --json generate list` before any re-submit. Raw output:\n" + out[:2000])


if __name__ == "__main__":
    main()

"""Make a project's planned stills, then run its Seedance jobs serially (serial keeps each credit delta one job's own).

usage: python3 tools/run_batch.py [JOB ...] [--project DIR] [--cap 1000] [--dry-run]
Reads <project>/SHOTS.md, two markdown tables:
  | Still | Prompt |                        -> tools/gpt_image.py, skipped when stills/<still>.png exists
  | Job | Start still | Dur | Prompt |      -> tools/hf_shot.py, skipped when takes/video/<job>.mp4 exists
With no JOB names it runs every job in the table. Stops at the first failure. --dry-run is passed through.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import project  # noqa: E402

TOOLS = os.path.dirname(os.path.abspath(__file__))


def tables(path):
    """{'stills': [(name, prompt)], 'jobs': [(job, still, seconds, prompt)]} from the SHOTS.md tables."""
    stills, jobs = [], []
    for line in open(path):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and re.fullmatch(r"s\w+", cells[0]):
            stills.append((cells[0], cells[1]))
        m = re.fullmatch(r"(\d+(?:\.\d+)?) ?s", cells[2]) if len(cells) == 4 else None
        if m and re.fullmatch(r"V\w+", cells[0]):
            jobs.append((cells[0], cells[1], m.group(1), cells[3]))
    return {"stills": stills, "jobs": jobs}


def step(args):
    r = subprocess.run([sys.executable, *args])
    if r.returncode:
        sys.exit(f"{os.path.basename(args[0])} {args[1]} failed ({r.returncode}); stopping batch")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs", nargs="*")
    ap.add_argument("--project", default=None)
    ap.add_argument("--cap", default="1000")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = project(a.project)
    plan = tables(os.path.join(root, "SHOTS.md"))
    if not plan["jobs"]:
        sys.exit(f"no '| Job | Start still | Dur | Prompt |' rows found in {root}/SHOTS.md")
    dry = ["--dry-run"] if a.dry_run else []
    for name, prompt in plan["stills"]:
        if not os.path.exists(os.path.join(root, "stills", f"{name}.png")):
            step([os.path.join(TOOLS, "gpt_image.py"), name, prompt, "--project", root, *dry])
    wanted = set(a.jobs) or {j[0] for j in plan["jobs"]}
    for job, still, seconds, prompt in plan["jobs"]:
        if job not in wanted:
            continue
        if os.path.exists(os.path.join(root, "takes", "video", f"{job}.mp4")):
            print(f"{job}: take on disk, skipped")
            continue
        step([os.path.join(TOOLS, "hf_shot.py"), job, f"stills/{still}.png", seconds, prompt,
              "--project", root, "--cap", a.cap, *dry])


if __name__ == "__main__":
    main()

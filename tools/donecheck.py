"""Done-check: walks the gates in order and names the FIRST missing or failing artifact. Done means this passes,
never that the last command exited 0.

usage: python3 tools/donecheck.py [--project DIR] [--verdict FILE]
Reads the `deliverables` block of <project>/edit.json:
  "deliverables": {
    "render": ["out/render.mp4", "out/render.mov"],          any one of these is the render
    "formats": [{"name": "wide", "width": 1280, "height": 720, "max_bytes": 20000000, "final": "out/final.mp4",
                 "poster": "...png", "first_frame": "...png", "last_frame": "...png", "contact_sheet": "...png"}],
    "spend": "SPEND.md",
    "verdict": {"path": "VERDICT.md", "allowed": ["PASSES", "PASSES WITH FIXES"]}
  }
The whole block (and edit.json's picture list) is validated before any gate runs: every format needs all of its
keys; width, height and max_bytes are positive integers; render, spend, verdict.path are non-empty strings (render
may be a list of them); `allowed` is a list of strings naming only the judge's passing words (docs/METHOD.md
section 4: PASSES, PASSES WITH FIXES), never FAILS. --verdict reads that file
instead of the block's verdict path (make demo-dry points it at a stand-in, so a real VERDICT.md is never touched).
Gates: brief (BRIEF.md), shots (SHOTS.md), still board (frames/still-board.png, from make still-board), takes or
placeholders (takes/video/<take>.mp4 for every take in the picture list), render, master (dimensions by ffprobe,
size), proof frames, spend, verdict (line 1 in `allowed`).
Prints `donecheck: all gates met` and exits 0, or prints the first failure with its path and exits 1. A bad
edit.json is a failure of the `edit` gate that names edit.json and the key; ffprobe ($FFPROBE, else PATH) missing or
failing is a failure of the master gate that names the tool and the file.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

PASSING = ("PASSES", "PASSES WITH FIXES")  # the judge words in docs/METHOD.md section 4 that let a film ship
PROOF = ("poster", "first_frame", "last_frame", "contact_sheet")
FORMAT_PATHS = ("name", "final") + PROOF
FORMAT_SIZES = ("width", "height", "max_bytes")


def fail(gate, msg):
    print(f"donecheck: {gate}: {msg}")
    sys.exit(1)


def config(edit_path, edit):
    """The deliverables block (and the picture list), validated whole before anything is used; any fault is an
    `edit` failure naming edit.json and the key. Returns the block with its defaults filled in."""
    def bad(msg):
        fail("edit", f"{edit_path}: {msg}")

    def text(v):
        return isinstance(v, str) and v != ""

    if not isinstance(edit, dict):
        bad("must be a JSON object")
    picture = edit.get("picture", [])
    if not isinstance(picture, list):
        bad(f"picture must be a list, got {picture!r}")
    for i, p in enumerate(picture):
        if not isinstance(p, dict):
            bad(f"picture[{i}] must be an object, got {p!r}")
        if "take" in p and not text(p["take"]):
            bad(f"picture[{i}].take must be a non-empty string, got {p['take']!r}")
    d = edit.get("deliverables")
    if not isinstance(d, dict):
        bad("no deliverables block")
    render = d.get("render", ["out/render.mp4"])
    render = [render] if isinstance(render, str) else render
    if not isinstance(render, list) or not render or not all(text(r) for r in render):
        bad(f"deliverables.render must be a path or a non-empty list of paths, got {d.get('render')!r}")
    formats = d.get("formats")
    if not isinstance(formats, list) or not formats:
        bad("deliverables.formats must be a non-empty list")
    for i, f in enumerate(formats):
        if not isinstance(f, dict):
            bad(f"deliverables.formats[{i}] must be an object")
        for k in FORMAT_PATHS:
            if not text(f.get(k)):
                bad(f"deliverables.formats[{i}].{k} is missing or not a non-empty string, got {f.get(k)!r}")
        for k in FORMAT_SIZES:
            n = f.get(k)
            if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
                bad(f"deliverables.formats[{i}].{k} must be a positive integer, got {n!r}")
    spend = d.get("spend", "SPEND.md")
    if not text(spend):
        bad(f"deliverables.spend must be a non-empty string, got {spend!r}")
    v = d.get("verdict", {})
    if not isinstance(v, dict):
        bad(f"deliverables.verdict must be an object, got {v!r}")
    vpath = v.get("path", "VERDICT.md")
    if not text(vpath):
        bad(f"deliverables.verdict.path must be a non-empty string, got {vpath!r}")
    allowed = v.get("allowed", list(PASSING))
    # element types first: set() on an unhashable element would raise before the subset test could name the key
    if (not isinstance(allowed, list) or not allowed or not all(isinstance(w, str) for w in allowed)
            or not set(allowed) <= set(PASSING)):
        bad(f"deliverables.verdict.allowed is {allowed!r}; it may name only passing verdicts {list(PASSING)}")
    return dict(d, render=render, spend=spend, verdict={"path": vpath, "allowed": allowed}, picture=picture)


def probe(gate, final):
    """'W,H' of the first video stream; ffprobe missing or failing is a failure naming the tool and the file."""
    tool = os.environ.get("FFPROBE") or shutil.which("ffprobe")
    if not tool:
        fail(gate, f"ffprobe not found (set FFPROBE or install ffmpeg); cannot probe {final}")
    try:
        r = subprocess.run([tool, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", final], capture_output=True, text=True)
    except OSError as e:
        fail(gate, f"ffprobe ({tool}) could not run on {final}: {e.strerror or e}")
    if r.returncode:
        tail = (r.stderr or r.stdout).strip()[-300:]
        fail(gate, f"ffprobe ({tool}) exit {r.returncode} on {final}{': ' + tail if tail else ''}")
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--verdict", help="the verdict file to read (default: the deliverables block's verdict path)")
    a = ap.parse_args()

    def path(rel):
        # joined to --project as given, so the printed path is the one the caller typed (no absolute home path)
        return os.path.join(a.project, rel)

    def need(gate, p):
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            fail(gate, f"missing {p}")
        return p

    edit_path = need("edit", path("edit.json"))
    try:
        with open(edit_path) as fh:
            edit = json.load(fh)
    except (OSError, ValueError) as e:
        fail("edit", f"{edit_path}: not readable JSON ({e})")
    d = config(edit_path, edit)
    need("brief", path("BRIEF.md"))
    need("shots", path("SHOTS.md"))
    need("still board", path("frames/still-board.png"))
    for p in d["picture"]:
        if "take" in p:
            need("takes", path(f"takes/video/{p['take']}.mp4"))
    renders = d["render"]
    if not any(os.path.isfile(path(r)) and os.path.getsize(path(r)) for r in renders):
        fail("render", "missing " + " or ".join(path(r) for r in renders))
    for f in d["formats"]:
        gate = f"master {f['name']}"
        final = need(gate, path(f["final"]))
        wh = probe(gate, final)
        if wh != f"{f['width']},{f['height']}":
            fail(gate, f"{final} is {wh.replace(',', 'x') or 'no video'}, want {f['width']}x{f['height']}")
        size = os.path.getsize(final)
        if size > f["max_bytes"]:
            fail(gate, f"{final} is {size} bytes, over max_bytes {f['max_bytes']}")
    for f in d["formats"]:
        for k in PROOF:
            need(f"proof {f['name']} {k}", path(f[k]))
    need("spend", path(d["spend"]))
    allowed = d["verdict"]["allowed"]
    # with --verdict the block's verdict path is never opened, read or even stat'ed
    vp = need("verdict", a.verdict or path(d["verdict"]["path"]))
    try:
        with open(vp) as fh:
            line1 = fh.readline().strip()
    except (OSError, UnicodeDecodeError) as e:
        fail("verdict", f"{vp}: not readable ({e})")
    if line1 not in allowed:
        fail("verdict", f"{vp} line 1 is {line1!r}, want one of {allowed}")
    print("donecheck: all gates met")


if __name__ == "__main__":
    main()

"""Done-check: walks the gates in order and names the FIRST missing or failing artifact. Done means this passes,
never that the last command exited 0.

usage: python3 tools/donecheck.py [--project DIR]
Reads the `deliverables` block of <project>/edit.json:
  "deliverables": {
    "render": ["out/render.mp4", "out/render.mov"],          any one of these is the render
    "formats": [{"name": "wide", "width": 1280, "height": 720, "max_bytes": 20000000, "final": "out/final.mp4",
                 "poster": "...png", "first_frame": "...png", "last_frame": "...png", "contact_sheet": "...png"}],
    "spend": "SPEND.md",
    "verdict": {"path": "VERDICT.md", "allowed": ["PASSES", "PASSES WITH FIXES"]}
  }
Gates: brief (BRIEF.md), shots (SHOTS.md), still board (frames/still-board.png: a warning only, for now), takes or
placeholders (takes/video/<take>.mp4 for every take in the picture list), render, master (dimensions by ffprobe,
size), proof frames, spend, verdict (line 1 in `allowed`, from the judge's vocabulary in docs/METHOD.md section 4).
Prints `donecheck: all gates met` and exits 0, or prints the first failure with its path and exits 1.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffprobe, run  # noqa: E402

VERDICTS = ("PASSES", "PASSES WITH FIXES", "FAILS")
PROOF = ("poster", "first_frame", "last_frame", "contact_sheet")


def fail(gate, msg):
    print(f"donecheck: {gate}: {msg}")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    a = ap.parse_args()

    def path(rel):
        # joined to --project as given, so the printed path is the one the caller typed (no absolute home path)
        return os.path.join(a.project, rel)

    def need(gate, rel):
        p = path(rel)
        if not os.path.isfile(p) or os.path.getsize(p) == 0:
            fail(gate, f"missing {p}")
        return p

    need("edit", "edit.json")
    edit = json.load(open(path("edit.json")))
    d = edit.get("deliverables")
    if not d or not d.get("formats"):
        fail("edit", f"no deliverables block with formats in {path('edit.json')}")
    need("brief", "BRIEF.md")
    need("shots", "SHOTS.md")
    board = path("frames/still-board.png")
    if not os.path.isfile(board):
        print(f"donecheck: warning: still board: missing {board} (optional until the still-board gate lands)")
    for p in edit.get("picture", []):
        if "take" in p:
            need("takes", f"takes/video/{p['take']}.mp4")
    renders = d.get("render", ["out/render.mp4"])
    renders = [renders] if isinstance(renders, str) else renders
    if not any(os.path.isfile(path(r)) and os.path.getsize(path(r)) for r in renders):
        fail("render", "missing " + " or ".join(path(r) for r in renders))
    for f in d["formats"]:
        final = need(f"master {f['name']}", f["final"])
        wh = run([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                  "-of", "csv=p=0", final]).stdout.strip()
        if wh != f"{f['width']},{f['height']}":
            fail(f"master {f['name']}", f"{final} is {wh.replace(',', 'x') or 'no video'}, "
                                        f"want {f['width']}x{f['height']}")
        size = os.path.getsize(final)
        if f.get("max_bytes") and size > f["max_bytes"]:
            fail(f"master {f['name']}", f"{final} is {size} bytes, over max_bytes {f['max_bytes']}")
    for f in d["formats"]:
        for k in PROOF:
            if not f.get(k):
                fail(f"proof {f['name']}", f"no {k} path in the deliverables block")
            need(f"proof {f['name']} {k}", f[k])
    need("spend", d.get("spend", "SPEND.md"))
    v = d.get("verdict") or {}
    allowed = v.get("allowed", ["PASSES", "PASSES WITH FIXES"])
    if not set(allowed) <= set(VERDICTS):
        fail("verdict", f"allowed {allowed} is outside the judge's vocabulary {list(VERDICTS)}")
    vp = need("verdict", v.get("path", "VERDICT.md"))
    line1 = open(vp).readline().strip()
    if line1 not in allowed:
        fail("verdict", f"{vp} line 1 is {line1!r}, want one of {allowed}")
    print("donecheck: all gates met")


if __name__ == "__main__":
    main()

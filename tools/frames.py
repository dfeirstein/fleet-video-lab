"""Proof frames: one labelled frame just after every cut, a contact sheet, dense strips, and the true last frame.

usage: python3 tools/frames.py <video> <out_dir> [--edit edit.json | --cuts 0,1.5,3 | --every 1.0]
                               [--dense a-b ...] [--dense-only] [--fps 12] [--after 0.2] [--poster t]
  --edit reads the cut times from a build_comp.py edit list (beats x 60/bpm), so the frames sit on the real cut.
Writes <out_dir>/NN-<t>s.png, contact-sheet.png (6 columns), dense-<a>-<b>.png per --dense window, first-frame.png,
last-frame.png, and poster.png (the frame at --poster seconds) when asked;
it replaces only its own earlier files of those names, so other PNGs in out_dir (still-board.png) stay.
  --dense-only writes just the --dense strips and removes nothing: the local re-proof for a repair round.
Frame n of an `f%03d` sequence is file n+1; this tool names files by TIME to avoid that off-by-one.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, ensure_dir, ffmpeg, run  # noqa: E402

TW, TH = 480, 270
# its own files: NN is f"{i:02d}", at least two digits, so 100- and up match too
OWN = re.compile(r"(\d{2,}-[\d.]+s|contact-sheet|dense-[\d.]+-[\d.]+|last-frame)\.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--edit", default=None)
    ap.add_argument("--cuts", default=None)
    ap.add_argument("--every", type=float, default=None)
    ap.add_argument("--dense", action="append", default=[], help="a-b seconds: a 12 fps strip of that stretch")
    ap.add_argument("--dense-only", action="store_true", help="only the --dense strips; nothing else is touched")
    ap.add_argument("--fps", type=int, default=12, help="dense strip rate")
    ap.add_argument("--after", type=float, default=0.2, help="sample this long after each cut")
    ap.add_argument("--vertical", action="store_true", help="9:16 tiles")
    ap.add_argument("--poster", type=float, default=None, help="write poster.png: the full-size frame at this time")
    a = ap.parse_args()
    tw, th = (TH, TW) if a.vertical else (TW, TH)
    end = duration(a.src) - 0.05
    if a.edit:
        e = json.load(open(a.edit))
        cuts = [p["beat"] * 60 / e["bpm"] for p in e["picture"]]
    elif a.cuts:
        cuts = [float(c) for c in a.cuts.split(",")]
    else:
        step = a.every or 1.0
        cuts = [i * step for i in range(int(end / step) + 1)]
    ensure_dir(a.out)
    if a.dense_only:
        cuts = []
    else:
        for f in os.listdir(a.out):
            if OWN.fullmatch(f):
                os.remove(os.path.join(a.out, f))
    paths = []
    for i, c in enumerate(cuts):
        ts = min(round(c + a.after, 3), round(end, 3))
        p = os.path.join(a.out, f"{i:02d}-{ts:06.3f}s.png")
        run([ffmpeg(), "-v", "error", "-y", "-ss", str(ts), "-i", a.src, "-frames:v", "1", "-vf",
             f"scale={tw}:{th},drawtext=text='{ts:.2f}s':x=10:y=10:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.7",
             p])
        paths.append(p)
    cols = max(1, min(6, len(paths)))
    rows = -(-len(paths) // cols)
    inputs = []
    for p in paths:
        inputs += ["-i", p]
    if len(paths) == 1:
        run([ffmpeg(), "-v", "error", "-y", "-i", paths[0], os.path.join(a.out, "contact-sheet.png")])
    elif paths:
        layout = "|".join(f"{(k % cols) * tw}_{(k // cols) * th}" for k in range(len(paths)))
        run([ffmpeg(), "-v", "error", "-y", *inputs, "-filter_complex",
             f"xstack=inputs={len(paths)}:layout={layout}:fill=black", os.path.join(a.out, "contact-sheet.png")])
    for w in a.dense:
        s, e = (float(v) for v in w.split("-"))
        n = int((e - s) * a.fps)
        # -ss before -i restarts pts at 0: setpts adds the window start back so the labels read film time
        run([ffmpeg(), "-v", "error", "-y", "-ss", str(s), "-t", str(e - s), "-i", a.src, "-vf",
             f"setpts=PTS+{s}/TB,fps={a.fps},scale={tw * 2 // 3}:{th * 2 // 3},"
             f"drawtext=text='%{{pts\\:flt}}':x=4:y=4:fontsize=18:fontcolor=white:box=1:boxcolor=black,"
             f"tile=8x{max(1, -(-n // 8))}", "-frames:v", "1", os.path.join(a.out, f"dense-{s:05.2f}-{e:05.2f}.png")])
    if a.dense_only:
        print(len(a.dense), "dense strips ->", a.out)
        return
    run([ffmpeg(), "-v", "error", "-y", "-i", a.src, "-frames:v", "1", os.path.join(a.out, "first-frame.png")])
    if a.poster is not None:
        run([ffmpeg(), "-v", "error", "-y", "-ss", str(a.poster), "-i", a.src, "-frames:v", "1",
             os.path.join(a.out, "poster.png")])
    # the true last frame: -ss near the end with -update 1 (an -sseof grab can leave a stale PNG)
    run([ffmpeg(), "-v", "error", "-y", "-ss", str(max(0, end - 0.1)), "-i", a.src, "-update", "1",
         os.path.join(a.out, "last-frame.png")])
    print(len(paths), "frames,", rows, "rows,", len(a.dense), "dense strips, last-frame.png ->", a.out)


if __name__ == "__main__":
    main()

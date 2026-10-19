"""Proof frames: one labelled frame just after every cut, a contact sheet, dense strips, and the true last frame.

usage: python3 tools/frames.py <video> <out_dir> [--edit edit.json | --cuts 0,1.5,3 | --every 1.0]
                               [--dense a-b ...] [--dense-only] [--fps 12] [--after 0.2]
                               [--stillness [--still-seconds 1.0] [--still-ydif 0.5]]
  --edit reads the cut times from a build_comp.py edit list (beats x 60/bpm), so the frames sit on the real cut.
  --stillness measures pacing: per-frame YDIF (ffmpeg signalstats, mean absolute luma change from the previous frame,
  at full resolution); a frame under --still-ydif is still. Frame 0 has no previous frame and is not counted; seconds
  come from the frame timestamps. Writes motion.txt: the longest still run in frames and seconds, and every window
  still longer than --still-seconds (something should change about every second).
Writes <out_dir>/NN-<t>s.png, contact-sheet.png (6 columns), dense-<a>-<b>.png per --dense window, last-frame.png;
it replaces only its own earlier files of those names, so other PNGs in out_dir (still-board.png) stay.
  --dense-only writes just the --dense strips and removes nothing: the local re-proof for a repair round.
Frame n of an `f%03d` sequence is file n+1; this tool names files by TIME to avoid that off-by-one.
"""
import argparse
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, ensure_dir, ffmpeg, run  # noqa: E402

TW, TH = 480, 270
# its own files: NN is f"{i:02d}", at least two digits, so 100- and up match too
OWN = re.compile(r"(\d{2,}-[\d.]+s|contact-sheet|dense-[\d.]+-[\d.]+|last-frame)\.png")


def stillness(src, out, still_ydif, still_seconds):
    """Write <out>/motion.txt from per-frame signalstats YDIF; returns its path."""
    # metadata=print writes to file=- (stdout), not the log, so it survives -v error
    lines = run([ffmpeg(), "-v", "error", "-i", src, "-map", "0:v:0", "-vf",
                 "signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-", "-f", "null", "-"]).stdout.splitlines()
    times, ydif = [], []
    for ln in lines:
        if ln.startswith("frame:"):
            times.append(float(ln.rsplit("pts_time:", 1)[1]))
        elif ln.startswith("lavfi.signalstats.YDIF="):
            ydif.append(float(ln.split("=", 1)[1]))
    if not ydif or len(times) != len(ydif):
        sys.exit(f"stillness: no YDIF read from {src}")
    path = os.path.join(out, "motion.txt")
    with open(path, "w") as f:
        f.write("\n".join(still_report(os.path.basename(src), times, ydif, still_ydif, still_seconds)) + "\n")
    return path


def still_report(name, times, ydif, still_ydif, still_seconds):
    """The motion.txt rows from per-frame pts_time and YDIF.

    Frame 0 has no previous frame (signalstats reports YDIF 0 for it), so it is left out: each counted frame is one
    comparison with the frame before it. Seconds come from the timestamps, not an average fps: a run lasts from its
    first frame's pts to its last frame's pts plus one median frame interval."""
    if len(times) < 2:
        sys.exit(f"stillness: {name} has {len(times)} frame(s); need at least 2 to compare")
    dt = statistics.median(b - a for a, b in zip(times, times[1:]))
    t, y = times[1:], ydif[1:]
    runs, start = [], None  # [first, last] index into t of each still run
    for i, v in enumerate(y + [still_ydif]):
        if v < still_ydif and start is None:
            start = i
        elif v >= still_ydif and start is not None:
            runs.append((start, i - 1))
            start = None

    def secs(r):
        return t[r[1]] - t[r[0]] + dt

    longest = max(runs, key=secs, default=None)
    long_runs = [r for r in runs if secs(r) > still_seconds + 1e-9]
    rows = [f"src: {name}", f"frames: {len(times)}, {len(y)} compared with the previous frame (frame 0 has none); "
            f"median interval {dt:.4f} s",
            f"still: YDIF < {still_ydif} (signalstats, full resolution); windows over {still_seconds} s listed",
            f"YDIF: mean {sum(y) / len(y):.3f}, max {max(y):.3f}"]
    if longest:
        a, b = longest
        rows.append(f"longest still run: {b - a + 1} frames, {secs(longest):.3f} s ({t[a]:.3f}-{t[b] + dt:.3f} s)")
    else:
        rows.append("longest still run: 0 frames, 0.000 s")
    rows.append(f"still windows over {still_seconds} s: {len(long_runs)}")
    for a, b in long_runs:
        rows.append(f"  {t[a]:.3f}-{t[b] + dt:.3f} s  {b - a + 1} frames  {secs((a, b)):.3f} s")
    return rows


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
    ap.add_argument("--stillness", action="store_true", help="also write motion.txt: the still runs, from signalstats YDIF")
    ap.add_argument("--still-seconds", type=float, default=1.0, help="list still windows longer than this")
    ap.add_argument("--still-ydif", type=float, default=0.5, help="a frame whose YDIF is under this is still")
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
    # the true last frame: -ss near the end with -update 1 (an -sseof grab can leave a stale PNG)
    run([ffmpeg(), "-v", "error", "-y", "-ss", str(max(0, end - 0.1)), "-i", a.src, "-update", "1",
         os.path.join(a.out, "last-frame.png")])
    print(len(paths), "frames,", rows, "rows,", len(a.dense), "dense strips, last-frame.png ->", a.out)
    if a.stillness:
        m = stillness(a.src, a.out, a.still_ydif, a.still_seconds)
        with open(m) as f:
            print(f.read().rstrip())


if __name__ == "__main__":
    main()

"""Still board: every start still, and the first and last frame of each kept take, in one labelled grid.

usage: python3 tools/still_board.py <stills_dir> <out.png> [--takes <dir>] [--cols 4]
Every recurring subject (person, vehicle, object, set) is then visible side by side, so the board can be checked
against the locked-attributes table in SHOTS.md before run_batch.py spends a credit on a take.
Cells are the stills (*.png, *.jpg) in name order, then for each *.mp4 in --takes its first and last frame; the
file name sits under each cell. Pure ffmpeg; nothing is generated, nothing is spent.
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import duration, ensure_dir, ffmpeg, run  # noqa: E402

TW, TH, LH = 480, 270, 36


def cell(src, label, out, tmp, ss=None):
    """One tile: the frame fitted into TW x TH on black, the label in a strip under it."""
    txt = os.path.join(tmp, os.path.basename(out) + ".txt")
    with open(txt, "w") as f:
        f.write(label)
    seek = ["-ss", str(ss)] if ss is not None else []
    run([ffmpeg(), "-v", "error", "-y", *seek, "-i", src, "-frames:v", "1", "-update", "1", "-vf",
         f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH + LH}:(ow-iw)/2:(oh-{LH}-ih)/2:black,"
         f"drawtext=textfile='{txt}':expansion=none:x=10:y={TH + 8}:fontsize=20:fontcolor=white",
         out])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stills")
    ap.add_argument("out")
    ap.add_argument("--takes", default=None, help="a folder of kept takes (*.mp4): adds each one's first and last frame")
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    stills = sorted(f for f in os.listdir(a.stills) if f.lower().endswith((".png", ".jpg", ".jpeg")))
    takes = sorted(f for f in os.listdir(a.takes) if f.lower().endswith(".mp4")) if a.takes else []
    if not stills and not takes:
        sys.exit(f"no stills in {a.stills}{' and no takes in ' + a.takes if a.takes else ''}")
    ensure_dir(os.path.dirname(os.path.abspath(a.out)))
    with tempfile.TemporaryDirectory() as tmp:
        tiles = [cell(os.path.join(a.stills, s), s, os.path.join(tmp, f"s{i:03d}.png"), tmp)
                 for i, s in enumerate(stills)]
        for i, t in enumerate(takes):
            src = os.path.join(a.takes, t)
            # the last frame: -ss near the end with -update 1 (an -sseof grab can leave a stale PNG)
            last = max(0.0, duration(src) - 0.1)
            tiles.append(cell(src, f"{t} first", os.path.join(tmp, f"t{i:03d}a.png"), tmp, 0))
            tiles.append(cell(src, f"{t} last", os.path.join(tmp, f"t{i:03d}b.png"), tmp, round(last, 3)))
        cols = max(1, min(a.cols, len(tiles)))
        rows = -(-len(tiles) // cols)
        if len(tiles) == 1:
            run([ffmpeg(), "-v", "error", "-y", "-i", tiles[0], a.out])
        else:
            inputs = []
            for p in tiles:
                inputs += ["-i", p]
            layout = "|".join(f"{(k % cols) * TW}_{(k // cols) * (TH + LH)}" for k in range(len(tiles)))
            run([ffmpeg(), "-v", "error", "-y", *inputs, "-filter_complex",
                 f"xstack=inputs={len(tiles)}:layout={layout}:fill=black", "-frames:v", "1", "-update", "1", a.out])
    print(f"{len(stills)} stills, {len(takes)} takes x first/last, {rows} rows -> {a.out}")


if __name__ == "__main__":
    main()

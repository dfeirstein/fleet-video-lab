"""Still board: every start still, and the first and last frame of each kept take, in one labeled grid.

usage: python3 tools/still_board.py <stills_dir> <out.png> [--takes <dir>] [--cols 4]
Every recurring subject (person, vehicle, object, set) is then visible side by side, so the board can be checked
against the locked-attributes table in SHOTS.md before run_batch.py spends a credit on a take.
Cells are the stills (*.png, *.jpg) in name order, then for each *.mp4 in --takes its first and last frame; the
file name sits under each cell (middle-ellipsized to fit). A missing or empty --takes folder is noted and skipped,
so the board works on a fresh project. Any entry that is not a regular file ffprobe reads as an image or video is
skipped with a note, and so is any cell ffmpeg or ffprobe cannot make (a truncated take, unreadable metadata); one
bad file never stops the board. The summary counts only the takes with both cells and names each partial take.
Pure ffmpeg; nothing is generated, nothing is spent.
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ensure_dir, ffmpeg, ffprobe, run  # noqa: E402

TW, TH, LH = 480, 270, 36
FONT = 20
ROOM = TW - 20  # label width in px: a 10 px margin each side
WIDEST = 1.0  # em: the advance assumed for EVERY character


def width(s):
    """A conservative upper bound on the drawn width of s in px: every character is counted as the widest glyph.
    No font is pinned (drawtext uses the fontconfig default, DejaVu Sans in CI); the assumption is that no glyph in
    a file name advances more than one em in that font. That holds for Latin capitals (W is 0.99 em in DejaVu Sans)
    and for East Asian wide characters (1 em), and combining marks (0 em) are over-counted, so a label never
    overflows; the cost is that narrow names are ellipsized sooner than a measured width would need."""
    return FONT * WIDEST * len(s)


def fit(name, suffix=""):
    """The label for a cell: name + suffix, middle-ellipsized to ROOM px so the end of the name (its extension)
    and the suffix always show."""
    if width(name + suffix) <= ROOM:
        return name + suffix
    head, tail = name[: len(name) // 2], name[len(name) // 2:]
    while width(head + "..." + tail + suffix) > ROOM and (head or tail):
        if len(head) >= len(tail) - 4 and head:
            head = head[:-1]
        else:
            tail = tail[1:]
    return head + "..." + tail + suffix


def probe(path):
    """True when path is a regular file ffprobe reads a video stream from (stills decode as one-frame video)."""
    if not os.path.isfile(path):
        return False
    r = subprocess.run([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "video"


def last_index(src):
    """Index of the last frame that decodes. ffprobe -count_frames decodes the whole stream and counts the frames
    (nb_read_frames), the same frames select=eq(n,N) numbers. Packet counts, the header's nb_frames and duration x
    fps are not decoded-frame counts (a truncated take keeps a header that promises frames it no longer has), so none
    is used. Raises ValueError when ffprobe fails or no frame decodes."""
    r = subprocess.run([ffprobe(), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=nb_read_frames", "-of", "default=nw=1:nk=1", src], capture_output=True, text=True)
    n = r.stdout.strip().splitlines()[0].strip() if r.stdout.strip() else ""
    if r.returncode or not n.isdigit() or int(n) < 1:
        why = r.stderr.strip() or f"nb_read_frames={n or 'none'}"
        raise ValueError(f"ffprobe decoded no frame ({why[-200:]})")
    return int(n) - 1


def cell(src, label, out, tmp, n=None):
    """One tile: frame n (default the first) fitted into TW x TH on black, the label in a strip under it.
    Returns out, or None (with a note) when ffmpeg cannot make it.
    The label goes through a textfile named only by out's basename and ffmpeg runs with cwd=tmp, so no path (a
    TMPDIR with ', : or \\ in it) ever reaches the filter parser; src and out go in as absolute arguments."""
    txt = os.path.basename(out) + ".txt"
    with open(os.path.join(tmp, txt), "w") as f:
        f.write(label)
    pick = f"select=eq(n\\,{n})," if n else ""
    r = subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", os.path.abspath(src), "-frames:v", "1", "-update", "1",
                        "-vf", f"{pick}scale={TW}:{TH}:force_original_aspect_ratio=decrease,"
                        f"pad={TW}:{TH + LH}:(ow-iw)/2:(oh-{LH}-ih)/2:black,"
                        f"drawtext=textfile={txt}:expansion=none:x=10:y={TH + 8}:fontsize={FONT}:fontcolor=white",
                        os.path.abspath(out)], capture_output=True, text=True, cwd=tmp)
    if r.returncode or not os.path.isfile(out):
        print(f"skip {src}: ffmpeg could not make a cell ({r.stderr.strip()[-200:]})", file=sys.stderr)
        return None
    return out


def entries(folder, exts, kind):
    """The files in folder with one of exts, in name order, that probe() accepts; each other match is noted."""
    keep = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(exts):
            continue
        if probe(os.path.join(folder, f)):
            keep.append(f)
        else:
            print(f"skip {os.path.join(folder, f)}: not a readable {kind} file", file=sys.stderr)
    return keep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stills")
    ap.add_argument("out")
    ap.add_argument("--takes", default=None, help="a folder of kept takes (*.mp4): adds each one's first and last frame")
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    stills = entries(a.stills, (".png", ".jpg", ".jpeg"), "image") if os.path.isdir(a.stills) else []
    takes = []
    if a.takes and os.path.isdir(a.takes):
        takes = entries(a.takes, (".mp4",), "video")
    if a.takes and not takes:
        print(f"note: no takes in {a.takes}; the board shows the stills only")
    if not stills and not takes:
        sys.exit(f"no stills in {a.stills}{' and no takes in ' + a.takes if a.takes else ''}")
    ensure_dir(os.path.dirname(os.path.abspath(a.out)))
    with tempfile.TemporaryDirectory() as tmp:
        tiles = [cell(os.path.join(a.stills, s), fit(s), os.path.join(tmp, f"s{i:03d}.png"), tmp)
                 for i, s in enumerate(stills)]
        stills = [s for s, p in zip(stills, tiles) if p]
        whole, partial = [], []
        for i, t in enumerate(takes):
            src = os.path.join(a.takes, t)
            first = cell(src, fit(t, " first"), os.path.join(tmp, f"t{i:03d}a.png"), tmp)
            try:
                last = cell(src, fit(t, " last"), os.path.join(tmp, f"t{i:03d}b.png"), tmp, last_index(src))
            except ValueError as e:
                print(f"skip {src} last cell: {e}", file=sys.stderr)
                last = None
            tiles += [first, last]
            missing = [k for k, p in (("first", first), ("last", last)) if not p]
            if missing:
                partial.append(f"{t} (no {' or '.join(missing)} cell)")
            else:
                whole.append(t)
        tiles = [p for p in tiles if p]
        if not tiles:
            sys.exit("no cell could be made; see the skip notes above")
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
    part = f", partial: {', '.join(partial)}" if partial else ""
    print(f"{len(stills)} stills, {len(whole)} takes x first/last{part}, {rows} rows -> {a.out}")


if __name__ == "__main__":
    main()

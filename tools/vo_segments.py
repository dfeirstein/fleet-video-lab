"""Print speech segments (voiced runs separated by >= 60 ms gaps) for each VO file, to time type slams and to know how
far a fixed narration bounds any tempo trim. Needs numpy.

usage: python3 tools/vo_segments.py <file>...
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg, run  # noqa: E402

SR = 16000
HOP = 0.01


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    import numpy as np  # after argparse so --help works without numpy

    for path in a.files:
        raw = run([ffmpeg(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                  text=False).stdout
        x = np.frombuffer(raw, dtype=np.float32)
        n = int(SR * HOP)
        env = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
        voiced = env > env.max() * 0.06
        segs, start, gap = [], None, 0
        for i, v in enumerate(voiced):
            if v:
                if start is None:
                    start = i
                gap = 0
            elif start is not None:
                gap += 1
                if gap >= 6:
                    segs.append((start * HOP, (i - gap + 1) * HOP))
                    start, gap = None, 0
        if start is not None:
            segs.append((start * HOP, len(voiced) * HOP))
        print(path, " ".join(f"[{s:.2f}-{e:.2f}]" for s, e in segs))


if __name__ == "__main__":
    main()

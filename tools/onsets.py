"""List the strongest onset within +-120 ms of every beat of a grid, over a time range (stdlib only).

Same onset function as tools/beat_grid.py (low-passed envelope, 10 ms hops); prints the onset time, its offset from the
grid and its strength relative to the strongest onset in the file, so cuts can be put on the score's real hits.
usage: python3 tools/onsets.py <audio> <bpm> <from_s> <to_s> [offset_s]
`offset_s` is subtracted from every time (use it when the composition advances the score by that much).
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beat_grid import onset_curve, pcm  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("bpm", type=float)
    ap.add_argument("t0", type=float)
    ap.add_argument("t1", type=float)
    ap.add_argument("offset", nargs="?", type=float, default=0.0)
    a = ap.parse_args()
    on = onset_curve(pcm(a.src))
    top = max(on) or 1.0
    beat = 60 / a.bpm
    k = math.ceil(a.t0 / beat)
    while k * beat <= a.t1:
        t = k * beat
        lo, hi = max(0, int((t + a.offset - 0.12) * 100)), min(len(on), int((t + a.offset + 0.12) * 100) + 1)
        if lo >= hi:
            break
        j = max(range(lo, hi), key=on.__getitem__)
        print(f"beat {k:3d} at {t:6.3f}: onset {j / 100 - a.offset:6.3f} ({(j / 100 - a.offset - t) * 1000:+5.0f} ms) "
              f"strength {on[j] / top:4.2f}")
        k += 1


if __name__ == "__main__":
    main()

"""Quarter-beat RMS profile of a time range, to find exactly where a hit or a stop lands. Needs numpy.

usage: python3 tools/fine_profile.py <file> <start_s> <end_s> [--bpm 120]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg, run  # noqa: E402

SR = 22050


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("start", type=float)
    ap.add_argument("end", type=float)
    ap.add_argument("--bpm", type=float, default=120.0)
    a = ap.parse_args()
    import numpy as np  # after argparse so --help works without numpy

    raw = run([ffmpeg(), "-v", "error", "-i", a.src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], text=False).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    step = 60 / a.bpm / 4
    t = a.start
    while t < a.end:
        seg = x[int(t * SR):int((t + step) * SR)]
        db = 20 * np.log10(np.sqrt(np.mean(seg ** 2) + 1e-12)) if len(seg) else -120.0
        print(f"{t:6.3f}  {db:6.1f}  " + "#" * max(0, int((db + 60) / 1.5)))
        t += step


if __name__ == "__main__":
    main()

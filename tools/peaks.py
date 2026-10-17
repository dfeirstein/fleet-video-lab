"""Find the brightest frame (YAVG) inside each media window of a take, e.g. to place a flash or a flicker on it.

usage: python3 tools/peaks.py <take.mp4> <start> <dur> [<start> <dur> ...]
Prints the media time of the peak frame per window, its YAVG and the window's minimum.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("take")
    ap.add_argument("windows", nargs="+", type=float, help="start dur pairs, in media seconds")
    a = ap.parse_args()
    if len(a.windows) % 2:
        sys.exit("windows come in <start> <dur> pairs")
    for i in range(0, len(a.windows), 2):
        ms, d = a.windows[i], a.windows[i + 1]
        # signalstats/metadata print at INFO: never add -v error here or the list comes back empty
        out = subprocess.run([ffmpeg(), "-hide_banner", "-ss", str(ms), "-t", str(d), "-i", a.take,
                              "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        ts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", out)]
        ys = [float(x) for x in re.findall(r"YAVG=([\d.]+)", out)]
        if not ys:
            sys.exit(f"no frames measured in {a.take} at {ms}+{d}")
        k = max(range(len(ys)), key=ys.__getitem__)
        print(f"{os.path.basename(a.take)} window {ms}+{d}: peak at media {ms + ts[k]:.3f} (+{ts[k]:.3f}), "
              f"YAVG {ys[k]:.1f} (min {min(ys):.1f})")


if __name__ == "__main__":
    main()

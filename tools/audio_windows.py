"""Tail proof: RMS per window over the whole file; fails on any digital-zero window or a quiet last window.

usage: python3 tools/audio_windows.py <video.mp4> [from_s] [window_s]
Prints every window from `from_s` (default 0) to the end, then PASS/FAIL. A window at -inf, or with RMS under -90 dB
(digital zero), anywhere in the file fails; so does a last window at or under -60 dB. A 0.25 s window can pass while
10 ms windows fail at the very end of a render: check the master with `... <mp4> 0 0.01`.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg  # noqa: E402

SR = 48000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("from_s", nargs="?", type=float, default=0.0)
    ap.add_argument("window_s", nargs="?", type=float, default=0.25)
    ap.add_argument("--quiet", action="store_true", help="print only the summary line and PASS/FAIL")
    a = ap.parse_args()
    win = a.window_s
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", a.src, "-vn", "-af",
                          f"aresample={SR},pan=mono|c0=0.5*c0+0.5*c1,asetnsamples=n={int(SR * win)}:p=0,"
                          "astats=metadata=1:reset=1:measure_perchannel=none,"
                          "ametadata=print:key=lavfi.astats.Overall.RMS_level",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    vals = re.findall(r"lavfi\.astats\.Overall\.RMS_level=(\S+)", err)
    if not vals:
        sys.exit(f"no audio windows measured in {a.src}")
    rms = [float("-inf") if v in ("-inf", "inf") else float(v) for v in vals]
    bad = [(round(i * win, 3), v) for i, v in enumerate(rms) if v <= -90]
    if not a.quiet:
        for i, v in enumerate(rms):
            if i * win >= a.from_s:
                print(f"{i * win:7.3f}-{(i + 1) * win:7.3f}s  {v:7.1f} dB")
    print(f"{len(rms)} windows of {win:g} s; digital-zero windows: {bad or 'none'}; last window {rms[-1]:.1f} dB")
    ok = not bad and rms[-1] > -60
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

"""Is the score at one level across sections? Per-second RMS (astats, 1 s windows) over the whole file, then ebur128
short-term loudness (3 s windows, 10 Hz) averaged in energy over each named window; prints the largest delta.

usage: python3 tools/score_level.py <audio-or-video> [...] --window 0-4 --window 4-10
Each window must be at least 3 s long (a short-term value covers the 3 s before it).
"""
import argparse
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg  # noqa: E402

SR = 48000


def rms_per_second(path):
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", path, "-vn", "-af",
                          f"aresample={SR},pan=mono|c0=0.5*c0+0.5*c1,asetnsamples=n={SR}:p=0,"
                          "astats=metadata=1:reset=1:measure_perchannel=none,"
                          "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(v) for v in re.findall(r"lavfi\.astats\.Overall\.RMS_level=(\S+)", err)]


def short_term(path):
    err = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                          "ebur128=metadata=1,ametadata=print:key=lavfi.r128.S", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    # each 100 ms frame's S closes at pts + 0.1
    return [(round(float(t) + 0.1, 3), float(s))
            for t, s in re.findall(r"pts_time:(\S+)\n\[[^\]]*\] lavfi\.r128\.S=(\S+)", err) if s not in ("-inf", "nan")]


def mean_lufs(st, a, e):
    # S at time t covers t-3..t: take the frames whose 3 s window lies wholly inside [a, e]
    vals = [s for t, s in st if a + 3.0 <= t <= e + 1e-6]
    if not vals:
        return float("nan")
    return 10 * math.log10(sum(10 ** (v / 10) for v in vals) / len(vals))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--window", action="append", required=True, help="a-b in seconds (repeatable)")
    a = ap.parse_args()
    windows = [tuple(float(v) for v in w.split("-")) for w in a.window]
    for path in a.files:
        print(f"== {path}")
        rms = rms_per_second(path)
        print("RMS per second: " + "  ".join(f"{i}:{v:.1f}" for i, v in enumerate(rms)))
        st = short_term(path)
        m = [mean_lufs(st, s, e) for s, e in windows]
        for (s, e), v in zip(windows, m):
            print(f"short-term {s:5.2f}-{e:5.2f} s: {v:6.2f} LUFS")
        ok = [v for v in m if not math.isnan(v)]
        if len(ok) > 1:
            print(f"max window delta: {max(ok) - min(ok):.2f} dB")


if __name__ == "__main__":
    main()

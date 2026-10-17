"""Measure a music bed's tempo and beat phase, and its loudness per bar (stdlib only, no numpy).

usage: python3 tools/beat_grid.py <audio> [bpm=120] [--beats 16]
Prints: the autocorrelation tempo (80-160 BPM), the beat phase (where the beats fall against a grid starting at 0),
the strongest onset near each expected beat for the first bars, and RMS dB per bar (to check the section plan).
If the beats fall N ms after the grid, advance the bed by N ms before you cut picture to it.
"""
import argparse
import array
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg, run  # noqa: E402

SR = 4000
HOP = 40  # 10 ms frames


def pcm(src, lowpass=True):
    af = ["-af", "lowpass=f=180"] if lowpass else []
    raw = run([ffmpeg(), "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), *af, "-f", "s16le", "-"],
              text=False).stdout
    return array.array("h", raw)


def onset_curve(x):
    n = len(x) // HOP
    env = [math.sqrt(sum(v * v for v in x[i * HOP:(i + 1) * HOP]) / HOP) for i in range(n)]
    return [0.0] + [max(0.0, env[i] - env[i - 1]) for i in range(1, n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("bpm", nargs="?", type=float, default=120.0)
    ap.add_argument("--beats", type=int, default=16, help="how many expected beats to list")
    a = ap.parse_args()
    on = onset_curve(pcm(a.src))
    full = pcm(a.src, lowpass=False)
    fps = SR / HOP  # 100 frames per second

    def ac(lag):
        return sum(on[i] * on[i - lag] for i in range(lag, len(on)))

    lags = range(int(fps * 60 / 160), int(fps * 60 / 80) + 1)
    scores = {lag: ac(lag) for lag in lags}
    best = max(scores, key=scores.get)
    lo, mid, hi = scores.get(best - 1, 0), scores[best], scores.get(best + 1, 0)
    off = 0.5 * (lo - hi) / (lo - 2 * mid + hi) if (lo - 2 * mid + hi) else 0  # parabola through the neighbours
    lag_s = (best + off) / fps
    print(f"tempo by autocorrelation: {60 / lag_s:.2f} BPM (beat {lag_s:.4f} s)")
    beat = 60 / a.bpm
    bins = int(round(beat * fps))
    fold = [0.0] * bins
    for i, v in enumerate(on):
        fold[int(round((i / fps) % beat * fps)) % bins] += v
    ph = max(range(bins), key=fold.__getitem__) / fps
    print(f"beat phase against a {a.bpm:g} BPM grid from 0: beats fall at {ph:.3f} s + k*{beat:.3f} s")
    print(f"strongest onset within +-60 ms of each expected beat, first {a.beats}:")
    for k in range(a.beats):
        t = k * beat
        lo_i, hi_i = max(0, int((t - 0.06) * fps)), min(len(on), int((t + 0.06) * fps) + 1)
        if lo_i >= hi_i:
            break
        j = max(range(lo_i, hi_i), key=on.__getitem__)
        print(f"  beat {k:2d} at {t:6.3f}: onset {j / fps:6.3f} ({(j / fps - t) * 1000:+4.0f} ms)")
    bar_s = 4 * beat
    print(f"RMS per {bar_s:g} s bar (full band):")
    bar = int(bar_s * SR)
    for k in range(0, len(full) // bar + 1):
        seg = full[k * bar:(k + 1) * bar]
        if not seg:
            break
        r = math.sqrt(sum(v * v for v in seg) / len(seg)) / 32768
        print(f"  bar {k + 1:2d} {bar_s * k:5.1f}-{bar_s * (k + 1):5.1f}s  {20 * math.log10(r) if r > 0 else -120:7.1f} dB")


if __name__ == "__main__":
    main()

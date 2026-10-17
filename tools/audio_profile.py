"""Print a per-half-bar loudness profile and an onset-based tempo estimate of an audio file. Needs numpy.

Use it to compare music takes against the plan's sections (where is the drop, where does the band stop).
usage: python3 tools/audio_profile.py <file> [--bpm 120]
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
    ap.add_argument("--bpm", type=float, default=120.0)
    a = ap.parse_args()
    import numpy as np  # after argparse so --help works without numpy

    raw = run([ffmpeg(), "-v", "error", "-i", a.src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], text=False).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    beat = 60 / a.bpm
    win = int(SR * beat * 2)  # half bar
    for i in range(0, len(x), win):
        seg = x[i:i + win]
        db = 20 * np.log10(np.sqrt(np.mean(seg ** 2) + 1e-12))
        t = i / SR
        print(f"{t:6.2f}s  bar {int(t / (beat * 4)) + 1:2d}  {db:6.1f} dB  " + "#" * max(0, int((db + 50) / 1.5)))
    # onset envelope -> tempo via autocorrelation
    hop = 512
    frames = np.lib.stride_tricks.sliding_window_view(x, 1024)[::hop]
    spec = np.abs(np.fft.rfft(frames * np.hanning(1024), axis=1))
    flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(axis=1)
    flux -= flux.mean()
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    fps = SR / hop
    lags = np.arange(len(ac)) / fps
    mask = (lags > 60 / 180) & (lags < 60 / 70)
    best = lags[mask][np.argmax(ac[mask])]
    print(f"tempo estimate: {60 / best:.1f} BPM")
    first = np.argmax(flux > flux.max() * 0.3) / fps
    print(f"first strong onset: {first:.3f}s")


if __name__ == "__main__":
    main()

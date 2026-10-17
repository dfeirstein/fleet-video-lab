"""Loudness master to -14 LUFS integrated, true peak under -1 dBTP; the video stream is copied untouched.

Gain + a brick-wall limiter, re-measured and corrected until within 0.05 LU, then re-checked on the ENCODED AAC file and
re-encoded if the encode moved it (loudnorm's linear mode can fall back to dynamic and miss the target).
With `content_end`, the render's audio is cut there (renders can pad the last video frame with digital zero) and the
last 0.2 s of real sound is crossfaded on, so the audio runs to an AAC-frame-exact length past the last video frame with
no zero samples at the tail. `--exact` trims the audio to the video length to the sample instead.
usage: python3 tools/master.py <render> <out.mp4> [content_end_s] [--exact] [--target -14]
"""
import argparse
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ffmpeg, ffprobe, run  # noqa: E402

SR = 48000


def measure(path, graph=None):
    """`graph` is a chain() graph over two copies of `path` ([0:a] and [1:a]); None measures `path` as it is."""
    graph = f"{graph}," if graph else "[0:a]"
    cmd = [ffmpeg(), "-hide_banner", "-i", path, "-i", path, "-filter_complex", f"{graph}ebur128=peak=true[o]",
           "-map", "[o]", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    return i, tp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("content_end", nargs="?", type=float, default=None)
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--target", type=float, default=-14.0)
    a = ap.parse_args()
    src, target = a.src, a.target

    def tail_fill():
        """The audio cut at content_end, its last 0.2 s crossfaded on, trimmed to whole AAC frames past the video."""
        if a.content_end is None:
            return "[0:a]"
        vdur = float(run([ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration",
                          "-of", "csv=p=0", src]).stdout.strip())
        n = round(vdur * SR) if a.exact else math.ceil(vdur * SR / 1024) * 1024
        e = a.content_end
        # two inputs of the same file, not asplit: an asplit branch trimmed by start reaches acrossfade empty (ffmpeg 7.1)
        return (f"[0:a]aresample={SR},atrim=end={e},asetpts=PTS-STARTPTS[a];"
                f"[1:a]aresample={SR},atrim=start={e - 0.2}:end={e},asetpts=PTS-STARTPTS[b];"
                f"[a][b]acrossfade=d=0.03:c1=tri:c2=tri,atrim=end_sample={n},")

    def chain(gain):
        return (f"{tail_fill()}aresample=192000,volume={gain:.2f}dB,alimiter=limit=0.84:attack=1:release=60:level=false,"
                "aresample=48000")

    i0, _ = measure(src)
    gain = target - i0
    for _ in range(4):
        i, tp = measure(src, chain(gain))
        if abs(i - target) <= 0.05:
            break
        gain += target - i
    for _ in range(3):
        run([ffmpeg(), "-v", "error", "-y", "-i", src, "-i", src, "-filter_complex", f"{chain(gain)}[out]",
             "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart",
             a.out])
        i, tp = measure(a.out)
        if abs(i - target) <= 0.05:
            break
        gain += target - i
    print(f"{a.out}: input {i0:.2f} LUFS, gain {gain:+.2f} dB -> {i:.2f} LUFS integrated, true peak {tp:.2f} dBFS")


if __name__ == "__main__":
    main()

"""frames.py replaces its own earlier files, three-digit indices included, and leaves the still board alone.

run: python3 -m unittest discover -s tests -v   (skips when ffmpeg or ffprobe is not on PATH)
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
sys.path.insert(0, TOOLS)
import frames  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class Own(unittest.TestCase):
    def test_own_names_match_index_100_and_up(self):
        for i in (0, 99, 100, 1234):
            self.assertTrue(frames.OWN.fullmatch(f"{i:02d}-{1.25:06.3f}s.png"), i)
        self.assertFalse(frames.OWN.fullmatch("still-board.png"))
        self.assertFalse(frames.OWN.fullmatch("1-01.250s.png"))


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not on PATH")
class Cleanup(unittest.TestCase):
    def test_stale_index_100_frame_is_removed_and_the_board_stays(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        clip, out = os.path.join(tmp, "c.mp4"), os.path.join(tmp, "frames")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=gray:s=320x180:r=24:d=1",
                        "-c:v", "mpeg4", clip], check=True)
        os.mkdir(out)
        for f in ("100-50.200s.png", "still-board.png"):  # a frame left by a longer earlier run, and the board
            open(os.path.join(out, f), "w").close()
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "frames.py"), clip, out, "--cuts", "0"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        left = sorted(os.listdir(out))
        self.assertNotIn("100-50.200s.png", left)
        self.assertIn("still-board.png", left)
        self.assertIn("00-00.200s.png", left)


if __name__ == "__main__":
    unittest.main()

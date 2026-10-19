"""still_board.py on synthetic ffmpeg inputs: the true last frame, long labels, bad entries, no takes folder.

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
import still_board  # noqa: E402

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def luma(png, x, y, w=1, h=1):
    """The brightest gray value in a w x h box of png."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-vf", f"crop={w}:{h}:{x}:{y},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return max(raw)


def board(*args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "still_board.py"), *args],
                          capture_output=True, text=True)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg/ffprobe not on PATH")
class StillBoard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.stills = os.path.join(self.tmp, "stills")
        os.mkdir(self.stills)
        ff("-f", "lavfi", "-i", "color=gray:s=320x180", "-frames:v", "1", os.path.join(self.stills, "s01.png"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_last_cell_is_frame_23_of_a_1s_24fps_clip(self):
        # every frame carries its number twice: drawn as text, and as its gray level (n x 10) for the check
        clip = os.path.join(self.tmp, "n.mp4")
        ff("-f", "lavfi", "-i", "color=black:s=320x180:r=24:d=1", "-vf",
           "format=gray,geq=lum='N*10',drawtext=text='%{n}':x=200:y=120:fontsize=48:fontcolor=white,format=yuv420p",
           "-c:v", "mpeg4", "-q:v", "1", clip)
        self.assertEqual(still_board.last_index(clip), 23)
        out = still_board.cell(clip, "n.mp4 last", os.path.join(self.tmp, "last.png"), self.tmp,
                               still_board.last_index(clip))
        self.assertAlmostEqual(luma(out, 20, 20), 230, delta=4)  # frame 23, not 22 (220)
        first = still_board.cell(clip, "n.mp4 first", os.path.join(self.tmp, "first.png"), self.tmp)
        self.assertLessEqual(luma(first, 20, 20), 4)  # frame 0

    def test_100_char_name_is_middle_ellipsized_and_fits_the_cell(self):
        for name in ("kitchen-table_take" * 6)[:92] + "-V09.png", "W" * 96 + ".png":
            self.assertEqual(len(name), 100)
            label = still_board.fit(name)
            self.assertLessEqual(still_board.width(label), still_board.ROOM)
            self.assertTrue(label.startswith(name[:4]) and label.endswith(name[-8:]) and "..." in label, label)
            self.assertTrue(still_board.fit(name, " last").endswith(".png last"))
        src = os.path.join(self.stills, name)
        shutil.copy(os.path.join(self.stills, "s01.png"), src)
        out = still_board.cell(src, still_board.fit(name, " last"), os.path.join(self.tmp, "c.png"), self.tmp)
        # the label strip's right 10 px stay black: the text ends inside the cell
        self.assertEqual(luma(out, still_board.TW - 10, still_board.TH, 10, still_board.LH), 0)

    def test_bad_entries_are_skipped_with_a_note(self):
        os.mkdir(os.path.join(self.stills, "x.png"))
        with open(os.path.join(self.stills, "y.jpg"), "w") as f:
            f.write("not an image\n")
        out = os.path.join(self.tmp, "board.png")
        r = board(self.stills, out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("x.png: not a readable image", r.stderr)
        self.assertRegex(r.stderr, r"skip \S*y\.jpg")
        self.assertIn("1 stills", r.stdout)
        self.assertTrue(os.path.isfile(out))

    def test_missing_or_empty_takes_folder_is_a_note(self):
        empty = os.path.join(self.tmp, "empty")
        os.mkdir(empty)
        for takes in (os.path.join(self.tmp, "absent"), empty):
            out = os.path.join(self.tmp, "board.png")
            r = board(self.stills, out, "--takes", takes)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"note: no takes in {takes}", r.stdout)
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()

"""still_board.py on synthetic ffmpeg inputs: the true last frame, long labels, bad entries and bad takes, no takes
folder, a TMPDIR the filter parser would choke on.

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


def board(*args, env=None):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "still_board.py"), *args],
                          capture_output=True, text=True, env=env)


def right_edge(label, tmp):
    """The rightmost lit column of label drawn the way cell() draws it (x=10, FONT px, default font), on a canvas so
    wide that nothing can clip: the real drawn width, not what survives inside the cell."""
    with open(os.path.join(tmp, "label.txt"), "w") as f:
        f.write(label)
    w = 4000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{still_board.LH}",
                          "-frames:v", "1", "-vf", f"drawtext=textfile=label.txt:expansion=none:x=10:y=8:"
                          f"fontsize={still_board.FONT}:fontcolor=white,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True, cwd=tmp).stdout
    return max((i % w for i, v in enumerate(raw) if v > 32), default=0)


def numbered_clip(path, *extra):
    """A 1 s 24 fps clip whose frame n is drawn with its number and coded as gray level n x 10."""
    ff("-f", "lavfi", "-i", "color=black:s=320x180:r=24:d=1", "-vf",
       "format=gray,geq=lum='N*10',drawtext=text='%{n}':x=200:y=120:fontsize=48:fontcolor=white,format=yuv420p",
       "-c:v", "mpeg4", "-q:v", "1", *extra, path)


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
        numbered_clip(clip)
        self.assertEqual(still_board.last_index(clip), 23)
        out = still_board.cell(clip, "n.mp4 last", os.path.join(self.tmp, "last.png"), self.tmp,
                               still_board.last_index(clip))
        self.assertAlmostEqual(luma(out, 20, 20), 230, delta=4)  # frame 23, not 22 (220)
        first = still_board.cell(clip, "n.mp4 first", os.path.join(self.tmp, "first.png"), self.tmp)
        self.assertLessEqual(luma(first, 20, 20), 4)  # frame 0

    def test_last_index_counts_decoded_frames_not_the_header(self):
        # a truncated take keeps a header (moov first) promising 24 frames; only the frames still in the file decode
        whole, cut = os.path.join(self.tmp, "whole.mp4"), os.path.join(self.tmp, "cut.mp4")
        ff("-f", "lavfi", "-i", "nullsrc=s=320x180:r=24:d=1,geq=random(1)*255:128:128", "-c:v", "mpeg4", "-q:v", "2",
           "-movflags", "+faststart", whole)
        with open(whole, "rb") as f:
            data = f.read()
        with open(cut, "wb") as f:
            f.write(data[: len(data) * 4 // 10])
        header = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=nb_frames", "-of", "csv=p=0", cut], capture_output=True, text=True).stdout
        self.assertEqual(header.strip(), "24")
        n = still_board.last_index(cut)
        self.assertLess(n, 23)
        self.assertIsNotNone(still_board.cell(cut, "cut.mp4 last", os.path.join(self.tmp, "c.png"), self.tmp, n))

    def test_100_char_name_is_middle_ellipsized_and_fits_the_cell(self):
        for name in ("kitchen-table_take" * 6)[:92] + "-V09.png", "W" * 96 + ".png", "WM" * 48 + ".png":
            self.assertEqual(len(name), 100)
            label = still_board.fit(name)
            self.assertLessEqual(still_board.width(label), still_board.ROOM)
            self.assertTrue(label.startswith(name[:4]) and label.endswith(name[-8:]) and "..." in label, label)
            self.assertTrue(still_board.fit(name, " last").endswith(".png last"))
            # drawn unclipped, the widest-glyph label still ends inside the 10 px right margin
            self.assertLessEqual(right_edge(still_board.fit(name, " last"), self.tmp), 10 + still_board.ROOM, name)
        wide = "\u6f22" * 96 + ".png"  # East Asian wide characters, one em each
        self.assertLessEqual(still_board.width(still_board.fit(wide, " last")), still_board.ROOM)
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

    def test_a_bad_take_becomes_a_skipped_cell_not_an_abort(self):
        takes = os.path.join(self.tmp, "takes")
        os.mkdir(takes)
        good = os.path.join(takes, "V01.mp4")
        numbered_clip(good)
        with open(good, "rb") as f:
            data = f.read()
        with open(os.path.join(takes, "V02.mp4"), "wb") as f:  # truncated, moov at the end: ffprobe cannot read it
            f.write(data[: len(data) // 2])
        out = os.path.join(self.tmp, "board.png")
        r = board(self.stills, out, "--takes", takes)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stderr, r"skip \S*V02\.mp4")
        self.assertIn("1 stills, 1 takes x first/last", r.stdout)
        self.assertTrue(os.path.isfile(out))

    def test_unreadable_take_metadata_is_a_partial_take(self):
        # fault injection: an ffprobe that reads the take but cannot count its frames (N/A, or a failed run)
        takes = os.path.join(self.tmp, "takes")
        os.mkdir(takes)
        numbered_clip(os.path.join(takes, "V01.mp4"))
        out = os.path.join(self.tmp, "board.png")
        for fault in ('echo N/A; exit 0', 'echo "V01.mp4: Invalid data" >&2; exit 1'):
            fake = os.path.join(self.tmp, "ffprobe")
            with open(fake, "w") as f:
                f.write(f'#!/bin/sh\ncase "$*" in *-count_frames*) {fault};; esac\nexec "{shutil.which("ffprobe")}" "$@"\n')
            os.chmod(fake, 0o755)
            r = board(self.stills, out, "--takes", takes, env={**os.environ, "FFPROBE": fake})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertRegex(r.stderr, r"skip \S*V01\.mp4 last cell: ffprobe decoded no frame")
            self.assertIn("1 stills, 0 takes x first/last, partial: V01.mp4 (no last cell)", r.stdout)
            self.assertTrue(os.path.isfile(out))

    def test_a_tmpdir_with_quote_colon_and_backslash_still_draws_labels(self):
        odd = os.path.join(self.tmp, "it's: a \\ dir")
        os.mkdir(odd)
        out = os.path.join(self.tmp, "board.png")
        r = board(self.stills, out, env={**os.environ, "TMPDIR": odd})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 stills", r.stdout)
        self.assertGreater(luma(out, 0, still_board.TH, still_board.TW, still_board.LH), 128)  # the label drew

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

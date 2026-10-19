"""Cut lint, caption window and escaping in tools/build_comp.py. Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
sys.path.insert(0, TOOLS)
import build_comp  # noqa: E402

# 120 BPM, 20 beats, cuts at beats 2, 8 and 14 (the hello-table picture)
PICTURE = [{"beat": 0, "beats": 2, "card": "HELLO,"}, {"beat": 2, "beats": 6, "take": "V01"},
           {"beat": 8, "beats": 6, "take": "V02"}, {"beat": 14, "beats": 6, "card": "TABLE."}]


def edit(captions, moves=()):
    return {"bpm": 120, "beats": 20, "picture": PICTURE, "captions": list(captions), "moves": list(moves)}


class CutLint(unittest.TestCase):
    def refused(self, e):
        with self.assertRaises(SystemExit) as cm:
            build_comp.cut_lint(e)
        return str(cm.exception.code)

    def test_inside_one_shot_passes(self):
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 3, "beats": 4, "text": "steam."}])), 0)

    def test_ending_on_the_cut_passes(self):
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 4, "beats": 4, "text": "steam."}])), 0)

    def test_straddle_is_refused_naming_caption_and_cut(self):
        msg = self.refused(edit([{"beat": 7, "beats": 2, "text": "across"}]))
        self.assertIn("'across'", msg)
        self.assertIn("straddles the cut at beat 8", msg)
        self.assertTrue(msg.endswith("cut lint: 1 straddles, 0 move overlaps, 0 out of film"))

    def test_bridged_straddle_passes(self):
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 7, "beats": 2, "text": "across", "bridge": True}])), 1)

    def test_caption_over_a_move_is_refused_even_bridged(self):
        msg = self.refused(edit([{"beat": 9, "beats": 4, "text": "light.", "bridge": True}],
                                moves=[{"beat": 12, "beats": 2}]))
        self.assertIn("overlaps the camera move at beats 12-14", msg)
        self.assertTrue(msg.endswith("cut lint: 0 straddles, 1 move overlaps, 0 out of film"))

    def test_counts_are_kept_apart(self):
        msg = self.refused(edit([{"beat": 7, "beats": 2, "text": "across"}, {"beat": 19, "beats": 2, "text": "late"},
                                 {"beat": 10, "beats": 1, "text": "moving"}], moves=[{"beat": 10, "beats": 2}]))
        self.assertIn("'late' (beats 19-21) runs outside the film", msg)
        self.assertTrue(msg.endswith("cut lint: 1 straddles, 1 move overlaps, 1 out of film"))

    def test_negative_and_zero_length_captions_are_refused(self):
        for beats, moves in ((-2, ()), (0, ()), (0, [{"beat": 9, "beats": 3}])):
            msg = self.refused(edit([{"beat": 10, "beats": beats, "text": "empty"}], moves=moves))
            self.assertEqual(msg, f"edit list: caption 'empty': 'beats' must be greater than 0, got {beats}")

    def test_non_numeric_window_is_refused(self):
        for k, v in (("beat", "3"), ("beats", None), ("beats", float("inf")), ("beat", True)):
            c = {"beat": 3, "beats": 2, "text": "odd"}
            c[k] = v
            self.assertIn(f"caption 'odd': {k!r} must be a finite number", self.refused(edit([c])))

    def test_bridge_must_be_a_boolean(self):
        for v in ("false", "true", 1, None):
            msg = self.refused(edit([{"beat": 7, "beats": 2, "text": "across", "bridge": v}]))
            self.assertEqual(msg, f"edit list: caption 'across': 'bridge' must be true or false, got {v!r}")
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 3, "beats": 2, "text": "in", "bridge": False}])), 0)
        self.refused(edit([{"beat": 7, "beats": 2, "text": "across", "bridge": False}]))

    def test_caption_next_to_a_move_passes(self):
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 9, "beats": 3, "text": "light."}],
                                                  moves=[{"beat": 12, "beats": 2}])), 0)

    def test_cli_exits_nonzero_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            e = edit([{"beat": 13, "beats": 2, "text": "across"}])
            e.update(title="t", fps=24, width=64, height=36, palette={"bg": "#000000", "fg": "#ffffff"}, font="sans-serif",
                     audio=[])
            with open(os.path.join(d, "edit.json"), "w") as f:
                json.dump(e, f)
            r = subprocess.run([sys.executable, os.path.join(TOOLS, "build_comp.py"), "--project", d],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("straddles the cut at beat 14", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(d, "index.html")))

    def test_hello_table_passes(self):
        root = os.path.join(os.path.dirname(TOOLS), "examples", "hello-table")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_comp.cut_lint(build_comp.load(root, "edit.json")), 0)


def full(captions, picture=PICTURE, beats=20):
    e = {"title": "t", "bpm": 120, "fps": 24, "width": 320, "height": 180, "beats": beats, "picture": picture,
         "palette": {"bg": "#000000", "fg": "#ffffff"}, "font": "sans-serif", "audio": [], "captions": captions,
         "moves": []}
    e["B"], e["dur"] = 0.5, beats * 0.5
    return e


class CaptionWindow(unittest.TestCase):
    def test_animatic_window_is_half_open(self):
        self.assertEqual(build_comp.enable_expr({"beat": 4, "beats": 4, "text": "x"}, 0.5), "gte(t,2.0)*lt(t,4.0)")

    def test_html_escapes_caption_and_card_text(self):
        doc = build_comp.html(full([{"beat": 0, "beats": 1, "text": "<b>salt & pepper</b>"}],
                                   picture=[{"beat": 0, "beats": 2, "card": "A < B & C"}], beats=2))
        self.assertIn("<span>&lt;b&gt;salt &amp; pepper&lt;/b&gt;</span>", doc)
        self.assertIn(">A &lt; B &amp; C</span>", doc)
        self.assertNotIn("<b>", doc)

    @unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
    def test_caption_is_gone_on_the_first_frame_after_the_cut(self):
        # 120 BPM, 24 fps: a caption at beat 4 for 4 beats ends on the cut at beat 8, t=4.0 s = frame 96
        picture = [{"beat": 0, "beats": 8, "card": "A"}, {"beat": 8, "beats": 4, "card": "B"}]
        with tempfile.TemporaryDirectory() as d:
            silence = os.path.join(d, "silence.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "6",
                            silence], check=True)
            e = full([{"beat": 4, "beats": 4, "text": "steam."}], picture=picture, beats=12)
            e["audio"] = [{"id": "s", "src": "silence.wav", "at": 0.0}]
            out = os.path.join(d, "a.mov")
            build_comp.animatic(e, d, out)

            def caption_luma(n):
                # the lower third, below the centered card type
                raw = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-vf", f"select=eq(n\\,{n})",
                                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                                     capture_output=True, check=True).stdout
                return max(raw[320 * 130:])

            self.assertGreater(caption_luma(95), 128)  # t=3.958, last frame of the shot: caption up
            self.assertLess(caption_luma(96), 40)  # t=4.0, first frame of the next shot: caption gone
            self.assertLess(caption_luma(47), 40)  # t=1.958, before the caption starts
            self.assertGreater(caption_luma(48), 128)  # t=2.0, its first frame


if __name__ == "__main__":
    unittest.main()

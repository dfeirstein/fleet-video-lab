"""Cut lint in tools/build_comp.py. Run: python3 -m unittest discover -s tests"""
import contextlib
import io
import json
import os
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
        self.assertTrue(msg.endswith("cut lint: 1 straddles"))

    def test_bridged_straddle_passes(self):
        self.assertEqual(build_comp.cut_lint(edit([{"beat": 7, "beats": 2, "text": "across", "bridge": True}])), 1)

    def test_caption_over_a_move_is_refused_even_bridged(self):
        msg = self.refused(edit([{"beat": 9, "beats": 4, "text": "light.", "bridge": True}],
                                moves=[{"beat": 12, "beats": 2}]))
        self.assertIn("overlaps the camera move at beats 12-14", msg)

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


if __name__ == "__main__":
    unittest.main()

"""tools/donecheck.py on a copy of the hello-table output: all gates met, then one poster deleted.

Needs `make demo-dry` first (it writes the output this copies). Run: python3 -m unittest discover -s tests -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "examples", "hello-table")
DONECHECK = os.path.join(ROOT, "tools", "donecheck.py")


class DoneCheck(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.isfile(os.path.join(SAMPLE, "out", "final.mp4")), "run make demo-dry first")
        self.tmp = tempfile.mkdtemp()
        self.project = os.path.join(self.tmp, "hello-table")
        shutil.copytree(SAMPLE, self.project)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def donecheck(self):
        return subprocess.run([sys.executable, DONECHECK, "--project", self.project], capture_output=True, text=True)

    def test_all_gates_met(self):
        r = self.donecheck()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("donecheck: all gates met", r.stdout)

    def test_missing_poster_is_named(self):
        with open(os.path.join(self.project, "edit.json")) as f:
            poster = json.load(f)["deliverables"]["formats"][0]["poster"]
        os.remove(os.path.join(self.project, poster))
        r = self.donecheck()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(os.path.join(self.project, poster), r.stdout)
        self.assertNotIn("all gates met", r.stdout)


if __name__ == "__main__":
    unittest.main()

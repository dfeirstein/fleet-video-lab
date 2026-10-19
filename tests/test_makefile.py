"""Every dry-* goal forces --dry-run on each paid command, even run alone with DRY= on the command line.

run: python3 -m unittest discover -s tests -v   (skips when make is not on PATH)
"""
import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@unittest.skipUnless(shutil.which("make"), "make not on PATH")
class DryGoals(unittest.TestCase):
    def test_each_dry_goal_alone_never_spends(self):
        for goal in ("dry-generate", "dry-cut", "dry-proof", "dry-board"):
            r = subprocess.run(["make", "-n", goal, "DRY=", "VOICE_ID=real"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            paid = [line for line in r.stdout.splitlines() if "tools/run_batch.py" in line or "tools/eleven.py" in line]
            self.assertEqual(len(paid), 4, (goal, r.stdout))
            for line in paid:
                self.assertTrue(line.rstrip().endswith("--dry-run"), (goal, line))


if __name__ == "__main__":
    unittest.main()

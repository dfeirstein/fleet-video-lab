"""Stillness report in tools/frames.py. Run: python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import frames  # noqa: E402


def report(times, ydif, still_seconds=1.0):
    return frames.still_report("x.mp4", times, ydif, 0.5, still_seconds)


class Stillness(unittest.TestCase):
    def test_frame_zero_is_not_a_comparison(self):
        # 24 black frames at 24 fps: signalstats emits 24 YDIF records, the first with no previous frame
        rows = report([n / 24 for n in range(24)], [0.0] * 24)
        self.assertIn("frames: 24, 23 compared with the previous frame", rows[1])
        self.assertTrue(rows[4].startswith("longest still run: 23 frames, 0.958 s (0.042-1.000 s)"), rows[4])

    def test_frame_zero_is_left_out_of_the_ydif_stats(self):
        rows = report([0, 1 / 24, 2 / 24], [99.0, 2.0, 4.0])
        self.assertEqual(rows[3], "YDIF: mean 3.000, max 4.000")

    def test_seconds_come_from_uneven_timestamps(self):
        rows = report([0, 0.04, 0.08, 2.0], [0.0, 10.0, 0.0, 0.0])
        self.assertIn("median interval 0.0400 s", rows[1])
        self.assertEqual(rows[4], "longest still run: 2 frames, 1.960 s (0.080-2.040 s)")
        self.assertEqual(rows[6], "  0.080-2.040 s  2 frames  1.960 s")

    def test_threshold_is_judged_in_seconds_not_frames(self):
        # 3 still frames that span 1.5 s pass the 1.0 s threshold; 30 dense ones over 0.6 s do not
        sparse = report([0, 0.5, 1.0, 1.5, 2.0], [0, 9, 0, 0, 0])
        self.assertEqual(sparse[5], "still windows over 1.0 s: 1")
        dense = report([n * 0.02 for n in range(31)], [0.0] * 31)
        self.assertEqual(dense[5], "still windows over 1.0 s: 0")

    def test_one_frame_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            report([0.0], [0.0])
        self.assertIn("need at least 2", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main()

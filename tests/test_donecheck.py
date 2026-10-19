"""tools/donecheck.py on a copy of the hello-table output: every gate, configuration fault and Makefile entry point.

Needs `make demo-dry` first (it writes the output this copies). Run: python3 -m unittest discover -s tests -v
"""
import builtins
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "examples", "hello-table")
DONECHECK = os.path.join(ROOT, "tools", "donecheck.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import donecheck  # noqa: E402
# make runs in ROOT; a relative PY survives a checkout whose own path has a space (the older recipes leave $(PY) bare)
MAKE_PY = "PY=" + os.path.relpath(sys.executable, ROOT)


class DoneCheck(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.isfile(os.path.join(SAMPLE, "out", "final.mp4")), "run make demo-dry first")
        self.tmp = tempfile.mkdtemp()
        self.project = os.path.join(self.tmp, "hello-table")
        shutil.copytree(SAMPLE, self.project)
        self.edit_path = os.path.join(self.project, "edit.json")
        self.final = os.path.join(self.project, "out", "final.mp4")
        # the copy carries a real-looking passing verdict (the demo's stand-in lives in VERDICT.dry-run.md)
        self.write("VERDICT.md", "PASSES\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, rel, text):
        with open(os.path.join(self.project, rel), "w") as f:
            f.write(text)

    def edit(self):
        with open(self.edit_path) as f:
            return json.load(f)

    def save(self, edit):
        with open(self.edit_path, "w") as f:
            json.dump(edit, f)

    def donecheck(self, *extra, env=None, project=None):
        return subprocess.run([sys.executable, DONECHECK, "--project", project or self.project, *extra],
                              capture_output=True, text=True, env=env)

    def assertPasses(self, r):
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("donecheck: all gates met", r.stdout)

    def assertFails(self, r, *needles):
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("all gates met", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        for n in needles:
            self.assertIn(n, r.stdout)

    def test_all_gates_met(self):
        self.assertPasses(self.donecheck())

    def test_missing_poster_is_named(self):
        poster = self.edit()["deliverables"]["formats"][0]["poster"]
        os.remove(os.path.join(self.project, poster))
        self.assertFails(self.donecheck(), os.path.join(self.project, poster))

    def test_absent_deliverables_block_names_edit_json(self):
        e = self.edit()
        del e["deliverables"]
        self.save(e)
        self.assertFails(self.donecheck(), self.edit_path, "no deliverables block")

    def test_malformed_edit_json_names_it(self):
        self.write("edit.json", "{not json")
        self.assertFails(self.donecheck(), self.edit_path, "not readable JSON")

    def test_required_size_keys(self):
        original = json.dumps(self.edit())
        for key in ("max_bytes", "width", "height"):
            for value in (None, 0):
                with self.subTest(key=key, value=value):
                    e = json.loads(original)
                    if value is None:
                        del e["deliverables"]["formats"][0][key]
                    else:
                        e["deliverables"]["formats"][0][key] = value
                    self.save(e)
                    self.assertFails(self.donecheck(), "donecheck: edit:", self.edit_path, key)

    def test_bad_types_name_edit_json_and_the_key(self):
        """Valid JSON, wrong types: each is an edit failure naming edit.json and the key, never a traceback."""
        cases = [
            ("deliverables.verdict.allowed", lambda e: e["deliverables"]["verdict"].update(allowed=[{}])),
            ("deliverables.render", lambda e: e["deliverables"].update(render=None)),
            ("deliverables.spend", lambda e: e["deliverables"].update(spend=42)),
            ("deliverables.verdict.path", lambda e: e["deliverables"]["verdict"].update(path=None)),
            ("picture", lambda e: e.update(picture=None)),
            ("deliverables.formats[0].poster", lambda e: e["deliverables"]["formats"][0].update(poster=["a.png"])),
        ]
        original = json.dumps(self.edit())
        for key, spoil in cases:
            with self.subTest(key=key):
                e = json.loads(original)
                spoil(e)
                self.save(e)
                self.assertFails(self.donecheck(), "donecheck: edit:", self.edit_path, key)

    def test_missing_still_board_is_named(self):
        board = os.path.join(self.project, "frames", "still-board.png")
        os.remove(board)
        self.assertFails(self.donecheck(), "donecheck: still board:", board)

    def test_verdict_flag_never_opens_the_real_verdict(self):
        """In process, every open() recorded: with --verdict the block's VERDICT.md is never opened."""
        real = os.path.join(self.project, "VERDICT.md")
        self.write("VERDICT.md", "FAILS\n")
        self.write("VERDICT.dry-run.md", "PASSES WITH FIXES\n")
        stand_in = os.path.join(self.project, "VERDICT.dry-run.md")
        opened, real_open = [], builtins.open

        def spy(file, *a, **k):
            opened.append(os.path.abspath(file))
            return real_open(file, *a, **k)

        argv, out = ["donecheck.py", "--project", self.project, "--verdict", stand_in], io.StringIO()
        with unittest.mock.patch.object(sys, "argv", argv), unittest.mock.patch.object(builtins, "open", spy), \
                contextlib.redirect_stdout(out):
            donecheck.main()
        self.assertIn("donecheck: all gates met", out.getvalue())
        self.assertIn(os.path.abspath(stand_in), opened)
        self.assertNotIn(os.path.abspath(real), opened)

    def test_missing_proof_key_names_edit_json(self):
        e = self.edit()
        del e["deliverables"]["formats"][0]["contact_sheet"]
        self.save(e)
        self.assertFails(self.donecheck(), self.edit_path, "contact_sheet")

    def test_allowed_rejects_failing_words(self):
        for allowed in (["FAILS"], ["PASSES", "DO NOT SHIP"], []):
            with self.subTest(allowed=allowed):
                e = self.edit()
                e["deliverables"]["verdict"]["allowed"] = allowed
                self.save(e)
                self.write("VERDICT.md", (allowed or ["FAILS"])[-1] + "\n")
                self.assertFails(self.donecheck(), "donecheck: edit:", self.edit_path, "allowed")

    def test_wrong_dimensions(self):
        e = self.edit()
        e["deliverables"]["formats"][0]["width"] = 1920
        self.save(e)
        self.assertFails(self.donecheck(), "donecheck: master wide:", self.final, "want 1920x720")

    def test_size_at_and_over_the_limit(self):
        size = os.path.getsize(self.final)
        e = self.edit()
        e["deliverables"]["formats"][0]["max_bytes"] = size
        self.save(e)
        self.assertPasses(self.donecheck())
        e["deliverables"]["formats"][0]["max_bytes"] = size - 1
        self.save(e)
        self.assertFails(self.donecheck(), self.final, f"over max_bytes {size - 1}")

    def test_two_formats(self):
        e = self.edit()
        second = dict(e["deliverables"]["formats"][0], name="copy", final="out/copy.mp4")
        e["deliverables"]["formats"].append(second)
        self.save(e)
        copy = os.path.join(self.project, "out", "copy.mp4")
        self.assertFails(self.donecheck(), "donecheck: master copy:", copy)
        shutil.copy(self.final, copy)
        self.assertPasses(self.donecheck())
        second["height"] = 1080
        self.save(e)
        self.assertFails(self.donecheck(), "donecheck: master copy:", copy, "want 1280x1080")

    def test_invalid_verdict_line_names_the_verdict_file(self):
        for line in ("FAILS", "PASSES!", "passes"):
            with self.subTest(line=line):
                self.write("VERDICT.md", line + "\nfindings\n")
                self.assertFails(self.donecheck(), os.path.join(self.project, "VERDICT.md"), repr(line))

    def test_verdict_flag_reads_another_file(self):
        self.write("VERDICT.md", "FAILS\n")
        self.write("VERDICT.dry-run.md", "PASSES WITH FIXES\n")
        stand_in = os.path.join(self.project, "VERDICT.dry-run.md")
        self.assertPasses(self.donecheck("--verdict", stand_in))
        self.assertFails(self.donecheck(), os.path.join(self.project, "VERDICT.md"))

    def test_ffprobe_missing_or_failing(self):
        for probe in (os.path.join(self.tmp, "no-such-ffprobe"), shutil.which("false") or "/usr/bin/false"):
            with self.subTest(probe=probe):
                env = dict(os.environ, FFPROBE=probe)
                self.assertFails(self.donecheck(env=env), "donecheck: master wide:", "ffprobe", probe, self.final)

    def test_project_path_with_a_space(self):
        spaced = os.path.join(self.tmp, "hello table")
        os.rename(self.project, spaced)
        self.assertPasses(self.donecheck(project=spaced))
        r = subprocess.run(["make", "-s", "-C", ROOT, "donecheck", MAKE_PY, f"P={spaced}"],
                           capture_output=True, text=True)
        self.assertPasses(r)
        os.remove(os.path.join(spaced, "frames", "poster.png"))
        r = subprocess.run(["make", "-s", "-C", ROOT, "donecheck", MAKE_PY, f"P={spaced}"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)  # make reports the recipe's exit 1 as 2
        self.assertIn(os.path.join(spaced, "frames", "poster.png"), r.stdout)


class DemoDry(unittest.TestCase):
    """make demo-dry on a fresh copy of the sample: an existing VERDICT.md that says FAILS, made unreadable for the
    run, is never read and survives byte for byte."""

    def test_demo_dry_never_touches_a_real_verdict(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        project = os.path.join(tmp, "film")
        os.mkdir(project)
        for name in ("BRIEF.md", "SHOTS.md", "edit.json", "music-plan.json"):
            shutil.copy(os.path.join(SAMPLE, name), project)
        real = b"FAILS\n\nF1 high 0:03 the cup melts at the cut (frames/cut-02.png). Re-roll V02.\n"
        verdict = os.path.join(project, "VERDICT.md")
        with open(verdict, "wb") as f:
            f.write(real)
        # unreadable for the whole run: any tool that opens it (to read or to write) fails, and the run with it
        os.chmod(verdict, 0)
        self.addCleanup(os.chmod, verdict, 0o644)
        if os.geteuid() != 0:  # root ignores the mode bits; the in-process open() spy test covers that case
            self.assertFalse(os.access(verdict, os.R_OK))
        before = os.stat(verdict)
        r = subprocess.run(["make", "-C", ROOT, "demo-dry", MAKE_PY, f"P={project}"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-3000:])
        self.assertIn("donecheck: all gates met", r.stdout)
        self.assertNotIn(verdict + ": not readable", r.stdout)
        after = os.stat(verdict)
        self.assertEqual((after.st_mode, after.st_size, after.st_mtime_ns), (before.st_mode, before.st_size,
                                                                              before.st_mtime_ns))
        os.chmod(verdict, 0o644)
        with open(verdict, "rb") as f:
            self.assertEqual(f.read(), real)
        self.assertTrue(os.path.isfile(os.path.join(project, "VERDICT.dry-run.md")))


if __name__ == "__main__":
    unittest.main()

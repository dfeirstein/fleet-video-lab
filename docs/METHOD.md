# METHOD: how a film gets made here

The tools are the easy part. This is the discipline that made the films come out well, and kept the spend honest.

## 1. The making-of is written as you go, not after

Every film keeps a `MAKING-OF.md` in its project folder, in this order:

1. **Concept, three ways.** Three concepts that differ in kind (object/physical, typographic/rhythmic, narrative),
   each with the risk that would make it read as generated. Pick one and say why.
2. **Direction, locked before any generation.** Aesthetic, palette (hex), typefaces, tempo (BPM, beat and bar in
   seconds, how many bars make the length), the music direction with its negatives, the exact VO lines.
3. **Sound first.** Make the music bed before the shots. Profile every take (`tools/audio_profile.py`,
   `tools/beat_grid.py`) and pick the one whose structure helps the story. Accidents in the music (a stop, a swell)
   are often the best gag in the film; cut picture to the bed, not the other way round.
4. **Shot list** (`SHOTS.md`): one row per still and per job, with the prompt verbatim. One house-look paragraph
   and one list of universal negatives, applied to every prompt.
   - **Locked attributes.** Under the house look, one table per recurring subject (a person, a vehicle, an object,
     a set) listing the attributes that must not change across takes: make and trim, wardrobe, hair, which side a
     door hinges, how many of a thing there are. Add a DO NOT COPY line for any reference: what must not be
     lifted from it (its subjects, logos, copy, people). A generator drifts a car make or an outfit between takes;
     code never does, so this table matters most for generated footage. Keep these tables at three columns:
     `run_batch.py` reads any two-column row whose first cell starts with `s` as a still to generate.
   - **The still board is a gate.** `tools/still_board.py stills/ frames/still-board.png` puts every start still
     side by side (with `--takes`, also the first and last frame of each kept take). It is approved, by the person
     or by a judge against the locked table, before `run_batch.py` spends a credit on a take. A still costs pennies;
     a take is a billed job. See `examples/hello-table/SHOTS.md` for a filled table.
5. **Rejected takes and why.** Every take that is not in the cut, with the reason in one line.
6. **"What I would fix" after watching it,** ranked. Fix the top three before calling it done.
7. **Residual risks.** What could still read as generated, said plainly.
8. **Rounds.** Each critic round gets its own section: finding id, what was done, where in the film, status.

## 2. Spend: quote, cap, log, never re-submit

- **Every paid call is quoted first and logged.** `tools/hf_shot.py` reads the account, quotes the job, checks the
  cap, runs it, reads the account again and logs the delta. `tools/eleven.py` and `tools/gpt_image.py` log every
  call. `tools/spend_report.py` turns the ledgers into `SPEND.md`.
- **Credits are metered and a take is one job.** Seedance has no "takes" count: one job is one take, billed at
  submit. Set a cap per film and a hard stop below it (`--cap`, `--stop`) and report when you reach the stop.
- **Run jobs serially** (`tools/run_batch.py`), so each before/after delta belongs to one job.
- **Never re-submit a pending job.** A job can sit `in_progress` for 15+ minutes. Poll
  `higgsfield --json generate list` instead. A re-submit is a second bill.
- **Dry-run first.** `--dry-run` on every generation tool makes ffmpeg placeholders of the right shape, so the
  whole cut, master and proof chain can be checked before a credit is spent.

## 3. Proof: frames and numbers, not adjectives

A claim about the film is either measured or marked `unverified:`.

- **The master:** `ffprobe` the file (duration, size, fps, codecs) and quote the line.
- **Loudness:** `tools/master.py` targets -14 LUFS integrated, true peak under -1 dBTP, and re-measures the
  ENCODED file (the AAC encode moves loudness about 0.1 LU).
- **The tail:** renders can pad the last video frame with digital zero. Master with `content_end`, then
  `tools/audio_windows.py <master> 0 0.01` must print PASS: a 0.25 s window can pass while 10 ms windows fail.
- **Frames:** `tools/frames.py --edit edit.json` puts a labelled frame just after every cut, a contact sheet, dense
  strips of the fast stretches, and the true last frame. Judge at 1:1 on the graded final render at its real fps,
  never on a coarse strip.
- **The judge cannot listen.** Sound claims are measured (`ebur128`, `astats`, `tools/score_level.py`,
  `tools/onsets.py`), or marked unverified.

## 4. The critic loop: the judge is never the maker

1. The maker finishes a round and writes the making-of, SPEND.md and the proof.
2. A **separate** agent (or person), read-only, judges the master against one question: *could any of this read as
   generated, or as careless?* It extracts its own frames and measurements; it does not trust the maker's notes.
   The maker's build script (`edit.json`, `tools/build_comp.py`) is the truth for what is in the cut, not the
   shot list or the making-of.
3. The verdict file's first line is the bare verdict (`PASSES`, `PASSES WITH FIXES`, `FAILS`), then findings, each
   with an id, a severity, a time in the film, evidence (frame file, number) and a proposed fix. The judge still
   reports EVERY finding (under-reporting is the failure mode), and ends the file with a ranked `## Top 3`: the
   three findings, by id, that most hurt the film.
4. **Repair is bounded.** In the next round the maker fixes the Top 3 plus any regression the verdict names, and
   nothing else: touch only the sections of the cut those findings name, and re-render proof only around them
   (`tools/frames.py <master> frames --dense-only --dense <t-1>-<t+1>` for a finding at time t: it writes just
   that strip and leaves every other file in `frames/`, the still board included). The Top 3 is the must-fix set,
   not the whole verdict: the maker answers every finding by id (fixed, accepted, rejected, or deferred), and
   hands the deferred and residual findings to the person as a list. In the round's table that is: fixed (how,
   where), accepted (why), rejected (with evidence), or deferred (not in this round's Top 3). Each repair goes
   back to the step that made the defect and passes that step's gate again: identity or physical defects to stills
   (step 4) or takes (step 5), composition defects to the cut (step 6). (Steps are the rows of SKILL.md's workflow
   table.) Re-rolls are judged against the cut's timing, not only on looks.
5. **Stop rule.** Stop when a verdict has no HIGH finding, or at the round cap stated in the brief (default 4
   rounds), or when the budget stops it. Hand whatever is left to the person as a list, not another round.

**Done means `tools/donecheck.py --project <dir>` prints `donecheck: all gates met`,** never that the last command
exited 0. A render can exit 0 with the wrong size, a missing poster or no verdict. The project's `edit.json` lists
its deliverables (per format: the final at its width, height and maximum size, a poster, first and last frames, a
contact sheet; then SPEND.md and the verdict file, whose line 1 must be `PASSES` or `PASSES WITH FIXES`), and the
done-check walks them in gate order and names the first one missing, so a round resumes from that gate.

### A neutral rubric for the judge

| Area | Ask |
|---|---|
| Physics | Do objects keep their shape, count and contact? Any self-drawing cracks, melting edges, sliding feet? |
| Identity | Is every recurring object/person the same across cuts? Check BOTH sides of each cut in full frames. |
| Motion | Any judder (24 fps takes in a 30 fps render), motion on twos, unmotivated drift? |
| Type | Legible at 1:1 (measure cap height in pixels), on the beat, never melting or morphing? |
| Cut | Every cut on the grid it claims (frame-accurate), no one-frame flashes the edit did not ask for? |
| Sound | Level steady across sections, no digital zero, VO intelligible over the bed, SFX on their frames? |
| Ending | Does the last frame hold, and does real sound run to the end of the file? |

## 5. Generic gotchas (each one cost a round somewhere)

- **24 fps takes in a 30 fps render judder.** Render at the takes' native rate (`--fps 24`).
- **Digital zero at the end of the render.** Master with `content_end` and check 10 ms windows.
- **ffmpeg 7.1: an `asplit` branch trimmed by start reaches `acrossfade` empty.** Feed the same file twice as two
  inputs instead (`tools/master.py` does).
- **loudnorm's linear mode can silently fall back to dynamic.** Use gain + a limiter, re-measured.
- **Never put `-v error` on a showinfo / signalstats / ametadata pass.** Those print at INFO; you get an empty list.
- **Scene-score cuts miss same-colour cuts and count one-frame flashes.** Reconcile against the edit list; use a
  lower threshold (0.2) for dark-to-dark cuts.
- **`-ss` before `-i` restarts pts at 0.** Add `setpts=PTS+<start>/TB` before `drawtext` or the labels lie.
- **`f%03d.jpg` starts at f001 = frame 0.** Frame n is file n+1; name proof frames by time instead.
- **Grab a last frame with `-ss <t> -update 1`,** not `-sseof` (it can leave a stale PNG).
- **Seedance ignores fine partial-motion prompts** ("only the top fifth lifts"). Plan the cut around what the take
  does, and check the footage length after the key moment before deciding a re-roll fits at 1x.
- **Lock identity to a frame pulled from the KEPT take,** and pass it both as the still's edit reference and as
  `--ref` (Seedance `--image-references`). Match the frame, not a critic's description of it.
- **Fixed narration bounds every tempo trim.** Measure VO extents (`tools/vo_segments.py`) before promising cuts.
- **To shorten a section, cut the music bed on beat boundaries** (atrim with 6 ms fades) and re-time the beats to
  the edited bed.
- **Keep grade and flicker layers below the type layer** in the composition, or the type tints for frames.
- **Renders leave state behind** (`.hyperframes/`, `renders/`, `.transcode-cache/`); keep them ignored. The
  `.hyperframes/` state holds absolute local paths: never commit it.
- **A Seedance batch outlives a turn** (3-4 min per job). An agent should wait in-turn on the job log, not end
  the turn mid-batch.

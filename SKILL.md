---
name: fleet-video-lab
description: >-
  Make short generated films (10-30 s) end to end: GPT image start stills, Seedance 2.5 takes through the
  Higgsfield CLI, ElevenLabs music/VO/SFX, a beat-locked Hyperframes cut, a -14 LUFS master, and proof by frames
  and ffprobe. Invoke when asked to make, cut, master, judge or fix a generated video, promo, sizzle or ad.
  Every paid call is quoted, capped and logged; every tool has a keyless --dry-run.
---

# fleet-video-lab

A small studio of command-line tools plus the method that made them work: sound first, cut on the beat, quote
and log every generation, prove the result with frames and numbers, and let a separate judge decide when it is
done. Tools live in `tools/`; the method is `docs/METHOD.md`; setup is `docs/SETUP.md`.

## When to use
- Someone wants a short film, promo, ad or sizzle made from generated footage, voice and music.
- A cut exists and needs mastering, proof frames, a loudness check, or a critic pass.
- Not for: editing real camera footage at length, or a single still image (use an image tool directly).

## Install
- `npx skills add dfeirstein/fleet-video-lab -g` (Claude Code, so every Fleet worker on the machine).
- Or `git clone https://github.com/dfeirstein/fleet-video-lab ~/.claude/skills/fleet-video-lab`.
- Then `python3 tools/doctor.py` from the skill folder and add the keys it lists (`docs/SETUP.md`).

## Before anything
1. `python3 tools/doctor.py` and read it. Missing keys: ask for them (Fleet: `fleet-ctl secret request <NAME> --dest env`).
2. `make demo-dry` once on a new machine: the whole pipeline with placeholders, no keys, no spend.
3. Agree the budget: a Higgsfield credit cap for the film (and a hard stop below it).

## The workflow
Make a project folder (copy `examples/hello-table/`), then work the steps in order. Each row ends at its gate;
the gates run in this order: references and assets; style guide and shot list; representative stills; rough cut
and contact sheet; top-3 repair; audio, formats, deliverables.

| Step | Do | Tool | Gate |
|---|---|---|---|
| 1. Brief | `BRIEF.md`: length, format, fps, BPM (beat and bar in seconds), concept chosen from three, look, palette, VO lines, budget, round cap (default 4) | by hand | references and assets approved; DO NOT COPY written |
| 2. Sound | music bed first (plan on the BPM grid), profile the takes, pick one; then VO and SFX | `eleven.py music/tts/sfx`, `audio_profile.py`, `beat_grid.py`, `onsets.py`, `vo_segments.py` | the bed is chosen before any picture |
| 3. Shots | `SHOTS.md`: stills table + jobs table, one house look, universal negatives, a locked-attributes table per recurring subject | by hand | style guide and shot list approved |
| 4. Stills | the start stills only, one `gpt_image.py` call per row of the stills table; then the board (`make still-board`) | `gpt_image.py`, `still_board.py` | Gate: the still board is approved (by the person, or by a judge against the locked table) before `run_batch.py` spends a credit |
| 5. Takes | the Seedance jobs, serially, quoted and logged; re-run the board with `--takes` | `run_batch.py` (-> `hf_shot.py`), `still_board.py --takes` | every kept take's first and last frame still match the locked table |
| 6. Comp | `edit.json`: picture in BEATS, sound in seconds, captions that never straddle a cut (or `bridge: true`); write the composition (+ an ffmpeg animatic) | `build_comp.py`, `peaks.py` | rough cut (the animatic) and its contact sheet (`frames.py`) reviewed |
| 7. Render | at the takes' native rate | `npx hyperframes@0.8.169 render <dir> -o out/render.mp4 --quality delivery --fps 24` | |
| 8. Master | -14 LUFS, true peak < -1 dBTP, real sound to the last sample | `master.py <render> out/final.mp4 <content_end_s>` | |
| 9. Proof | ffprobe line, 10 ms tail windows PASS, frames on every cut, the longest still run, section levels, SPEND.md | `audio_windows.py ... 0 0.01`, `frames.py --edit --stillness`, `score_level.py`, `spend_report.py` | |
| 10. Critic | a SEPARATE read-only judge reports every finding and ends with a ranked `## Top 3`; the maker fixes those plus any regression, only there. The Top 3 is the must-fix set, not the whole verdict: the maker answers every finding by id (fixed, accepted, rejected, or deferred), and hands the deferred and residual findings to the person as a list. Each repair goes back to the step that made the defect and passes that step's gate again: identity or physical defects to stills (step 4) or takes (step 5), composition defects to the cut (step 6). | `docs/METHOD.md` section 4 | top-3 repair; stop at no HIGH finding, the round cap, or the budget, and hand what is left to the person as a list |
| 11. Deliver | after the last round: loudness and the 10 ms tail re-checked on the final master, every format and deliverable on disk | `audio_windows.py`, `score_level.py`, `spend_report.py` | audio, formats, deliverables |

## Commands
```bash
python3 tools/doctor.py [--strict]                     # what is missing and where to set it
python3 tools/run_batch.py --project P --cap 1000 [--dry-run]
python3 tools/hf_shot.py V01 stills/s01.png 4 "<prompt>" --project P --cap 1000 [--stop 800] [--ref still.png]
python3 tools/eleven.py music music-plan.json audio/music.mp3 --project P [--seed 7]
python3 tools/eleven.py tts <voice_id> "<line>" audio/vo-1.mp3 --project P
python3 tools/gpt_image.py s01 "<prompt>" --project P [--size 1536x1024]
python3 tools/build_comp.py --project P [--animatic out/render.mov]
python3 tools/master.py P/out/render.mp4 P/out/final.mp4 <content_end_s>
python3 tools/audio_windows.py P/out/final.mp4 0 0.01
python3 tools/frames.py P/out/final.mp4 P/frames --edit P/edit.json [--dense 12-16] [--dense-only] [--stillness]
python3 tools/still_board.py P/stills P/frames/still-board.png [--takes P/takes/video]
python3 tools/spend_report.py --project P --cap 1000 --used V01,V02
node tools/capture.mjs page.html out.png 1920 1080    # 1:1 proof of a card or page
bash tools/scan_private.sh                            # before every push
```
Every tool answers `--help` without keys. A missing key fails with one line: `set ELEVENLABS_API_KEY (...)`.

## Keys
| Name | Used by | Where |
|---|---|---|
| Higgsfield login | `hf_shot.py`, `run_batch.py` | `higgsfield auth login` (the CLI keeps its own token) |
| `ELEVENLABS_API_KEY` | `eleven.py` | env var |
| `OPENAI_API_KEY` | `gpt_image.py` | env var, or skip it and make stills with the gpt-image MCP into `stills/` |
Keys come from the environment only and are never printed or committed.

## Rules that are not optional
- **Quote and log every generation job.** `hf_shot.py` quotes, checks the cap, runs, and logs the before/after
  delta; `eleven.py` and `gpt_image.py` log every call. SPEND.md is generated from the ledgers, never typed.
- **Credits are metered; one job is one take, billed at submit.** Run jobs serially. Never re-submit a pending
  job: poll `higgsfield --json generate list`. Stop at the hard stop and report.
- **Dry-run before you spend.** `--dry-run` everywhere makes placeholders of the right shape.
- **Proof by frames and ffprobe.** Every claim about the film is a frame file, a number, or marked `unverified:`.
  Judge on the final graded render at its native fps, at 1:1.
- **The judge is never the maker.** A separate read-only reviewer issues the verdict; the edit list
  (`edit.json`), not the making-of, is the truth for what is in the cut.
- **Sound first, cut on the grid.** Picture events are placed in beats so the cut cannot drift off the music.
- Read `docs/METHOD.md` section 5 (the gotchas) before the first render.

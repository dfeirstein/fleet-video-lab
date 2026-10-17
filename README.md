# fleet-video-lab

A video studio as a skill: command-line tools and a working method for making short generated films (10-30 s)
with **GPT image** stills, **Seedance 2.5** takes through the **Higgsfield CLI**, **ElevenLabs** music, voice and
sound effects, a beat-locked **Hyperframes** cut, and **ffmpeg** for mastering and proof.

It loads as a skill in Fleet and Claude Code ([SKILL.md](SKILL.md) at the root), and every tool also runs on its
own from a shell.

What makes it different from a pile of API scripts is the discipline built into the tools:

- every paid generation is **quoted, capped and logged** before and after it runs;
- every generation tool has a **`--dry-run`** that makes placeholders, so you can run the whole pipeline before
  spending anything;
- the cut is placed **in beats**, so picture cannot drift off the music;
- "done" means **proof**: an ffprobe line, a 10 ms tail check, frames on every cut, a SPEND.md, and a verdict from a
  judge who is not the maker ([docs/METHOD.md](docs/METHOD.md)).

## 5-minute start

```bash
git clone https://github.com/dfeirstein/fleet-video-lab && cd fleet-video-lab
python3 -m venv .venv && . .venv/bin/activate   # optional, keeps numpy out of your system Python
pip install -r requirements.txt   # numpy, for the proof step (make demo-dry stops with this line if it is missing)
python3 tools/doctor.py        # what you have, what is missing, where to set it
make demo-dry                  # the sample film end to end: no keys, no spend (needs python3 + numpy + ffmpeg)
```

`make demo-dry` builds `examples/hello-table/` (a 10 s film: two shots, two type cards, music, one VO line, one
SFX) from ffmpeg placeholders, writes the Hyperframes composition and an ffmpeg animatic, masters it to -14 LUFS,
checks the tail at 10 ms, writes a contact sheet and SPEND.md. Look at `examples/hello-table/frames/contact-sheet.png`
and `examples/hello-table/out/final.mp4`.

Then, with keys set:

```bash
make render                                   # optional: render the composition with Hyperframes (Node 22 + Chrome)
VOICE_ID=<an ElevenLabs voice id> make demo   # the real sample: quotes every job first, cap 200 credits
```

## Keys

| | For | Set |
|---|---|---|
| Higgsfield login | Seedance takes | `higgsfield auth login` |
| `ELEVENLABS_API_KEY` | music, VO, SFX | env var (Fleet: `fleet-ctl secret request ELEVENLABS_API_KEY --dest env`) |
| `OPENAI_API_KEY` | start stills | env var, or make stills with the gpt-image MCP instead |

Keys are read from the environment only, never printed, never committed. Details and version pins:
[docs/SETUP.md](docs/SETUP.md).

## What a 30 s film costs

Measured, not promised: your account's quote is the truth, and the tools print it before every job.

- **Seedance 2.5 (Higgsfield credits):** on 2026-10-17 a 4 s 1080p take quoted **64 credits** (16 per second). A
  30 s film typically needs 10-14 takes of 4-5 s once rejects and one re-roll round are counted, so plan for
  roughly **650-1,100 credits**, and set the cap (`--cap`) before the first job. The four films this method came
  from spent between about 200 and 2,000 credits each.
- **GPT image:** one start still per take plus a few rejects, 10-20 calls (check OpenAI's current image pricing).
- **ElevenLabs:** 2-3 music takes, 4-8 VO lines, a handful of SFX: well inside a starter plan's monthly quota.
- **Your time:** sound and shot planning is most of it; the tools make the rest fast.

The sample film (`make demo`) is 2 takes: about **128 credits**, 2 stills, 3 ElevenLabs calls.

## What is in here

```
SKILL.md                the skill: when to use it, the workflow, commands, keys, the rules
tools/                  the pipeline (run any tool with --help)
  doctor.py             dependency + key report         run_batch.py  stills then takes, serially
  gpt_image.py          start stills                    hf_shot.py    one Seedance take, quoted + capped + logged
  eleven.py             music / TTS / SFX               build_comp.py edit.json -> Hyperframes HTML (+ animatic)
  master.py             -14 LUFS master, clean tail     audio_windows.py  digital-zero / tail proof
  frames.py             cut frames, contact sheet       beat_grid.py, onsets.py, audio_profile.py, fine_profile.py
  score_level.py        section loudness                vo_segments.py, peaks.py, spend_report.py, capture.mjs
  scan_private.sh       privacy scan, run before every push
  local/keychain_env.sh optional macOS Keychain -> env adapter (local only)
examples/hello-table/   the 10 s sample: BRIEF.md, SHOTS.md, edit.json, music-plan.json
docs/                   SETUP.md, METHOD.md, PORTING.md
```

## Credits

The tools and method were developed making four private 30-second films with Fleet workers and Claude Code; this
repo carries the generic parts only (see [docs/PORTING.md](docs/PORTING.md)). Built on
[Higgsfield CLI](https://github.com/higgsfield-ai/cli), [ElevenLabs](https://elevenlabs.io),
[Hyperframes](https://github.com/heygen-com/hyperframes), [GSAP](https://gsap.com) and [FFmpeg](https://ffmpeg.org).

MIT licensed: see [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).

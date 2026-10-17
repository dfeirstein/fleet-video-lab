# PORTING: what came from the private studio, and what did not

fleet-video-lab was cut from a private scratch studio that made four 30-second client films. Every file in its
`tools/` and its `capture.mjs` was classified:

- **GENERIC** ships, ported: relative paths, binaries from PATH, keys from env vars, `--help` without keys, a
  one-line `set NAME` failure, and a `--dry-run` on every generation tool.
- **SPLIT** a generic core inside a film script: the core was extracted and the film's content left behind.
- **FILM-SPECIFIC** does not ship: it names a client or hardcodes one film's shots, timings or proofs.

Client and project names are redacted below on purpose (`<client-a>`, `<client-b>`);
they are private brand material.

| Source file | Decision | Shipped as / why not |
|---|---|---|
| `capture.mjs` | GENERIC | `tools/capture.mjs`; Chrome from `$CHROME` or the platform default; `--help` added |
| `tools/audio_profile.py` | GENERIC | same name; hardcoded 128 BPM became `--bpm`; ffmpeg from PATH |
| `tools/audio_windows.py` | GENERIC | same name; default `from_s` 0 (was one film's tail), `--quiet` added |
| `tools/beat_grid.py` | GENERIC | same name; bar length follows the BPM (was a fixed 2 s); `--beats` |
| `tools/build_comp.py` | SPLIT | same name: the beat-locked composition writer, now driven by `edit.json`; adds an ffmpeg animatic. The film's shots, cards and timings stayed behind |
| `tools/build_<client-a>_noir.py` | FILM-SPECIFIC | one film's edit list and layouts |
| `tools/build_fleet_ad.py` | FILM-SPECIFIC | one ad's two compositions (its "build once, lay out twice" idea is in `docs/METHOD.md`) |
| `tools/build_<client-b>.py` | FILM-SPECIFIC | one film's edit list |
| `tools/build_<client-b>_call_it.py` | FILM-SPECIFIC | one film's edit list |
| `tools/build_r3j.py` | FILM-SPECIFIC | an 8 s clip for one ad |
| `tools/door_strip.py` | FILM-SPECIFIC | a one-round hinge gate for one film's car doors (the frame-strip idea is in `frames.py --dense`) |
| `tools/<client-a>_audio.py` | FILM-SPECIFIC | one film's stem prep |
| `tools/<client-a>_shots.py` | FILM-SPECIFIC | one film's job list (generic runner: `run_batch.py`) |
| `tools/eleven.py` | GENERIC | same name; key check is a one-line `set ELEVENLABS_API_KEY`; music/sfx/tts dry-run placeholders; log under the project |
| `tools/fine_profile.py` | GENERIC | same name; `--bpm` |
| `tools/fleet_ad_audio.py` | FILM-SPECIFIC | one ad's stem prep |
| `tools/fleet_ad_bars.py` | FILM-SPECIFIC | one ad's per-bar check (generic: `beat_grid.py`, `score_level.py`) |
| `tools/fleet_ad_frames.py` | FILM-SPECIFIC | one ad's frames (generic: `frames.py`) |
| `tools/fleet_ad_probe.mjs` | FILM-SPECIFIC | reads one composition's private camera log |
| `tools/fleet_ad_sound.py` | FILM-SPECIFIC | one ad's ElevenLabs call list |
| `tools/fleet_ad_sound.sh` | FILM-SPECIFIC | read a key from a personal Keychain (replaced by env vars + optional `tools/local/keychain_env.sh`) |
| `tools/frames.py` | SPLIT | same name; cut times from `--edit`, `--cuts` or `--every` (were four films' hardcoded lists); `--dense`, `--vertical`, true last frame |
| `tools/hf_shot.py` | SPLIT | same name; the quote -> cap -> create -> delta -> ledger core with `--cap`, `--stop`, `--aspect`, `--ref`, `--dry-run`. The per-film/per-round caps stayed behind |
| `tools/<client-b>_audio.py` | FILM-SPECIFIC | one film's stem prep |
| `tools/<client-b>_shots.py` | FILM-SPECIFIC | one film's job list |
| `tools/<client-b>_two_phones_audio.py` | FILM-SPECIFIC | one film's stem prep |
| `tools/master.py` | GENERIC | same name; `exact` became `--exact`, `--target` added |
| `tools/onsets.py` | GENERIC | same name; shares the onset function with `beat_grid.py` |
| `tools/peaks.py` | GENERIC | same name; takes a file path (was a fixed takes folder) |
| `tools/r3j_contact.py` | FILM-SPECIFIC | one clip's proof sheet |
| `tools/r8_proof.py` | FILM-SPECIFIC | one round's proof images |
| `tools/run_batch.py` | GENERIC | same name; also makes the planned stills; `--project`, `--cap`, `--dry-run` |
| `tools/score_level.py` | SPLIT | same name; the windows are `--window a-b` (were one film's three sections) |
| `tools/spend_report.py` | GENERIC | same name; reads all three ledgers, `--cap`, marks dry-run rows |
| `tools/vo_segments.py` | GENERIC | same name |

New in this package (no source file): `tools/doctor.py`, `tools/gpt_image.py` (the source made stills through an
MCP server, by hand), `tools/scan_private.sh`, `tools/local/keychain_env.sh`, `tools/_common.py`.

Totals: 35 source files: 12 GENERIC, 4 SPLIT, 19 FILM-SPECIFIC. 16 ported tools ship, plus 5 new files.
Not carried over at all: the films, takes, renders, cast and brand stills, captions and post copy, the per-film
making-of and spend records, the studio's own rules file, and its intent docs.

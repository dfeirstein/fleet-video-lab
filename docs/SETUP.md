# SETUP

Start with `python3 tools/doctor.py`: it lists every dependency, what it found, how to get what is missing and
where to set it. It always exits 0 in report mode; `--strict` exits 1 when something a real film needs is missing.

## What you need

| Need | For | Get it | Set it |
|---|---|---|---|
| python3 >= 3.10 | every tool | python.org / package manager | PATH |
| ffmpeg + ffprobe (with drawtext) | everything after generation | `brew install ffmpeg` / `apt-get install ffmpeg` | PATH, or `FFMPEG` / `FFPROBE` |
| Python deps (numpy) | `vo_segments.py`, `audio_profile.py`, `fine_profile.py` (the proof step of every demo) | `pip install -r requirements.txt` | the python3 that runs make (PATH or `PY=`; a venv is fine) |
| Higgsfield CLI, logged in | Seedance 2.5 takes (`hf_shot.py`) | see below | PATH, or `HIGGSFIELD`; login via `higgsfield auth login` |
| `ELEVENLABS_API_KEY` | music, VO, SFX (`eleven.py`) | elevenlabs.io, Developers, API keys | env var |
| `OPENAI_API_KEY` (or the gpt-image MCP) | start stills (`gpt_image.py`) | platform.openai.com, API keys | env var |
| node >= 22 | Hyperframes render, `capture.mjs` | nodejs.org / `nvm install 22` | PATH |
| Hyperframes CLI | the final render | runs via `npx hyperframes@0.8.169` | nothing to set |
| Chrome or Chromium (optional) | `capture.mjs` proofs | google.com/chrome | `CHROME` |

Only python3, numpy (`pip install -r requirements.txt`) and ffmpeg are needed for `make demo-dry`. Without numpy it
stops before doing anything, with one line: `run: pip install -r requirements.txt`.

## Keys: environment variables only

The tools read keys from the environment and nowhere else, and never print them. A tool that needs a missing key
exits with one line: `set ELEVENLABS_API_KEY (...)`. Ways to set them:

- **Shell:** `export ELEVENLABS_API_KEY=...` (or a `.env` you source; `.env` is gitignored).
- **Fleet:** `fleet-ctl secret request ELEVENLABS_API_KEY --dest env` (same for `OPENAI_API_KEY`). Fleet asks you for
  the value once and injects it into the worker's environment.
- **macOS Keychain (optional, local only):** `source tools/local/keychain_env.sh` exports keys stored in your login
  Keychain into the current shell. Nothing in the tools calls it. Setup lines are at the top of that file.

The Higgsfield CLI has no key env var: `higgsfield auth login` runs a browser OAuth login and the CLI keeps its own
token. `doctor.py` checks login by reading `higgsfield account status` (it never prints the token).

## Install commands and version pins (resolved live, 2026-10-17)

| Tool | Pin / version seen | Install | Source |
|---|---|---|---|
| Higgsfield CLI | npm `@higgsfield/cli` 1.2.2 (published 2026-10-16); the tools were also run against binary 1.1.23 | `curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh \| sh`, or `brew install higgsfield-ai/tap/higgsfield`, or `npm install -g @higgsfield/cli`; then `higgsfield auth login` | https://github.com/higgsfield-ai/cli (README, read 2026-10-17); `npm view @higgsfield/cli` |
| Seedance model id | `seedance_2_5` | listed by `higgsfield model list --video` | live CLI, 2026-10-17 |
| Hyperframes | `hyperframes@0.8.169` (npm, published 2026-10-17; `engines.node >= 22`) | `npx hyperframes@0.8.169 render <dir> -o out/render.mp4 --quality delivery --fps 24` | `npm view hyperframes`; https://github.com/heygen-com/hyperframes; `render --help` of 0.8.169 |
| GSAP (in the composition) | 3.14.2 via jsDelivr | loaded by the page | the version the source films rendered with; 3.15.0 is current on npm |
| ElevenLabs API | v1: `POST /v1/music` (`music_v2_5`, plan `chunks` with `duration_ms`), `POST /v1/sound-generation`, `POST /v1/text-to-speech/{voice_id}` (default model `eleven_multilingual_v2`); header `xi-api-key` | an API key | https://elevenlabs.io/docs/api-reference/music/compose and https://elevenlabs.io/docs/api-reference/text-to-speech/convert (read 2026-10-17) |
| OpenAI Images | `POST /v1/images/generations`, `b64_json` response; model id is a flag, default `gpt-image-2` | an API key | unverified: the official API reference returned 403 to the fetch on 2026-10-17; the default matches the gpt-image MCP's engine. Check https://platform.openai.com/docs before a real run, and pass `--model` or `OPENAI_IMAGE_MODEL` |

Re-resolve these before trusting them: they were true on 2026-10-17. Seedance prices move too: on 2026-10-17
`higgsfield generate cost seedance_2_5 --mode omni_reference --duration 4 --resolution 1080p` quoted 64 credits.

## First run

```bash
python3 -m venv .venv && . .venv/bin/activate   # optional, keeps numpy out of your system Python
pip install -r requirements.txt    # numpy, for the proof step
python3 tools/doctor.py            # what is missing
make demo-dry                      # the whole pipeline, no keys, no spend (python3 + numpy + ffmpeg)
npx hyperframes@0.8.169 lint examples/hello-table    # optional: the composition the demo wrote is valid
make render                        # optional: render it with Hyperframes on the placeholders (Node + Chrome)
VOICE_ID=<your ElevenLabs voice id> make demo        # the real sample film: quotes first, cap 200 credits
```

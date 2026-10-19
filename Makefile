# fleet-video-lab: the sample film end to end.
#   make doctor     what is installed, what is missing, where to set it (always exits 0)
#   make demo-dry   the whole pipeline with NO keys and NO spend: ffmpeg placeholders stand in for every generation
#   make demo       the real thing (quotes first; cap 200 credits). Needs doctor all-ok and VOICE_ID set.
#   make render     render the Hyperframes composition (index.html) the demo wrote
#   make donecheck  every deliverable in edit.json, gate by gate; names the first one missing (VERDICT=<file> to override)
#   make test       the unit tests (after make demo-dry)
#   make lint scan  ruff, and the privacy scan
PY ?= python3
P ?= examples/hello-table
HYPERFRAMES ?= npx -y hyperframes@0.8.169
CAP ?= 200
BPM := 120
END := 10
DRY ?=

.PHONY: doctor deps demo-dry demo generate cut proof render donecheck test lint scan clean-demo

doctor:
	$(PY) tools/doctor.py

# Python deps (numpy, for the proof step) are checked before anything runs: one line, never a traceback.
deps:
	@$(PY) -c "import numpy" 2>/dev/null || { echo "run: pip install -r requirements.txt"; exit 1; }

demo-dry: deps
	$(MAKE) generate cut proof DRY=--dry-run VOICE_ID=placeholder
	@# no judge runs on placeholders: a stand-in verdict in its own file, so the done-check can walk every gate
	@# without ever writing or reading the project's real VERDICT.md
	printf 'PASSES WITH FIXES\n\nDry run: placeholder footage, no judge ran. A real film needs a separate judge in VERDICT.md.\n' > "$(P)/VERDICT.dry-run.md"
	$(MAKE) donecheck P="$(P)" VERDICT="$(P)/VERDICT.dry-run.md"

demo: deps
	@test -n "$(VOICE_ID)" || { echo "set VOICE_ID (an ElevenLabs voice id; list yours with GET https://api.elevenlabs.io/v1/voices)"; exit 1; }
	$(PY) tools/doctor.py --strict
	$(MAKE) generate DRY= VOICE_ID=$(VOICE_ID)
	$(MAKE) render cut-real proof RENDER=out/render.mp4

# 1. generation: stills -> takes (serial, quoted, logged) -> music, VO, SFX
generate:
	$(PY) tools/run_batch.py --project $(P) --cap $(CAP) $(DRY)
	$(PY) tools/eleven.py music music-plan.json audio/music.mp3 --bpm $(BPM) --project $(P) $(DRY)
	$(PY) tools/eleven.py tts $(VOICE_ID) "Hello, table." audio/vo-1.mp3 --project $(P) $(DRY)
	$(PY) tools/eleven.py sfx "a single soft ceramic tap on a coffee cup" 1 audio/sfx-tap.mp3 --project $(P) $(DRY)

# 2. the cut: Hyperframes composition + an ffmpeg animatic of the same edit list, then the -14 LUFS master
RENDER ?= out/render.mov
cut:
	$(PY) tools/build_comp.py --project $(P) --animatic out/render.mov
	$(PY) tools/master.py $(P)/$(RENDER) $(P)/out/final.mp4 $(END)

cut-real:
	$(PY) tools/master.py $(P)/$(RENDER) $(P)/out/final.mp4 $(END)

render:
	$(PY) tools/build_comp.py --project $(P)
	$(HYPERFRAMES) render $(P) -o $(P)/out/render.mp4 --quality delivery --fps 24

# 3. proof: ffprobe, no digital zero at 10 ms, frames on every cut, the sound measured, the spend written down
proof:
	ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact $(P)/out/final.mp4
	$(PY) tools/audio_windows.py $(P)/out/final.mp4 0 0.01 --quiet
	$(PY) tools/frames.py $(P)/out/final.mp4 $(P)/frames --edit $(P)/edit.json --dense 3.5-5.5 --poster 9
	$(PY) tools/beat_grid.py $(P)/audio/music.mp3 $(BPM) --beats 8
	$(PY) tools/onsets.py $(P)/audio/music.mp3 $(BPM) 0 3
	$(PY) tools/vo_segments.py $(P)/audio/vo-1.mp3
	$(PY) tools/audio_profile.py $(P)/audio/music.mp3 --bpm $(BPM)
	$(PY) tools/fine_profile.py $(P)/audio/music.mp3 0 1 --bpm $(BPM)
	$(PY) tools/peaks.py $(P)/takes/video/V01.mp4 0 2 2 2
	$(PY) tools/score_level.py $(P)/out/final.mp4 --window 0-5 --window 5-10
	$(PY) tools/spend_report.py --project $(P) --cap $(CAP) --used V01,V02 --title "Hello, Table"

# done means this passes, never that the last command exited 0
# VERDICT= reads that verdict file instead of the one edit.json names
VERDICT ?=
donecheck:
	$(PY) tools/donecheck.py --project "$(P)" $(if $(VERDICT),--verdict "$(VERDICT)")

test:
	$(PY) -m unittest discover -s tests -v

lint:
	ruff check tools tests
	bash -n tools/scan_private.sh tools/local/keychain_env.sh

scan:
	bash tools/scan_private.sh

clean-demo:
	git clean -fdX $(P)

# BRIEF: "Hello, Table" (10 s sample film)

The smallest film that touches every step of the pipeline. It exists to prove the tools work on your machine,
first with no keys (`make demo-dry`), then for real (`make demo`, about 128 Seedance credits plus 2 stills and 3
ElevenLabs calls).

- **Length / format:** 10.000 s, 1280x720, 24 fps (the Seedance takes' native rate). 120 BPM: beat 0.5 s, 20 beats.
- **Concept:** a still life wakes up. A white cup on a bare oak table, morning side light; steam starts to rise.
  The type says hello to it.
- **Look:** one physical world in both stills: the same table, the same cup, the same window light from frame left,
  35 mm grain. No people, no hands, no text in picture, no logos, no camera drift.
- **Sound:** a soft 120 BPM brushed-drum and upright-bass bed; one dry spoken line, "Hello, table."; a single
  ceramic tap on the cup when the second shot lands.
- **Structure (beats):**

| Beats | Picture | Sound |
|---|---|---|
| 0-2 | card "HELLO," | bed starts; VO "Hello, table." at 0.5 s |
| 2-8 | V01 the cup, close, steam begins | |
| 8-14 | V02 the table, wide, light shifts | ceramic tap at 4.0 s |
| 14-20 | card "TABLE." | bed resolves under the end card |

- **Budget:** cap 200 credits for this sample (`--cap 200`); the plan should quote about 128 (2 jobs x 64 credits:
  `higgsfield generate cost seedance_2_5` quoted 64 for a 4 s 1080p omni_reference take on 2026-10-17). Your account's
  quote is the truth; the tools print it before any job.
- **Proof:** the master's ffprobe line, `tools/audio_windows.py ... 0 0.01` PASS, the contact sheet, SPEND.md.

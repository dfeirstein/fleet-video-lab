# SHOTS: "Hello, Table"

House look for every generated frame: a bare oak table, one plain white ceramic cup, soft morning window light from
frame left, warm neutral palette, 35 mm film grain, shallow depth of field. Universal negatives: no people, no hands,
no text in picture, no logos, no camera drift, no lens flares.

## Locked attributes

Checked on the still board (`frames/still-board.png`) before any take, and on both sides of every cut after.

### The cup (object)

| Attribute | Locked value | Check on |
|---|---|---|
| Body | one plain white ceramic cup, matte glaze, no pattern | s01, s02, V01 and V02 first/last |
| Handle | a single loop handle, pointing frame right | s01, s02, V01 and V02 first/last |
| Contents | black coffee, filled to about a finger below the rim | s01, V01 first/last |
| Count | exactly one cup; no saucer, no spoon | every cell |

### The table (set)

| Attribute | Locked value | Check on |
|---|---|---|
| Surface | bare light oak, grain running left to right, no cloth | every cell |
| Contents | the cup and nothing else | every cell |
| Light | soft morning window light from frame left, warm neutral | every cell |

DO NOT COPY: no reference image is used for this film. When a film uses one, name here what must not be lifted
from it (its subjects, logos, copy, people), and keep only the analyzed look.

## Stills (GPT image, `tools/gpt_image.py`, 1536x1024)

| Still | Prompt |
|---|---|
| s01 | Close still-life photograph of a plain white ceramic cup of black coffee on a bare oak table, soft morning window light from frame left, warm neutral palette, 35 mm film grain, shallow depth of field. No people, no hands, no text, no logos. |
| s02 | Wide still-life photograph of a bare oak table by a window, one plain white ceramic cup at the center, soft morning light from frame left falling across the grain of the wood, warm neutral palette, 35 mm film grain. No people, no hands, no text, no logos. |

## Seedance 2.5 jobs (Higgsfield CLI, `tools/hf_shot.py`: omni_reference, 1080p, no generated audio)

One job = one take. Every job is quoted before it runs and logged with its before/after credit delta.

| Job | Start still | Dur | Prompt |
|---|---|---|---|
| V01 | s01 | 4 s | Locked-off static camera. Thin steam begins to rise from the coffee and curls slowly in the window light. Nothing else moves. Real physics, film grain. No camera movement, no hands, no new objects. |
| V02 | s02 | 4 s | Locked-off static camera. The morning light slowly brightens and slides a few centimetres across the table; a faint wisp of steam rises from the cup. Real physics, film grain. No camera movement, no hands, no new objects. |

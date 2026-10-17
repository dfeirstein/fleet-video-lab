# Intent: package fun-video-lab as an open-source Fleet skill (fleet-video-lab)

## Problem
`~/repos/fun-video-lab` is a private scratch studio (2.6 GB history, 634 tracked media files, four finished client films) whose tools make 30-second generated films: Seedance shots via the Higgsfield CLI, GPT image stills, ElevenLabs voice, Hyperframes motion, ffmpeg comp and master, beat and onset analysis, a maker/critic review loop. Nothing in it can be shared: keys are read from Doug's Keychain, paths are absolute, and brand material (Dryver, JerkCheck, Fleet, the Mahjong cast, the Casey Reed reference) is mixed in with the method.

## Proposed outcome (Doug's decisions, 2026-10-17)
- A NEW public repo `dfeirstein/fleet-video-lab` with a clean history (created private today; Doug flips it public after review). The old repo stays private and untouched.
- Contents: the generic pipeline tools and the method (making-of discipline, critic loop, proof rules), a tiny sample project that proves the pipeline end to end, a `SKILL.md` that Fleet workers and Claude Code can load, a setup guide, and a `doctor` command that tells a new user exactly which API keys and CLIs are missing and where to put them. No client films, no cast or brand assets, no Casey Reed reference, no Doug-specific rules file.
- License: MIT.

## Affected users and systems
- Users: anyone running Fleet or Claude Code who wants the video studio as a skill; Doug as the first user on a clean machine.
- Systems: Higgsfield CLI (Seedance 2.5, credits metered), ElevenLabs API, OpenAI image API (or the GPT image MCP), Hyperframes CLI, ffmpeg; Fleet's secret store and `fleet-ctl secret request` for keys; the Fleet skill loader (same shape as the bundled `elite-design` skill).

## Constraints
- Keys ONLY from environment variables, never from Doug's Keychain in shipped code; a Keychain shim may exist as an optional, documented local adapter. Never print a key.
- No secret, token, absolute `/Users/douglasfeirstein` path, or private asset may land in the new repo or its history; verify with a scan before every push.
- Every shipped tool must run `--help` without keys and must fail with a one-line "set X" message when its key is missing.
- Pin external tool versions from the live source (Higgsfield CLI, Hyperframes, ElevenLabs API), never from memory.
- Deploy via PR + review; the Captain and Doug decide when the repo goes public.

## Open questions (pick a default, note it in the PR)
- Repo and skill name: `fleet-video-lab` unless the worker finds a conflict on GitHub or in the skills registry.
- Whether the GPT image step ships as an API script or as instructions to use the MCP the user already has.
- How much of the maker/critic rubric is generic enough to ship (the 12 launch-video rules stay private; a neutral rubric may be written fresh).

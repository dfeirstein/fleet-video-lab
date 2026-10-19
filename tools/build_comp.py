"""Write a beat-locked Hyperframes composition (and, optionally, an ffmpeg animatic) from one edit list.

Every picture event is placed in BEATS so the cut cannot drift off the music grid; sound is placed in seconds.
usage: python3 tools/build_comp.py [--project DIR] [--edit edit.json] [--animatic out/render.mov]
  writes <project>/index.html (render it with: npx hyperframes@<pin> render, see docs/SETUP.md)
  --animatic also renders the same edit with ffmpeg alone (cards as plain type, no motion), so the cut, the timing and
  the sound can be checked, mastered and judged without Node, Chrome or Hyperframes.

edit.json:
  {"title": "...", "bpm": 120, "fps": 24, "width": 1280, "height": 720, "beats": 20,
   "palette": {"bg": "#111111", "fg": "#F2EDE4"}, "font": "Helvetica, Arial, sans-serif",
   "picture": [{"beat": 0, "beats": 2, "card": "HELLO,"},
               {"beat": 2, "beats": 6, "take": "V01", "media_start": 0.5}, ...],
   "audio": [{"id": "music", "src": "audio/music.mp3", "at": 0.0, "volume": 0.8}, ...],
   "captions": [{"beat": 3, "beats": 4, "text": "steam."}, {"beat": 7, "beats": 2, "text": "...", "bridge": true}],
   "moves": [{"beat": 10, "beats": 2}]}
Picture events must tile the film with no gap or overlap; the tool refuses an edit list that does not.
Cut lint (captions and moves are optional, both in beats): a caption may not cross a picture-event boundary unless it
says "bridge": true, and may not be up while a camera move ("moves") runs. The tool refuses the edit list and names
every offending caption; on success it prints `cut lint: 0 straddles`.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ensure_dir, ffmpeg, project, run  # noqa: E402

GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"


def load(root, name):
    e = json.load(open(os.path.join(root, name)))
    e["B"] = 60 / e["bpm"]
    e["dur"] = round(e["beats"] * e["B"], 5)
    at = 0
    for p in e["picture"]:
        if abs(p["beat"] - at) > 1e-9:
            sys.exit(f"edit list: picture event at beat {p['beat']} should start at beat {at} (gap or overlap)")
        at = p["beat"] + p["beats"]
    if abs(at - e["beats"]) > 1e-9:
        sys.exit(f"edit list: picture ends at beat {at}, the film is {e['beats']} beats")
    e.setdefault("captions", [])
    e.setdefault("moves", [])
    return e


def cut_lint(e):
    """Refuse a caption that crosses a cut (unless bridged), overlaps a camera move, or runs off the film.

    Returns the number of bridged captions; exits with one line per offending caption otherwise."""
    cuts = [p["beat"] for p in e["picture"][1:]]
    bad, bridged = [], 0
    for c in e["captions"]:
        a, b = c["beat"], c["beat"] + c["beats"]
        name = f"caption {c['text']!r} (beats {a}-{b})"
        if a < 0 or b > e["beats"] + 1e-9:
            bad.append(f"cut lint: {name} runs outside the film (0-{e['beats']})")
        straddled = [x for x in cuts if a + 1e-9 < x < b - 1e-9]
        if straddled and c.get("bridge"):
            bridged += 1
        elif straddled:
            bad.append(f"cut lint: {name} straddles the cut at beat {straddled[0]}; "
                       f"end it by beat {straddled[0]} or mark it \"bridge\": true")
        for m in e["moves"]:
            if a + 1e-9 < m["beat"] + m["beats"] and m["beat"] + 1e-9 < b:
                bad.append(f"cut lint: {name} overlaps the camera move at beats {m['beat']}-{m['beat'] + m['beats']}")
    if bad:
        sys.exit("\n".join(bad + [f"cut lint: {len(bad)} straddles"]))
    return bridged


def html(e):
    B, body, js = e["B"], [], []
    for n, p in enumerate(e["picture"]):
        s, d = round(p["beat"] * B, 5), round(p["beats"] * B, 5)
        if "take" in p:
            body.append(f'<video id="p{n:02d}" class="clip fill" src="takes/video/{p["take"]}.mp4" muted playsinline '
                        f'data-start="{s}" data-duration="{d}" data-media-start="{p.get("media_start", 0)}" '
                        f'data-track-index="0"></video>')
        else:
            body.append(f'<div id="p{n:02d}" class="clip card" data-start="{s}" data-duration="{d}" '
                        f'data-track-index="0"><span id="t{n:02d}">{p["card"]}</span></div>')
            # every type entry is a hard cut with a short scale punch: no fades, no melting type
            js.append(f'tl.fromTo("#t{n:02d}", {{scale: 1.5}}, {{scale: 1, duration: 0.06, ease: "power4.out"}}, {s});')
    for n, c in enumerate(e["captions"]):
        s, d = round(c["beat"] * B, 5), round(c["beats"] * B, 5)
        body.append(f'<div id="c{n:02d}" class="clip caption" data-start="{s}" data-duration="{d}" '
                    f'data-track-index="{1 + len(e["audio"])}"><span>{c["text"]}</span></div>')
    for k, a in enumerate(e["audio"]):
        body.append(f'<audio id="{a["id"]}" src="{a["src"]}" data-start="{a["at"]}" '
                    f'data-volume="{a.get("volume", 1)}" data-track-index="{1 + k}"></audio>')
    w, h, bg, fg = e["width"], e["height"], e["palette"]["bg"], e["palette"]["fg"]
    nl = "\n      "
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <title>{e["title"]}</title>
    <script src="{GSAP}"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {w}px; height: {h}px; overflow: hidden; background: {bg}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: {bg}; }}
      .clip {{ position: absolute; inset: 0; }}
      .fill {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
      .card {{ display: flex; align-items: center; justify-content: center; background: {bg}; color: {fg};
               font-family: {e["font"]}; font-weight: 800; font-size: {h // 5}px; letter-spacing: -0.02em; }}
      .card span {{ display: block; }}
      .caption {{ display: flex; align-items: flex-end; justify-content: center; padding-bottom: {h // 12}px; color: {fg};
                  font-family: {e["font"]}; font-weight: 700; font-size: {h // 16}px; text-shadow: 0 2px 12px rgba(0,0,0,0.6); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{e["dur"]}" data-fps="{e["fps"]}" data-width="{w}" data-height="{h}">
      {nl.join(body)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {nl.join(js)}
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def drawtext_escape(text):
    return text.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace("%", "\\%")


def animatic(e, root, out):
    B, w, h, fps = e["B"], e["width"], e["height"], e["fps"]
    inputs, chains, labels = [], [], []
    font = os.environ.get("DRAWTEXT_FONTFILE")
    ff = f"fontfile='{font}':" if font else ""
    for n, p in enumerate(e["picture"]):
        d = round(p["beats"] * B, 5)
        if "take" in p:
            inputs += ["-ss", str(p.get("media_start", 0)), "-t", str(d), "-i",
                       os.path.join(root, "takes", "video", f"{p['take']}.mp4")]
            chains.append(f"[{n}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},"
                          f"trim=duration={d},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{n}]")
        else:
            inputs += ["-f", "lavfi", "-i", f"color=c={e['palette']['bg']}:s={w}x{h}:r={fps}:d={d}"]
            chains.append(f"[{n}:v]drawtext={ff}text='{drawtext_escape(p['card'])}':fontcolor={e['palette']['fg']}:"
                          f"fontsize={h // 5}:x=(w-tw)/2:y=(h-th)/2,format=yuv420p,setsar=1[v{n}]")
        labels.append(f"[v{n}]")
    caps = "".join(f",drawtext={ff}text='{drawtext_escape(c['text'])}':fontcolor={e['palette']['fg']}:fontsize={h // 16}:"
                   f"x=(w-tw)/2:y=h-th-{h // 12}:enable='between(t,{round(c['beat'] * B, 5)},"
                   f"{round((c['beat'] + c['beats']) * B, 5)})'" for c in e["captions"])
    chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0{caps}[v]")
    base = len(e["picture"])
    for k, a in enumerate(e["audio"]):
        inputs += ["-i", os.path.join(root, a["src"])]
        ms = int(round(a["at"] * 1000))
        chains.append(f"[{base + k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={a.get('volume', 1)},"
                      f"adelay={ms}|{ms}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(e["audio"])))
    chains.append(f"{mix}amix=inputs={len(e['audio'])}:normalize=0:duration=longest,apad,atrim=end={e['dur']}[a]")
    ensure_dir(os.path.dirname(out))
    run([ffmpeg(), "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", str(fps), "-c:a", "pcm_s16le",
         "-t", str(e["dur"]), out])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=None)
    ap.add_argument("--edit", default="edit.json")
    ap.add_argument("--animatic", default=None, help="also render an ffmpeg-only cut to this path (.mov or .mkv)")
    a = ap.parse_args()
    root = project(a.project)
    e = load(root, a.edit)
    bridged = cut_lint(e)
    print("cut lint: 0 straddles" + (f", {bridged} bridged" if bridged else ""))
    out = os.path.join(root, "index.html")
    with open(out, "w") as f:
        f.write(html(e))
    print(f"{out}: {len(e['picture'])} picture events, {len(e['audio'])} sounds, {e['dur']} s at {e['fps']} fps")
    if a.animatic:
        dest = a.animatic if os.path.isabs(a.animatic) else os.path.join(root, a.animatic)
        animatic(e, root, dest)
        print(f"animatic: {dest}")


if __name__ == "__main__":
    main()

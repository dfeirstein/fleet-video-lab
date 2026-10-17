"""One GPT image still (a Seedance start frame) through the OpenAI Images API. Every call is logged.

The key comes from OPENAI_API_KEY and is never printed. If you already run the gpt-image MCP server in Claude Code,
you can make stills there instead and save them under <project>/stills/; this script is the keyed, scriptable path.

usage: python3 tools/gpt_image.py <name> <prompt> [--size 1536x1024] [--quality high] [--model gpt-image-2]
                                  [--project DIR] [--dry-run]
Writes <project>/stills/<name>.png and appends a row to <project>/takes/image-calls.jsonl.
--dry-run makes no call and needs no key: ffmpeg writes a test-pattern still of the same size.
The model id is a flag (or $OPENAI_IMAGE_MODEL) on purpose: image model ids change, check the OpenAI docs.
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ensure_dir, ffmpeg, need_key, project, run  # noqa: E402

API = "https://api.openai.com/v1/images/generations"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("prompt")
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"))
    ap.add_argument("--project", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = project(a.project)
    if not a.dry_run:
        need_key("OPENAI_API_KEY", f" -- or make the still with the gpt-image MCP and save it to stills/{a.name}.png")
    dest = os.path.join(ensure_dir(os.path.join(root, "stills")), f"{a.name}.png")
    log_path = os.path.join(ensure_dir(os.path.join(root, "takes")), "image-calls.jsonl")
    entry = {"name": a.name, "prompt": a.prompt, "size": a.size, "quality": a.quality, "model": a.model, "out": dest}

    if a.dry_run:
        hue = sum(map(ord, a.name)) * 47 % 360  # a different tint per still, so placeholder shots are told apart
        run([ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={a.size}:rate=1",
             "-vf", f"hue=h={hue}", "-frames:v", "1", dest])
        entry["dry_run"] = True
    else:
        key = need_key("OPENAI_API_KEY", " -- or make the still with the gpt-image MCP and save it to " + dest)
        body = {"model": a.model, "prompt": a.prompt, "size": a.size, "quality": a.quality, "n": 1}
        req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"OpenAI HTTP {e.code}: {e.read().decode()[:800]}")
        with open(dest, "wb") as f:
            f.write(base64.b64decode(data["data"][0]["b64_json"]))
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"still: {dest}{' (dry run)' if a.dry_run else ''}")


if __name__ == "__main__":
    main()

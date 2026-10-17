"""Write <project>/SPEND.md from the generation ledgers: every Seedance job (quote, before, after, delta), every
ElevenLabs call and every GPT image call. Quote vs billed mismatches are called out.

usage: python3 tools/spend_report.py [--project DIR] [--cap 1000] [--used V01,V02] [--title "My film"]
Reads takes/hf-ledger.jsonl, takes/eleven-calls.jsonl, takes/image-calls.jsonl (missing files count as empty).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import project  # noqa: E402


def rows(path):
    return [json.loads(line) for line in open(path) if line.strip()] if os.path.exists(path) else []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=None)
    ap.add_argument("--cap", type=float, default=1000)
    ap.add_argument("--used", default="", help="comma list of jobs in the final cut")
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    root = project(a.project)
    hf = rows(os.path.join(root, "takes", "hf-ledger.jsonl"))
    el = rows(os.path.join(root, "takes", "eleven-calls.jsonl"))
    im = rows(os.path.join(root, "takes", "image-calls.jsonl"))
    used = set(filter(None, a.used.split(",")))
    dry = sum(1 for r in hf + el + im if r.get("dry_run"))
    total = sum(e["delta"] for e in hf)
    quoted = sum(e["quote"] for e in hf)
    lines = [
        f"# SPEND: {a.title or os.path.basename(root)}",
        "",
        f"**Higgsfield (Seedance 2.5): {total:g} credits spent of the {a.cap:g} cap** ({len(hf)} jobs, one take each; "
        f"quoted {quoted:g}).",
        f"**ElevenLabs: {len(el)} calls** ({sum(e['kind'] == 'music' for e in el)} music, "
        f"{sum(e['kind'] == 'tts' for e in el)} TTS, {sum(e['kind'] == 'sfx' for e in el)} SFX).",
        f"**GPT image: {len(im)} calls.**",
    ]
    if dry:
        lines.append(f"**{dry} of these rows are DRY RUNS** (placeholders made with ffmpeg; nothing billed).")
    lines += ["", "Every Seedance job ran through `tools/hf_shot.py`: account status -> cost quote -> cap check -> "
              "create --wait -> account status; the delta is before - after.", "",
              "| # | Job | Dur | Quote | Before | After | Delta | Running total | In final cut | Job id |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    run_total = 0.0
    for i, e in enumerate(hf, 1):
        run_total += e["delta"]
        flag = "yes" if e["job"] in used else ("-" if not used else "no")
        lines.append(f"| {i} | {e['job']} | {e['duration']} s | {e['quote']:g} | {e['before']:g} | {e['after']:g} | "
                     f"{e['delta']:g} | {run_total:g} | {flag} | `{e.get('job_id') or ''}` |")
    mism = [e["job"] for e in hf if abs(e["delta"] - e["quote"]) > 0.01]
    lines += ["", "Quote vs billed: " + (f"MISMATCH on {', '.join(mism)}." if mism else "all deltas equal their quotes."),
              "", "## ElevenLabs calls", "", "| # | Kind | Detail | Output |", "|---|---|---|---|"]
    for i, e in enumerate(el, 1):
        detail = e.get("text") or f"composition plan {os.path.basename(e.get('plan', ''))}, seed {e.get('seed')}"
        lines.append(f"| {i} | {e['kind']} | {detail} | `{e['out']}` |")
    lines += ["", "## GPT image calls", "", "| # | Still | Model | Size | Quality |", "|---|---|---|---|---|"]
    for i, e in enumerate(im, 1):
        lines.append(f"| {i} | {e['name']} | {e['model']} | {e['size']} | {e['quality']} |")
    out = os.path.join(root, "SPEND.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print(f"{out}: {total:g} credits, {len(el)} ElevenLabs calls, {len(im)} image calls ({dry} dry-run rows)")


if __name__ == "__main__":
    main()

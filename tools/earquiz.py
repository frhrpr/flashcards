#!/usr/bin/env python3
"""A say-it-and-he-guesses sheet of every ear-training word, hard ones spread out.

    python3 tools/earquiz.py            # writes Downloads/.../lessons/<today>-sybilanty.html

For the teacher to read aloud: say the bold word, he names which of the
alternatives he heard, then work on that one before moving on.

The spec, which was lost once and had to be reverse-engineered from a sheet:

- Every word in `SETS` in index.html, whether or not it has audio — the
  teacher's voice is the recording here.
- Banded by the set's worst pair: **hard** under 60% correct, **mid** under
  85%, else **easy**. The whole set shares its worst pair's band, because the
  words of one set are only hard in relation to each other.
- Judged on each pair's **last 20 trials**, not on everything in the log.
  All-time figures kept kos/kosz/koś and nic/nić in "hard" long after he had
  stopped missing them, and proszę/prosię looked better than it was.
- **Interleaved, not worst-first** (asked 2026-10-21): one easy item as a
  warm-up, then hard, mid, easy in turn, so a hard item comes every third row
  and is always followed by one he can get. A sheet that opened with three
  sets he fails was discouraging and taught nothing extra. Stopping early
  still means the hard items were covered, because they run out first.
- **No two neighbours from the same set** — hearing a minimal pair back to
  back lets the contrast do the work for him.
- Each row: number (coloured by band), the word with its gloss, the set's
  alternatives, an empty tick box.

Reads WORDS and SETS out of index.html and the log from Firestore, so it
cannot drift from the trainer.
"""
import html, json, random, re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import progress  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HARD, MID = 0.60, 0.85
WINDOW = 20   # trials per pair that decide its band


def content():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    words = {m.group(1): ("".join(json.loads("[" + m.group(2) + "]")), m.group(3))
             for m in re.finditer(
                 r'"([\w-]+)":\s*\{w:\[([^\]]*)\],\s*g:"([^"]*)"', src)}
    sets_src = re.search(r"const SETS = \[(.*?)\n\];", src, re.S).group(1)
    sets = [re.findall(r'"([\w-]+)"', row) for row in re.findall(r"\[([^\]]*)\]", sets_src)]
    if not words or not sets:
        sys.exit("earquiz: could not read WORDS / SETS out of index.html")
    missing = [w for s in sets for w in s if w not in words]
    if missing:
        sys.exit(f"earquiz: in SETS but not WORDS: {', '.join(missing)}")
    return words, sets


def bands(sets, log):
    hist = defaultdict(list)
    for e in sorted(log, key=lambda e: e["ts"]):
        if not e["card"].endswith("__ear") or not e.get("vs"):
            continue
        hist["|".join(sorted([e["card"][:-5], e["vs"]]))].append(e["grade"] == "good")
    out = []
    for s in sets:
        rates = [sum(h[-WINDOW:]) / len(h[-WINDOW:]) for k, h in hist.items()
                 if set(k.split("|")) <= set(s) and h]
        worst = min(rates) if rates else None
        band = "mid" if worst is None else "hard" if worst < HARD else "mid" if worst < MID else "easy"
        out.append((band, worst))
    return out


def order(items, seed):
    """Easy warm-up, then hard/mid/easy in turn; no neighbours from one set.

    A band that runs out is skipped, so the tail is mid and easy. Retried with
    a fresh shuffle until no two neighbours share a set."""
    rng = random.Random(seed)
    for _ in range(5000):
        pools = {b: [i for i in items if i["band"] == b] for b in ("hard", "mid", "easy")}
        for chunk in pools.values():
            rng.shuffle(chunk)
        seq = [pools["easy"].pop()] if pools["easy"] else []
        while any(pools.values()):
            for b in ("hard", "mid", "easy"):
                if pools[b]:
                    seq.append(pools[b].pop())
        if all(a["set"] != b["set"] for a, b in zip(seq, seq[1:])):
            return seq
    sys.exit("earquiz: could not separate neighbours — a band is dominated by one set")


def main():
    words, sets = content()
    _, cards, log, *_ = progress.load_remote(progress.api_key(), "evert")
    items = []
    for i, (s, (band, worst)) in enumerate(zip(sets, bands(sets, log))):
        alts = " · ".join(words[w][0] for w in s)
        for w in s:
            items.append({"set": i, "band": band, "worst": worst,
                          "say": words[w][0], "gloss": words[w][1], "alts": alts})
    seq = order(items, seed=date.today().isoformat())

    rows = "".join(
        f'<tr class={it["band"]}><td class=no>{n}</td>'
        f'<td class=say><b>{html.escape(it["say"])}</b><i>{html.escape(it["gloss"])}</i></td>'
        f'<td class=ch>{html.escape(it["alts"])}</td><td class=tick></td></tr>'
        for n, it in enumerate(seq, 1))
    page = f"""<!doctype html><meta charset=utf-8><title>Sybilanty — na głos</title>
<meta name=color-scheme content="dark light"><style>
:root{{--bg:#15171a;--card:#1d2024;--ink:#e6e8e6;--dim:#9aa0a6;--faint:#767c82;
--line:#2e3339;--hard:#e8796b;--mid:#e8c07c}}
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;
padding:0 1.2rem 4rem;background:var(--bg);color:var(--ink);line-height:1.5}}
h1{{font-size:1.3rem;font-weight:400;margin:0}}
.meta{{font-family:ui-monospace,monospace;font-size:.72rem;letter-spacing:.1em;
text-transform:uppercase;color:var(--dim);margin-bottom:1.4rem}}
.intro{{background:var(--card);border:1px solid var(--line);padding:1rem 1.2rem;
margin-bottom:1.6rem;font-size:.9rem;line-height:1.55}}
.intro p{{margin:.4rem 0}} .intro p:first-child{{margin-top:0}}
.intro p:last-child{{margin-bottom:0}}
table{{width:100%;border-collapse:collapse}}
td{{padding:.5rem .4rem;border-bottom:1px solid var(--line);vertical-align:top}}
td.no{{font-family:ui-monospace,monospace;font-size:.68rem;color:var(--faint);
width:1.8rem;text-align:right}}
td.say{{width:11rem;font-size:1.3rem;font-weight:300}}
td.say i{{display:block;font-style:normal;font-size:.72rem;color:var(--faint);
margin-top:.1rem}}
td.ch{{font-size:.9rem;color:var(--dim);padding-top:.75rem}}
td.tick{{width:3.4rem;border-bottom:1px solid var(--line)}}
tr.hard td.no{{color:var(--hard)}}
tr.mid td.no{{color:var(--mid)}}
@media print{{
:root{{--bg:#fff;--card:#fff;--ink:#111;--dim:#555;--faint:#777;--line:#ccc;
--hard:#a32c22;--mid:#8a5a00}}
body{{margin:0;max-width:none;font-size:10.5pt}}
.intro{{border-color:#999}}}}
</style>
<h1>Sybilanty — powiedz, niech zgadnie</h1>
<div class=meta>{len(seq)} pozycji &middot; trudne co trzecie</div>
<div class=intro>
<p>Say the bold word. He says which of the alternatives he heard. Then help
him with that one — mirror, lips, tongue — before moving on.</p>
<p>Mixed from his trainer data (last 20 tries per pair): an easy one to
start, then a hard one every third row, each followed by something he can
get. Red numbers are under 60%, amber under 85%. The hard ones run out first,
so <b>stop wherever you like</b> after the first third and they are covered.</p>
<p>No two neighbouring items come from the same set, so he never hears a
minimal pair back to back — that would let the contrast do the work for him.</p>
</div>
<table>{rows}</table>
"""
    dest = Path("/mnt/c/Users/frhrpr/Downloads/flashcards/lessons")
    if not dest.is_dir():
        dest = ROOT / ".out"
        dest.mkdir(exist_ok=True)
    path = dest / f"{date.today().isoformat()}-sybilanty.html"
    path.write_text(page, encoding="utf-8")
    print(f"wrote {path}")
    for b in ("hard", "mid", "easy"):
        shown = sorted({(it["alts"], it["worst"]) for it in seq if it["band"] == b},
                       key=lambda x: (x[1] is None, x[1] or 0))
        print(f"  {b:<4} " + "; ".join(
            f"{a} {'—' if w is None else f'{w:.0%}'}" for a, w in shown))
    return 0


if __name__ == "__main__":
    sys.exit(main())

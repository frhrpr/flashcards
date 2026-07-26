#!/usr/bin/env python3
"""Build the approval page, and record approvals.

    python3 tools/review.py                    # build the page, open-able in Windows
    python3 tools/review.py --approve kot,dom  # mark those notes reviewed
    python3 tools/review.py --approve-all      # mark every note reviewed

Nothing reaches the student on the strength of generation alone. A note is
`reviewed: false` until a human has read the Polish and heard the audio;
tools/audio.py clears the flag again whenever a clip changes.

The page is written somewhere Windows can open it, because the repo lives in
WSL and Explorer cannot reach WSL paths without the \\\\wsl$ prefix.
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_PATH = ROOT / "deck/notes.json"
MANIFEST_PATH = ROOT / "media/manifest.json"
# One folder for everything this project puts on the Windows side.
OUT_ROOT = "flashcards"
OUT_SUB = "review"


def out_dir():
    for d in sorted(Path("/mnt/c/Users").glob("*/Downloads")):
        if d.is_dir() and not d.parent.name.startswith(("Default", "All Users", "Public")):
            return d / OUT_ROOT / OUT_SUB
    return ROOT / ".out" / OUT_SUB   # gitignored fallback when not on WSL


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def source_label(manifest, rel):
    m = manifest.get(rel or "", {})
    if m.get("source") == "commons":
        return f"human · {esc(m.get('author', '?'))} · {esc(m.get('licence', '?'))}"
    if m.get("source") == "tts":
        lang = " · lang pinned" if m.get("language_code") else ""
        why = " · no human recording" if m.get("why") else ""
        return f"synthetic · {esc(m.get('model', '?'))}{lang}{why}"
    return '<span class="bad">no manifest entry</span>'


def build(notes, manifest, dest):
    dest.mkdir(parents=True, exist_ok=True)
    audio_out = dest / "audio"
    audio_out.mkdir(exist_ok=True)
    img_out = dest / "img"
    img_out.mkdir(exist_ok=True)
    copied = 0
    for n in notes:
        for rel in (n.get("audio"), (n.get("sentence") or {}).get("audio")):
            if rel and (ROOT / rel).exists():
                shutil.copy2(ROOT / rel, audio_out / Path(rel).name)
                copied += 1
        if n.get("image") and (ROOT / n["image"]).exists():
            shutil.copy2(ROOT / n["image"], img_out / Path(n["image"]).name)
            copied += 1

    def player(rel):
        return (f'<audio controls preload=none src="audio/{esc(Path(rel).name)}"></audio>'
                if rel else '<span class="bad">missing</span>')

    cards = ""
    for n in sorted(notes, key=lambda x: (x.get("reviewed", False), x["id"])):
        s = n.get("sentence") or {}
        done = n.get("reviewed", False)
        pic = (f'<img src="img/{esc(Path(n["image"]).name)}" alt="">'
               if n.get("image") else '<div class="noimg">no image</div>')
        chk = (manifest.get(n.get("image") or "", {}) or {}).get("check") or {}
        if chk.get("verdict") == "flag":
            pic += (f'<div class="flag">flagged: {esc(chk.get("why",""))}'
                    + (f'<em>{esc(chk["problem"])}</em>' if chk.get("problem") else "")
                    + '</div>')
        elif chk:
            pic += '<div class="chk">auto-check ok</div>' 
        cards += f'''
<div class="c{' ok' if done else ''}">
  <div class="pic">{pic}</div>
  <div class="body">
  <div class="h"><span class="w">{esc(n['word'])}</span>
    <span class="ipa">[{esc(n.get('ipa',''))}]</span>
    <span class="gl">{esc(n.get('gloss',''))}</span>
    <span class="pos">{esc(n.get('pos',''))}</span>
    <span class="st">{'approved' if done else 'NEEDS REVIEW'}</span></div>
  <div class="row"><div class="lab">word<em>{source_label(manifest, n.get('audio'))}</em></div>
    {player(n.get('audio'))}</div>
  <div class="row"><div class="lab">sentence<em>{source_label(manifest, s.get('audio'))}</em></div>
    {player(s.get('audio'))}</div>
  <div class="pl">{esc(s.get('pl',''))}</div>
  <div class="en">{esc(s.get('en',''))}</div>
  <div class="gap">gap: {esc(s.get('gap',''))} &nbsp;→&nbsp; <b>{esc(s.get('answer',''))}</b>
</div>
  </div>
</div>'''

    pending = [n["id"] for n in notes if not n.get("reviewed")]
    html = f'''<!doctype html><meta charset=utf-8><title>Deck review</title><style>
body{{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;
background:#E8EBE4;color:#181B18;line-height:1.5}}
h1{{font-size:1.15rem;margin-bottom:.25rem}}
.sum{{font-size:.85rem;color:#6C736B;margin-bottom:1.5rem}}
.c{{background:#FCFDFB;border:1px solid #C9CFC4;border-left:3px solid #A32C22;
padding:.9rem 1.1rem;margin:1rem 0;display:flex;gap:1.1rem;align-items:flex-start}}
.pic{{flex:0 0 11rem}}
.pic img{{width:11rem;height:11rem;object-fit:contain;background:#F2F4F0;
border:1px solid #C9CFC4}}
.noimg{{width:11rem;height:11rem;display:flex;align-items:center;justify-content:center;
background:#F2F4F0;color:#A32C22;font-size:.78rem;border:1px solid #C9CFC4}}
.body{{flex:1;min-width:0}}
@media (max-width:38rem){{.c{{flex-direction:column}}.pic,.pic img,.noimg{{width:100%}}}}
.c.ok{{border-left-color:#2F6B3E;opacity:.62}}
.h{{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;margin-bottom:.6rem}}
.w{{font-size:1.5rem;font-weight:300}}
.ipa,.pos{{font-family:ui-monospace,monospace;font-size:.75rem;color:#6C736B}}
.gl{{color:#6C736B}}
.st{{margin-left:auto;font-family:ui-monospace,monospace;font-size:.65rem;
letter-spacing:.1em;color:#A32C22}}
.c.ok .st{{color:#2F6B3E}}
.row{{display:flex;align-items:center;gap:.8rem;margin:.25rem 0}}
.lab{{flex:0 0 11rem;font-size:.8rem}}
.lab em{{display:block;font-style:normal;font-size:.68rem;color:#6C736B;
font-family:ui-monospace,monospace}}
audio{{flex:1;height:2rem}}
.pl{{font-size:1.05rem;margin-top:.7rem}} .en{{font-size:.85rem;color:#6C736B}}
.gap{{margin-top:.6rem;padding-top:.5rem;border-top:1px solid #E8EBE4;
font-family:ui-monospace,monospace;font-size:.7rem;color:#6C736B}}
.bad{{color:#A32C22}}
.flag{{margin-top:.4rem;padding:.35rem .5rem;border-left:2px solid #A32C22;
background:#F6EDEC;font-family:ui-monospace,monospace;font-size:.62rem;
line-height:1.45;color:#A32C22}}
.flag em{{display:block;font-style:normal;color:#6C736B;margin-top:.2rem}}
.chk{{margin-top:.4rem;font-family:ui-monospace,monospace;font-size:.6rem;
color:#6C736B}}</style>
<h1>Deck review — {len(notes)} notes, {len(pending)} awaiting approval</h1>
<div class=sum>Everything for each note in one place — image, both recordings, sentence, gap.\nTell Claude which are wrong;
anything you do not flag gets approved. Approved notes are dimmed and sink to the bottom.</div>
{cards}'''
    (dest / "review.html").write_text(html, encoding="utf-8")
    return copied, pending


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--approve", default="", help="comma-separated note ids")
    ap.add_argument("--approve-all", action="store_true")
    args = ap.parse_args()

    deck = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    notes = deck["notes"]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}

    if args.approve or args.approve_all:
        ids = {n["id"] for n in notes} if args.approve_all else \
              {s.strip() for s in args.approve.split(",") if s.strip()}
        unknown = ids - {n["id"] for n in notes}
        if unknown:
            sys.exit(f"review: unknown note id(s): {', '.join(sorted(unknown))}")
        blocked = [n["id"] for n in notes if n["id"] in ids
                   and not (n.get("audio") and (n.get("sentence") or {}).get("audio"))]
        if blocked:
            sys.exit("review: these have missing audio and cannot be approved: "
                     + ", ".join(blocked))
        for n in notes:
            if n["id"] in ids:
                n["reviewed"] = True
        NOTES_PATH.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        print(f"approved {len(ids)}: {', '.join(sorted(ids))}")
        print(f"{sum(1 for n in notes if not n.get('reviewed'))} still awaiting review")
        return 0

    dest = out_dir()
    copied, pending = build(notes, manifest, dest)
    print(f"wrote {dest / 'review.html'}  ({copied} clips copied)")
    if pending:
        print(f"{len(pending)} awaiting approval: {', '.join(pending)}")
    else:
        print("everything is approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Take images you have collected and wire them into the deck.

    python3 tools/images.py                       # what's needed, what's in the inbox
    python3 tools/images.py --assign 1.png=kot,x.jpg=dom --go
    python3 tools/images.py --sheet               # contact sheet, to check the pairing

Filenames do not matter. Drop whatever you collected into the inbox folder;
Claude looks at each image, works out which word it belongs to, and passes
the pairing here. The contact sheet then shows every image beside the word it
was assigned, so a wrong pairing is caught in one glance rather than by Evert.

Images are converted to WebP, capped in width and stripped of metadata, so
whatever mix of formats and sizes came off the web ends up consistent.
Assigning an image clears `reviewed` — a new picture has not been looked at.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_PATH = ROOT / "deck/notes.json"
MANIFEST_PATH = ROOT / "media/manifest.json"
IMG_DIR = ROOT / "media/img"
OUT_ROOT, OUT_SUB = "flashcards", "images"

MAX_WIDTH = 800
QUALITY = 82
MIN_SOURCE_WIDTH = 400   # below this it will look poor on a phone
PROCESS_VERSION = 1

KEY_ORDER = ["id", "word", "gloss", "pos", "ipa", "note", "image", "image_alt",
             "audio", "sentence", "cards", "reviewed"]


def die(msg): sys.exit(f"images: {msg}")


def out_dir():
    for d in sorted(Path("/mnt/c/Users").glob("*/Downloads")):
        if d.is_dir() and not d.parent.name.startswith(("Default", "All Users", "Public")):
            return d / OUT_ROOT / OUT_SUB
    return ROOT / ".out" / OUT_SUB


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except ValueError:
        return None, None


def convert(src, dest):
    """Whatever came off the web -> a consistent, small, metadata-free WebP."""
    w, h = probe(src)
    if not w:
        raise RuntimeError("not a readable image (ffprobe found no video stream)")
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-vf", f"scale='min({MAX_WIDTH},iw)':-2",
         "-c:v", "libwebp", "-quality", str(QUALITY), "-compression_level", "5",
         "-map_metadata", "-1", "-frames:v", "1", "-f", "image2", str(dest)],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg could not convert it: {r.stderr.strip()[:140]}")
    nw, nh = probe(dest)
    return (w, h), (nw, nh)


def load():
    deck = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    return deck, deck["notes"], manifest


def save(deck, notes, manifest):
    deck["notes"] = [{k: n[k] for k in KEY_ORDER if k in n} |
                     {k: v for k, v in n.items() if k not in KEY_ORDER} for n in notes]
    NOTES_PATH.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                        sort_keys=True) + "\n", encoding="utf-8")


def cmd_status(notes, inbox):
    missing = [n for n in notes if "image" not in n]
    have = [n for n in notes if "image" in n]
    print(f"{len(have)}/{len(notes)} notes have an image\n")
    if missing:
        print("still needed — find one picture for each:")
        for n in missing:
            s = (n.get("sentence") or {}).get("pl", "")
            print(f"  {n['id']:<10} {n['word']:<10} {n['gloss']:<16} {s}")
        print()
    files = sorted(p for p in inbox.glob("*") if p.is_file()
                   and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"})
    print(f"inbox: {inbox}")
    if not files:
        print("  (empty — drop images here, any names, any formats)")
    for p in files:
        w, h = probe(p)
        flag = "  << small" if w and w < MIN_SOURCE_WIDTH else ""
        print(f"  {p.name:<44} {w}x{h}{flag}")
    return 0


def cmd_assign(deck, notes, manifest, inbox, pairs, go):
    by_id = {n["id"]: n for n in notes}
    plan = []
    for pair in pairs:
        if "=" not in pair:
            die(f"expected file=note_id, got {pair!r}")
        fname, nid = pair.split("=", 1)
        src = inbox / fname.strip()
        if not src.exists():
            die(f"no such file in the inbox: {src}")
        if nid.strip() not in by_id:
            die(f"unknown note id: {nid.strip()}")
        plan.append((src, by_id[nid.strip()]))

    seen = {}
    for src, n in plan:
        if n["id"] in seen:
            die(f"two images assigned to {n['id']}: {seen[n['id']].name} and {src.name}")
        seen[n["id"]] = src

    for src, n in plan:
        w, h = probe(src)
        warn = "  (LOW RESOLUTION)" if w and w < MIN_SOURCE_WIDTH else ""
        print(f"  {src.name:<40} -> {n['id']:<10} {n['word']}   {w}x{h}{warn}")
    if not go:
        print(f"\n{len(plan)} image(s). Dry run — re-run with --go.")
        return 0

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for src, n in plan:
        rel = f"media/img/{n['id']}.webp"
        dest = IMG_DIR / f"{n['id']}.webp"
        tmp = dest.with_suffix(".part")
        try:
            (ow, oh), (nw, nh) = convert(src, tmp)
        except RuntimeError as e:
            tmp.unlink(missing_ok=True)
            failed.append((src.name, str(e)))
            print(f"  FAILED {src.name}: {e}")
            continue
        tmp.replace(dest)
        dest.chmod(0o644)
        n["image"] = rel
        n.setdefault("image_alt", n["gloss"])
        if n.get("reviewed"):
            n["reviewed"] = False
        manifest[rel] = {
            "fingerprint": hashlib.sha256(src.read_bytes()).hexdigest()[:16],
            "source": "supplied", "original": src.name,
            "original_size": f"{ow}x{oh}", "size": f"{nw}x{nh}",
            "bytes": dest.stat().st_size, "process_version": PROCESS_VERSION,
        }
        print(f"  ok  {rel}  {ow}x{oh} -> {nw}x{nh}, {dest.stat().st_size // 1024} KB")

    save(deck, notes, manifest)
    if failed:
        print(f"\n{len(failed)} failed — nothing written for those.")
        return 1
    print("\nRun tools/images.py --sheet and check the pairing, then tools/validate.py.")
    return 0


def cmd_sheet(notes, manifest, dest):
    dest.mkdir(parents=True, exist_ok=True)
    shot = dest / "check"
    shot.mkdir(exist_ok=True)
    cards = ""
    for n in notes:
        rel = n.get("image")
        if rel and (ROOT / rel).exists():
            shutil.copy2(ROOT / rel, shot / Path(rel).name)
            img = f'<img src="check/{esc(Path(rel).name)}" alt="">'
            m = manifest.get(rel, {})
            meta = f"{esc(m.get('original','?'))} · {esc(m.get('size','?'))}"
        else:
            img = '<div class="none">no image</div>'
            meta = "—"
        s = (n.get("sentence") or {}).get("pl", "")
        cards += (f'<div class=c>{img}<div class=w>{esc(n["word"])}</div>'
                  f'<div class=g>{esc(n.get("gloss",""))}</div>'
                  f'<div class=s>{esc(s)}</div><div class=m>{meta}</div></div>')
    html = f'''<!doctype html><meta charset=utf-8><title>Image check</title><style>
body{{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;
background:#E8EBE4;color:#181B18}}
h1{{font-size:1.15rem}} p{{font-size:.9rem;color:#6C736B}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(11rem,1fr));gap:1rem}}
.c{{background:#FCFDFB;border:1px solid #C9CFC4;padding:.6rem;text-align:center}}
.c img{{width:100%;height:8rem;object-fit:contain;background:#F2F4F0}}
.none{{height:8rem;display:flex;align-items:center;justify-content:center;
background:#F2F4F0;color:#A32C22;font-size:.8rem}}
.w{{font-size:1.15rem;font-weight:300;margin-top:.4rem}}
.g{{font-size:.8rem;color:#6C736B}}
.s{{font-size:.75rem;margin-top:.35rem}}
.m{{font-family:ui-monospace,monospace;font-size:.6rem;color:#6C736B;margin-top:.35rem}}
</style><h1>Image check — does each picture match its word?</h1>
<p>If any pairing is wrong, tell Claude which. This is the only place a
mismatched image gets caught before Evert sees it.</p>
<div class=grid>{cards}</div>'''
    (dest / "check.html").write_text(html, encoding="utf-8")
    print(f"wrote {dest / 'check.html'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assign", default="", help="comma-separated file=note_id pairs")
    ap.add_argument("--sheet", action="store_true", help="build the contact sheet")
    ap.add_argument("--go", action="store_true")
    args = ap.parse_args()

    deck, notes, manifest = load()
    dest = out_dir()
    inbox = dest / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    if args.sheet:
        return cmd_sheet(notes, manifest, dest)
    if args.assign:
        pairs = [p for p in (s.strip() for s in args.assign.split(",")) if p]
        return cmd_assign(deck, notes, manifest, inbox, pairs, args.go)
    return cmd_status(notes, inbox)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build the deck's audio: human recordings for words, TTS for sentences.

    python3 tools/audio.py            # dry run — says what it would do
    python3 tools/audio.py --go       # actually fetch and synthesise
    python3 tools/audio.py --go --only kot,pies
    python3 tools/audio.py --go --tts-words   # skip Commons, synthesise words

Why the split: a multilingual TTS model infers language from the text, so a
sentence gives it plenty of Polish to lock onto but an isolated "kot" or
"dom" reads as English. Wikimedia Commons has native-speaker recordings of
exactly those isolated words (and no sentences), so the two sources cover
each other's gap. Where no recording exists we fall back to TTS with the
language pinned, which also fixes it.

Safe to re-run. A clip is rebuilt only when its text, source, voice or model
changes. Nothing enters deck/notes.json until ffprobe confirms real audio,
and any note whose audio changes has `reviewed` cleared — new audio has not
been listened to yet.
"""
import argparse, hashlib, html, json, re, subprocess, sys, tempfile, time
import urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_PATH = ROOT / "deck/notes.json"
AUDIO_DIR = ROOT / "media/audio"
MANIFEST_PATH = ROOT / "media/manifest.json"
ATTRIB_PATH = ROOT / "media/ATTRIBUTION.md"
ENV_PATH = ROOT / ".env"

VOICE_ID = "ErXwobaYiN019PkySvjV"
VOICE_NAME = "Antoni"
# Sentences: highest quality, and enough context to infer Polish unaided.
SENTENCE_MODEL = "eleven_multilingual_v2"
# Isolated words: language must be pinned, which multilingual_v2 cannot do.
WORD_MODEL = "eleven_turbo_v2_5"
WORD_LANG = "pl"

TTS_API = "https://api.elevenlabs.io/v1/text-to-speech/"
COMMONS_FILE = "https://commons.wikimedia.org/wiki/Special:FilePath/"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UA = "flashcards-vocab/0.1 (https://github.com/frhrpr/flashcards; personal study tool)"

MIN_BYTES, MIN_SECONDS, PAUSE = 2000, 0.2, 0.6
KEY_ORDER = ["id", "word", "gloss", "pos", "ipa", "note", "image", "image_alt",
             "audio", "sentence", "cards", "reviewed"]
SENT_KEY_ORDER = ["pl", "en", "gap", "answer", "answer_lemma", "audio"]


def die(msg): sys.exit(f"audio: {msg}")


def load_key():
    if not ENV_PATH.exists():
        die(f"no .env — create it with:\n  echo 'ELEVENLABS_API_KEY=your_key' > {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("ELEVENLABS_API_KEY="):
            key = line.split("=", 1)[1].strip().strip("'\"")
            if key:
                return key
    die(".env has no ELEVENLABS_API_KEY value")


def fingerprint(*parts):
    """Covers source and model, so changing either invalidates the clip."""
    return hashlib.sha256("\0".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]


def reorder(d, order):
    return {k: d[k] for k in order if k in d} | {k: v for k, v in d.items() if k not in order}


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def commons_meta(filename):
    """Licence and author, so ATTRIBUTION.md is generated rather than owed."""
    q = urllib.parse.urlencode({"action": "query", "titles": f"File:{filename}",
                                "prop": "imageinfo", "iiprop": "extmetadata|url",
                                "format": "json"})
    try:
        page = list(json.loads(get(f"{COMMONS_API}?{q}", 30))["query"]["pages"].values())[0]
        info = page["imageinfo"][0]
        m = info.get("extmetadata", {})
        author = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()
        return {"licence": m.get("LicenseShortName", {}).get("value", "unknown"),
                "author": html.unescape(author) or "unknown",
                "page": info.get("descriptionurl", "")}
    except Exception as e:
        return {"licence": "unknown", "author": "unknown", "page": "", "meta_error": str(e)}


def fetch_commons(word, dest_tmp):
    """Returns provenance, or None if Commons has no recording for this word."""
    name = f"Pl-{word}.ogg"
    try:
        data = get(COMMONS_FILE + urllib.parse.quote(name))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"Commons HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Commons network error: {e.reason}") from None
    ogg = dest_tmp.with_suffix(".ogg")
    ogg.write_bytes(data)
    # -f mp3 is required: the temp file ends in .part, so ffmpeg cannot infer
    # the output format from the extension.
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ogg),
                        "-codec:a", "libmp3lame", "-q:a", "5", "-f", "mp3", str(dest_tmp)],
                       capture_output=True, text=True)
    ogg.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg could not convert {name}: {r.stderr.strip()[:120]}")
    return {"source": "commons", "commons_file": name, **commons_meta(name)}


def synthesise(key, text, model, lang=None):
    body = {"text": text, "model_id": model}
    if lang:
        body["language_code"] = lang
    req = urllib.request.Request(TTS_API + VOICE_ID, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        try:
            detail = json.loads(detail)["detail"]["message"]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason}") from None


def verify(path):
    """An mp3 that is really a JSON error page passes an existence check."""
    size = path.stat().st_size if path.exists() else 0
    if size < MIN_BYTES:
        return f"only {size} bytes — an error response, not audio"
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        return f"ffprobe rejected it: {r.stderr.strip()[:120]}"
    try:
        if float(r.stdout.strip()) < MIN_SECONDS:
            return f"duration {r.stdout.strip()}s — too short to be real"
    except ValueError:
        return f"ffprobe gave no duration: {r.stdout.strip()[:80]}"
    return None


def plan(notes, only, tts_words):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    jobs = []
    for n in notes:
        if only and n["id"] not in only:
            continue
        want = "tts" if tts_words else "commons"
        targets = [(n["word"], f"{n['id']}.mp3", n, "audio", "word", want)]
        s = n.get("sentence")
        if s and s.get("pl"):
            targets.append((s["pl"], f"{n['id']}__sentence.mp3", s, "audio", "sentence", "tts"))
        for text, name, holder, key, kind, want in targets:
            rel = f"media/audio/{name}"
            model = SENTENCE_MODEL if kind == "sentence" else WORD_MODEL
            fp = fingerprint(kind, want, text,
                             VOICE_ID if want == "tts" else "commons",
                             model if want == "tts" else "-")
            entry = manifest.get(rel)
            if entry and entry.get("fingerprint") == fp and (ROOT / rel).exists():
                if holder.get(key) != rel:
                    jobs.append(dict(rel=rel, text=text, holder=holder, key=key, kind=kind,
                                     want=want, fp=fp, note=n, relink=True))
                continue
            jobs.append(dict(rel=rel, text=text, holder=holder, key=key, kind=kind,
                             want=want, fp=fp, note=n, relink=False))
    return jobs, manifest


def write_attribution(manifest):
    rows = sorted((v for v in manifest.values() if v.get("source") == "commons"),
                  key=lambda v: v.get("commons_file", ""))
    if not rows:
        ATTRIB_PATH.unlink(missing_ok=True)
        return
    lines = ["# Audio attribution", "",
             "Word recordings come from Wikimedia Commons and are reused under the",
             "licences below. Generated by `tools/audio.py` — do not edit by hand.",
             "", "| File | Author | Licence |", "| --- | --- | --- |"]
    for v in rows:
        lines.append(f"| [{v.get('commons_file','')}]({v.get('page','')}) "
                     f"| {v.get('author','unknown')} | {v.get('licence','unknown')} |")
    ATTRIB_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save(deck, notes, manifest):
    deck["notes"] = [reorder({**n, **({"sentence": reorder(n["sentence"], SENT_KEY_ORDER)}
                                      if isinstance(n.get("sentence"), dict) else {})}, KEY_ORDER)
                     for n in notes]
    NOTES_PATH.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                        sort_keys=True) + "\n", encoding="utf-8")
    write_attribution(manifest)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--tts-words", action="store_true",
                    help="skip Commons and synthesise words too")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    deck = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    notes = deck["notes"]
    if only:
        unknown = only - {n["id"] for n in notes}
        if unknown:
            die(f"unknown note id(s): {', '.join(sorted(unknown))}")

    jobs, manifest = plan(notes, only, args.tts_words)
    todo = [j for j in jobs if not j["relink"]]
    relink = [j for j in jobs if j["relink"]]

    print(f"words: {'TTS' if args.tts_words else 'Commons, falling back to TTS'}"
          f"  |  sentences: {SENTENCE_MODEL}, voice {VOICE_NAME}")
    if not todo and not relink:
        print("nothing to do — every clip is present and current")
        return 0
    for j in todo:
        print(f"  build  {j['rel']:<38} {('commons?' if j['want']=='commons' else 'tts'):<9} "
              f"{j['text'][:40]!r}")
    for j in relink:
        print(f"  relink {j['rel']:<38} (file already correct)")
    tts_chars = sum(len(j["text"]) for j in todo if j["want"] == "tts")
    print(f"\n{len(todo)} clip(s) to build; {tts_chars} TTS characters "
          f"(Commons words cost nothing)")
    if not args.go:
        print("\ndry run. Re-run with --go.")
        return 0

    key = load_key()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    failed, changed, counts = [], set(), {"commons": 0, "tts": 0, "fallback": 0}

    for j in relink:
        j["holder"][j["key"]] = j["rel"]
        print(f"  relinked {j['rel']}")

    for i, j in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {j['rel']} ... ", end="", flush=True)
        tmp = Path(tempfile.mkstemp(dir=AUDIO_DIR, suffix=".part")[1])
        prov, fell_back = None, False
        try:
            if j["want"] == "commons":
                prov = fetch_commons(j["text"], tmp)
                if prov is None:            # no recording exists — pin the language
                    fell_back = True
                    tmp.write_bytes(synthesise(key, j["text"], WORD_MODEL, WORD_LANG))
                    prov = {"source": "tts", "voice": VOICE_ID, "voice_name": VOICE_NAME,
                            "model": WORD_MODEL, "language_code": WORD_LANG,
                            "why": "no Commons recording for this word"}
            else:
                model = SENTENCE_MODEL if j["kind"] == "sentence" else WORD_MODEL
                lang = None if j["kind"] == "sentence" else WORD_LANG
                tmp.write_bytes(synthesise(key, j["text"], model, lang))
                prov = {"source": "tts", "voice": VOICE_ID, "voice_name": VOICE_NAME,
                        "model": model, **({"language_code": lang} if lang else {})}
        except RuntimeError as e:
            tmp.unlink(missing_ok=True)
            print("FAILED")
            failed.append((j["rel"], str(e)))
            continue
        problem = verify(tmp)
        if problem:
            tmp.unlink(missing_ok=True)
            print("FAILED")
            failed.append((j["rel"], problem))
            continue
        tmp.replace(ROOT / j["rel"])
        (ROOT / j["rel"]).chmod(0o644)
        manifest[j["rel"]] = {"fingerprint": j["fp"], "text": j["text"], **prov}
        j["holder"][j["key"]] = j["rel"]
        changed.add(j["note"]["id"])
        counts["fallback" if fell_back else prov["source"]] += 1
        print(f"ok  [{'TTS fallback' if fell_back else prov['source']}]")
        if prov["source"] == "tts":
            time.sleep(PAUSE)

    # New audio has not been listened to, so the note is no longer approved.
    for n in notes:
        if n["id"] in changed and n.get("reviewed"):
            n["reviewed"] = False
            print(f"  reviewed cleared for {n['id']} — audio changed")

    save(deck, notes, manifest)

    print(f"\n{counts['commons']} human recording(s), {counts['tts']} synthesised, "
          f"{counts['fallback']} synthesised because Commons had nothing")
    if failed:
        print(f"\n{len(failed)} FAILED — nothing written for these:")
        for rel, why in failed:
            print(f"  {rel}\n      {why}")
        print("\nRe-run to retry just these; everything else is saved.")
        return 1
    print("Run tools/review.py next, then tools/validate.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

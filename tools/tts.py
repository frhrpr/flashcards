#!/usr/bin/env python3
"""Synthesise any missing audio for deck/notes.json.

    python3 tools/tts.py          # dry run — says what it would do
    python3 tools/tts.py --go     # actually calls the API
    python3 tools/tts.py --go --only kot,pies

Safe to re-run. A clip is regenerated only when its text, voice or model has
changed, so fixing one sentence costs one request and nothing else moves.
Nothing is written into deck/notes.json until a file exists on disk and
ffprobe confirms it is real audio of non-zero length.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
import urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_PATH = ROOT / "deck/notes.json"
AUDIO_DIR = ROOT / "media/audio"
MANIFEST_PATH = ROOT / "media/manifest.json"
ENV_PATH = ROOT / ".env"

# Change these two and the next run regenerates everything, by design:
# the fingerprint below covers voice and model as well as the text.
VOICE_ID = "ErXwobaYiN019PkySvjV"
VOICE_NAME = "Antoni"
MODEL_ID = "eleven_multilingual_v2"

API = "https://api.elevenlabs.io/v1/text-to-speech/"
SUBSCRIPTION = "https://api.elevenlabs.io/v1/user/subscription"
MIN_BYTES = 2000        # anything smaller is an error page, not speech
MIN_SECONDS = 0.2
PAUSE = 0.4             # be gentle with the free tier's concurrency limit

# Keeps notes.json diffs small when audio keys are added.
KEY_ORDER = ["id", "word", "gloss", "pos", "ipa", "note", "image", "image_alt",
             "audio", "sentence", "cards", "reviewed"]
SENT_KEY_ORDER = ["pl", "en", "gap", "answer", "answer_lemma", "audio"]


def die(msg):
    sys.exit(f"tts: {msg}")


def load_key():
    if not ENV_PATH.exists():
        die(f"no {ENV_PATH.name}. Create it with:\n"
            f"  echo 'ELEVENLABS_API_KEY=your_key' > {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ELEVENLABS_API_KEY="):
            key = line.split("=", 1)[1].strip().strip("'\"")
            if key:
                return key
    die(f"{ENV_PATH.name} has no ELEVENLABS_API_KEY value")


def fingerprint(text):
    """Covers voice and model too, so switching either invalidates the clip."""
    h = hashlib.sha256()
    h.update(f"{MODEL_ID}\0{VOICE_ID}\0{text}".encode("utf-8"))
    return h.hexdigest()[:16]


def reorder(d, order):
    return {k: d[k] for k in order if k in d} | {k: v for k, v in d.items() if k not in order}


def build_jobs(notes, only):
    """One job per clip that is missing, stale, or has lost its file."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    jobs = []
    for n in notes:
        if only and n["id"] not in only:
            continue
        targets = [(n["word"], f"{n['id']}.mp3", n, "audio")]
        s = n.get("sentence")
        if s and s.get("pl"):
            targets.append((s["pl"], f"{n['id']}__sentence.mp3", s, "audio"))
        for text, name, holder, key in targets:
            rel = f"media/audio/{name}"
            fp = fingerprint(text)
            entry = manifest.get(rel)
            fresh = entry and entry.get("fingerprint") == fp and (ROOT / rel).exists()
            if fresh:
                # Repair the note if the file is there but the key went missing.
                if holder.get(key) != rel:
                    jobs.append({"rel": rel, "text": text, "holder": holder,
                                 "key": key, "fp": fp, "relink_only": True,
                                 "note_id": n["id"]})
                continue
            jobs.append({"rel": rel, "text": text, "holder": holder, "key": key,
                         "fp": fp, "relink_only": False, "note_id": n["id"]})
    return jobs, manifest


def quota(key):
    try:
        req = urllib.request.Request(SUBSCRIPTION, headers={"xi-api-key": key})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        used, limit = d.get("character_count"), d.get("character_limit")
        if used is not None and limit is not None:
            return used, limit
    except Exception:
        pass          # informational only — never block a run on this
    return None, None


def synthesise(key, text):
    body = json.dumps({"text": text, "model_id": MODEL_ID}).encode("utf-8")
    req = urllib.request.Request(API + VOICE_ID, data=body, headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
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
    size = path.stat().st_size
    if size < MIN_BYTES:
        return f"only {size} bytes — almost certainly an error response, not audio"
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"could not run ffprobe: {e}"
    if out.returncode != 0:
        return f"ffprobe rejected the file: {out.stderr.strip()[:120]}"
    try:
        if float(out.stdout.strip()) < MIN_SECONDS:
            return f"duration {out.stdout.strip()}s is too short to be real"
    except ValueError:
        return f"ffprobe gave no duration: {out.stdout.strip()[:80]}"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--go", action="store_true", help="actually call the API")
    ap.add_argument("--only", default="", help="comma-separated note ids")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    deck = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    notes = deck["notes"]
    if only:
        unknown = only - {n["id"] for n in notes}
        if unknown:
            die(f"unknown note id(s): {', '.join(sorted(unknown))}")

    jobs, manifest = build_jobs(notes, only)
    todo = [j for j in jobs if not j["relink_only"]]
    relink = [j for j in jobs if j["relink_only"]]
    chars = sum(len(j["text"]) for j in todo)

    print(f"voice {VOICE_NAME} ({VOICE_ID}), model {MODEL_ID}")
    if not todo and not relink:
        print("nothing to do — every clip is present and current")
        return 0
    for j in todo:
        print(f"  synth  {j['rel']:<38} {len(j['text']):>4} chars  {j['text'][:44]!r}")
    for j in relink:
        print(f"  relink {j['rel']:<38} (file already correct)")
    print(f"\n{len(todo)} clip(s), {chars} characters")

    if not args.go:
        key = load_key()
        used, limit = quota(key)
        if limit:
            print(f"quota: {used}/{limit} used, {limit - used} left "
                  f"— this run needs {chars}")
            if chars > limit - used:
                die("this run would exceed the remaining quota")
        print("\ndry run. Re-run with --go to synthesise.")
        return 0

    key = load_key()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    failed = []

    for j in relink:
        j["holder"][j["key"]] = j["rel"]
        print(f"  relinked {j['rel']}")

    for i, j in enumerate(todo, 1):
        dest = ROOT / j["rel"]
        print(f"  [{i}/{len(todo)}] {j['rel']} ... ", end="", flush=True)
        try:
            data = synthesise(key, j["text"])
        except RuntimeError as e:
            print("FAILED")
            failed.append((j["rel"], str(e)))
            continue
        # Write to a temp file and only adopt it once it verifies, so a bad
        # response can never masquerade as a finished clip.
        tmp = Path(tempfile.mkstemp(dir=AUDIO_DIR, suffix=".part")[1])
        tmp.write_bytes(data)
        problem = verify(tmp)
        if problem:
            tmp.unlink(missing_ok=True)
            print("FAILED")
            failed.append((j["rel"], problem))
            continue
        tmp.replace(dest)
        dest.chmod(0o644)
        manifest[j["rel"]] = {"fingerprint": j["fp"], "voice": VOICE_ID,
                              "voice_name": VOICE_NAME, "model": MODEL_ID,
                              "text": j["text"], "bytes": len(data)}
        j["holder"][j["key"]] = j["rel"]
        print(f"ok ({len(data) // 1024} KB)")
        time.sleep(PAUSE)

    # Persist whatever succeeded, even if some clips failed — a partial run
    # must leave the deck consistent so a re-run resumes cleanly.
    deck["notes"] = [reorder({**n, **({"sentence": reorder(n["sentence"], SENT_KEY_ORDER)}
                                      if isinstance(n.get("sentence"), dict) else {})},
                             KEY_ORDER) for n in notes]
    NOTES_PATH.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2,
                                        sort_keys=True) + "\n", encoding="utf-8")

    if failed:
        print(f"\n{len(failed)} clip(s) FAILED — nothing was written for these:")
        for rel, why in failed:
            print(f"  {rel}\n      {why}")
        print("\nRe-run to retry just these; everything else is already saved.")
        return 1
    print(f"\n{len(todo)} clip(s) written. Run tools/validate.py next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

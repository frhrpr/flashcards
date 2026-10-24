#!/usr/bin/env python3
"""Listening episodes: one evenly paced mp3 per story, and the list the app reads.

    python3 tools/listen.py lessons/<date>-sluchanie-<slug>.story.txt          # dry run
    python3 tools/listen.py lessons/<date>-sluchanie-<slug>.story.txt --go     # synthesise
    python3 tools/listen.py --index                                            # rebuild the list only

Writes `listen/<slug>.mp3` (served by the site, and the file to send by hand)
and rebuilds `listen/episodes.json` from every story whose mp3 exists. The list is
generated, never edited: the story file is the one source for the text and
the questions.

The story file is the usual storycheck format, with the questions in their
own section so storycheck covers their words too:

    Jest sobota. Jest rano. ...

    --- pytania ---

    Co pije Marek rano? | wodę | *kawę | lody      (* marks the right answer)

    --- lemmas ---
    ...

Run storycheck first.

Every choice here was made by ear on 2026-10-21, on the first episode:

- **Voice River** (`SAz9YHcvj6GT2YYXdXww`). Antoni, the deck's sentence voice,
  sounded aggressive over a whole minute. Six calm premade voices were
  auditioned and River was picked. Cards keep Antoni, so the deck stays
  consistent.
- **One request per sentence**, joined with silence made here: SENT_GAP between
  sentences, PARA_GAP between paragraphs. Whole paragraphs in one request
  came out with the first sentences run together, and `<break>` tags only
  helped between paragraphs.
- **Each request carries its neighbours as `previous_text` / `next_text` and
  is pinned to Polish** (`eleven_turbo_v2_5`, `language_code: "pl"`). Splitting
  into sentences starved the model of context: "Sven kupuje lody" and
  "On kupuje ser" both came back read as English. A test of six variants
  showed either fix alone cured it; both are used.
- **Polish names only.** Even pinned to Polish and with context, "Swen" got an
  English W. Foreign names invite the model to switch language, so the
  listening stories have their own cast (Marek, Ania, their cat) rather than
  Sven and Ewa from the reading stories.
- **Speed 0.85.** Slow enough for a beginner, still natural.
- A dialogue tag stays with its line ("Idziemy do parku? pyta Ania.") so it
  is read as one utterance; dashes are dropped because they are not spoken.
"""
import argparse, json, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audio  # noqa: E402  (load_key, TTS_API)

VOICE = "SAz9YHcvj6GT2YYXdXww"   # River
MODEL = "eleven_turbo_v2_5"
SETTINGS = {"stability": 0.6, "similarity_boost": 0.75, "speed": 0.85}
SENT_GAP, PARA_GAP = 0.7, 1.5
TRIM = ("silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse")


def sentences(path):
    body = path.read_text(encoding="utf-8").split("--- lemmas ---")[0]
    body = body.split("--- pytania ---")[0].strip()
    paras = []
    for p in body.split("\n\n"):
        p = re.sub(r"\s*—\s*", " ", p).strip()
        out = []
        for s in re.findall(r"[^.!?]+[.!?]", p):
            s = s.strip()
            if out and s[0].islower():      # dialogue tag: keep with its line
                out[-1] += " " + s
            else:
                out.append(s)
        paras.append(out)
    return paras

REPO = Path(__file__).resolve().parent.parent
LISTEN = REPO / "listen"


def slug_of(path):
    return re.sub(r"^\d{4}-\d{2}-\d{2}-sluchanie-", "", path.name.replace(".story.txt", ""))


def questions(path):
    """One per line: question | option | *right option | option. Exactly one
    star per line, at least two options, or this refuses."""
    body = path.read_text(encoding="utf-8").split("--- lemmas ---")[0]
    if "--- pytania ---" not in body:
        return []
    out = []
    for line in body.split("--- pytania ---")[1].strip().splitlines():
        if not line.strip():
            continue
        q, *opts = [x.strip() for x in line.split("|")]
        stars = [i for i, o in enumerate(opts) if o.startswith("*")]
        if len(opts) < 2 or len(stars) != 1:
            sys.exit(f"listen: {path.name}: needs 2+ options and exactly one *: {line}")
        out.append({"q": q, "options": [o.lstrip("*").strip() for o in opts],
                    "answer": stars[0]})
    return out


def write_index():
    """listen/episodes.json from every story whose mp3 is in listen/. Newest first."""
    eps = []
    for story in sorted((REPO / "lessons").glob("*-sluchanie-*.story.txt")):
        slug = slug_of(story)
        mp3 = LISTEN / f"{slug}.mp3"
        if not mp3.exists():
            continue
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", mp3], capture_output=True, text=True).stdout.strip()
        title = re.sub(r"^\d+-", "", slug).replace("-", " ").capitalize()
        body = story.read_text(encoding="utf-8").split("--- lemmas ---")[0]
        text = [p.strip() for p in body.split("--- pytania ---")[0].strip().split("\n\n")]
        eps.append({"id": slug, "title": title, "date": story.name[:10],
                    "audio": f"listen/{slug}.mp3", "seconds": round(float(dur)),
                    "text": text, "questions": questions(story)})
    eps.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    (LISTEN / "episodes.json").write_text(
        json.dumps({"schema": 1, "episodes": eps}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"wrote listen/episodes.json ({len(eps)} episode(s))")


def synth(key, text, prev, nxt):
    body = {"text": text, "model_id": MODEL, "language_code": "pl",
            "voice_settings": SETTINGS}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    req = urllib.request.Request(audio.TTS_API + VOICE, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", type=Path, nargs="?")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--index", action="store_true", help="rebuild listen/episodes.json only")
    a = ap.parse_args()
    if a.index:
        write_index()
        return 0
    if not a.story:
        ap.error("give a story file, or --index")
    paras = sentences(a.story)
    qs = questions(a.story)
    flat = [s for p in paras for s in p]
    slug = slug_of(a.story)
    dest = LISTEN / f"{slug}.mp3"
    print(f"{len(flat)} sentences, {sum(map(len, flat))} characters spoken")
    for p in paras:
        print("  " + " | ".join(p))
    print(f"{len(qs)} question(s)")
    if not a.go:
        print(f"\ndry run. Re-run with --go to write {dest}")
        return 0
    key = audio.load_key()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(SENT_GAP), td / "s.wav")
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(PARA_GAP), td / "p.wav")
        parts, i = [], 0
        for pi, p in enumerate(paras):
            for si, s in enumerate(p):
                prev = " ".join(flat[max(0, i - 2):i]) or None
                nxt = " ".join(flat[i + 1:i + 3]) or None
                raw = td / f"{i:03d}.mp3"
                raw.write_bytes(synth(key, s, prev, nxt))
                wav = td / f"{i:03d}.wav"
                ff("-i", raw, "-af", TRIM, "-ar", "44100", "-ac", "1", wav)
                parts.append(wav)
                if si < len(p) - 1:
                    parts.append(td / "s.wav")
                i += 1
                print(f"  [{i}/{len(flat)}] {s}")
            if pi < len(paras) - 1:
                parts.append(td / "p.wav")
        (td / "list.txt").write_text("".join(f"file '{x}'\n" for x in parts))
        dest.parent.mkdir(parents=True, exist_ok=True)
        ff("-f", "concat", "-safe", "0", "-i", td / "list.txt",
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-b:a", "128k", dest)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", dest], capture_output=True, text=True).stdout.strip()
    print(f"wrote {dest}  ({float(dur):.0f} s)")
    write_index()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Listening episodes: one evenly paced mp3 per story, and the list the app reads.

    python3 tools/listen.py lessons/<date>-sluchanie-<slug>.story.txt          # dry run
    python3 tools/listen.py lessons/<date>-sluchanie-<slug>.story.txt --go     # synthesise
    python3 tools/listen.py --index                                            # rebuild the list only
    python3 tools/listen.py <story> --go --retake     # ask for a new take of the whole story
    python3 tools/listen.py <story> --go --per-sentence [--redo 3,7]   # the old way, see below

**The default since 2026-10-25 is one take of the whole story** (`main_whole`):
the per-character timestamps from /with-timestamps say where each sentence
ends, and the pause there is lengthened to SENT_GAP / PARA_GAP. The teacher
heard the sentence-by-sentence version as "a bunch of sentences stitched
together" — the tone reset and an in-breath came at every join — and chose
this one. Pauses *inside* a sentence are the voice's own: in "Ania mówi:
Dobrze!" the colon got almost none, which only splitting the line would fix.
The notes below describe the per-sentence mode, kept for comparison.

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

**Each sentence's take is kept** in out/listen-parts/<slug>/NNN.mp3 with its
text beside it, and reused on the next run while the text is unchanged. A
TTS take is different every time and now and then comes back with a tap or
a glitch in it (episode 2, 2026-10-25); regenerating the whole episode to
fix one sentence throws away the good takes with the bad. `--redo` names the
sentences to take again; the run prints each sentence's start time in the
finished mp3, so "a tap at 0:23" maps to a number.

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
import argparse, base64, json, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audio  # noqa: E402  (load_key, TTS_API)
from deckio import out_dir  # noqa: E402

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


def stray_tail(path):
    """Where a take should end if it closes on a stray blip, else None.

    Some takes come back with a click or breath after the speech has ended:
    a gap of silence, then 20-80 ms of sound at the very end of the file.
    The -50 dB trim keeps it, so it lands just before the pause and is heard
    as a tap (episode 2, 2026-10-25: five of 21 takes). Speech never ends
    that way, so a final burst under SHORT seconds after a gap of at least
    GAP seconds is cut at the start of the gap."""
    SHORT, GAP, BLIP_DB = 0.12, 0.08, -40
    out = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-45dB:d=%s" % GAP,
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", path], capture_output=True, text=True).stdout)
    # the last silence that closes before the file does, and what follows it
    gaps = [(st, en) for st, en in zip(starts, ends) if en < dur - 0.005]
    if not (gaps and dur - gaps[-1][1] < SHORT and gaps[-1][0] > 0.3):
        return None
    # silencedetect also "ends" a silence at the end of the file; only a tail
    # that is actually loud is a blip
    out = subprocess.run(["ffmpeg", "-i", path, "-af",
                          f"atrim=start={gaps[-1][1]},astats=metadata=1,"
                          "ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-",
                          "-f", "null", "-"], capture_output=True, text=True).stdout
    peaks = [float(x) for x in re.findall(r"Peak_level=(-?[\d.]+)", out)]
    return gaps[-1][0] if peaks and max(peaks) > BLIP_DB else None


def whole_take(key, paras):
    """The whole story in one request, with per-character timestamps.

    Returns (mp3 bytes, [(sentence, start_s, end_s), ...], [para index per
    sentence]). One take keeps the voice's tone and breathing continuous;
    the timestamps say where each sentence ends so the pauses can be made
    as long as a beginner needs."""
    text, spans, para_of = "", [], []
    for pi, p in enumerate(paras):
        for si, sent in enumerate(p):
            if text:
                text += "\n\n" if si == 0 else " "
            spans.append((len(text), len(text) + len(sent)))
            para_of.append(pi)
            text += sent
    body = {"text": text, "model_id": MODEL, "language_code": "pl", "voice_settings": SETTINGS}
    req = urllib.request.Request(audio.TTS_API + VOICE + "/with-timestamps", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.load(r)
    al = res["alignment"]
    if "".join(al["characters"]) != text:
        sys.exit("listen: the timestamps do not line up with the text sent; nothing written")
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    times = [(s_, st[a], en[b - 1]) for (a, b), s_ in zip(spans, [x for p in paras for x in p])]
    return base64.b64decode(res["audio_base64"]), times, para_of


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", type=Path, nargs="?")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--index", action="store_true", help="rebuild listen/episodes.json only")
    ap.add_argument("--redo", default="", help="sentence numbers to take again, e.g. 3,7")
    ap.add_argument("--per-sentence", action="store_true", help="the old way: one request per sentence")
    ap.add_argument("--retake", action="store_true", help="ask for a new take of the whole story")
    a = ap.parse_args()
    if a.index:
        write_index()
        return 0
    if not a.story:
        ap.error("give a story file, or --index")
    paras = sentences(a.story)
    if not a.per_sentence:
        return main_whole(a, paras)
    qs = questions(a.story)
    flat = [s for p in paras for s in p]
    slug = slug_of(a.story)
    dest = LISTEN / f"{slug}.mp3"
    parts_dir = out_dir("listen-parts") / slug
    redo = {int(x) for x in a.redo.split(",") if x.strip()}
    bad = [n for n in redo if not 1 <= n <= len(flat)]
    if bad:
        sys.exit(f"listen: --redo {bad}: there are {len(flat)} sentences")
    def cached(i):
        mp3, txt = parts_dir / f"{i + 1:03d}.mp3", parts_dir / f"{i + 1:03d}.txt"
        return (i + 1 not in redo and mp3.exists() and txt.exists()
                and txt.read_text(encoding="utf-8") == flat[i])
    todo = [i for i in range(len(flat)) if not cached(i)]
    print(f"{len(flat)} sentences, {sum(map(len, flat))} characters spoken; "
          f"{len(todo)} to synthesise ({sum(len(flat[i]) for i in todo)} characters), "
          f"{len(flat) - len(todo)} kept from the last run")
    n = 0
    for p in paras:
        print("  " + " | ".join(f"{n + j + 1}. {x}" for j, x in enumerate(p)))
        n += len(p)
    print(f"{len(qs)} question(s)")
    if not a.go:
        print(f"\ndry run. Re-run with --go to write {dest}")
        return 0
    key = audio.load_key() if todo else None
    parts_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(SENT_GAP), td / "s.wav")
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(PARA_GAP), td / "p.wav")
        parts, i, t, timeline = [], 0, 0.0, []
        def secs(f):
            return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
        for pi, p in enumerate(paras):
            for si, s in enumerate(p):
                raw = parts_dir / f"{i + 1:03d}.mp3"
                if i in todo:
                    prev = " ".join(flat[max(0, i - 2):i]) or None
                    nxt = " ".join(flat[i + 1:i + 3]) or None
                    raw.write_bytes(synth(key, s, prev, nxt))
                    (parts_dir / f"{i + 1:03d}.txt").write_text(s, encoding="utf-8")
                wav = td / f"{i:03d}.wav"
                cut = stray_tail(raw)
                if cut is not None:
                    print(f"  {i + 1:>2}: stray sound after the speech, cut at {cut:.2f}s")
                ff("-i", raw, "-af", (f"atrim=0:{cut}," if cut is not None else "") + TRIM
                   , "-ar", "44100", "-ac", "1", wav)
                timeline.append((i + 1, t, s, i in todo))
                t += secs(wav)
                parts.append(wav)
                if si < len(p) - 1:
                    parts.append(td / "s.wav"); t += SENT_GAP
                i += 1
            if pi < len(paras) - 1:
                parts.append(td / "p.wav"); t += PARA_GAP
        for num, start, s, new in timeline:
            print(f"  {num:>2}  {int(start // 60)}:{start % 60:04.1f}  {'new ' if new else 'kept'}  {s}")
        (td / "list.txt").write_text("".join(f"file '{x}'\n" for x in parts))
        dest.parent.mkdir(parents=True, exist_ok=True)
        ff("-f", "concat", "-safe", "0", "-i", td / "list.txt",
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-b:a", "128k", dest)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", dest], capture_output=True, text=True).stdout.strip()
    print(f"wrote {dest}  ({float(dur):.0f} s)")
    write_index()
    return 0


def main_whole(a, paras):
    """One take, then the pause after each sentence lengthened to SENT_GAP or
    PARA_GAP. Each cut sits just after the sentence's last sound, so an
    in-breath stays where the voice put it, before the next sentence."""
    flat = [x for p in paras for x in p]
    slug = slug_of(a.story)
    dest = LISTEN / f"{slug}.mp3"
    parts_dir = out_dir("listen-parts") / slug
    cache = parts_dir / "whole.json"
    text_key = json.dumps(paras, ensure_ascii=False)
    have = (not a.retake and cache.exists()
            and json.loads(cache.read_text(encoding="utf-8")).get("paras") == text_key)
    print(f"{len(flat)} sentences, {sum(map(len, flat))} characters; "
          + ("reusing the saved take" if have else "one new take"))
    if not a.go:
        print(f"\ndry run. Re-run with --go to write {dest}")
        return 0
    parts_dir.mkdir(parents=True, exist_ok=True)
    if have:
        saved = json.loads(cache.read_text(encoding="utf-8"))
        mp3, times, para_of = base64.b64decode(saved["mp3"]), saved["times"], saved["para_of"]
    else:
        mp3, times, para_of = whole_take(audio.load_key(), paras)
        cache.write_text(json.dumps({"paras": text_key, "times": times, "para_of": para_of,
                                     "mp3": base64.b64encode(mp3).decode()}), encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "take.mp3").write_bytes(mp3)
        ff("-i", td / "take.mp3", "-ar", "44100", "-ac", "1", td / "take.wav")
        cuts, adds = [0.0], []
        for i in range(len(times) - 1):
            end, nxt = times[i][2], times[i + 1][1]
            gap = max(0.0, nxt - end)
            cuts.append(end + min(0.06, gap / 2))
            want = PARA_GAP if para_of[i + 1] != para_of[i] else SENT_GAP
            adds.append(max(0.0, want - gap))
        parts, t, line = [], 0.0, []
        for i, c in enumerate(cuts):
            seg = td / f"{i:03d}.wav"
            end = f":end={cuts[i + 1]}" if i + 1 < len(cuts) else ""
            ff("-i", td / "take.wav", "-af", f"atrim=start={c}{end},asetpts=PTS-STARTPTS", seg)
            parts.append(seg)
            line.append((i + 1, t + (times[i][1] - c if i else 0), flat[i]))
            t += (cuts[i + 1] - c) if i + 1 < len(cuts) else 0
            if i < len(adds) and adds[i] > 0:
                sil = td / f"s{i:03d}.wav"
                ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{adds[i]:.3f}", sil)
                parts.append(sil)
                t += adds[i]
        (td / "list.txt").write_text("".join(f"file '{x}'\n" for x in parts))
        dest.parent.mkdir(parents=True, exist_ok=True)
        ff("-f", "concat", "-safe", "0", "-i", td / "list.txt",
           "-af", "silenceremove=start_periods=1:start_threshold=-50dB,loudnorm=I=-16:TP=-1.5:LRA=11",
           "-ar", "44100", "-b:a", "128k", dest)
    for num, start, sent in line:
        print(f"  {num:>2}  {int(start // 60)}:{start % 60:04.1f}  {sent}")
    print(f"wrote {dest}")
    write_index()
    return 0


if __name__ == "__main__":
    sys.exit(main())

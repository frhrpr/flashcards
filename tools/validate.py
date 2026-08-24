#!/usr/bin/env python3
"""Check deck/notes.json before it reaches a student.

Errors (exit 1) are things that would break the app or teach something wrong.
Warnings (exit 0) are things worth a human look. Run it after every edit:

    python3 tools/validate.py
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES, VOCAB = ROOT / "deck/notes.json", ROOT / "deck/vocab.csv"
MANIFEST = ROOT / "media/manifest.json"

CARD_TYPES = {"recognition", "production", "listening", "form"}
POS = {"noun", "verb", "adjective", "adverb", "preposition", "conjunction",
       "particle", "pronoun", "interjection"}
ID_RE = re.compile(r"[a-z0-9_]+$")

# Deliberately NOT checked: whether every word in a sentence is one Evert
# already knows. Doing that properly needs a lemmatiser — Polish inflection
# means "nie mam psa" is a perfectly good sentence for "pies", and prefix
# matching flags być→jest and skakać→skacze on every correct sentence.
# Allowlist compliance is enforced where it belongs: the generator is handed
# the allowlist, and a human reads the result before `reviewed` is set.

errors, warnings = [], []
def err(nid, msg): errors.append(f"{nid}: {msg}")
def warn(nid, msg): warnings.append(f"{nid}: {msg}")


def load():
    try:
        data = json.loads(NOTES.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"deck/notes.json is not valid JSON: {e}")
    if data.get("schema") != 1:
        sys.exit(f"unknown schema version: {data.get('schema')!r}")
    vocab = {}
    with VOCAB.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vocab[row["note_id"]] = row
    return data["notes"], vocab


def check_sentence(nid, s, word):
    for field in ("pl", "en", "gap", "answer", "answer_lemma"):
        if not s.get(field):
            err(nid, f"sentence.{field} is missing or empty")
            return
    if "___" not in s["gap"]:
        err(nid, "sentence.gap has no ___ placeholder")
    if s["gap"].count("___") > 1:
        err(nid, "sentence.gap has more than one ___")
    # The gap filled with the answer must reproduce the sentence exactly,
    # or the student is shown one string and graded against another.
    if s["gap"].replace("___", s["answer"]) != s["pl"]:
        err(nid, "sentence.gap + answer does not reconstruct sentence.pl")
    # A sentence-initial gap used to warn here, on the theory that the answer's
    # capital is ambiguous. It is not worth a warning: the blank hides the
    # capital, so nothing leaks before he answers, and whether the capital is
    # positional or lexical changes nothing he would write. Polish drops
    # pronouns, so "Lubię mojego psa." cannot avoid starting with the verb —
    # the check fired on correct sentences, which is how warnings get ignored.
    #
    # What is worth catching is the same capital in a place position cannot
    # explain: a mid-sentence answer capitalised when the headword is not.
    # That is always a typo in the data.
    if (s["answer"][:1].isupper() and not word[:1].isupper()
            and not s["gap"].strip().startswith("___")):
        warn(nid, f"answer {s['answer']!r} is capitalised mid-sentence, but "
                  f"{word!r} is not a proper noun")
    if s["answer_lemma"] != word:
        warn(nid, f"answer_lemma {s['answer_lemma']!r} is not the note word {word!r}")


def main():
    notes, vocab = load()
    todo = {"image": [], "audio": [], "sentence audio": [],
            "listening audio": [], "review": []}
    manifest = {}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"media/manifest.json is not valid JSON: {e}")
    sources = {"commons": 0, "tts": 0, "unrecorded": 0}

    seen = set()
    for n in notes:
        nid = n.get("id", "<no id>")
        if not ID_RE.fullmatch(nid):
            err(nid, "id must match [a-z0-9_]+ (it becomes a Firestore field path)")
        if nid in seen:
            err(nid, "duplicate id")
        seen.add(nid)

        for field in ("word", "gloss", "pos", "ipa", "sentence", "cards"):
            if not n.get(field):
                err(nid, f"{field} is missing or empty")

        if n.get("pos") not in POS:
            err(nid, f"pos must be one of {sorted(POS)}, got {n.get('pos')!r}")

        for t in n.get("cards", []):
            if t not in CARD_TYPES:
                err(nid, f"unknown card type {t!r}")
        # A listening card needs word audio, but media arrives after the text,
        # so this is a to-do rather than an error — the app drops the card
        # type until the file exists (see NEEDS in index.html).
        if "listening" in n.get("cards", []) and "audio" not in n:
            todo["listening audio"].append(nid)
        # Only worth saying once a note is otherwise finished; before that the
        # "awaiting image" to-do already covers it.
        if (n.get("reviewed") and "production" in n.get("cards", [])
                and not n.get("image") and not n.get("note")):
            warn(nid, "production card has only the English gloss as a cue (no image)")

        if isinstance(n.get("sentence"), dict):
            check_sentence(nid, n["sentence"], n.get("word", ""))

        # Media is absent until generated. A path that IS set must resolve,
        # and every clip must have provenance — without it, tools/audio.py
        # cannot tell a stale clip from a current one and will never rebuild.
        clips = [(key, n[key]) for key in ("image", "audio") if key in n]
        if isinstance(n.get("sentence"), dict) and "audio" in n["sentence"]:
            clips.append(("sentence.audio", n["sentence"]["audio"]))
        for key, rel in clips:
            if not (ROOT / rel).exists():
                err(nid, f"{key} points at a missing file: {rel}")
            elif key.endswith("audio"):
                entry = manifest.get(rel)
                if not entry:
                    err(nid, f"{key} has no entry in media/manifest.json — "
                             f"delete {rel} and re-run tools/audio.py")
                    sources["unrecorded"] += 1
                else:
                    sources[entry.get("source", "unrecorded")] = \
                        sources.get(entry.get("source", "unrecorded"), 0) + 1
                    if entry.get("text") != (n["word"] if key == "audio"
                                             else n["sentence"]["pl"]):
                        err(nid, f"{key} was generated from "
                                 f"{entry.get('text')!r}, which is no longer the text — "
                                 f"re-run tools/audio.py")

        if n.get("reviewed") and not (n.get("audio") and
                                      (n.get("sentence") or {}).get("audio")):
            err(nid, "marked reviewed but audio is missing")
        # Not-yet-generated media is normal, so it is counted rather than
        # listed — 30 lines of "no image yet" would bury a real problem.
        for key in ("image", "audio"):
            if key not in n:
                todo[key].append(nid)
        if isinstance(n.get("sentence"), dict) and "audio" not in n["sentence"]:
            todo["sentence audio"].append(nid)
        if "image" in n and not n.get("image_alt"):
            err(nid, "image without image_alt")

        if not n.get("reviewed"):
            todo["review"].append(nid)

        # Conjugation drills are notes but not vocabulary: jestem is a form of
        # być, not a word he has "learned", so they stay out of vocab.csv.
        if n.get("kind") == "form":
            if not n.get("parent"):
                err(nid, "form note has no parent verb")
            elif n["parent"] not in {m["id"] for m in notes}:
                err(nid, f"parent {n['parent']!r} is not a note")
            if n.get("cards") != ["form"]:
                err(nid, "a form note should carry exactly the form card")
            continue

        row = vocab.get(nid)
        if row is None:
            err(nid, "not in deck/vocab.csv")
        else:
            if row["word"] != n.get("word"):
                err(nid, f"word {n.get('word')!r} disagrees with vocab.csv {row['word']!r}")
            if row["status"] != "carded":
                err(nid, f"vocab.csv status is {row['status']!r}, expected 'carded'")
            if row["flashcard"] != "yes":
                err(nid, "vocab.csv says flashcard=no but a note exists")

    for nid, row in vocab.items():
        if row["status"] == "carded" and nid not in seen:
            err(nid, "vocab.csv says carded but there is no note")

    print(f"{len(notes)} notes checked\n")
    for w in warnings:
        print(f"  warn   {w}")
    if warnings:
        print()

    human = sources.get("commons", 0)
    synth = sources.get("tts", 0)
    if human or synth:
        print(f"  audio  {human} human recording(s), {synth} synthesised")
    for label, ids in todo.items():
        if not ids:
            continue
        shown = ", ".join(ids[:6]) + (f" +{len(ids) - 6} more" if len(ids) > 6 else "")
        print(f"  todo   {len(ids)}/{len(notes)} awaiting {label}: {shown}")
    if any(todo.values()):
        print()

    for e in errors:
        print(f"  ERROR  {e}")
    if errors:
        print(f"\n{len(errors)} error(s) — not safe to ship")
        return 1
    print(f"no errors ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())

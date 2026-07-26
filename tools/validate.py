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

CARD_TYPES = {"recognition", "cloze"}
GENDERS = {"m-anim", "m-inan", "f", "n"}
ASPECTS = {"impf", "pf"}
ID_RE = re.compile(r"[a-z0-9_]+$")
# Polish letters only — used to pull words out of a sentence.
WORD_RE = re.compile(r"[a-ząćęłńóśźż]+", re.IGNORECASE)

# Inflected forms whose stem does not prefix-match their lemma — consonant
# alternation (skakać → skacze), ć→j (pić → pije), suppletion (być → jest).
# Extend as the deck grows. Keeping this honest matters: a check that warns
# on every correct sentence is one you stop reading.
IRREGULAR = {
    "jest": "być", "jestem": "być", "są": "być", "było": "być",
    "pije": "pić", "piję": "pić", "pijesz": "pić",
    "je": "jeść", "jem": "jeść", "jedzą": "jeść",
    "skacze": "skakać", "skaczę": "skakać",
    "idzie": "iść", "idę": "iść", "idziesz": "iść",
    "mówi": "mówić", "mówię": "mówić",
    "widzi": "widzieć", "widzę": "widzieć",
    "siedzi": "siedzieć", "siedzę": "siedzieć",
    "daje": "dawać", "daję": "dawać",
}

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
    if s["gap"].strip().startswith("___"):
        warn(nid, "gap is sentence-initial — capitalisation makes the answer ambiguous")
    if s["answer_lemma"] != word:
        warn(nid, f"answer_lemma {s['answer_lemma']!r} is not the note word {word!r}")


def check_vocabulary(nid, sentence_pl, known_words, known_stems):
    """Heuristic: every word should trace back to something he already knows.

    This is not a lemmatiser. It resolves known irregulars, then falls back to
    a 4-character stem match, so treat a hit as 'look at this', not 'wrong'.
    """
    for w in WORD_RE.findall(sentence_pl.lower()):
        if len(w) <= 3:
            continue  # function words: to, na, w, i, do, pod ...
        if w in known_words or IRREGULAR.get(w) in known_words:
            continue
        stem = w[:4]
        if any(w.startswith(k) or k.startswith(stem) for k in known_stems):
            continue
        warn(nid, f"sentence word {w!r} may be outside the allowlist "
                  f"(add to IRREGULAR in this script if it is a known form)")


def main():
    notes, vocab = load()
    known_words = {r["word"].lower() for r in vocab.values()}
    known_stems = {w[:4] for w in known_words if len(w) >= 3}
    todo = {"image": [], "audio": [], "sentence audio": [], "review": []}

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

        pos = n.get("pos")
        if pos == "noun" and n.get("gender") not in GENDERS:
            err(nid, f"noun needs gender one of {sorted(GENDERS)}, got {n.get('gender')!r}")
        if pos == "verb":
            if n.get("aspect") not in ASPECTS:
                err(nid, f"verb needs aspect impf/pf, got {n.get('aspect')!r}")
            if not n.get("aspect_pair"):
                warn(nid, "verb has no aspect_pair")

        for t in n.get("cards", []):
            if t not in CARD_TYPES:
                err(nid, f"unknown card type {t!r}")
        if "cloze" in n.get("cards", []) and not n.get("sentence"):
            err(nid, "cloze card needs a sentence")

        if isinstance(n.get("sentence"), dict):
            check_sentence(nid, n["sentence"], n.get("word", ""))
            check_vocabulary(nid, n["sentence"].get("pl", ""), known_words, known_stems)

        # Media is absent until generated. A path that IS set must resolve.
        for key in ("image", "audio"):
            if key in n and not (ROOT / n[key]).exists():
                err(nid, f"{key} points at a missing file: {n[key]}")
        if isinstance(n.get("sentence"), dict) and "audio" in n["sentence"]:
            if not (ROOT / n["sentence"]["audio"]).exists():
                err(nid, f"sentence.audio points at a missing file: {n['sentence']['audio']}")
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

#!/usr/bin/env python3
"""Check a draft story against what the student has actually MET.

    python3 tools/storycheck.py draft.txt --stub > draft.txt.new   # skeleton map
    python3 tools/storycheck.py draft.txt                          # check it

Why this exists: a lesson story was built against `deck/vocab.csv` and fifteen
of its words turned out to be ones he had never seen — carded, yes, but
sitting unintroduced in the bank. The homework written to fix that repeated
the mistake with three more. `vocab.csv` is the *sentence allowlist*; what he
has met is a set less than half its size, and only the second one decides
whether he can read a story.

## The file

One artefact: the story, then a `--- lemmas ---` line, then one
`token = headword` per line. `-` on the right means "not vocabulary" — a
proper noun, or anything else deliberately outside the deck.

    Marek mieszka w nowym mieście.

    --- lemmas ---
    Marek    = -
    mieszka  = mieszkać
    w        = w

`--stub` writes that skeleton for you with the right-hand sides blank. It
lists the tokens; it does not guess what they mean.

## Why there is no lemmatiser

There was one, briefly. It cut words back a letter at a time and matched
stems, and in twenty minutes it needed four patches: it missed every
infinitive, read sentence-initial verbs as proper nouns, resolved `duże` to
`dużo` rather than `duży`, and could not reach `śmieje` at all. Each new
batch of vocabulary would have wanted another exception.

The judgement about what a Polish word is belongs to whoever writes the
story, who has just made that judgement anyway in order to write it. What
does not belong to them is remembering to check sixty headwords against a
database, which is the part that failed twice. So the split is: you supply
the mapping, this verifies you covered every token and answers the question
the mapping cannot.

Anything unmapped is an error, not a warning. A token nobody classified is a
word nobody checked, and that must never look like a pass.
"""
import argparse, csv, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "deck" / "notes.json"
VOCAB = ROOT / "deck" / "vocab.csv"
APP = ROOT / "index.html"

SEP = re.compile(r"^\s*-{2,}\s*lemmas\s*-{2,}\s*$", re.I | re.M)
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)   # letters only: gap numbers are not words
SKIP = "-"


def die(msg):
    sys.exit(f"storycheck: {msg}")


def split_file(text, path):
    parts = SEP.split(text)
    if len(parts) == 1:
        die(f"{path}: no '--- lemmas ---' line. Run with --stub to make one.")
    if len(parts) > 2:
        die(f"{path}: more than one '--- lemmas ---' line")
    return parts[0], parts[1]


def parse_map(block, path):
    out, seen = {}, {}
    for i, raw in enumerate(block.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            die(f"{path}: line {i} is not 'token = headword': {raw.strip()!r}")
        tok, head = (x.strip() for x in line.split("=", 1))
        if not tok or not head:
            die(f"{path}: line {i} has an empty side: {raw.strip()!r}")
        low = tok.lower()
        if low in seen and seen[low] != head:
            die(f"{path}: {tok!r} is mapped to both {seen[low]!r} and {head!r}")
        seen[low] = head
        out[low] = head
    if not out:
        die(f"{path}: the lemma block is empty")
    return out


def met_notes(uid):
    key = re.search(r'apiKey: "([^"]+)"', APP.read_text(encoding="utf-8"))
    if not key:
        die("no apiKey in index.html")
    url = (f"https://firestore.googleapis.com/v1/projects/flashcards-f5b40/"
           f"databases/(default)/documents/progress/{uid}?key={key.group(1)}")
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            doc = json.load(r)
    except Exception as e:
        die(f"could not read progress for {uid!r}: {e}")
    if "fields" not in doc:
        die(f"no progress document for {uid!r}")
    return {k.rsplit("__", 1)[0]
            for k in doc["fields"]["cards"]["mapValue"]["fields"]}


def stub(text, path):
    body, _, _ = text.partition("--- lemmas ---")
    order, seen = [], set()
    for tok in TOKEN.findall(body):
        if tok.lower() not in seen:
            seen.add(tok.lower())
            order.append(tok)
    width = max(len(t) for t in order) if order else 8
    lines = "\n".join(f"{t:<{width}} = " for t in order)
    return (f"{body.rstrip()}\n\n--- lemmas ---\n"
            f"# one 'token = headword' per line; '-' means not vocabulary\n"
            f"{lines}\n")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story")
    ap.add_argument("--user", default="evert")
    ap.add_argument("--stub", action="store_true",
                    help="print the file with a blank lemma block appended")
    args = ap.parse_args()

    path = Path(args.story)
    if not path.exists():
        die(f"no such file: {path}")
    text = path.read_text(encoding="utf-8")

    if args.stub:
        sys.stdout.write(stub(text, path))
        return 0

    body, block = split_file(text, path)
    lemmas = parse_map(block, path)
    vocab = {r["word"]: r for r in
             csv.DictReader(VOCAB.read_text(encoding="utf-8").splitlines())}
    notes = {n["word"]: n for n in
             json.loads(NOTES.read_text(encoding="utf-8"))["notes"]}

    tokens, unmapped = [], []
    for tok in TOKEN.findall(body):
        head = lemmas.get(tok.lower())
        if head is None:
            unmapped.append(tok)
        elif head != SKIP:
            tokens.append((tok, head))

    if unmapped:
        print(f"UNMAPPED ({len(sorted(set(unmapped)))}) — these were not checked:\n")
        for t in sorted(set(unmapped)):
            print(f"    {t}")
        print("\nAdd them to the lemma block. Nothing else was checked.")
        return 1

    started = met_notes(args.user)
    heads = {}
    for tok, head in tokens:
        heads.setdefault(head, tok)

    met, prio, bank, nocard, absent = [], [], [], [], []
    for w in sorted(heads):
        row, n = vocab.get(w), notes.get(w)
        if row is None:
            absent.append(w)
        elif n is None:
            (nocard if row.get("flashcard") == "no" else bank).append(w)
        elif n["id"] in started:
            met.append(w)
        elif n.get("priority"):
            prio.append(w)
        else:
            bank.append(w)

    unused = sorted(set(lemmas) - {t.lower() for t in TOKEN.findall(body)})

    def show(label, ws):
        if ws:
            print(f"\n  {label} ({len(ws)})")
            for i in range(0, len(ws), 6):
                print("      " + "  ".join(f"{w:<14}" for w in ws[i:i + 6]))

    print(f"{len(heads)} headwords in {path}")
    show("met — he has answered a card for these", met)
    show("prioritised — carded, arriving within days", prio)
    show("grammar words, no card by design", sorted(nocard))
    if unused:
        print(f"\n  mapped but never used ({len(unused)}) — a typo in the block?")
        print("      " + "  ".join(unused))

    problems = 0
    if bank:
        print(f"\n  IN THE BANK, UNSEEN ({len(bank)}) — he has never met these, and")
        print(  "  nothing brings them near this story. Flag them or cut them.")
        for i in range(0, len(bank), 6):
            print("      " + "  ".join(f"{w:<14}" for w in bank[i:i + 6]))
        problems += len(bank)
    if absent:
        print(f"\n  NOT IN THE DECK ({len(absent)}) — not even in vocab.csv:")
        print("      " + "  ".join(absent))
        problems += len(absent)

    if not problems:
        print("\nEvery word is one he has met or will meet within days.")
        return 0
    print(f"\n{problems} word(s) need a decision — not safe to send as it stands.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

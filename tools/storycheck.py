#!/usr/bin/env python3
"""Check a draft story against what the student has actually MET.

    python3 tools/storycheck.py lessons/draft.txt
    cat draft.txt | python3 tools/storycheck.py -

Why this exists: a lesson story was once built against `deck/notes.json` and
fifteen of its words turned out to be ones he had never seen — carded, yes,
but sitting unintroduced in the bank. The deck is more than twice the size of
what he has met, so "it is in the deck" is not the question. This asks the
question that matters, reading his live card states over REST the way
tools/progress.py does.

Four buckets, and only the last two need you:

  met         he has answered a card for it — safe, he will follow it
  prioritised carded and flagged, so it arrives within days — fine in a story
              he is about to be taught
  in the bank carded but unflagged and unseen. It will surface whenever the
              shuffle gets to it, which could be months. Flag it or cut it.
  NOT CARDED  not a note at all. Either card it or rewrite the line.

## The lemmatiser, and why it shows its working

There is no Polish lemmatiser here and adding one is not worth it. Instead
both the token and every word in `deck/vocab.csv` are cut back a letter at a
time, and a match is the longest stem they share — which catches
mieszka/mieszkać and nowym/nowy without enumerating a single ending. An
earlier version did enumerate them and missed every infinitive. A table
handles the suppletive words no cutting can reach (być, mieć, iść, ludzie),
and ó folds to o for stół/stole and samochód/samochody.

That is still a guess, and a guess that quietly resolves `mieście` to the
wrong headword would defeat the whole point.

So every non-exact match is printed under `assumed`, for a human to read.
Anything it cannot resolve at all goes under `UNRESOLVED` and the tool exits
non-zero: an unresolved token is a word that has not been checked, which is
exactly the failure this exists to prevent, and it must not look like a pass.
"""
import argparse, json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "deck" / "notes.json"
VOCAB = ROOT / "deck" / "vocab.csv"
APP = ROOT / "index.html"

# Polish alternates vowels inside the stem, so fold the ones that actually
# occur in this deck before comparing: stół/stole, samochód/samochody,
# wieczór/wieczorem all differ only by ó.
FOLD = str.maketrans({"ó": "o"})

# Suppletive words, and the few whose stem alternation no fold can reach.
# Everything else is handled by truncation, which covers the regular verb and
# noun endings without needing them enumerated.
IRREGULAR = {
    "jestem": "być", "jesteś": "być", "jest": "być", "jesteśmy": "być",
    "jesteście": "być", "są": "być", "być": "być",
    "mam": "mieć", "masz": "mieć", "ma": "mieć", "mamy": "mieć",
    "macie": "mieć", "mają": "mieć", "mieć": "mieć",
    "idę": "iść", "idziesz": "iść", "idzie": "iść", "idziemy": "iść",
    "idziecie": "iść", "idą": "iść", "iść": "iść",
    "jadę": "jechać", "jedziesz": "jechać", "jedzie": "jechać",
    "jedziemy": "jechać", "jadą": "jechać",
    "ludzi": "ludzie", "ludźmi": "ludzie", "ludziom": "ludzie",
    "je": "jeść", "jem": "jeść", "jesz": "jeść", "jedzą": "jeść",
    "jedzenie": "jeść",
    "mogę": "móc", "możesz": "móc", "może": "móc", "mogą": "móc",
    "wiem": "wiedzieć", "wiesz": "wiedzieć", "wie": "wiedzieć",
    "wiedzą": "wiedzieć",
    "psa": "pies", "psy": "pies", "psu": "pies", "psem": "pies",
    "psów": "pies",
    "dnia": "dzień", "dni": "dzień", "dniu": "dzień",
    "tygodnia": "tydzień", "tygodniu": "tydzień",
    "ręce": "ręka", "ręku": "ręka", "oczy": "oko", "uszy": "ucho",
    "mieście": "miasto", "mieścia": "miasto",
    # duży/dużo is a true minimal pair under stemming: duże cuts to the same
    # stem as both, and guessing wrong invents a word the story never used.
    "duże": "duży", "dużego": "duży", "dużym": "duży", "dużej": "duży",
    "dużą": "duży", "duzi": "duży",
    "śmieje": "śmiać się", "śmieję": "śmiać się", "śmiać": "śmiać się",
    "śmiejesz": "śmiać się", "śmieją": "śmiać się",
    "się": "się", "mnie": "ja", "ci": "ty", "cię": "ty", "ciebie": "ty",
    "niego": "on", "jego": "jego",
}

MIN_STEM = 3
MAX_TRIM = 4

# Proper nouns are deliberately not vocabulary — Marek is a name, not a
# word learned. Only consulted after resolution fails, or every
# sentence-initial verb would look like one.
PROPER = re.compile(r"^[A-ZŁŚŻŹĆŃÓĄĘ]")


def die(msg):
    sys.exit(f"storycheck: {msg}")


def load_vocab():
    import csv
    words = {}
    with VOCAB.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            words[row["word"]] = row
    return words


def cands(w):
    """Every stem this word could be cut back to, longest first. Comparing two
    such sets catches mieszka/mieszkać and nowym/nowy without enumerating a
    single ending, which is what the first version tried and got wrong."""
    w = w.lower().translate(FOLD)
    out = [w]
    for k in range(1, MAX_TRIM + 1):
        if len(w) - k >= MIN_STEM:
            out.append(w[:-k])
    return out


def build_index(vocab):
    idx = {}
    for word in vocab:
        for c in cands(word):
            idx.setdefault(c, set()).add(word)
    return idx


def resolve(tok, vocab, idx):
    """-> (headword, how, alternatives). how is exact / irregular / stem / stem?"""
    low = tok.lower()
    if low in vocab:
        return low, "exact", ()
    if low in IRREGULAR:
        h = IRREGULAR[low]
        return (h, "irregular", ()) if h in vocab else (None, None, ())
    # Longest shared stem wins: it is the least aggressive cut that still
    # matches, so mieszka finds mieszkać rather than something three letters long.
    for c in cands(low):
        hits = idx.get(c)
        if not hits:
            continue
        if len(hits) == 1:
            return next(iter(hits)), "stem", ()
        exact = [w for w in hits if w.lower().translate(FOLD) == c]
        if len(exact) == 1:
            return exact[0], "stem", ()
        # Genuinely ambiguous — duże fits both duży and dużo. Pick one so the
        # word is still bucketed, but hand back the rivals: an unannounced
        # coin-flip here is how a wrong bucket looks like a real finding.
        ranked = sorted(hits)
        return ranked[0], "stem?", tuple(ranked[1:])
    return None, None, ()


def met_words(uid, notes):
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
    cards = doc["fields"]["cards"]["mapValue"]["fields"]
    return {k.rsplit("__", 1)[0] for k in cards}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", help="path to the draft, or - for stdin")
    ap.add_argument("--user", default="evert")
    args = ap.parse_args()

    text = (sys.stdin.read() if args.story == "-"
            else Path(args.story).read_text(encoding="utf-8"))
    vocab = load_vocab()
    notes = {n["word"]: n for n in
             json.loads(NOTES.read_text(encoding="utf-8"))["notes"]}
    started = met_words(args.user, notes)

    idx = build_index(vocab)
    seen, assumed, unresolved, proper = {}, [], [], set()
    for tok in re.findall(r"[\w']+", text, re.UNICODE):
        head, how, alts = resolve(tok, vocab, idx)
        if head is None:
            # Only now is a capital meaningful. Testing it first made every
            # sentence-initial verb a proper noun — Jest, Mam, Kupuje.
            if PROPER.match(tok):
                proper.add(tok)
            else:
                unresolved.append(tok)
            continue
        seen.setdefault(head, tok)
        if how != "exact":
            assumed.append((tok, head, how, alts))

    met, prio, bank, nocard = [], [], [], []
    for w in sorted(seen):
        row, n = vocab[w], notes.get(w)
        if not n:
            (nocard if row.get("flashcard") == "no" else bank).append(w)
        elif n["id"] in started:
            met.append(w)
        elif n.get("priority"):
            prio.append(w)
        else:
            bank.append(w)

    def show(label, ws):
        print(f"\n  {label} ({len(ws)})")
        for i in range(0, len(ws), 6):
            print("      " + "  ".join(f"{w:<14}" for w in ws[i:i + 6]))

    print(f"{len(seen)} headwords in {args.story}")
    show("met — he has answered a card for these", met)
    show("prioritised — carded, arriving within days", prio)
    show("grammar words, no card by design", sorted(nocard))
    if proper:
        print(f"\n  proper nouns, skipped ({len(proper)})"
              f"\n      {'  '.join(sorted(proper))}")

    if assumed:
        print(f"\n  assumed — guessed, please eyeball ({len(assumed)})")
        for tok, head, how, alts in sorted(set(assumed)):
            extra = f"  or {', '.join(alts)}" if alts else ""
            print(f"      {tok:<16} -> {head:<14} ({how}){extra}")

    bad = 0
    if bank:
        print(f"\n  IN THE BANK, UNSEEN ({len(bank)}) — he has never met these,")
        print( "  and nothing brings them near this story. Flag or cut them.")
        for i in range(0, len(bank), 6):
            print("      " + "  ".join(f"{w:<14}" for w in bank[i:i + 6]))
        bad += len(bank)
    if unresolved:
        print(f"\n  UNRESOLVED ({len(unresolved)}) — not checked at all:")
        print("      " + "  ".join(sorted(set(unresolved))))
        bad += len(unresolved)

    if not bad:
        print("\nEvery word is one he has met or will meet within days.")
        return 0
    print(f"\n{bad} word(s) need a decision — not safe to send as it stands.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Reading stories for the app: story files → read/stories.json.

    python3 tools/reading.py          # rebuild the list

Every story file in lessons/ dated FIRST or later that has a `--- pytania ---`
section AND whose id is listed in read/approved.txt goes in, listening
scripts excepted. **Nothing goes live without the teacher's approval**: on
2026-10-25 a lesson story was pushed to the app before they had read it, and
they had to find it there. Add the id to approved.txt only when they have
said yes to that story; the tool prints what is waiting. Earlier stories stay paper-only
(asked 2026-10-24: "not the previous ones, all the ones from now on"). The
list is generated, never edited: the story file is the one source.

What goes in:

- **The story**, as paragraphs of tokens. Each word carries the headword its
  lemma block maps it to, so the app can show a gloss when it is tapped
  without knowing any Polish morphology. The story ends at the questions, or
  at the first paragraph with a `(…)` gap — lesson stories carry their gap
  exercises after the text, and those are for paper.
- **A gloss for every headword**: the card's gloss and note id where there is
  an approved card (the app then shows its picture and plays its recording),
  else FUNCTION_GLOSS below. A headword with no gloss is an error: a tap
  that shows nothing is worse than no tap.

  Not vocab.csv's `notes` column. That is a record of why a word has no
  card ("possessive; given free"), not a definition, and the first version
  showed it to him as one: tapping *mój* said "possessive; given free".
- **The questions**, in the listening format (see tools/listen.py).

Run storycheck on the story first; this trusts the lemma block it checked.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from listen import questions  # noqa: E402  (same question format)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "read" / "stories.json"
APPROVED = ROOT / "read" / "approved.txt"
FIRST = "2026-10-21"
WORD = re.compile(r"[^\W\d_]+", re.U)

# Glosses for words with no card: grammar words, and the odd word kept off
# the cards on purpose. Written for him to read when he taps the word, so
# plain English, no bookkeeping. The tool says when a story needs a new one.
FUNCTION_GLOSS = {
    "a": "and, while", "ale": "but", "i": "and", "albo": "or", "bo": "because",
    "że": "that", "więc": "so", "czy": "whether; or (question word)",
    "do": "to", "na": "on, onto", "pod": "under", "nad": "above, by (a river)",
    "w": "in", "z": "with; from", "dla": "for", "od": "from",
    "się": "oneself (with some verbs)", "to": "this, it", "ten": "this",
    "co": "what", "kto": "who", "gdzie": "where", "jak": "how", "który": "which",
    "ja": "I", "ty": "you", "on": "he", "ona": "she", "my": "we", "wy": "you (all)",
    "oni": "they", "mój": "my", "twój": "your", "jego": "his", "jej": "her",
    "nie": "no, not", "tak": "yes",
    "dziękuję": "thank you", "otwierać": "to open (is opening, opens often)",
    # new in a lesson, not carded yet: cards come after the lesson
    "cytryna": "lemon",
    "pierogi": "pierogi (filled dumplings)", "ryż": "rice", "czekolada": "chocolate",
    "kelner": "waiter", "rachunek": "the bill", "smacznego": "enjoy your meal!",
    "naleśniki": "pancakes", "miło": "nicely (miło mi: pleased to meet you)",
    "u": "at (someone's place): u nas, at our place",
    "po": "after; po polsku: in Polish", "trochę": "a little",
}


def title_of(story):
    md = story.with_name(story.name.replace(".story.txt", ".md"))
    head = md.read_text(encoding="utf-8").splitlines()[0] if md.exists() else ""
    m = re.search(r"—\s*(.+?)\s*(\(|$)", head)
    if not m:
        sys.exit(f"reading: {md.name}: no '# … — Title' heading to take the title from")
    return m.group(1)


def glosses():
    notes = json.loads((ROOT / "deck/notes.json").read_text(encoding="utf-8"))["notes"]
    cards = {n["word"]: n for n in notes if n.get("kind") != "form" and n.get("reviewed")}

    def look(head):
        if head in cards:
            return {"gloss": cards[head]["gloss"], "note": cards[head]["id"]}
        if head in FUNCTION_GLOSS:
            return {"gloss": FUNCTION_GLOSS[head]}
        return None
    return look


def build(story, look):
    text = story.read_text(encoding="utf-8")
    body, _, block = text.partition("--- lemmas ---")
    lemmas = {}
    for line in block.splitlines():
        line = line.split("#", 1)[0]
        if "=" in line:
            tok, head = (x.strip() for x in line.split("=", 1))
            lemmas[tok.lower()] = head
    paras = []
    for p in body.split("--- pytania ---")[0].strip().split("\n\n"):
        if "(…)" in p:
            break
        segs, at = [], 0
        for m in WORD.finditer(p):
            if m.start() > at:
                segs.append([p[at:m.start()]])
            head = lemmas.get(m.group().lower())
            if head is None:
                sys.exit(f"reading: {story.name}: {m.group()!r} is not in the lemma block "
                         "— run storycheck")
            segs.append([m.group()] if head == "-" else [m.group(), head])
            at = m.end()
        if at < len(p):
            segs.append([p[at:]])
        paras.append(segs)
    heads = sorted({s[1] for p in paras for s in p if len(s) == 2})
    words, missing = {}, []
    for h in heads:
        g = look(h)
        if g:
            words[h] = g
        else:
            missing.append(h)
    if missing:
        sys.exit(f"reading: {story.name}: no gloss for {', '.join(missing)} — "
                 "add it to FUNCTION_GLOSS")
    qs = questions(story)
    if not qs:
        sys.exit(f"reading: {story.name}: no questions")
    return {"id": story_id(story), "title": title_of(story), "date": story.name[:10],
            "paras": paras, "words": words, "questions": qs}


def story_id(path):
    return re.sub(r"^\d{4}-\d{2}-\d{2}-(homework-)?", "", path.name.replace(".story.txt", ""))


def main():
    look = glosses()
    approved = {l.split("#")[0].strip() for l in APPROVED.read_text(encoding="utf-8").splitlines()} - {""}
    cands = [s for s in sorted((ROOT / "lessons").glob("*.story.txt"))
             if s.name[:10] >= FIRST and "-sluchanie-" not in s.name
             and "--- pytania ---" in s.read_text(encoding="utf-8")]
    for s in cands:
        if story_id(s) not in approved:
            print(f"  waiting for approval, not published: {story_id(s)}")
    stories = [build(s, look) for s in cands if story_id(s) in approved]
    ids = [s["id"] for s in stories]
    if len(ids) != len(set(ids)):
        sys.exit(f"reading: duplicate story ids: {ids}")
    stories.sort(key=lambda s: (s["date"], s["id"]), reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"schema": 1, "stories": stories}, ensure_ascii=False,
                              indent=1) + "\n", encoding="utf-8")
    for s in stories:
        n = sum(len(x) == 2 for p in s["paras"] for x in p)
        print(f"  {s['date']}  {s['title']:<14} {n} words, {len(s['words'])} headwords, "
              f"{len(s['questions'])} questions")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(stories)} stories)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

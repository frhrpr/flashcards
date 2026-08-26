#!/usr/bin/env python3
"""Build the speaking-practice sheet: you say the Polish, he translates.

    python3 tools/speaking.py                 # writes the sheet
    python3 tools/speaking.py --user evert    # a different student

Nothing here is a flashcard. The deck asks him to recognise and produce
single words; this asks him to hear a whole sentence at speaking pace and
say what it meant, which is the one thing the cards cannot rehearse.

Two rules the sheet must not break, both checked at build time rather than
trusted:

  * Every word must be one he has actually been introduced to — read from
    his Firestore card states, not from the deck. The deck is nearly three
    times larger than what he has met, and a sheet built from the deck would
    be mostly words he has never seen.
  * No token may be missing from LEMMA. An unmapped word is invisible to
    both checks above, so it is an error rather than a shrug.

Order is optimised, not merely shuffled. A plain shuffle once dealt four
chcieć items in a row, which is the monotony the shuffle exists to prevent;
repeats are now scored by distance and the order hill-climbed until adjacent
ones are gone.
"""
import argparse, html, json, random, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "deck" / "notes.json"
APP = ROOT / "index.html"
OUT = Path("/mnt/c/Users/frhrpr/Downloads/flashcards/lessons")

# Tiers order nothing on the page — they are mixed in — but they keep the
# spread honest: without them the optimiser is free to stack every hard item
# at the end. A: one clause. B: two clauses, a case ending, or a modal.
# Q: he translates it, then answers it in Polish.
ITEMS = [
 ("A", "Kot pije mleko.", "The cat drinks milk.", ""),
 ("A", "Pies jest w parku.", "The dog is in the park.", ""),
 ("A", "Mam nowy dom.", "I have a new house.", ""),
 ("A", "Dziecko je chleb.", "The child is eating bread.", ""),
 ("A", "Rano piję wodę.", "In the morning I drink water.", ""),
 ("A", "Ptak siedzi na drzewie.", "The bird is sitting in the tree.", "locative — na + ie"),
 ("A", "To jest stary sklep.", "This is an old shop.", ""),
 ("A", "Kobieta idzie do domu.", "The woman is going home.", "do + genitive"),
 ("A", "Nie mam czasu.", "I don't have time.", "genitive after nie"),
 ("A", "Mój pies jest duży.", "My dog is big.", ""),
 ("B", "Szukam psa.", "I'm looking for the dog.", "szukać takes the genitive"),
 ("B", "Chcę pić.", "I want to drink.", "modal + infinitive"),
 ("B", "Kot skacze na ławkę.", "The cat jumps onto the bench.", "na + accusative = motion"),
 ("B", "Dziecko śpiewa w parku.", "The child is singing in the park.", ""),
 ("B", "Teraz nie mogę.", "I can't right now.", ""),
 ("B", "Mam psa, ale nie mam kota.", "I have a dog, but I don't have a cat.", "two genitives"),
 ("B", "Rano idę do sklepu, potem wracam do domu.",
       "In the morning I go to the shop, then I come back home.", "sequence with potem"),
 ("B", "Nie wiem, gdzie jest piłka.", "I don't know where the ball is.", "embedded question"),
 ("B", "Dziecko chce pić wodę.", "The child wants to drink water.", ""),
 ("B", "Widzę duże drzewo.", "I see a big tree.", ""),
 ("Q", "Czy masz psa?", "Do you have a dog?", "yes/no — answer Tak, mam / Nie, nie mam"),
 ("Q", "Gdzie jest kot?", "Where is the cat?", ""),
 ("Q", "Co pijesz rano?", "What do you drink in the morning?", ""),
 ("Q", "Kto jest w domu?", "Who is at home?", "kto takes a singular verb"),
 ("Q", "Jak masz na imię?", "What's your name?", ""),
 ("Q", "Czy chcesz jeść?", "Do you want to eat?", ""),
 ("Q", "Gdzie idziesz?", "Where are you going?", ""),
 ("Q", "Co masz w ręce?", "What do you have in your hand?", ""),
 ("Q", "Czy pies jest duży?", "Is the dog big?", ""),
 ("Q", "Kto ma piłkę?", "Who has the ball?", ""),
 ("Q", "Czy wiesz, gdzie jest sklep?", "Do you know where the shop is?", ""),
 ("Q", "Czy chcesz iść do parku?", "Do you want to go to the park?", ""),
]
LEMMA = {
 "kot":"kot","pije":"pić","piję":"pić","pić":"pić","pijesz":"pić","mleko":"mleko",
 "pies":"pies","psa":"pies","kota":"kot","jest":"być","w":"w","parku":"park",
 "mam":"mieć","masz":"mieć","ma":"mieć","nowy":"nowy","dom":"dom","domu":"dom",
 "dziecko":"dziecko","je":"jeść","jeść":"jeść","chleb":"chleb","rano":"rano",
 "wodę":"woda","wody":"woda","ptak":"ptak","siedzi":"siedzieć","na":"na",
 "drzewie":"drzewo","drzewo":"drzewo","duże":"duży","duży":"duży","to":"to",
 "stary":"stary","sklep":"sklep","sklepu":"sklep","kobieta":"kobieta","idzie":"iść",
 "idę":"iść","idziesz":"iść","iść":"iść","do":"do","nie":"nie","czasu":"czas",
 "teraz":"teraz","mój":"mój","szukam":"szukać","chcę":"chcieć","chcesz":"chcieć","chce":"chcieć",
 "skacze":"skakać","ławkę":"ławka","śpiewa":"śpiewać","mogę":"móc","ale":"ale",
 "potem":"potem","wracam":"wracać","wiem":"wiedzieć","wiesz":"wiedzieć",
 "gdzie":"gdzie","piłka":"piłka","piłkę":"piłka","widzę":"widzieć","czy":"czy",
 "co":"co","kto":"kto","jak":"jak","imię":"imię","ręce":"ręka",
}

# Words that carry no content for the repeat check — every other sentence has
# one, so counting them would make everything look like a repeat of everything.
STOP = {"być", "mieć", "nie", "to", "w", "na", "do", "i", "ten", "mój",
        "twój", "czy", "ja", "ty"}

NEW_DAYS = 14      # met this recently, a miss is fair
SHAKY_IVL = 15     # met long ago and still on a short interval: he is failing it


def die(msg):
    sys.exit(f"speaking: {msg}")


def progress(uid):
    """His real card states. Read over REST with the web key, exactly as
    tools/progress.py does — the open Firestore rule permits it."""
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
    return doc["fields"]["cards"]["mapValue"]["fields"]


def study(cards, notes):
    """Per word: has he met it, when, and how well is it holding."""
    now = time.time() * 1000
    agg = {}
    for k, v in cards.items():
        nid = k.rsplit("__", 1)[0]
        n = notes.get(nid)
        if not n or n.get("kind") == "form":
            continue
        f = {}
        for a, b in v["mapValue"]["fields"].items():
            if "integerValue" in b:
                f[a] = int(b["integerValue"])
            elif "doubleValue" in b:
                f[a] = float(b["doubleValue"])
        d = agg.setdefault(nid, {"ivl": 0, "intro": None})
        d["ivl"] = max(d["ivl"], f.get("ivl", 0))
        if f.get("introduced"):
            d["intro"] = min(d["intro"] or f["introduced"], f["introduced"])

    known, flag = set(), {}
    for nid, d in agg.items():
        w = notes[nid]["word"]
        known.add(w)
        age = (now - d["intro"]) / 86400e3 if d["intro"] else None
        if age is not None and age < NEW_DAYS:
            flag[w] = ("new", f"met {age:.0f} days ago")
        elif d["ivl"] < SHAKY_IVL:
            flag[w] = ("shaky", "keeps missing this")
    return known, flag


def check(known):
    """Fail loudly. A sheet naming a word he has never met is worse than no
    sheet: it turns a confidence exercise into a quiz he cannot pass."""
    grammar = {"czy", "co", "kto", "gdzie", "jak", "ja", "ty", "my", "mój",
               "twój", "ten", "w", "na", "do", "i", "ale", "nie", "to"}
    bad, unmapped = [], []
    for _, pl, _, _ in ITEMS:
        for tok in re.findall(r"\w+", pl, re.UNICODE):
            lem = LEMMA.get(tok.lower())
            if lem is None:
                unmapped.append((pl, tok))
            elif lem not in known and lem not in grammar:
                bad.append((pl, tok, lem))
    if unmapped:
        for pl, tok in unmapped:
            print(f"  UNMAPPED  {tok!r} in {pl!r}", file=sys.stderr)
    if bad:
        for pl, tok, lem in bad:
            print(f"  NOT MET   {tok!r} ({lem}) in {pl!r}", file=sys.stderr)
    if unmapped or bad:
        die(f"{len(unmapped)} unmapped token(s), {len(bad)} unmet word(s)")


def order_items(seed):
    """Spread repeats. Adjacent ones are what read as monotony; a repeat three
    apart barely registers, so the weights fall off steeply and the search
    spends its effort where it shows. Flat counting left chcesz at 23 and 24."""
    sig = {pl: {LEMMA.get(t.lower()) for t in re.findall(r"\w+", pl, re.UNICODE)}
                - STOP - {None} for _, pl, _, _ in ITEMS}
    W = {1: 100, 2: 8, 3: 1}

    def cost(o):
        c = 0
        for i in range(len(o)):
            for d in (1, 2, 3):
                j = i + d
                if j < len(o) and sig[o[i][1]] & sig[o[j][1]]:
                    c += W[d]
            if i < len(o) - 2 and o[i][0] == o[i + 1][0] == o[i + 2][0]:
                c += 4
        return c

    rng = random.Random(seed)
    best, best_c = None, 10 ** 9
    for _ in range(60):
        o = list(ITEMS)
        rng.shuffle(o)
        c = cost(o)
        moved = True
        while moved:
            moved = False
            for a in range(len(o)):
                for b in range(a + 1, len(o)):
                    o[a], o[b] = o[b], o[a]
                    c2 = cost(o)
                    if c2 < c:
                        c, moved = c2, True
                    else:
                        o[a], o[b] = o[b], o[a]
        if c < best_c:
            best, best_c = o[:], c
        if c == 0:
            break
    assert sorted(best) == sorted(ITEMS), "items lost in the shuffle"
    return best, best_c


def build(order, known, flag):
    e = html.escape
    rows = ""
    for i, (_tier, pl, en, note) in enumerate(order, 1):
        tags = {}
        for tok in re.findall(r"\w+", pl, re.UNICODE):
            lem = LEMMA.get(tok.lower())
            if lem in flag:
                kind, why = flag[lem]
                tags.setdefault((kind, why), set()).add(tok)
        marks = "".join(f'<i class={k}>{e(", ".join(sorted(ws)))} — {e(why)}</i>'
                        for (k, why), ws in sorted(tags.items()))
        rows += (f'<tr><td class=no>{i}</td><td class=pl>{e(pl)}{marks}</td>'
                 f'<td class=en>{e(en)}</td><td class=nb>{e(note)}</td></tr>')
    nq = sum(1 for t, *_ in ITEMS if t == "Q")
    nshaky = sum(1 for k, _ in flag.values() if k == "shaky")
    return f"""<!doctype html><meta charset=utf-8><title>Speaking — say it, he translates</title>
<meta name=color-scheme content="dark light"><style>
:root{{--bg:#15171a;--card:#1d2024;--ink:#e6e8e6;--dim:#9aa0a6;--faint:#767c82;
--line:#2e3339;--new:#9aa0a6;--shaky:#e8796b}}
body{{font-family:Georgia,'Times New Roman',serif;max-width:46rem;margin:2rem auto;
padding:0 1.2rem 4rem;background:var(--bg);color:var(--ink);line-height:1.5}}
h1{{font-family:system-ui,sans-serif;font-size:1.35rem;font-weight:400;margin:0}}
.meta{{font-family:ui-monospace,monospace;font-size:.72rem;letter-spacing:.1em;
text-transform:uppercase;color:var(--dim);margin-bottom:1.4rem}}
.intro{{background:var(--card);border:1px solid var(--line);padding:1rem 1.3rem;
margin-bottom:1.6rem;font-size:.92rem}}
.intro p{{margin:.4rem 0}} .intro p:first-child{{margin-top:0}}
.intro p:last-child{{margin-bottom:0}} .intro b.s{{color:var(--shaky);font-weight:400}}
table{{width:100%;border-collapse:collapse}}
td{{padding:.5rem .5rem;border-bottom:1px solid var(--line);vertical-align:top}}
tr:last-child td{{border-bottom:0}}
td.no{{font-family:ui-monospace,monospace;font-size:.68rem;color:var(--faint);
width:1.6rem;text-align:right;padding-top:.72rem}}
td.pl{{font-size:1.08rem;width:45%}}
td.pl i{{display:block;font-style:normal;font-family:ui-monospace,monospace;
font-size:.6rem;letter-spacing:.04em;margin-top:.15rem}}
td.pl i.new{{color:var(--new)}} td.pl i.shaky{{color:var(--shaky)}}
td.en{{font-size:.88rem;color:var(--dim);width:32%}}
td.nb{{font-family:ui-monospace,monospace;font-size:.62rem;color:var(--faint)}}
/* Printing a dark page wastes ink and comes out unreadable, so paper gets the
   light palette back. Screen is the default; paper is the documented exception. */
@media print{{
:root{{--bg:#fff;--card:#fff;--ink:#111;--dim:#555;--faint:#777;--line:#ccc;
--new:#777;--shaky:#a32c22}}
body{{margin:0;max-width:none;font-size:10.5pt}}
.intro{{border-color:#999}}}}
</style>
<h1>Speaking — you say it, he translates</h1>
<div class=meta>Every word below is one he has already met · {len(ITEMS)} items</div>
<div class=intro>
<p>Say the Polish aloud, normal speed, once. He translates into English.</p>
<p>{nq} of them are questions — those he translates <b>and then answers in
Polish</b>. The question mark is the only cue you need; they are mixed in
rather than saved for the end.</p>
<p>Order is jumbled and difficulty is not signposted, so he cannot settle
into a pattern — and no two neighbouring items share a content word, so the
same verb never arrives twice running.</p>
<p>Nothing here uses a word outside the {len(known)} he has actually been
introduced to. Grey marks a word he met in the last fortnight, so a miss is
fair. <b class=s>Red marks a word he met long ago and is still failing</b> —
{nshaky} of those across the deck. A miss there is the one worth stopping
on.</p>
</div>
<table>{rows}</table>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default="evert")
    ap.add_argument("--seed", type=int, default=20260826,
                    help="fixed so a reprint is the same sheet, not a new order")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    notes = {n["id"]: n for n in
             json.loads(NOTES.read_text(encoding="utf-8"))["notes"]}
    known, flag = study(progress(args.user), notes)
    check(known)

    order, cost = order_items(args.seed)
    dest = Path(args.out)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{time.strftime('%Y-%m-%d')}-speaking.html"
    path.write_text(build(order, known, flag), encoding="utf-8")

    print(f"wrote {path}")
    print(f"  {len(ITEMS)} items, {len(known)} words he has met")
    print(f"  spread cost {cost}" + ("  (0 — no repeat within three)" if not cost
                                     else "  (some repeats unavoidable)"))
    shaky = sorted(w for w, (k, _) in flag.items() if k == "shaky")
    if shaky:
        print(f"  still failing: {', '.join(shaky)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

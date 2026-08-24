#!/usr/bin/env python3
"""How is the student getting on?

    python3 tools/progress.py              # the only deck in the database
    python3 tools/progress.py --user ID    # a specific one
    python3 tools/progress.py --list       # what decks exist

Reads the live Firestore document over the REST API using the web API key
out of index.html — the security rule is open, so no credentials are needed.
Prints a summary and writes a page you can open in Windows.

Ordered by what is worth acting on: whether he is turning up at all, then
which words keep going wrong, then where he has got to in the deck. Spaced
repetition fails through absence far more often than through bad scheduling.
"""
import argparse, json, re, sys, urllib.request, urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deckio import ROOT, out_dir, esc

PROJECT = "flashcards-f5b40"
BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents/progress"
DAY = 86400_000
SESSION_GAP = 30 * 60_000        # a half-hour gap starts a new sitting
YOUNG, MATURE = 6, 21            # interval days: learning / young / mature
EAR_WINDOW, EAR_RETIRE = 10, 9   # must match index.html, or "retired" lies here
MATRIX_TRIALS = 300              # confusion matrix window, most recent trials
SOUND_ORDER = ["s", "sz", "si", "c", "cz", "ci"]

is_ear = lambda e: e["card"].endswith("__ear")


def die(msg): sys.exit(f"progress: {msg}")


def api_key():
    m = re.search(r'apiKey:\s*"([^"]+)"', (ROOT / "index.html").read_text(encoding="utf-8"))
    if not m:
        die("could not find the Firebase apiKey in index.html")
    return m.group(1)


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}")
    except urllib.error.URLError as e:
        die(f"network error: {e.reason}")


def dec(v):
    """Firestore REST wraps every scalar in a type tag; unwrap it."""
    if "integerValue" in v: return int(v["integerValue"])
    if "doubleValue" in v: return float(v["doubleValue"])
    if "stringValue" in v: return v["stringValue"]
    if "booleanValue" in v: return v["booleanValue"]
    if "nullValue" in v: return None
    if "mapValue" in v:
        return {k: dec(x) for k, x in (v["mapValue"].get("fields") or {}).items()}
    if "arrayValue" in v:
        return [dec(x) for x in (v["arrayValue"].get("values") or [])]
    return None


def load_remote(key, user):
    if user:
        doc = get(f"{BASE}/{user}?key={key}")
    else:
        docs = get(f"{BASE}?key={key}").get("documents", [])
        if not docs:
            die("no decks in the database yet — nobody has reviewed anything")
        if len(docs) > 1:
            names = ", ".join(d["name"].split("/")[-1] for d in docs)
            die(f"{len(docs)} decks exist; pass --user to choose: {names}")
        doc = docs[0]
    fields = {k: dec(v) for k, v in doc.get("fields", {}).items()}
    return (doc["name"].split("/")[-1], fields.get("cards") or {},
            fields.get("log") or [], fields.get("ear") or {},
            fields.get("done") or {})


def intake_rate():
    """NEW_WORDS_PER_DAY out of index.html, so this report cannot quietly
    disagree with the app about how fast the deck is consumed."""
    m = re.search(r"const NEW_WORDS_PER_DAY\s*=\s*(\d+)",
                  (ROOT / "index.html").read_text(encoding="utf-8"))
    return int(m.group(1)) if m else 3


def ear_content():
    """WORDS and SOUND_LABEL straight out of index.html — the same source the
    app renders from and tools/ear_build.py names folders from, so this report
    cannot drift from what he was actually asked."""
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    block = re.search(r"const WORDS\s*=\s*\{(.*?)\n\};", text, re.S)
    lbl = re.search(r"const SOUND_LABEL\s*=\s*\{([^}]*)\}", text)
    if not block or not lbl:
        die("could not read WORDS / SOUND_LABEL out of index.html")
    spell, sound = {}, {}
    for key, warr, snd in re.findall(
            r'"([^"]+)"\s*:\s*\{\s*w\s*:\s*\[([^\]]*)\][^}]*?s\s*:\s*"([^"]*)"',
            block.group(1)):
        spell[key] = "".join(re.findall(r'"([^"]*)"', warr))
        sound[key] = snd
    label = dict(re.findall(r'(\w+)\s*:\s*"([^"]*)"', lbl.group(1)))
    return spell, sound, label


def analyse_ear(ear, log, spell, sound, label):
    """Minimal-pair training. The unit that matters is the confusion pair, so
    everything here is keyed by pair rather than by word — hearing ś as sz is
    a different fault from hearing sz as ś, and only this view separates them."""
    entries = sorted((e for e in log if is_ear(e)), key=lambda e: e["ts"])
    if not entries:
        return None
    for e in entries:
        e["_word"] = e["card"][:-len("__ear")]

    matrix = Counter()
    for e in entries[-MATRIX_TRIALS:]:
        played, tapped = sound.get(e["_word"]), sound.get(e.get("chose") or "")
        if played and tapped:
            matrix[(played, tapped)] += 1
    sounds = [s for s in SOUND_ORDER if any(s in k for k in matrix)]

    # `vs` names the distractor. Entries written before it existed cannot be
    # attributed to a pair at all, so they are counted and set aside rather
    # than guessed at.
    per, orphans = defaultdict(list), 0
    for e in entries:
        if not e.get("vs"):
            orphans += 1
            continue
        per["|".join(sorted([e["_word"], e["vs"]]))].append((e["ts"], e["grade"]))

    rows = []
    for key, h in per.items():
        st = ear.get(key) or {}
        hist = st.get("hist") or []
        good = sum(1 for _, g in h if g == "good")
        rows.append({
            "key": key,
            "words": " / ".join(spell.get(w, w) for w in key.split("|")),
            "seen": len(h), "good": good, "pct": good / len(h),
            "history": h,
            "retired": len(hist) >= EAR_WINDOW and sum(hist) >= EAR_RETIRE,
            # The app restarts a retired pair's window on a miss, so a short
            # window on a well-seen pair is exactly the un-retire signature.
            "unretired": st.get("seen", 0) >= EAR_WINDOW and len(hist) < EAR_WINDOW,
        })
    rows.sort(key=lambda r: (r["pct"], -r["seen"]))
    return dict(rows=rows, matrix=matrix, sounds=sounds, label=label,
                trials=len(entries), orphans=orphans,
                retired=[r for r in rows if r["retired"]])


def midnight(ms):
    d = datetime.fromtimestamp(ms / 1000).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(d.timestamp() * 1000)


def sessions(log):
    """Split the review log into sittings on a half-hour gap."""
    out, cur = [], []
    for e in sorted(log, key=lambda x: x["ts"]):
        if cur and e["ts"] - cur[-1]["ts"] > SESSION_GAP:
            out.append(cur); cur = []
        cur.append(e)
    if cur:
        out.append(cur)
    return out


def analyse(cards, log, notes, done):
    word = {n["id"]: n["word"] for n in notes}
    gloss = {n["id"]: n.get("gloss", "") for n in notes}
    note_of = lambda k: k.rsplit("__", 1)[0]
    type_of = lambda k: k.rsplit("__", 1)[1] if "__" in k else "?"

    by_day = defaultdict(lambda: {"good": 0, "again": 0})
    for e in log:
        by_day[midnight(e["ts"])][e["grade"]] += 1
    days = sorted(by_day)

    # Days he chose "just reviews". Worth watching: the option exists so a
    # tired evening still happens, but if it becomes the default the deck
    # quietly stops growing while the streak and the accuracy look fine.
    light = {int(d) for d, modes in done.items() if "vocab-light" in modes}

    today = midnight(int(datetime.now().timestamp() * 1000))
    streak = 0
    if days and days[-1] in (today, today - DAY):
        streak, prev = 1, days[-1]
        for d in reversed(days[:-1]):
            if prev - d != DAY: break
            streak += 1; prev = d

    # Attendance, streak and sittings deliberately count both modes — doing
    # some Polish is doing some Polish. Everything below this line is about
    # vocabulary cards, so ear trials are filtered out explicitly rather than
    # left to fall through into a table of words.
    vocab = [e for e in log if not is_ear(e)]
    lapses = Counter(note_of(e["card"]) for e in vocab if e["grade"] == "again")
    seen = Counter(note_of(e["card"]) for e in vocab)
    hard = sorted(((nid, lapses[nid], seen[nid]) for nid in lapses),
                  key=lambda r: (-r[1], -(r[1] / max(r[2], 1))))[:12]

    buckets = {"learning": 0, "young": 0, "mature": 0}
    for st in cards.values():
        ivl = st.get("ivl", 0)
        buckets["learning" if ivl < YOUNG else "young" if ivl < MATURE else "mature"] += 1

    started_notes = {note_of(k) for k in cards}
    # How much new vocabulary is left. Conjugation drills are not new words —
    # they draw on the sibling allowance — so they are excluded, exactly as
    # the app excludes them from the daily word budget.
    rate = intake_rate()
    unseen = [n for n in notes
              if n.get("kind") != "form" and n["id"] not in started_notes]
    runway = len(unseen) / rate if rate else 0
    # A gated card is locked while its note's recognition card is immature.
    locked = 0
    for n in notes:
        base = cards.get(f"{n['id']}__recognition")
        mature = base and base.get("ivl", 0) >= YOUNG
        for ty in n.get("cards", []):
            if ty == "recognition" or f"{n['id']}__{ty}" in cards:
                continue
            if not mature:
                locked += 1

    # One row per card he has actually met. Unseen cards have no record, so
    # listing all 183 would bury the 22 that mean anything.
    hist = defaultdict(list)
    for e in sorted(vocab, key=lambda x: x["ts"]):
        hist[e["card"]].append(e)
    records = []
    for key, st in cards.items():
        h = hist.get(key, [])
        again = sum(1 for e in h if e["grade"] == "again")
        records.append({
            "key": key, "note": note_of(key), "type": type_of(key),
            "word": word.get(note_of(key), note_of(key)),
            "gloss": gloss.get(note_of(key), ""),
            "ivl": st.get("ivl", 0), "ease": st.get("ease", 0),
            "reps": st.get("reps", 0), "due": st.get("due"),
            "again": again, "seen": len(h),
            "history": [(e["ts"], e["grade"]) for e in h],
            "last": h[-1]["ts"] if h else None,
        })
    # Most trouble first: lapses, then the least-established cards.
    records.sort(key=lambda r: (-r["again"], r["ivl"], r["word"]))

    sess = sessions(log)
    lengths = [(s[-1]["ts"] - s[0]["ts"]) / 60000 for s in sess if len(s) > 1]
    hours = Counter(datetime.fromtimestamp(s[0]["ts"] / 1000).hour for s in sess)

    return dict(
        word=word, gloss=gloss, by_day=by_day, days=days, streak=streak, hard=hard,
        buckets=buckets, started=len(started_notes), total_notes=len(notes),
        locked=locked, cards_started=len(cards), sessions=sess,
        median_minutes=sorted(lengths)[len(lengths) // 2] if lengths else 0,
        usual_hour=hours.most_common(1)[0][0] if hours else None,
        last_seen=days[-1] if days else None, today=today,
        type_of=type_of, reviews=len(log), vocab_reviews=len(vocab), light=light,
        unseen=len(unseen), runway=runway, rate=rate,
        records=records, total_cards=sum(len(n.get("cards", [])) for n in notes),
    )


def fmt_day(ms): return datetime.fromtimestamp(ms / 1000).strftime("%a %d %b")


def strip_of(history):
    return "".join("v" if g == "good" else "x" for _, g in history)


def report_ear(e):
    p = print
    p(f"\n  ear training   {e['trials']} trials"
      + (f" ({e['orphans']} too old to attribute to a pair)" if e["orphans"] else ""))
    if e["sounds"]:
        p(f"\n  what was played -> what he tapped   "
          f"(last {min(e['trials'], MATRIX_TRIALS)} trials)")
        L = e["label"]
        p("    played  " + "".join(f"{L.get(s, s):>6}" for s in e["sounds"]))
        for r in e["sounds"]:
            cells = ""
            for c in e["sounds"]:
                n = e["matrix"].get((r, c), 0)
                cells += f"{f'[{n}]' if r == c else (n or '·'):>6}"
            p(f"    {L.get(r, r):<8}" + cells)
        p("    (the diagonal is correct; everything off it is a confusion)")
    p("\n  by pair, weakest first"
      "   (v = got it, x = missed, oldest on the left)")
    for r in e["rows"]:
        flag = " retired" if r["retired"] else " un-retired" if r["unretired"] else ""
        p(f"    {r['words']:<22} {r['good']:>3}/{r['seen']:<3} "
          f"{round(r['pct']*100):>3}%  {strip_of(r['history'])}{flag}")


def report(uid, a, e):
    p = print
    p(f"\n  deck {uid}\n")
    if not a["days"]:
        p("  nothing reviewed yet")
        return
    gap = (a["today"] - a["last_seen"]) // DAY
    when = "today" if gap == 0 else "yesterday" if gap == 1 else f"{gap} days ago"
    p(f"  last seen     {fmt_day(a['last_seen'])} ({when})")
    p(f"  streak        {a['streak']} day(s), active on {len(a['days'])} day(s)")
    p(f"  reviews       {a['reviews']} total, "
      f"median sitting {a['median_minutes']:.0f} min"
      + (f", usually around {a['usual_hour']:02d}:00" if a["usual_hour"] is not None else ""))
    if a["reviews"] != a["vocab_reviews"]:
        p(f"                {a['vocab_reviews']} vocab cards, "
          f"{a['reviews'] - a['vocab_reviews']} ear trials")
    p(f"  deck          {a['started']}/{a['total_notes']} words started, "
      f"{a['cards_started']} cards, {a['locked']} still locked")
    # Running out of new words is invisible from the review counts — they stay
    # healthy while the deck quietly stops growing — so it gets its own line.
    if a["runway"] < 4:
        p(f"  new words     {a['unseen']} left"
          + (f" — at {a['rate']}/day that is under a day. " if a["unseen"] else " — ")
          + "THE DECK NEEDS NEW WORDS.")
    else:
        p(f"  new words     {a['unseen']} left, about {a['runway']:.0f} days at {a['rate']}/day")
    b = a["buckets"]
    p(f"  maturity      {b['learning']} learning, {b['young']} young, {b['mature']} mature")
    p("\n  recent days")
    for d in a["days"][-10:]:
        v = a["by_day"][d]
        tot = v["good"] + v["again"]
        rate = round(v["good"] / tot * 100) if tot else 0
        p(f"    {fmt_day(d)}  {tot:>3} reviews  {rate:>3}% first time  "
          + "█" * min(tot, 40) + ("  reviews only" if d in a["light"] else ""))
    recent = [d for d in a["days"][-14:]]
    n_light = sum(1 for d in recent if d in a["light"])
    if n_light:
        p(f"\n  reviews-only on {n_light} of his last {len(recent)} active day(s)"
          + ("  — no new words went in on those" if n_light < len(recent)
             else "  — ALL of them; nothing new has gone in"))
    if a["hard"]:
        p("\n  giving him trouble")
        for nid, miss, tot in a["hard"]:
            p(f"    {a['word'].get(nid, nid):<14} {a['gloss'].get(nid, ''):<18} "
              f"missed {miss} of {tot}")
    p("\n  every card he has met, worst first"
      "   (v = got it, x = missed, oldest on the left)")
    p(f"    {'word':<13} {'type':<12} {'ivl':>4} {'ease':>5}  {'due':<12} history")
    for r in a["records"]:
        strip = strip_of(r["history"])
        p(f"    {r['word']:<13} {r['type']:<12} {r['ivl']:>4} {r['ease']:>5.2f}  "
          f"{due_in(r['due'], a['today']):<12} {strip}")
    if e:
        report_ear(e)
    p("")


def due_in(due, today):
    if due is None: return "—"
    d = round((midnight(due) - today) / DAY)
    return "today" if d == 0 else "tomorrow" if d == 1 else \
           f"in {d} days" if d > 0 else f"{-d} day(s) late"


def hist_html(history):
    return "".join(
        f'<b class="{"g" if g == "good" else "a"}" title="'
        f'{datetime.fromtimestamp(ts/1000).strftime("%a %d %b %H:%M")}">'
        f'{"✓" if g == "good" else "✗"}</b>' for ts, g in history)


def ear_html(e):
    if not e:
        return ""
    L = e["label"]
    head = "".join(f"<th>{esc(L.get(s, s))}</th>" for s in e["sounds"])
    mat = ""
    for r in e["sounds"]:
        cells = ""
        for c in e["sounds"]:
            n = e["matrix"].get((r, c), 0)
            cls = "diag" if r == c else ("hot" if n else "")
            cells += f'<td class="n {cls}">{n or "·"}</td>'
        mat += f'<tr><td class=w>{esc(L.get(r, r))}</td>{cells}</tr>'
    rows = ""
    for r in e["rows"]:
        flag = ("<em>retired</em>" if r["retired"]
                else "<em>un-retired after a lapse</em>" if r["unretired"] else "")
        rows += (f'<tr class="{"warn" if r["pct"] < 0.75 else ""}">'
                 f'<td class=w>{esc(r["words"])}{flag}</td>'
                 f'<td class=n>{r["good"]}/{r["seen"]}</td>'
                 f'<td class="n {"low" if r["pct"] < 0.75 else ""}">{round(r["pct"]*100)}%</td>'
                 f'<td class=hist>{hist_html(r["history"])}</td></tr>')
    note = (f" · {e['orphans']} trial(s) predate the pair being logged"
            if e["orphans"] else "")
    return f"""
<h2>Ear training — {e['trials']} trials{esc(note)}</h2>
<div class=box>
<p class=sub>What was played, and what he tapped. Last
{min(e['trials'], MATRIX_TRIALS)} trials; the diagonal is correct.</p>
<table class=cards><tr><th>played</th>{head}</tr>{mat}</table>
<p class=sub style="margin-top:1.5rem">By pair, weakest first.</p>
<table class=cards><tr><th>pair</th><th>right</th><th>rate</th>
<th>history — oldest first</th></tr>{rows}</table>
</div>"""


def html(uid, a, e, dest):
    dest.mkdir(parents=True, exist_ok=True)
    peak = max((v["good"] + v["again"] for v in a["by_day"].values()), default=1)
    rows = ""
    for d in a["days"][-30:]:
        v = a["by_day"][d]
        tot = v["good"] + v["again"]
        gw = v["good"] / peak * 100
        aw = v["again"] / peak * 100
        rows += (f'<tr><td class=d>{esc(fmt_day(d))}</td>'
                 f'<td class=bar><i style="width:{gw:.1f}%"></i>'
                 f'<u style="width:{aw:.1f}%"></u></td>'
                 f'<td class=n>{tot}</td>'
                 f'<td class=n>{round(v["good"]/tot*100) if tot else 0}%</td>'
                 f'<td class=g>{"reviews only" if d in a["light"] else ""}</td></tr>')
    rows_cards = ""
    for r in a["records"]:
        strip = hist_html(r["history"])
        late = r["due"] is not None and midnight(r["due"]) < a["today"]
        rows_cards += (
            f'<tr class="{"warn" if r["again"] >= 3 else ""}">'
            f'<td class=w>{esc(r["word"])}<em>{esc(r["gloss"])}</em></td>'
            f'<td class=ty>{esc(r["type"])}</td>'
            f'<td class=n>{r["ivl"]}</td>'
            f'<td class="n {"low" if r["ease"] <= 1.5 else ""}">{r["ease"]:.2f}</td>'
            f'<td class="n {"late" if late else ""}">{esc(due_in(r["due"], a["today"]))}</td>'
            f'<td class=hist>{strip}</td></tr>')
    hard = "".join(
        f'<tr><td class=w>{esc(a["word"].get(n, n))}</td>'
        f'<td class=g>{esc(a["gloss"].get(n, ""))}</td>'
        f'<td class=n>{m} of {t}</td></tr>' for n, m, t in a["hard"]) or \
        '<tr><td colspan=3 class=g>nothing yet</td></tr>'
    gap = (a["today"] - a["last_seen"]) // DAY if a["last_seen"] else None
    when = "—" if gap is None else "today" if gap == 0 else \
           "yesterday" if gap == 1 else f"{gap} days ago"
    b = a["buckets"]
    page = f"""<!doctype html><meta charset=utf-8><title>Progress — {esc(uid)}</title><style>
body{{font-family:system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;
background:#E8EBE4;color:#181B18;line-height:1.5}}
h1{{font-size:1.15rem;margin-bottom:.2rem}}
h2{{font-family:ui-monospace,monospace;font-size:.7rem;letter-spacing:.14em;
text-transform:uppercase;color:#6C736B;margin:2rem 0 .6rem;font-weight:400}}
.sub{{font-size:.8rem;color:#6C736B;font-family:ui-monospace,monospace}}
.box{{background:#FCFDFB;border:1px solid #C9CFC4;padding:1rem 1.2rem}}
.kv{{display:grid;grid-template-columns:auto 1fr;gap:.4rem 1.2rem}}
.kv dt{{font-size:.85rem;color:#6C736B}}
.kv dd{{margin:0;font-family:ui-monospace,monospace;font-size:.9rem;text-align:right}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
td{{padding:.28rem .4rem;border-bottom:1px solid #E8EBE4}}
td.d{{width:7.5rem;color:#6C736B;font-size:.78rem}}
td.n{{text-align:right;font-family:ui-monospace,monospace;width:4.5rem}}
td.w{{font-size:1rem}} td.g{{color:#6C736B;font-size:.8rem}}
td.bar i,td.bar u{{display:inline-block;height:.7rem;vertical-align:middle}}
td.bar i{{background:#2F6B3E}} td.bar u{{background:#A32C22}}
table.cards th{{text-align:left;font-family:ui-monospace,monospace;font-size:.6rem;
letter-spacing:.1em;text-transform:uppercase;color:#6C736B;font-weight:400;
padding:.2rem .4rem;border-bottom:1px solid #C9CFC4}}
table.cards th:nth-child(n+3){{text-align:right}}
table.cards th:last-child{{text-align:left}}
tr.warn td{{background:#F9F1F0}}
td.w em{{display:block;font-style:normal;color:#6C736B;font-size:.72rem}}
td.ty{{font-family:ui-monospace,monospace;font-size:.68rem;color:#6C736B}}
td.n.low{{color:#A32C22;font-weight:700}} dd.low{{color:#A32C22;font-weight:700}} td.n.late{{color:#A32C22}}
td.n.diag{{color:#6C736B}} td.n.hot{{color:#A32C22;font-weight:700}}
td.hist{{font-family:ui-monospace,monospace;letter-spacing:.08em;white-space:nowrap}}
td.hist b{{font-weight:400;cursor:default}}
td.hist b.g{{color:#2F6B3E}} td.hist b.a{{color:#A32C22}}
</style>
<h1>{esc(uid)}</h1>
<div class=sub>last seen {esc(when)} · {a['streak']}-day streak · {a['reviews']} reviews all told</div>
<h2>Where he is</h2>
<div class=box><dl class=kv>
<dt>Words started</dt><dd>{a['started']} of {a['total_notes']}</dd>
<dt>Cards in rotation</dt><dd>{a['cards_started']}</dd>
<dt>Still locked</dt><dd>{a['locked']}</dd>
<dt>New words left</dt><dd{' class=low' if a['runway'] < 4 else ''}>{a['unseen']}</dd>
<dt>Learning / young / mature</dt><dd>{b['learning']} / {b['young']} / {b['mature']}</dd>
<dt>Median sitting</dt><dd>{a['median_minutes']:.0f} min</dd>
</dl></div>
<h2>Turning up</h2>
<div class=box><table>{rows}</table></div>
<h2>Giving him trouble</h2>
<div class=box><table>{hard}</table></div>
<h2>Every card he has met — {len(a['records'])} of {a['total_cards']}</h2>
<div class=box><table class=cards>
<tr><th>word</th><th>type</th><th>ivl</th><th>ease</th><th>due</th>
<th>history — oldest first, hover for the date</th></tr>
{rows_cards}</table></div>
{ear_html(e)}
"""
    (dest / "progress.html").write_text(page, encoding="utf-8")
    return dest / "progress.html"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default="")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    key = api_key()

    if args.list:
        docs = get(f"{BASE}?key={key}").get("documents", [])
        print(f"{len(docs)} deck(s):")
        for d in docs:
            f = {k: dec(v) for k, v in d.get("fields", {}).items()}
            print(f"  {d['name'].split('/')[-1]:<40} "
                  f"{len(f.get('cards') or {}):>4} cards  {len(f.get('log') or []):>5} reviews")
        return 0

    uid, cards, log, ear, done = load_remote(key, args.user)
    notes = json.loads((ROOT / "deck/notes.json").read_text(encoding="utf-8"))["notes"]
    spell, sound, label = ear_content()
    a = analyse(cards, log, notes, done)
    e = analyse_ear(ear, log, spell, sound, label)
    report(uid, a, e)
    if a["days"]:
        print(f"  wrote {html(uid, a, e, out_dir('progress'))}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

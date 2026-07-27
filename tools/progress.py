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
    return doc["name"].split("/")[-1], fields.get("cards") or {}, fields.get("log") or []


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


def analyse(cards, log, notes):
    word = {n["id"]: n["word"] for n in notes}
    gloss = {n["id"]: n.get("gloss", "") for n in notes}
    note_of = lambda k: k.rsplit("__", 1)[0]
    type_of = lambda k: k.rsplit("__", 1)[1] if "__" in k else "?"

    by_day = defaultdict(lambda: {"good": 0, "again": 0})
    for e in log:
        by_day[midnight(e["ts"])][e["grade"]] += 1
    days = sorted(by_day)

    today = midnight(int(datetime.now().timestamp() * 1000))
    streak = 0
    if days and days[-1] in (today, today - DAY):
        streak, prev = 1, days[-1]
        for d in reversed(days[:-1]):
            if prev - d != DAY: break
            streak += 1; prev = d

    lapses = Counter(note_of(e["card"]) for e in log if e["grade"] == "again")
    seen = Counter(note_of(e["card"]) for e in log)
    hard = sorted(((nid, lapses[nid], seen[nid]) for nid in lapses),
                  key=lambda r: (-r[1], -(r[1] / max(r[2], 1))))[:12]

    buckets = {"learning": 0, "young": 0, "mature": 0}
    for st in cards.values():
        ivl = st.get("ivl", 0)
        buckets["learning" if ivl < YOUNG else "young" if ivl < MATURE else "mature"] += 1

    started_notes = {note_of(k) for k in cards}
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
        type_of=type_of, reviews=len(log),
    )


def fmt_day(ms): return datetime.fromtimestamp(ms / 1000).strftime("%a %d %b")


def report(uid, a):
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
    p(f"  deck          {a['started']}/{a['total_notes']} words started, "
      f"{a['cards_started']} cards, {a['locked']} still locked")
    b = a["buckets"]
    p(f"  maturity      {b['learning']} learning, {b['young']} young, {b['mature']} mature")
    p("\n  recent days")
    for d in a["days"][-10:]:
        v = a["by_day"][d]
        tot = v["good"] + v["again"]
        rate = round(v["good"] / tot * 100) if tot else 0
        p(f"    {fmt_day(d)}  {tot:>3} reviews  {rate:>3}% first time  "
          + "█" * min(tot, 40))
    if a["hard"]:
        p("\n  giving him trouble")
        for nid, miss, tot in a["hard"]:
            p(f"    {a['word'].get(nid, nid):<14} {a['gloss'].get(nid, ''):<18} "
              f"missed {miss} of {tot}")
    p("")


def html(uid, a, dest):
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
                 f'<td class=n>{round(v["good"]/tot*100) if tot else 0}%</td></tr>')
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
</style>
<h1>{esc(uid)}</h1>
<div class=sub>last seen {esc(when)} · {a['streak']}-day streak · {a['reviews']} reviews all told</div>
<h2>Where he is</h2>
<div class=box><dl class=kv>
<dt>Words started</dt><dd>{a['started']} of {a['total_notes']}</dd>
<dt>Cards in rotation</dt><dd>{a['cards_started']}</dd>
<dt>Still locked</dt><dd>{a['locked']}</dd>
<dt>Learning / young / mature</dt><dd>{b['learning']} / {b['young']} / {b['mature']}</dd>
<dt>Median sitting</dt><dd>{a['median_minutes']:.0f} min</dd>
</dl></div>
<h2>Turning up</h2>
<div class=box><table>{rows}</table></div>
<h2>Giving him trouble</h2>
<div class=box><table>{hard}</table></div>
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

    uid, cards, log = load_remote(key, args.user)
    notes = json.loads((ROOT / "deck/notes.json").read_text(encoding="utf-8"))["notes"]
    a = analyse(cards, log, notes)
    report(uid, a)
    if a["days"]:
        print(f"  wrote {html(uid, a, out_dir('progress'))}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

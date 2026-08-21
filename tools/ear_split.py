#!/usr/bin/env python3
"""
Split ONE continuous recording into the per-word folders.

    python3 tools/ear_split.py                 # just (re)write the order sheet
    python3 tools/ear_split.py mytake.wav

Read the words aloud in the order printed in ear/reading-order.txt (this script
writes that file), leaving about a second of silence between each. The script
finds the gaps, checks it got exactly the number of words it expected, and only
then drops each piece into ear/raw/<word>/.

If the count is wrong it writes NOTHING and shows you where the gaps landed, so a
miscount can never quietly shift every word into the wrong folder.

Re-recording only a few? Give them in order:
    python3 tools/ear_split.py fixes.wav --subset kos,kosz,siad

Read each word several times in a row for a bigger sample? Say how many:
    python3 tools/ear_split.py mytake.wav --reps 3
The app picks one take at random per trial, so extra takes cost nothing and
stop him learning one particular recording instead of the contrast.

The input filename becomes the speaker tag (frank0.wav -> "frank0"), so the
app can pin the "listen to both" comparison to one voice. Override it with
--speaker if you'd rather name it something else:
    python3 tools/ear_split.py anna-session2.wav --speaker anna

Preview without writing:
    python3 tools/ear_split.py mytake.wav --dry-run

Standard library + ffmpeg only.
"""

import argparse
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
RAW   = ROOT / "ear/raw"
INDEX = ROOT / "index.html"
ORDER = ROOT / "ear/reading-order.txt"

# Reading order is FIXED once and stored, not derived fresh each run. Every
# reader gets the same order and --subset must match it, so a second opinion
# about the order would file a whole take into the wrong folders — and the
# segment count would still come out exactly right, so nothing would catch it.
ORDER_SEED = 20260821
MIN_APART  = 4     # positions between two words of the same contrast set

DEF_NOISE = "-35dB"   # louder than this counts as speech; raise toward -30 if gaps are noisy, lower toward -45 if quiet
DEF_GAP   = 0.30      # a silence must last this long to count as a word boundary
DEF_PAD   = 0.20      # seconds of silence kept around each cut (ear_build.py trims tight later)
MIN_SEG   = 0.12      # anything shorter than this isn't a word — a click or breath


def die(msg):
    print("X " + msg)
    sys.exit(1)


def speaker_from_filename(name):
    """frank0.wav -> frank0, Anna Session 2.wav -> Anna_Session_2.
    Keeps it filesystem-safe and collapses '__' so it can't be mistaken
    for the name/rest separator ear_build.py looks for."""
    s = re.sub(r"[^A-Za-z0-9-]+", "_", name)
    s = re.sub(r"_+", "_", s).strip("_-")
    return s or "speaker"


def have_ffmpeg():
    from shutil import which
    return which("ffmpeg") and which("ffprobe")


def ffmpeg_too_old():
    """Presence isn't enough — a genuinely ancient build (pre-2014) rejects
    flags this script relies on and fails in ways that look like a levels
    problem. Catch that here, once, with a clear message, instead of letting
    it surface later as a confusing false 'no silence found'."""
    p = run(["ffmpeg", "-hide_banner", "-version"])
    if p.returncode == 0:
        return None
    from shutil import which
    path = which("ffmpeg") or "(not found)"
    ver = run(["ffmpeg", "-version"])
    first_line = ver.stdout.splitlines()[0] if ver.stdout else "(couldn't even get a version string)"
    return (f"The ffmpeg on your PATH is too old for this script.\n"
            f"    Location: {path}\n"
            f"    Reports:  {first_line}\n\n"
            f"    This isn't a levels or recording problem — ffmpeg is rejecting basic flags,\n"
            f"    which happens with builds from roughly pre-2014. Likely a leftover from an\n"
            f"    old Audacity install still sitting earlier on PATH than anything newer.\n\n"
            f"    Fix: winget install Gyan.FFmpeg  (or brew install ffmpeg on Mac), then make\n"
            f"    sure that one — not this one — is what 'ffmpeg' resolves to. On Windows,\n"
            f"    'Get-Command ffmpeg -All' in PowerShell lists every copy in PATH order;\n"
            f"    rename or delete the old ffmpeg.exe it finds, then reopen the terminal.")


def run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def parse_index():
    """Word keys and spellings out of index.html — the same source the app
    renders from and ear_build.py names folders from."""
    try:
        text = INDEX.read_text(encoding="utf-8")
    except OSError:
        die("can't read index.html")
    sets = re.search(r"const SETS\s*=\s*\[(.*?)\n\];", text, re.S)
    words = re.search(r"const WORDS\s*=\s*\{(.*?)\n\};", text, re.S)
    if not sets or not words:
        die("couldn't parse SETS/WORDS out of index.html")
    rows, keys, seen = [], [], set()
    for line in sets.group(1).splitlines():
        row = re.findall(r'"([^"]+)"', line)
        if not row:
            continue
        rows.append(row)
        for k in row:
            if k not in seen:
                seen.add(k); keys.append(k)
    spell = {}
    for k, warr in re.findall(r'"([^"]+)"\s*:\s*\{\s*w\s*:\s*\[([^\]]*)\]', words.group(1)):
        spell[k] = "".join(re.findall(r'"([^"]*)"', warr))
    return keys, rows, spell


def shuffled(keys, rows):
    """An order that keeps a contrast set's members well apart. Reading
    kos / kosz / koś back to back invites contrastive stress, and a trainer
    built from hyperarticulated tokens is easier than speech."""
    setof = {k: i for i, row in enumerate(rows) for k in row}
    rng = random.Random(ORDER_SEED)
    def gap(o):
        last, worst = {}, 99
        for i, k in enumerate(o):
            s = setof[k]
            if s in last:
                worst = min(worst, i - last[s])
            last[s] = i
        return worst
    best = None
    for _ in range(200000):
        o = keys[:]; rng.shuffle(o)
        g = gap(o)
        if best is None or g > best[0]:
            best = (g, o)
            if g > MIN_APART + 1:
                break
    if best[0] < MIN_APART:
        die(f"couldn't find a reading order with {MIN_APART} positions between "
            f"members of a contrast set (best was {best[0]}). Lower MIN_APART.")
    return best[1]


def read_order(reorder=False):
    keys, rows, spell = parse_index()

    if ORDER.exists() and not reorder:
        # Parse the --subset line, not the numbered list: that line is written
        # for machines, while the list carries "(done)" marks and column
        # padding meant for a person. Reading the pretty half is how this
        # broke the first time.
        body = ORDER.read_text(encoding="utf-8")
        m = re.search(r"^--subset\s+(\S+)\s*$", body, re.M)
        if not m:
            die(f"{ORDER.relative_to(ROOT)} has no --subset line — delete it and "
                f"re-run to regenerate, or restore it from git")
        have = [k for k in m.group(1).split(",") if k]
        extra = [k for k in have if k not in keys]
        missing = [k for k in keys if k not in have]
        if extra or missing:
            # Silently carrying on would file a take into the wrong folders
            # while the segment count still matched exactly — invisible.
            print("X ear/reading-order.txt disagrees with index.html.")
            if missing:
                print(f"    new in index.html, not in the order: {', '.join(missing)}")
            if extra:
                print(f"    in the order, gone from index.html: {', '.join(extra)}")
            print("\n  The order is fixed on purpose: every reader gets the same one and")
            print("  --subset must match it. Regenerate it with:")
            print("      python3 tools/ear_split.py --reorder")
            print("  Any reading sheet already sent out becomes stale when you do.")
            sys.exit(1)
        return have, spell

    order = shuffled(keys, rows)
    if reorder:
        print("! regenerated the reading order — any sheet already sent out is now")
        print("  stale, and a take read from it would be filed wrongly.\n")
    return order, spell


def already_recorded():
    """Words with at least one clip in ear/raw/ already. Marked on the sheet so
    a top-up session doesn't mean re-reading the whole list."""
    if not RAW.exists():
        return set()
    return {d.name for d in RAW.iterdir()
            if d.is_dir() and any(f.is_file() for f in d.iterdir())}


def write_order_sheet(order, spell, have):
    """The one order, and the --subset line that matches it. Regenerated on
    every run from the same list read_order returned, so the file on disk
    can never disagree with what the splitter would use."""
    todo = [k for k in order if k not in have]
    lines = [
        "THE reading order. Fixed — every reader gets this one, and",
        "tools/ear_split.py --subset must match it. Regenerated on each run",
        "of that tool; to change the order itself, use --reorder.",
        "",
        "Read these aloud IN THIS ORDER into one continuous recording.",
        "Leave ~1 second of clear silence between each. Normal pace — please",
        "don't over-enunciate: many of these are near-identical to others",
        "further down, and that is the whole exercise.",
        "",
        "    python3 tools/ear_split.py yourfile.wav",
        "",
    ]
    if have and todo:
        lines += [f"{len(have)} of these are already recorded, marked (done) below.",
                  "To record only what is missing, read just the unmarked ones and run:",
                  "",
                  "    python3 tools/ear_split.py yourfile.wav --subset " + ",".join(todo),
                  ""]
    for i, k in enumerate(order, 1):
        lines.append(f"{i:2}. {spell.get(k, k):<9} {k}" + ("   (done)" if k in have else ""))
    lines += ["", "--subset " + ",".join(order)]
    ORDER.parent.mkdir(parents=True, exist_ok=True)
    ORDER.write_text("\n".join(lines) + "\n", encoding="utf-8")
    back, _ = read_order()
    if back != order:
        die(f"{ORDER.relative_to(ROOT)} does not read back as it was written — "
            f"the format and the parser disagree. This is a bug in ear_split.py.")


def duration(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(p.stdout.strip())
    except ValueError:
        die(f"ffprobe couldn't read {path}")


def detect_speech(path, noise, gap, total):
    """Return list of (start, end) speech segments as the complement of silence."""
    p = run(["ffmpeg", "-hide_banner", "-i", str(path),
             "-af", f"silencedetect=noise={noise}:d={gap}", "-f", "null", "-"])
    starts = [float(m) for m in re.findall(r"silence_start:\s*(-?\d+\.?\d*)", p.stderr)]
    ends   = [float(m) for m in re.findall(r"silence_end:\s*(-?\d+\.?\d*)",   p.stderr)]
    if not starts and not ends:
        # could genuinely mean "no silence in this audio" — or ffmpeg choked
        # (missing filter, bad build, unreadable file) and said so on stderr.
        # Tell the two apart instead of quietly assuming the first.
        lower = p.stderr.lower()
        trouble = ("error" in lower or "unrecognized" in lower or "no such filter" in lower
                   or "invalid" in lower or p.returncode != 0)
        if trouble:
            die("ffmpeg couldn't run silence detection — this isn't a levels problem.\n"
                "    Last lines from ffmpeg:\n    " +
                "\n    ".join(p.stderr.strip().splitlines()[-6:]) +
                "\n\n    Likely a stripped-down ffmpeg build missing a filter, or a corrupt/"
                "unreadable file.\n    Try: ffmpeg -filters | findstr silence   (Windows)"
                "   /   ffmpeg -filters | grep silence   (Mac/Linux)\n"
                "    If that shows nothing, reinstall ffmpeg (a full/essentials build, not a minimal one).")
    # pair them into silence intervals, tolerating a trailing unmatched start
    sil = []
    ei = 0
    for s in starts:
        s = max(0.0, s)
        if ei < len(ends):
            sil.append((s, ends[ei])); ei += 1
        else:
            sil.append((s, total))
    # complement -> speech
    seg, cur = [], 0.0
    for s, e in sil:
        if s - cur > MIN_SEG:
            seg.append((cur, s))
        cur = max(cur, e)
    if total - cur > MIN_SEG:
        seg.append((cur, total))
    return seg


def cut(src, seg, pad, total, dst):
    a = max(0.0, seg[0] - pad)
    b = min(total, seg[1] + pad)
    p = run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
             "-i", str(src), "-ac", "1", str(dst)])
    return p.returncode == 0 and dst.exists()


def main():
    # let "--noise -35dB" work: argparse would otherwise read -35dB as a flag.
    argv = sys.argv[1:]
    fixed = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--noise" and i + 1 < len(argv) and argv[i + 1].startswith("-"):
            fixed.append("--noise=" + argv[i + 1]); i += 2; continue
        fixed.append(a); i += 1

    ap = argparse.ArgumentParser()
    ap.add_argument("recording", nargs="?",
                    help="the take to split; omit to just (re)write the order sheet")
    ap.add_argument("--subset", help="comma-separated words, in recording order")
    ap.add_argument("--speaker", help="speaker tag override (default: taken from the input filename)")
    ap.add_argument("--noise", default=DEF_NOISE,
                    help="silence threshold, e.g. -35dB (a leading dash is fine)")
    ap.add_argument("--gap", type=float, default=DEF_GAP)
    ap.add_argument("--pad", type=float, default=DEF_PAD)
    ap.add_argument("--reorder", action="store_true",
                    help="regenerate the reading order itself (invalidates sheets already sent)")
    ap.add_argument("--reps", type=int, default=1,
                    help="how many times each word was read, in a row (default 1)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(fixed)

    order, spell = read_order(args.reorder)
    RAW.mkdir(parents=True, exist_ok=True)
    write_order_sheet(order, spell, already_recorded())
    print("wrote ear/reading-order.txt")
    if not args.recording:
        return 0

    if not have_ffmpeg():
        die("ffmpeg/ffprobe not found on PATH.")
    problem = ffmpeg_too_old()
    if problem:
        die(problem)
    src = Path(args.recording)
    if not src.exists():
        die(f"no such file: {src}   (ear/reading-order.txt is ready, though)")

    if args.subset:
        want = [w.strip() for w in args.subset.split(",") if w.strip()]
        bad = [w for w in want if w not in order]
        if bad:
            die(f"unknown word(s): {', '.join(bad)}  (see ear/raw/_WORDS.txt)")
    else:
        want = order

    if args.reps < 1:
        die("--reps must be at least 1")
    # Each word read R times in a row, so segment i belongs to word i // R.
    # Extra takes are pure gain: the app picks one at random per trial, so
    # more tokens per word means he learns the contrast rather than one clip.
    expect = [w for w in want for _ in range(args.reps)]

    total = duration(src)
    seg = detect_speech(src, args.noise, args.gap, total)
    speaker = speaker_from_filename(args.speaker if args.speaker else src.stem)

    print(f"expected {len(want)} words"
          + (f" x {args.reps} takes = {len(expect)} segments" if args.reps > 1 else "")
          + f", found {len(seg)} sound segments in {total:.1f}s"
          + f"  (noise={args.noise} gap={args.gap}s)")
    print(f"speaker tag: {speaker}"
          + ("" if args.speaker else f"  (from filename — override with --speaker)") + "\n")

    if len(seg) != len(expect):
        print("COUNT MISMATCH — nothing written. Detected segments:\n")
        for i, (s, e) in enumerate(seg, 1):
            flag = "  <- very short" if e - s < 0.2 else ("  <- long, two words merged?" if e - s > 1.2 else "")
            print(f"  {i:2}. {s:6.2f}–{e:6.2f}  ({e-s:.2f}s){flag}")
        print("\nLikely fixes:")
        print("  too many segments  -> a breath or click was counted; raise --gap (e.g. 0.5)")
        print("                        or lower the noise floor (e.g. --noise -45dB)")
        print("  too few segments   -> two words ran together; leave longer gaps and re-record,")
        print("                        or lower --gap (e.g. 0.25)")
        print("  Re-record just the run that went wrong with --subset.")
        if args.reps > 1:
            over = len(seg) - len(expect)
            print(f"  Off by {over:+d}. With --reps {args.reps} the count must be an exact")
            print(f"  multiple of {args.reps}, so a single dropped or doubled take shifts")
            print(f"  every word after it — which is why nothing is written.")
        sys.exit(1)

    # count matches: assign in order
    rows, outliers = [], []
    durs = [e - s for s, e in seg]
    med = sorted(durs)[len(durs) // 2]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for i, (word, (s, e)) in enumerate(zip(expect, seg), 1):
        d = e - s
        note = ""
        if d < 0.18:
            note = "SHORT — may be clipped"; outliers.append(word)
        elif d > med * 2.2:
            note = "LONG — may contain two words"; outliers.append(word)
        rows.append((i, word, spell.get(word, word), s, d, note))

    # One line per word, its takes side by side. Reading across shows whether
    # the repeats agree with each other — a hurried one stands out.
    w = max(len(r[2]) for r in rows)
    print("assignment:" + (f"  {len(want)} words x {args.reps} takes" if args.reps > 1 else ""))
    for n, word in enumerate(want):
        take = rows[n * args.reps:(n + 1) * args.reps]
        spread = ""
        if args.reps > 1:
            ds = [r[4] for r in take]
            if max(ds) > min(ds) * 1.8:
                spread = "  <- takes disagree, listen"
                outliers.append(word)
        notes = "  ".join(dict.fromkeys(r[5] for r in take if r[5]))
        print(f"  {n+1:2}. {take[0][2].ljust(w)}  @{take[0][3]:6.2f}s  "
              + " ".join(f"{r[4]:.2f}" for r in take)
              + f"  -> ear/raw/{word}/  {notes}{spread}")

    if args.dry_run:
        print("\ndry run — nothing written.")
        return

    if outliers:
        print(f"\n! flagged: {', '.join(dict.fromkeys(outliers))} — listen to these after.")

    print()
    written = 0
    for i, key, sp, s, d, note in rows:
        (RAW / key).mkdir(parents=True, exist_ok=True)
        dst = RAW / key / f"{speaker}__{stamp}-{i:03}.wav"
        if cut(src, seg[i - 1], args.pad, total, dst):
            written += 1
        else:
            print(f"  X failed to cut {key}")
    print(f"wrote {written}/{len(rows)} clips into ear/raw/ (speaker: {speaker}).\n"
          f"Now run:  python3 tools/ear_build.py")


if __name__ == "__main__":
    main()

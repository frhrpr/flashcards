# Polish vocab flashcards (barebones SRS)

Spaced-repetition vocab trainer for the same student as the sibilants repo (a separate,
unrelated tool — don't merge them). Repo: github.com/frhrpr/flashcards. Built with Claude
on claude.ai; this file is the handoff to CLI work.

## What it is
One file, `vocab.html`. No build pipeline (unlike the sibilants repo) — deliberately kept
that simple for v1.

## Key decisions (don't relitigate without reason)
- **Firebase Firestore**, chosen specifically for *low hassle*, not for "control" — that
  was an earlier, explicitly abandoned framing. Don't suggest Supabase (its free tier
  pauses projects after 7 days idle — ruled out for that reason) or a hand-rolled
  Cloudflare Worker unless asked; Firebase needs zero server code, just the CDN SDK.
- **One Firestore document per student**, holding all card states + a review log.
  No per-card documents, no separate collections.
- **No login screen.** Identity is a long random ID embedded in the URL (`?u=...`),
  read from the URL or localStorage, generated and written into the URL via
  `history.replaceState` if missing. This is explicitly *not* real security — anyone
  with the exact link could read/write that student's progress. Accepted trade-off
  given what's actually at stake (flashcard review state, nothing sensitive).
- Firestore rule is deliberately wide open *within one collection*:
  ```
  match /progress/{docId} { allow read, write: if true; }
  ```
- **SM-2-lite scheduling**, two grades only (Again / Good) — not Anki's four-grade
  Again/Hard/Good/Easy. Ease starts at 2.5, floors at 1.3, only moves on a lapse.
  Intervals: 1 day, then 6 days, then `ivl * ease`. No sub-day learning steps.
  On "Again", the card is also spliced back into the in-memory session queue
  (`position min(queue.length, 3)`) so it resurfaces later the same sitting, not just
  the next calendar day.
- `CARDS` is a plain JS object at the top of the file — `front`, `back`, optional `img`
  and `audio` (schema supports both, neither is populated yet).

## Explicitly deferred (v1 was scoped down on purpose, not accidentally incomplete)
- Only 2 grades, not 4
- No stats screen (Firestore has the data, no view for it yet)
- No daily new-card cap (irrelevant at 8 cards, will matter once the real ~400-word
  deck loads)
- No real images/audio in any card yet

## Seed deck
8 cards, all real words already used in the student's actual graded-reader stories —
not arbitrary examples: dom, pies, kot, słońce, piłka, skakać, śpiewać, zielony.

## Current state — VERIFY, DON'T ASSUME
As of the handoff, Firebase project setup was in progress (web app registered, script-tag
CDN approach confirmed over npm) and the repo was being cloned into WSL with a fresh PAT.
**Not confirmed**: whether the Firebase config has been pasted into `vocab.html` and
`FIREBASE_READY` flipped to `true`, whether `vocab.html` has actually been pushed to the
repo yet, or whether the Firestore rule above has been published. Check `git log`,
`git status`, and the actual contents of `firebaseConfig` in the file before assuming
any of this is done.
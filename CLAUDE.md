# Polish vocab flashcards

Spaced-repetition vocab trainer for one adult student — Evert, 40s, A1/A2
Polish. Repo: github.com/frhrpr/flashcards, served at
https://frhrpr.github.io/flashcards/

Same student as the sibling *sibilants* repo. That is a separate, unrelated
tool — don't merge them.

## Layout

```
index.html         the whole app — one file, no build step, served by Pages
deck/vocab.csv     every word he has met (see deck/README.md)
deck/frequency.csv top-500 Polish list — the sentence allowlist, NOT a syllabus
```

The app has deliberately **no build pipeline**. A content pipeline under
`tools/` is planned (see Roadmap) — that generates data, it does not build
the app. Keep `index.html` a single static file.

## Key decisions — don't relitigate without reason

- **Firebase Firestore**, chosen for *low hassle*, not for "control" — an
  earlier framing that was explicitly abandoned. Don't suggest Supabase
  (free tier pauses projects after 7 days idle) or a hand-rolled Cloudflare
  Worker unless asked. Firebase needs zero server code, just the CDN SDK.
- **One Firestore document per student**, holding all card states plus a
  review log. No per-card documents, no separate collections.
- **No login screen.** Identity is a long random id in the URL (`?u=...`),
  read from the URL or localStorage, generated via `history.replaceState`
  if absent. Explicitly *not* security — anyone with the link can read and
  write that student's progress. Fine for flashcard state.
- Firestore rule is deliberately wide open within one collection:
  `match /progress/{docId} { allow read, write: if true; }`
- **SM-2-lite, two grades** (Again / Good) — not Anki's four. Ease starts
  at 2.5, floors at 1.3, moves only on a lapse. Intervals 1 day, 6 days,
  then `ivl * ease`. No sub-day learning steps. "Again" also splices the
  card back into the session queue at `min(queue.length, 3)`.
- **Writes are deltas.** `updateDoc` with a field path for the one card that
  changed plus `arrayUnion` on the log. The old `setDoc` re-uploaded every
  card state and the whole log on every grade — hundreds of KB per button
  press once the log is long, felt on mobile long before the 1 MiB document
  ceiling matters. First run still needs `setDoc`; `updateDoc` requires an
  existing document.
- **State is keyed `${noteId}__${cardType}`**, so production / listening /
  cloze cards can be added without migrating live progress. Only
  `recognition` exists today. Legacy bare-note-id state is folded in on load.
- **`note_id` must match `[a-z0-9_]+`** — it is used as a Firestore field
  path, where diacritics would need backtick quoting. `słońce` → `slonce`,
  `śmiać się` → `smiac_sie`.
- **`NEW_PER_DAY` caps new cards.** Counted from an `introduced` stamp on
  card state, not session state, so it survives reloads and a second device.
- **Grammar words don't get cards.** `deck/vocab.csv` marks prepositions,
  conjunctions and similar `flashcard: no`. They still count as known and
  stay in the sentence allowlist — `na` is learned through the case it
  governs, not from a card saying "na = on".

## Current state

Working and deployed. Firebase config is live in `index.html` and
`FIREBASE_READY` is true.

`deck/notes.json` holds 8 notes — gloss, part of speech, IPA, and an example
sentence with an English translation and a gapped variant. The app fetches
it at load; `CARDS` no longer exists. Text was authored by Claude, **not yet
checked by a human** (`reviewed: false` on every note). No audio and no
images exist yet, so those keys are absent and cards render without them.

**No grammar metadata.** Gender, aspect, and declension tables were tried
and deliberately removed: this trains vocabulary, not morphology, and
sentences are free to use any inflected form (`Nie mam psa.` for `pies`).
Don't reintroduce them. For the same reason the validator does not try to
check sentence words against the allowlist — that needs a lemmatiser, and a
prefix heuristic warns on every correct sentence.

The remaining 52 words in `deck/vocab.csv` have no notes yet.

**Unverified:** whether the Firestore security rule above has actually been
published, and whether the `updateDoc` delta writes succeed against a real
document (syntax and queue logic are tested, the Firestore round-trip is
not). Check before assuming.

## Roadmap

Full Anki-style notes: image, audio, IPA, example sentence, gapped sentence
for cloze, part of speech, short Polish definition. One note produces up to
four cards (recognition, production, listening, cloze).

Decided so far:

- **Text** (POS, gender/aspect, definition, sentence, cloze) — one LLM call
  per word with structured outputs. Constrain sentence vocabulary to an
  allowlist of `deck/vocab.csv` plus the top N of `deck/frequency.csv`, or
  sentences come out full of words he doesn't know.
- **Audio** — neural pl-PL TTS, generated once at build time and committed,
  not fetched per review. SRS means ~20 reviews per card; on-demand would
  re-synthesise the same string every time and add latency to every flip.
  The whole deck is ~25k characters, inside every provider's free tier.
  Name files by hash of text+voice so editing one sentence regenerates one
  clip.
- **IPA** — carried in the data whether or not it's displayed. Polish
  orthography is near-phonemic, so this is low value next to audio.
- **Images** — only for concrete words; roughly half the deck has nothing
  depictable. LLM sets a `concrete`/`scene`/`none` flag. No image-gen API
  key yet, so the plan is to generate *prompts* and produce them by hand
  (~10/week is tractable).

Deferred on purpose: 4 grades instead of 2, a stats screen, staged unlock
of production cards behind mature recognition cards.

## Working notes

- **Verify, don't assume.** Check `git log`, `git status`, and the actual
  file contents. This file has been wrong before.
- **Fail loudly.** The user has asked explicitly for the pipeline to be
  bulletproof and to surface errors rather than swallow them. Validate at
  every boundary, make re-runs idempotent and resumable, put failures in a
  visible list rather than a log, dry-run anything that spends money.
- **The user spot-checks the Polish.** Generated sentences go to a real
  student, so build a review step rather than trusting generation.
- **The Google Drive connector is read-and-create only** — no update, no
  delete. A file there can never be edited in place. This is why the word
  list lives in the repo. A Drive sheet *the user* writes and Claude only
  reads would work, if phone editing of the CSV ever becomes annoying.
- Auth is an SSH key; the remote is `git@github.com:frhrpr/flashcards.git`.
  Claude can't push from the sandbox (it denies `~/.ssh` by design).

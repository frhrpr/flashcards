# Polish vocab flashcards

Spaced-repetition vocab trainer for one adult student — Evert, 40s, A1/A2
Polish. Repo: github.com/frhrpr/flashcards, served at
https://frhrpr.github.io/flashcards/

Same student as the sibling *sibilants* repo. That is a separate, unrelated
tool — don't merge them.

**The user does everything through Claude.** He does not edit these files by
hand and should not be told to. He supplies words after a lesson, approves
sentences and image prompts, and drops generated images into a folder;
Claude does the rest, including running the tools and pushing.

## Layout

```
index.html          the whole app — one file, no build step, served by Pages
deck/notes.json     card content, fetched by the app at load
deck/vocab.csv      every word he has met, whether or not it has a card
deck/frequency.csv  top-500 Polish list — sentence allowlist, NOT a syllabus
media/audio/*.mp3   generated once and committed, never fetched per review
media/manifest.json what each clip was generated from, for staleness checks
tools/validate.py   run after every change; exits non-zero if unshippable
tools/tts.py        synthesises missing audio; dry-run by default
```

The app has deliberately **no build pipeline**. Tools under `tools/` generate
data; they do not build the app. Keep `index.html` a single static file.

### notes.json

```jsonc
{ "id": "kot",              // == a note_id in vocab.csv, [a-z0-9_]+
  "word": "kot", "gloss": "cat", "pos": "noun", "ipa": "kɔt",
  "note": null,             // Polish, short, only when it earns its place
  "image": "media/img/kot.webp",  // omit the key until the file exists
  "image_alt": "a cat",           // required whenever image is set
  "audio": "media/audio/kot.mp3", // omit the key until the file exists
  "sentence": {
    "pl": "Mały kot pije mleko.", "en": "The little cat is drinking milk.",
    "gap": "Mały ___ pije mleko.",  // gap + answer must rebuild pl exactly
    "answer": "kot",                // the form as it appears in the sentence
    "answer_lemma": "kot",          // the headword it belongs to
    "audio": "media/audio/kot__sentence.mp3" },
  "cards": ["recognition"], // add "cloze" to drill the gapped sentence too
  "reviewed": false }       // true once a human has read the Polish
```

Media keys are **absent until the file exists**. A path that is set but
missing is an error; a missing key is only a to-do. The deck therefore stays
shippable, and `validate.py` still reports what is outstanding.

`vocab.csv` columns: `word, note_id, pos, flashcard, status, source, added,
notes`. `status` is `queued` → `known` → `carded`.

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
- **State is keyed `${noteId}__${cardType}`**, so card types can be added
  without migrating live progress. Legacy bare-note-id state is folded in on
  load. Three types exist. Cloze was built and removed: its only unique
  contribution was drilling the *inflected* form, which is the morphology
  this tool deliberately does not teach.
  What each side shows is declared in `LAYOUT` in `index.html` — a front
  never carries anything that would give its own answer away, which is why
  production withholds the audio and IPA as well as the word.
- **`recognition` is what the user calls "comprehension".** Kept as-is: the
  id is a live Firestore field path, and renaming it would migrate real
  progress for a cosmetic gain.
- **Siblings are buried.** Answering one card of a note drops its other
  cards from today's queue, and the daily new-card budget takes at most one
  card per note. Without this he passes the second and third on ten-second
  recall rather than on knowing the word, and the scheduler believes it.
- **Staged unlock.** `production` and `listening` are not introduced
  until that note's `recognition` card has `ivl >= 6` — two correct answers,
  about a week in. The gate governs *introducing* only: a card that already
  has state stays in rotation, so a later lapse on recognition cannot yank
  away production work under way.
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
for cloze, part of speech, short Polish definition. One note produces three
cards (recognition, production, listening).

Decided so far:

- **Text** (POS, gender/aspect, definition, sentence, cloze) — one LLM call
  per word with structured outputs. Constrain sentence vocabulary to an
  allowlist of `deck/vocab.csv` plus the top N of `deck/frequency.csv`, or
  sentences come out full of words he doesn't know.
- **IPA** — carried in the data whether or not it's displayed. Polish
  orthography is near-phonemic, so this is low value next to audio.
- **Images** — generated with `gemini-2.5-flash-image`, ~4 euro cents each,
  billing enabled on the Gemini key (the free tier reports `limit: 0` for
  every image model — it has never been free). Flash not pro: these render
  at 800px on a phone.

**Keep image prompts as simple as the word allows.** Every clause is a
chance to be wrong. The first `skakać` prompt asked for a cat jumping *onto*
a bench and got one jumping away — spatial relations are what these models
fumble. Describe a position ("above the bench, about to land") rather than a
direction, and drop any detail the word does not need. `image_basis` records
whether a picture illustrates the word alone or the sentence's scene;
concrete words take `word`, and the sentence is then irrelevant to the image
because the card already carries it as text and audio.

`tools/images.py --check` asks a vision model specific yes/no questions —
does it show the word, is it unambiguous, is there text — and flags rather
than blocks. It caught the `skakać` direction fault on its own. Judging a
`word`-basis image against the sentence produces nothing but noise, which is
why the prompt is conditional on `image_basis`.

Deferred on purpose: 4 grades instead of 2, and a stats screen.

## Working notes

- **Verify, don't assume.** Check `git log`, `git status`, and the actual
  file contents. This file has been wrong before.
- **Fail loudly.** The user has asked explicitly for the pipeline to be
  bulletproof and to surface errors rather than swallow them. Validate at
  every boundary, make re-runs idempotent and resumable, put failures in a
  visible list rather than a log, dry-run anything that spends money.
- **The user spot-checks the Polish.** Generated sentences go to a real
  student, so build a review step rather than trusting generation.
- **Audio is generated once and committed**, never fetched per review — a
  card is seen ~20 times, so on-demand would re-synthesise the same string
  every time and put a round-trip in front of every flip. `tools/tts.py`
  fingerprints each clip over text + voice + model, so a corrected sentence
  regenerates exactly one file. ElevenLabs, free tier, voice Antoni
  (`ErXwobaYiN019PkySvjV`), `eleven_multilingual_v2`. Key in `.env`,
  gitignored. Free-tier keys **cannot use Voice Library voices via the API**,
  only certain built-ins.
- **Verify audio before adopting it.** A 256-byte JSON error page passes an
  existence check happily; `tts.py` writes to a temp file and only keeps it
  once ffprobe confirms real audio of non-zero length.
- Auth is an SSH key; the remote is `git@github.com:frhrpr/flashcards.git`.
  Pushing and any non-allowlisted network call need
  `dangerouslyDisableSandbox` — the sandbox denies `~/.ssh` and allows only
  github/npm/pypi. Writing to `/mnt/c/...` (to put files somewhere Windows
  can open them) needs it too.
- **The Google Drive connector is read-and-create only** — no update, no
  delete, so nothing there can be maintained in place. The repo is the only
  store both sides can write to. Superseded in practice: the user works
  through Claude at this machine rather than editing files from a phone.

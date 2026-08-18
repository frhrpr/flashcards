# Polish vocab flashcards

Spaced-repetition vocab trainer for one adult student — Evert, 40s, A1/A2
Polish. Repo: github.com/frhrpr/flashcards, served at
https://frhrpr.github.io/flashcards/

Two modes, one site, one Firestore document per student: **vocab**
flashcards and **ear training** on minimal pairs. The ear trainer was a
separate repo (`~/projects/Polish`, "sibilants") until 2026-08-18 and was
merged in here; that repo is archived and its `CLAUDE.md` now points at
this one.

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
lessons/*.md        one per lesson: story, new words, questions asked
media/audio/*.mp3   generated once and committed, never fetched per review
media/img/*.webp    one image per note, 800px, generated
media/manifest.json provenance for every media file — source, licence, checks
media/ATTRIBUTION.md generated from the manifest; do not edit
ear/raw/*/          source recordings, one folder per word, plus the master take
ear/audio/*/        trimmed and levelled mp3s — generated, do not edit
ear/manifest.json   which clips exist for which word — generated
tools/validate.py   run after every change; exits non-zero if unshippable
tools/smoke.mjs     renders every card face AND every ear trial in node
tools/audio.py      Commons recordings for words, TTS for sentences
tools/images.py     generate / fetch / assign images, and --check them
tools/review.py     builds the approval page; records approvals
tools/progress.py   how the student is getting on; reads Firestore over REST
tools/deckio.py     shared loading, saving, attribution (not runnable)
tools/ear_split.py  cuts one long take into ear/raw/<word>/; prints the read-aloud sheet
tools/ear_build.py  ear/raw → ear/audio + ear/manifest.json (trim, level, encode)
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
  "cards": ["recognition", "production", "listening"],
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
  at 2.5 and floors at 1.3. Intervals 1 day, 6 days, then `ivl * ease`. No
  sub-day learning steps. "Again" also splices the card back into the session
  queue at `min(queue.length, 3)`.
- **Ease recovers, but only when earned.** A lapse costs 0.2; a correct
  answer returns 0.15, and only from the third consecutive one — which is
  also where ease starts affecting the interval. Ten correct answers in a row
  climb from the floor back to 2.5. Ease used to fall only, so a word failed
  during one bad fortnight stayed on short intervals permanently, long after
  it was learned. With two grades there is no "Easy" button, so recovery has
  to be inferred from a streak.
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
- **Staged unlock, per type.** `UNLOCK_IVL` maps each gated type to the
  recognition interval it waits for. Intervals run 1, 6, 15, 38, so the
  thresholds land at real points: `production` at `ivl >= 6` opens the day
  after the word is introduced, `listening` at `ivl >= 15` a week in. Note
  that 6 is reached on day *one*, not after a week — two correct answers
  happen on consecutive days. Listening is pushed back deliberately: reading
  leaves him the spelling to lean on and the recording leaves him nothing.
  The gate governs *introducing* only: a card that already has state stays in
  rotation, so a later lapse on recognition cannot yank away work under way.
- **`note_id` must match `[a-z0-9_]+`** — it is used as a Firestore field
  path, where diacritics would need backtick quoting. `słońce` → `slonce`,
  `śmiać się` → `smiac_sie`.
- **Order is shuffled, seeded on the day plus the user id.** Due date still
  dominates; the shuffle only breaks ties and orders the new-card pool. The
  seed makes a mid-session reload stable rather than reshuffling under him,
  while every day differs. Without it the sequence was identical every
  session and new words arrived in file order, so notes at the end of the
  file would never be introduced.
- **Any user id starting `test` never writes, and skips the maturity gate**
  so every card type is visible at once. A scratch session is for looking at
  the app, not for learning; waiting a week to see a production card would
  defeat it. A banner says so, and progress dies on reload — that is the
  point. Nothing to corrupt, since these sessions never save.
- **The closing screen sells coming back, not completeness.** Order is:
  you are finished, well done, come back on this day. Locked cards are last,
  small and grey, with a line saying there is nothing to do about them — a
  count he cannot act on reads as a backlog and discourages.
- **Intake is capped in words, not cards** — 3 a day, matched to what he
  meets in lessons. A word's other card types are not new vocabulary, and on
  a shared budget an unlocking backlog would starve new words entirely, so
  siblings get their own smaller allowance (5). The first ever session gets
  10, because there is nothing to review yet and finishing after two cards
  reads as broken; that is a day-one problem, not a reason to top up every
  quiet day. All counted from `introduced` stamps on card state, so the
  numbers survive a reload and a second device.
- **Conjugation drills are notes with `kind: "form"`.** `być` and `mieć` are
  his worst cards precisely because the deck teaches a headword he will never
  utter — he says *jestem*, *jest*, *są*. Each form is therefore its own note
  (`byc_jestem`, `miec_mam`, …) carrying one `form` card: a gapped sentence
  with the verb cued in brackets, plus its own image and audio.

  They are notes rather than a nested array *because* each needs its own
  media — that way `audio.py`, `images.py`, `review.py` and `smoke.mjs` work
  unchanged. They never enter `vocab.csv`: `jestem` is a form of `być`, not a
  word learned, so the word count stays honest and `validate.py` skips the
  cross-check for them.

  Two rules differ from ordinary notes. They are **not buried** — knowing
  `jest` gives away nothing about `jestem`, so when several do fall on the
  same day the contrast is welcome. And they are **gated on the parent verb's**
  recognition card, having none of their own.

  They draw on the *sibling* allowance, not the daily word budget: a form was
  already taught in the lesson, so it is not new vocabulary. An earlier
  version introduced a whole paradigm at once, exempt from both budgets; that
  was removed as unnecessary for the same reason.

  This is a deliberate, bounded exception to the no-morphology rule. It
  applies to two irregular verbs whose forms *are* the vocabulary. Do not let
  it grow into declension tables.
- **A note can drop a card type when that type is unanswerable.** `chodzić`
  and `iść` are both "to go"; `siadać` and `siedzieć` are both about sitting.
  Shown the English and asked for the Polish there are two right answers and
  only one is marked correct, so those four notes carry no `production` card.
  The distinction is real Polish and is taught in the `note` field and in
  lessons — it is just not something a flashcard can grade. Check
  `deck/notes.json` glosses for collisions before adding a word.
- **Grammar words don't get cards.** `deck/vocab.csv` marks prepositions,
  conjunctions and similar `flashcard: no`. They still count as known and
  stay in the sentence allowlist — `na` is learned through the case it
  governs, not from a card saying "na = on".

## Ear training

Merged in from the sibilants repo on 2026-08-18. Forced-choice minimal
pairs: hear a word, tap which of two you heard.

- **A separate session, not cards in the vocab queue.** The interaction
  models are opposites — a flashcard is revealed and self-graded, a minimal
  pair is tapped and graded automatically — and they want different
  schedulers. SM-2 pushes a known item toward long maintenance intervals,
  which is exactly wrong for a perceptual skill measured across many
  exemplars.
- **The unit is the confusion pair, not the word.** `SETS` in `index.html`
  declares contrast families; `PAIRS` expands each into its two-way
  combinations at runtime, so `kos/kosz/koś` is three pairs. The old app
  showed all three at once, which half-reports: a miss tells you which
  confusion, but a hit only tells you he avoided both. And s-vs-sz is a
  different skill from s-vs-ś — only pair-level state can see which one he
  is failing, or aim the next trial at it.
- **Twenty trials, shrinking.** Length is set by trial count, never by
  mastery: if "done" meant clearing the failing pairs, a bad day would get
  longer exactly when he is having the worst time. The block does shrink as
  pairs retire — `clamp(round(20 * active / total), 6, 20)` — and that is
  the reward.
- **Sampling is weighted toward what he is currently failing**, and every
  active pair is guaranteed one appearance before anything repeats. Both
  were on the old repo's roadmap and never done; trials there were uniformly
  random.
- **Retirement at 9 of the last 10, and any miss un-retires.** Those two
  rules only coexist if a retired pair's window *restarts* on a miss —
  otherwise 10/10 followed by a miss is still 9/10 and the pair never comes
  back. So it does restart. Once every pair has retired, a 6-trial
  maintenance block from the longest-unseen pairs, at most every third day;
  on other days the landing shows ear training as satisfied. Never offer a
  mode you cannot fill.
- **Firestore: two new top-level fields, and `cards` is untouched.**
  `ear: { "kos|kosz": { seen, hist, last } }` where `hist` is the trailing
  ten outcomes, and `done: { "<dayMs>": ["vocab","ear"] }` pruned at 90 days.
  Putting pair items in `cards` would entangle a perceptual drill with the
  daily budgets, the unlock gates and sibling burying for no gain and real
  risk to live progress. Burying needs no exemption as a result: `kasa` is
  both a vocab note and an ear word, but an ear trial never touches `queue`.
- **Ear keys need `FieldPath`.** They carry `|` and `-`, and `done` keys are
  bare digits; none are legal in an unquoted dotted field path, so ear writes
  use `new FieldPath("ear", key)` rather than a template string. Renaming the
  ids to dodge this was rejected — the ids are `ear/raw/` folder names, and
  renaming them orphans the recordings.
- **One log shape.** Ear entries are `{card: "kos__ear", grade, ts, chose, vs}`.
  Keying `<word>__ear` matches `${noteId}__${cardType}`, and keeping `grade`
  means the day buckets, the streak and the sittings split in `progress.py`
  work untouched — attendance is unified for free. `chose` powers the
  confusion matrix. `vs` names the distractor, and is a deliberate addition
  to the merge plan's shape: on a correct answer `chose == played`, so
  without it the pair a trial belonged to is unrecoverable from the log and
  only the ten-trial window could say anything about it.
- **One streak, not two**, derived from the shared log's day buckets. Two
  streaks would let a good day on one side visibly break the other's,
  manufacturing a failure out of a success. The per-mode breakdown is fully
  available to the teacher because the log is granular; this is a display
  decision only.
- **The landing states each mode's size**, and a satisfied mode is greyed and
  not tappable — tapping in and landing on "nothing due" reads as broken
  rather than finished. When both are open ear training gets the visual
  default: it is short, it is a warm-up, and there is no
  did-I-remember-this pressure in it. Completion is read from `done`, not
  session state, so a reload or his other device does not re-offer it.
- **`FALLBACK_TTS` is gone.** It existed so the app was testable before any
  audio existed. Worse than useless now: for c/cz/ć before recordings exist
  it would drill him against a TTS voice that may not render the contrast at
  all. Skipping sets with no audio is the right fallback and already works.
- **Pairs are not vocabulary.** Like `kind: "form"` notes they never enter
  `deck/vocab.csv`, so the word count stays honest. They live in `WORDS` and
  `SETS` in `index.html` rather than a JSON file because `ear_build.py` and
  `ear_split.py` parse them straight out of it.
- The old per-browser `localStorage` stats (`pl-sibilants-v1`) were dropped
  rather than migrated — per-browser, modest, and never reached the teacher.

### Recording new pairs

1. Add the words to `WORDS` and the row to `SETS` in `index.html`. They ship
   immediately and are skipped until audio exists.
2. `python3 tools/ear_split.py` — writes `ear/raw/_RECORD_ORDER.txt`, which
   marks what is already recorded and prints the `--subset` line for the rest.
3. He reads the unmarked words into one take, ~1 s of silence between each.
4. `python3 tools/ear_split.py take.wav --subset a,b,c` then
   `python3 tools/ear_build.py`. The split refuses to write anything if the
   number of segments it finds disagrees with the number of words expected,
   so a miscount can never quietly shift every word into the wrong folder.

The 150 ms silence pad and the RMS levelling in `ear_build.py` are tuned for
frication onsets and have nothing to do with `tools/audio.py`. The ffmpeg
version check in both scripts must survive: it exists because an ancient 2013
`ffmpeg.exe` in `Python310\Scripts` once shadowed the real one on this user's
PATH and every call failed confusingly.

## Current state

Working and deployed. Firebase config is live in `index.html` and
`FIREBASE_READY` is true.

`deck/notes.json` holds **78 complete, human-approved notes** — 66 words, every
one in
`vocab.csv` marked `flashcard: yes`. Each has an image, word audio (human,
from Wikimedia Commons, except `siadać` which is TTS), sentence audio, an
example sentence with translation and gap, gloss, part of speech and IPA.
plus 12 `kind: "form"` conjugation drills. 206 cards across four types
(66 recognition, 66 listening, 62 production, 12 form); four notes carry no
`production` card (see the gloss-collision rule above).

Ear training holds **24 minimal pairs** derived from 18 contrast sets, of
which 16 have recordings. The 8 c/cz/ć pairs are approved and shipped in
`WORDS`/`SETS` but unrecorded, so the app skips them until the audio lands.

Live since 2026-07-26 at `?u=evert`, and he is using it — ~390 reviews over
15 days, 90%+ correct in the most recent week. Three lessons taught, all in
`lessons/`, and their words are carded.

**No grammar metadata.** Gender, aspect, and declension tables were tried
and deliberately removed: this trains vocabulary, not morphology, and
sentences are free to use any inflected form (`Nie mam psa.` for `pies`).
Don't reintroduce them. For the same reason the validator does not try to
check sentence words against the allowlist — that needs a lemmatiser, and a
prefix heuristic warns on every correct sentence.

The Firestore rule **is** published — confirmed by reading and deleting
documents over the REST API with only the web key, which is exactly what the
open rule permits. Delta writes work against a real document. Documents can
be listed and deleted from here:

    K=$(grep -o 'apiKey: "[^"]*"' index.html | cut -d'"' -f2)
    curl -s "https://firestore.googleapis.com/v1/projects/flashcards-f5b40/databases/(default)/documents/progress?key=$K"

## Roadmap

Full Anki-style notes: image, audio, IPA, example sentence, gapped sentence
part of speech, short Polish definition. One note produces up to four cards
(recognition, production, listening, and `form` for conjugation drills).

Decided so far:

- **Text** (POS, definition, sentence, gap) — written by Claude in session
  per word with structured outputs. Constrain sentence vocabulary to an
  allowlist of `deck/vocab.csv` plus the top N of `deck/frequency.csv`, or
  sentences come out full of words he doesn't know.
- **IPA** — carried in the data whether or not it's displayed. Polish
  orthography is near-phonemic, so this is low value next to audio.
- **Images** — generated with `gemini-2.5-flash-image`, ~4 euro cents each,
  billing enabled on the Gemini key (the free tier reports `limit: 0` for
  every image model — it has never been free). Flash not pro: these render
  at 800px on a phone.

**Prefer the sentence's scene, but not at the cost of a complicated prompt.**
An image that shows what the sentence says is worth more than a stock picture
of the word, because it reinforces the card as one unit. Take it whenever the
sentence is a subject doing one plain action — `Mały kot pije mleko.` is a
cat drinking milk from a bowl, and that beats a cat standing about.

Fall back to the word alone when the sentence hinges on a **spatial relation**
(`pod ławką`, `na ławkę`, `w parku`) or needs several elements arranged just
so. Those are what these models fumble, and a wrong picture is worse than a
plain one. `image_basis` records which was used, and the check prompt depends
on it.

**"Plain background" is for objects, not people.** It suits a single concrete
noun, where anything else in frame competes with the thing being named. Asked
for a *person*, the same phrase produces a figure marooned in a grey studio,
which looks synthetic and gives the sentence nothing to sit in. Let the scene
be wherever the sentence implies — a kitchen, a shop, a park — and simply say
nothing about the background when the sentence names no place. Do not invent
a setting for its own sake either; an unstated one is fine.

**Keep image prompts as simple as the word allows.** Every clause is a
chance to be wrong. The first `skakać` prompt asked for a cat jumping *onto*
a bench and got one jumping away — spatial relations are what these models
fumble. Describe a position ("above the bench, about to land") rather than a
direction, and drop any detail the word does not need. `image_basis` records
whether a picture illustrates the word alone or the sentence's scene;
concrete words take `word`, and the sentence is then irrelevant to the image
because the card already carries it as text and audio.

`tools/images.py --check` asks a vision model specific yes/no questions and
flags rather than blocks. It caught the `skakać` direction fault on its own.
Two calibration lessons, both learned by getting 24 flags out of 43:

- Judging a `word`-basis image against the sentence is pure noise, so the
  prompt is conditional on `image_basis`. Almost every image is `word` basis
  — a picture of the concept, however abstract. Only `skakać` and `śpiewać`
  actually re-enact their sentence.
- The bar is **misleading, not merely insufficient**. The card also shows the
  gloss and the sentence, so a picture only has to be a memory hook. Asking
  "would a learner guess this word from the picture alone" flags every verb,
  because a bird in flight does also contain a bird.

Some words cannot be depicted at all — `być`, `teraz`. They keep their
flagged image; the gloss and sentence carry the meaning.

Deferred on purpose: 4 grades instead of 2, and a stats screen.

## Working notes

- **`node --check` is not enough for index.html.** It parses; it does not
  resolve names, so it passes a file that calls a function an edit has
  deleted. That happened. Run `node tools/smoke.mjs` after any change to
  the app — it renders every card face against the real deck, drives a whole
  ear session, and catches it in a second. It works by slicing three regions
  out of `index.html` between literal markers rather than copying them, so it
  cannot drift; if a marker moves it fails loudly. A slice must not end
  inside a comment — one did, silently commenting out the block after it,
  which is why `/* ── end of ear content ── */` exists as an explicit
  boundary.
- **Verify, don't assume.** Check `git log`, `git status`, and the actual
  file contents. This file has been wrong before.
- **Fail loudly.** The user has asked explicitly for the pipeline to be
  bulletproof and to surface errors rather than swallow them. Validate at
  every boundary, make re-runs idempotent and resumable, put failures in a
  visible list rather than a log, dry-run anything that spends money.
- **Lessons are stories.** Each lesson introduces ~10 new words inside a
  short story built from the deck plus those words, because a narrative gives
  each word a hook and the story's lines can become the card sentences later.
  Words are picked from `deck/frequency.csv` *and* for whether a story can be
  written round them — utility first, coherence second. Ten a week sits under
  the 3-a-day intake cap, so a lesson is absorbed without backing up. Kept in
  `lessons/` as the teaching record; a page for use during the lesson goes to
  `Downloads/flashcards/lessons/`. Cards are made **after** the lesson, so
  only words that actually landed get carded.
- **The user spot-checks the Polish.** Generated sentences go to a real
  student, so build a review step rather than trusting generation. He caught
  `Czy mogę mieć wodę?` as a calque — Polish uses `mieć` to possess, never to
  request. Watch for English idioms carried over word-for-word; the validator
  cannot see them and neither can the generator that wrote them.
- **Use the implicit subject.** The allowlist contains no words for people,
  so sentences kept reaching for animals and came out absurd — a bird that
  walks, a dog fed milk. Polish drops pronouns, so a conjugated verb supplies
  a human subject at zero vocabulary cost: `Rano jem chleb.` is natural where
  `Pies je chleb.` is not. Prefer 1st and 2nd person for verbs, and reach for
  `deck/frequency.csv` when a sentence needs a noun the deck lacks — a
  natural sentence with one unmet common word beats a strange one.
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

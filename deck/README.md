# deck/

Source data for the trainer. Edit from anywhere — github.com's web editor
works fine from a phone. **Run `python3 tools/validate.py` after any edit**;
it catches everything below and exits non-zero if the deck is unshippable.

## notes.json

Card content. `index.html` fetches this at load, so adding a word means
editing this file, never the app.

```jsonc
{
  "id": "kot",              // must equal a note_id in vocab.csv, [a-z0-9_]+
  "word": "kot",
  "gloss": "cat",           // English
  "pos": "noun",
  "gender": "m-anim",       // nouns: m-anim | m-inan | f | n
  "aspect": "impf",         // verbs: impf | pf
  "aspect_pair": "skoczyć", // verbs: the other half of the pair
  "forms": {                // nouns gen+pl, verbs sg1+sg3, adjectives f+n
    "gen": "kota", "pl": "koty"
  },
  "ipa": "kɔt",
  "note": null,             // Polish, short, only when it earns its place
  "image": "media/img/kot.webp",   // omit until the file exists
  "image_alt": "a cat",            // required whenever image is set
  "audio": "media/audio/kot.mp3",  // omit until the file exists
  "sentence": {
    "pl": "Mały kot pije mleko.",
    "en": "The little cat is drinking milk.",
    "gap": "Mały ___ pije mleko.",  // gap + answer must rebuild pl exactly
    "answer": "kot",                // the inflected form as it appears
    "answer_lemma": "kot",          // the dictionary form
    "audio": "media/audio/kot__sentence.mp3"
  },
  "cards": ["recognition"], // add "cloze" to also drill the gapped sentence
  "reviewed": false         // set true once a human has read the Polish
}
```

**Media keys are absent until the file exists.** A path that is set but
missing is an error; a missing key is just a to-do. That way the deck is
always shippable and the validator still tells you what's outstanding.

**Gaps should not be sentence-initial** — capitalisation would give the
answer away, and the validator warns about it.

**`answer` is the inflected form**, because Polish sentences don't contain
citation forms. `answer_lemma` keeps the link back to the headword.

## vocab.csv

Every word Evert has met, whether or not it has a flashcard.

| column | meaning |
| --- | --- |
| `word` | the lemma, written properly, with diacritics |
| `note_id` | ASCII key used in filenames and Firestore field paths — see below |
| `pos` | noun, verb, adjective, adverb, preposition, conjunction, particle, pronoun, interjection |
| `flashcard` | `yes` / `no` — whether this word should get cards of its own |
| `status` | `queued` (new, unprocessed) / `known` (introduced, no card) / `carded` (live in the deck) |
| `source` | where it came from — which reader, lesson, conversation |
| `added` | ISO date, or blank for the pre-2026-07-26 backfill |
| `notes` | anything worth remembering |

**Adding a word:** fill in `word`, `pos`, `source`, `added`, and set
`status` to `queued`. Leave `note_id` blank and the pipeline will derive it.

**`flashcard: no`** is for grammar words. `na` doesn't want a card saying
"na = on" — it's learned through the case it governs. These words still
count as known, so generated sentences are free to use them.

**`note_id` must match `[a-z0-9_]+`.** It ends up as a Firestore field path
in `evertflashcards.html`, where diacritics would need backtick quoting.
Derived by transliterating (`słońce` → `slonce`) and replacing anything
else with `_` (`śmiać się` → `smiac_sie`). Must be unique.

## frequency.csv

Top 500 Polish nouns, verbs and adjectives by corpus frequency. **Not a
curriculum** — it is the allowlist for sentence generation, so a generated
example can be restricted to words Evert already knows plus the commonest
words in the language. Columns come from the original export: `rank, lemma,
pos, freq, ipm, ARF, total_freq, source_tags, rows`.

# deck/

## Which file do I edit?

| I want to… | Edit |
| --- | --- |
| record a word Evert has met | `vocab.csv` — add a row |
| fix a bad sentence, gloss or IPA | `notes.json` |
| mark Polish as checked | `notes.json` — set `"reviewed": true` |
| turn on cloze cards for a word | `notes.json` — add `"cloze"` to `cards` |

Nothing else. `index.html` holds no card content.

github.com's web editor works fine from a phone for both. **Run
`python3 tools/validate.py` after any edit** — it exits non-zero if the deck
is in a state that shouldn't reach a student.

## notes.json

Card content. `index.html` fetches this at load.

```jsonc
{
  "id": "kot",              // must equal a note_id in vocab.csv, [a-z0-9_]+
  "word": "kot",            // dictionary form
  "gloss": "cat",           // English
  "pos": "noun",            // shown on the card, in Polish: "rzeczownik"
  "ipa": "kɔt",
  "note": null,             // Polish, short, only when it earns its place
  "image": "media/img/kot.webp",   // omit the key until the file exists
  "image_alt": "a cat",            // required whenever image is set
  "audio": "media/audio/kot.mp3",  // omit the key until the file exists
  "sentence": {
    "pl": "Mały kot pije mleko.",
    "en": "The little cat is drinking milk.",
    "gap": "Mały ___ pije mleko.",  // gap + answer must rebuild pl exactly
    "answer": "kot",                // the form as it appears in the sentence
    "answer_lemma": "kot",          // the headword it belongs to
    "audio": "media/audio/kot__sentence.mp3"
  },
  "cards": ["recognition"], // add "cloze" to also drill the gapped sentence
  "reviewed": false         // set true once a human has read the Polish
}
```

**No grammar tables.** Gender, aspect and declension are not stored — this
trains vocabulary, not morphology. Sentences use whatever form reads
naturally, so `Nie mam psa.` is a fine sentence for `pies`; only `answer`
and `answer_lemma` record that the surface form differs from the headword.

**Media keys are absent until the file exists.** A path that is set but
missing is an error; a missing key is just a to-do. So the deck is always
shippable, and the validator still tells you what is outstanding.

**Gaps should not be sentence-initial** — capitalisation would give the
answer away, and the validator warns about it.

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

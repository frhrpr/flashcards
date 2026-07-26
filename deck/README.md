# deck/

Source data for the trainer. Edit `vocab.csv` from anywhere — github.com's
web editor works fine from a phone.

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

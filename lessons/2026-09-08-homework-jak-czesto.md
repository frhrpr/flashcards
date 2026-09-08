# Praca domowa — Jak często

Homework set 2026-09-08, after [[2026-09-08-zawsze-nigdy]]. Student sheet:
`Downloads/flashcards/lessons/2026-09-08-homework-jak-czesto.html` — two
parts, no answers on it.

## What it drills

**Part 1 — the four frequency words we kept.** `zawsze`, `nigdy`,
`codziennie`, `czasami`. `często` and `zwykle` are withdrawn from rotation
(see `tools/withdraw.py`) and deliberately do not appear anywhere on the
sheet: putting them back in front of him in writing while they are out of the
deck would rebuild exactly the six-way competition the withdrawal exists to
break.

**Ten items, three options each, and every wrong option is eliminated by one
of exactly two mechanisms.** That constraint is the whole design, and it is
the second design — the first draft failed and is worth recording.

The first version built each item on a plausible *reason*: "Marek has no
money" → "he ___ pays by card". But a reason does not fix a frequency.
*Sometimes he pays by card* is perfectly true of a man with no money, and half
the items had two or three defensible answers. **Plausibility cannot force a
choice between three adverbs that are all grammatical nearly everywhere.**

So each item now eliminates its distractors one of two ways only:

- **Named and denied.** The setup says `Ale nie zawsze!` or `Nie czasami!`,
  which kills that option by name. Seven items do this.
- **Impossible in the world.** Fish do not go shopping; the sun is not green.
  Two items do this, and both also carry `nie`, so `nigdy` is doubly forced.

Three of the ten carry `nie` for the second thing being taught: `nigdy` is
never alone, it is always `nigdy nie`.

**`zawsze` and `codziennie` are never offered in the same item.** English
*always* covers both, and nothing buildable out of his 102 met words separates
them cleanly — every attempt admitted both readings. Offering them together
would teach confusion rather than test a distinction. The distinction is real
and worth drawing, but it wants a teacher saying "`codziennie` counts days,
`zawsze` counts occasions", not a gap on a sheet.

**Part 2 — a story on his weakest cards, with six new words.** The story is
built to put his worst cards in front of him in context rather than on a
flashcard: `chcieć` (missed 17 of 37, his worst), `wiedzieć` (7 of 19),
`dziwny`, `pamiętać`, `myśleć`, `móc`, `miejsce`, `droga`, `patrzeć`,
`pytać`, `pierwszy`, `skakać`, `chodzić`.

## The six new words

`czytać`, `książka`, `znać`, `pytanie`, `robić`, `słowo` — all already carded
and complete, all sitting unseen in the bank, all now `priority: true`, so
they arrive within days of him reading this. Glossed on the sheet in English
and Dutch.

They were picked to earn their place in *this* story rather than off a list:

- **`robić`** is the verb the follow-up exercise needs. *Co robisz rano? Co
  robisz wieczorem?* cannot be asked without it, and it is top-50 frequency.
- **`znać` against `wiedzieć`** is deliberate and is the one judgement call
  here. `wiedzieć` is one of his worst cards, and its note already cites
  Dutch *kennen*/*weten* — but a note on a card is read once and forgotten.
  The story uses them side by side eight times: *Nie wiem, co to jest* /
  *Nie znam tego słowa*, *Ewa zna polski* / *Marek nie wie, gdzie jest sklep*.
  This is two of a pair, not a set of six, and the extremes-first rule is
  satisfied — the two are as far apart as the distinction goes.
- **`czytać` and `książka`** collocate, and they are what he is actually
  doing when he reads this sheet.
- **`pytanie`** shares a root with `pytać`, which is a weak card (`xxvxvxv`).
- **`słowo`** is what the whole story is about.

## Part 1 — answers

| | answer | what rules the other two out |
| --- | --- | --- |
| 1 | nigdy | fish do not shop at any frequency, and `nie` is in the sentence |
| 2 | zawsze | `Nie czasami!` by name; three occasions named with no exception |
| 3 | czasami | `Ale nie zawsze!` by name; `nigdy` needs `nie`, which is absent |
| 4 | codziennie | `Nie czasami!` by name; he does eat breakfast, so not `nigdy` |
| 5 | nigdy | the sun is yellow, so never green; `nie` again |
| 6 | czasami | `Ale nie zawsze pociągiem!` by name; and he does go by car |
| 7 | codziennie | `Nie czasami!` by name; two days running, counted as days |
| 8 | nigdy | both occasions are refusals, and Polish says `nigdy nie`, not `zawsze nie` |
| 9 | zawsze | `Nie czasami.` by name; `W deszczu też!` states the no-exception |
| 10 | czasami | `Ale nie codziennie!` by name; he does go, so not `nigdy` |

Three `nigdy`, three `czasami`, two `zawsze`, two `codziennie`. The correct
option sits first three times, second three times and third four times.

## What to watch

**Items 3, 6 and 10 are the ones that reward reading.** Each hides its answer
in a signpost — `ale nie zawsze`, `ale nie codziennie` — in the setup rather
than the gap. If he is getting these wrong he is reading the gap sentence and
skipping the line above it, which is a technique problem, not a vocabulary
one, and it is worth naming out loud.

**Item 8 is the only grammatical one.** `zawsze nie pije` and `czasami nie
pije` are both sayable Polish, so the elimination there is about which word
Polish actually uses to mean "not ever". If he picks `zawsze` he has built the
English sentence and translated it.

**`znać` vs `wiedzieć` in the story.** Watch for him producing *wiem* where
`znam` belongs. Dutch gives him the distinction free — *ik ken dat woord niet*
/ *ik weet het niet* — so if it goes wrong, the problem is that he has not
connected the Polish pair to the Dutch pair he already owns, which is a
thirty-second fix rather than a vocabulary problem.

## The sheet

No instructions and no questions on it — the teacher supplies both. The
glossary sits **above** the story rather than under it, covering the four
frequency words (green, on a 0–100% scale) and the six new ones (orange, with
the forms that appear in the text), so nothing has to be looked up by
scrolling past the thing you are reading.

## Checked

`tools/storycheck.py` on the whole sheet, both parts together: 85 headwords,
63 met, 6 prioritised and arriving, 16 grammar words, nothing in the bank
unseen and nothing missing from the deck. The checked source is kept beside
this file as `2026-09-08-homework-jak-czesto.story.txt`, lemma map included,
so it can be re-run rather than re-judged.

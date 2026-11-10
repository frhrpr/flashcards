# Lekcja 2026-11-10 — Urodziny Ewy (the -ę / -isz verbs)

Sheet: `out/lessons/2026-11-10-urodziny-ewy.pdf` (three pages: glosses and
story; the table and sixteen sentences; eight questions) and
`-opowiadanie.pdf` (story alone).

## Why this

The second present-tense group, as planned in *Szukam psa!* (2026-09-13),
and parked on 2026-10-29 so the cases could settle first. They have: every
accusative and instrumental form card was clean or nearly on 2026-11-10.

The case for it now is his own data. *dzwonić* recognition was 2 of his last
6 and *przychodzić* alternated every answer — cards for words he knows, failing
once conjugated — and in *Przyjaciel Svena* he tapped *śpisz, przychodzisz,
dzwonić*. Most of the verbs he says are in this group.

Same shape as *Szukam psa!*: one model verb in all six persons in the story,
a table beside the *czytać* column he already knows, an exercise where exactly
one person fits each gap.

## Scope

Regular verbs only, no stem change: *mówić, robić, lubić, dzwonić, myśleć*,
and with *-ysz/-y* after *cz, sz, rz, ż*: *słyszeć, patrzeć, uczyć się*.
**Kept out**: verbs whose consonant changes before *-ę/-ą* — *chodzę,
przychodzę, płacę, widzę, siedzę, muszę* — and *spać* (*śpię*). The story uses
*przychodzisz* only, which looks regular. A later lesson, or a sentence if he
asks why it is not *przychodzię*.

## Story

*mówić* and *słyszeć* in all six persons (no *mówię*, which is in the table),
every ending highlighted on the sheet. The phone call gives *ty*, the friends
outside give *wy* and *my*, narration gives *oni*. Ewa knows about the party
all along because Adam cannot speak quietly.

Problem words in it: *człowiek, słyszeć, włączyć, dzwonić, przychodzić,
głośno, szczęśliwy, nieść, wtedy, przyjaciel*. Nothing new.

## Exercise — answers

| | answer | person |
| --- | --- | --- |
| 1 | robisz | ty |
| 2 | lubię | ja |
| 3 | patrzą | oni |
| 4 | dzwonicie | wy |
| 5 | uczymy się | my |
| 6 | uczy się | on |
| 7 | lubicie | wy |
| 8 | myślisz | ty |
| 9 | lubią | oni |
| 10 | dzwonię | ja |
| 11 | patrzymy | my |
| 12 | patrzy | on |
| 13 | robicie | wy |
| 14 | dzwonią | oni |
| 15 | uczysz się | ty |
| 16 | myślimy | my |

Two for *ja* and *on*, three for the rest. Six are the *-y* verbs. Checked
mechanically: every answer distinct, none in the story, none printed in
another item's clue. *mówić* and *słyszeć* are never gapped — they are the
model. *kończyć* was drafted in and swapped out: carded but unseen.

## What to watch

**Items 5 and 16 (*Sven i ja*, *Adam i ja*)** are *my*, the trap from
*Szukam psa!*. **Item 4** is address — *Marcin, Robert, …?* — so *wy*.
**-ą for oni** (*lubią, patrzą*) now looks like the instrumental ending; one
sentence if he notices.

## Checked

`tools/storycheck.py` on story, exercise and questions: every word met.
Source and lemma map in `2026-11-10-urodziny-ewy.story.txt`.

## Revised before approval

The first draft had Ewa want to switch the lamp on and Sven say *Jeszcze
nie!*, and ended *Teraz można włączyć lampę* — there for *włączyć*, but it
connected to nothing and the teacher could not see why it was there. Cut.
*włączyć* came back as a running joke instead: on the phone Adam objects that
*w sobotę gra Polska*, and at the end, once they have gone into the living
room, he says *Sven, włącz telewizor! Polska gra!* — *Nie! Dzisiaj są moje
urodziny!* A first try put the TV in with no setup and no move out of the
hall; the teacher caught both. *Adam widzi telewizor*, not *patrzy*, because
*patrzy* is an exercise answer. *Polska* is recorded in vocab.csv as known,
no card: it is in frequency.csv, so storycheck will not take it as a name. Item 8's reply was *Myślę, że pada deszcz*,
an odd answer to *Co myślisz?*; now *Myślę, że Adam mówi bardzo głośno*.

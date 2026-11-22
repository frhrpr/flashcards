# Lekcja 2026-11-23 — Dwa bilety (the -ę / -esz verbs, harder reading)

Sheet: `out/lessons/2026-11-23-dwa-bilety.pdf` (three pages: glosses and
story; eight questions; the table and twelve sentences to build) and
`-opowiadanie.pdf` (story alone).

## Why this

The third present-tense group, named as the next new topic in *Dwa chleby*
(2026-11-16), and the last one he needs for the verbs he actually says:
*chcę, mogę, piję, idę, jadę*. His data backs it up: *chcieć* recognition is
one of his worst cards (17 of 47 missed) and *móc* recognition sits at ease
1.5.

## The reading steps up

Agreed 2026-11-22: the readings had become easy (and listening was 30 of 32
right first time). Four changes, all in this story; the fifth suggestion,
glossing less, was left as it was.

1. **Longer sentences, joined.** He already knew *bo, ale, więc, kiedy, że,
   który* and *albo*, but the stories barely used them. Measured on the story
   text alone: **6.6 words per sentence, longest 19**, against 4.4 and 11 in
   *Dwa chleby*. Reported speech (*Piotr mówi, że on i Ola bardzo chcą iść,
   ale nie mogą, bo…*), relative clauses (*babci, która zawsze ma czas*;
   *człowiek, który gotuje zupę*).
2. **Longer: 332 words** against 177, with more narration and less
   back-and-forth dialogue.
3. **Harder questions.** Six of the eight are *dlaczego?*, which need two
   sentences put together, and two need inference rather than finding a
   word: no. 6 (he watches the cooking man, not the match) and no. 8 (*bilety
   mają Ewa i babcia* is never said in that order).
4. **Three words to guess**, unglossed: *koncert, mecz, pizza*. Cognates for
   a Dutch speaker, and the context pins each down. The sheet tells him three
   words are new and asks him to work them out. `storycheck.py` now accepts a
   trailing `?` in the lemma block for exactly this, at most three per story.
   After the lesson, add the three to `vocab.csv` as `queued`.

## Scope

All six persons of *chcieć* and *móc* are in the story; *pić, iść, jechać,
pisać, brać, kupować, pracować, myć* turn up in one or two persons each.

The table has one column per class: *czytać* (-am), *mówić* (-ę, -isz),
*chcieć* (-ę, -esz). Under each column are the verbs that go with it,
including every verb in the exercise, so he can see which class a verb
belongs to. Below the table there is one note: *móc* changes inside (*mogę,
możesz … mogą*). The first draft had five columns and three lines of
small print (*pij-*, *-uję*, *piszę*, *idę/idziesz*). The teacher found it
chaotic and preferred to explain the small changes out loud, so they were
taken off the sheet. If he asks: *ja* and *oni* share one stem in *móc,
iść, jechać, brać*; *-ować* gives *-uję*; *pisać* keeps *sz* throughout.

**Kept out**: the *-em* verbs (*jem, wiem, rozumiem, umiem*). *jedzą* and
*rozumie* each appear once and are glossed; *jeść* is glossed with its
paradigm in case he asks.

## Story

Ewa has two tickets for a concert in the park on Saturday. Sven won't come,
because Poland are playing; Piotr and Ola are going to Gdańsk; Adam is
working, then watching the match with Sven. Babcia, who always has time,
says yes. On Saturday it rains, Ewa and babcia go anyway, and Sven switches
on the TV and finds only a man cooking soup. Adam arrives with pizza, checks
his phone: the match is tomorrow. Sven rings Ewa to ask whether they can
still come. No, says Ewa, babcia and I have the tickets. In the background
babcia is singing loudly. Sven and Adam spend the evening watching the soup.

*Adam i ja chcemy* and *Babcia i ja mamy* are the *X i ja = my* trap again;
*Ty i Adam zawsze chcecie* is the *wy* version.

Problem words in it: *człowiek, włączyć, znaleźć, chcieć, słyszeć,
jeszcze, ważny, inny, smutny, odpowiadać, przychodzić, dzwonić*.

Carded but not yet introduced, glossed on the sheet, and to be
**prioritised when this story is approved**: *bilet, brać, jutro, najpierw,
parasol, pisać, piątek, rozumieć*.

## Exercise — build a sentence

The same format as *Dwa chleby*, which worked. Eight items for the new group
cover all six persons; four revise *-am* and *-ę/-isz*. Cases come along as
before.

| | prompt | answer | verb | case |
| --- | --- | --- | --- | --- |
| ex. | Piotr i Ola / chcieć / iść / na / koncert | Piotr i Ola chcą iść na koncert. | | |
| 1 | ja / pić / kawa / z / mleko | Piję kawę z mlekiem. | -ę/-esz, ja | acc, ins (-iem) |
| 2 | ty / móc / otworzyć / okno? | Możesz otworzyć okno? | móc, ty (ż) | acc (no change) |
| 3 | Ewa / kupować / ryba | Ewa kupuje rybę. | -uję, ona | acc |
| 4 | my / czekać / na / babcia | Czekamy na babcię. | -am, my | acc |
| 5 | oni / iść / na / koncert | Idą na koncert. | iść, oni (d) | acc (no change) |
| 6 | wy / chcieć / czytać / książka | Chcecie czytać książkę. | -ę/-esz, wy | acc |
| 7 | Sven / lubić / herbata / z / cytryna | Sven lubi herbatę z cytryną. | -isz, on | acc, ins |
| 8 | my / jechać / z / Ola | Jedziemy z Olą. | jechać, my (dzi) | ins |
| 9 | ja / móc / włączyć / telewizor | Mogę włączyć telewizor. | móc, ja (g) | acc (no change) |
| 10 | wy / mieć / samochód | Macie samochód. | -am, wy | acc (no change) |
| 11 | Adam / pracować / z / brat | Adam pracuje z bratem. | -uję, on | ins |
| 12 | oni / patrzeć / na / kot | Patrzą na kota. | -isz, oni (-y group) | acc, living |

Accept the pronoun kept or dropped, and any sensible word order.

## What to watch

- **2 and 9**: *możesz* against *mogę*, the one stem change that matters.
- **5 and 8**: *idą* and *jedziemy*, the same pattern in two more verbs.
- **11 against 3**: *pracuje* and *kupuje*, the *-ować* verbs.
- **12 against 5**: *patrzą* and *idą*, the same *-ą* from two groups.
- In the story, whether he works out *koncert, mecz, pizza* without asking,
  and whether he gets nos. 6 and 8 without going back to the text.

## Checked

`tools/storycheck.py` on story, exercise and questions: every word met apart
from the eight bank words above and the three marked to guess. Source and
lemma map in `2026-11-23-dwa-bilety.story.txt`.

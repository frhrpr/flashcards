# Homework 2026-11-16 — Nad jeziorem (mixed revision, sentence building)

Sheet: `out/lessons/2026-11-16-homework-nad-jeziorem.pdf` (three pages:
glosses and story; eight questions; the two tables and twelve sentences to
build) and `-opowiadanie.pdf` (story alone, for email). For the Reading page
once approved. Listening episode 5, *Autobus*, goes with it.

## Why this

Homework after *Dwa chleby*, in the same shape at the teacher's request: a
story carrying both cases and both present-tense groups, then sentences to
build from dictionary forms.

Marcin, Sven's friend from *W pociągu* and *Gość Marcina*, has a new dog,
Burek. At the lake Burek eats the sausage Ewa brought for dinner, runs into
the lake and then to Sven, who is now wet, and so is his book. They have
only cucumbers and tomatoes left, so Marcin pays for dinner in a restaurant.
When the waiter asks whether the dog wants dinner too, Ewa says *Burek już ma
obiad!*

**New words, on purpose** (the teacher's call: food is useful): *kiełbasa,
musztarda, ogórek, pomidor*, and *mokry*. They are marked ✦ in the glosses and
recorded in `vocab.csv` as `queued`. Storycheck lists them as unseen, which is
expected. Two first drafts were revised on review. Dinner was bread and butter
and bread and cheese, too basic to be the point of a picnic. The dog then put
butter on Sven's shirt again, a repeat of the lesson's joke for no reason.

Highlighted as in the lesson:

- **Accusative:** *psa, Burka, kiełbasę, ptaka, książkę, Marcina, rybę*.
- **Instrumental:** *nad jeziorem, z Marcinem i z Burkiem* (*-iem* after *k*),
  *z musztardą, pod drzewem, z ryżem*.
- **Verbs:** *mam, mamy* for *-am*; *przychodzicie, przychodzimy, lubisz,
  lubię, patrzą* for *-ę/-isz*, and others in narration.

*Svena* in *przyjaciel Svena* and *do Svena* is genitive and deliberately not
highlighted.

Problem words, from his last six answers per card on 2026-11-16: *dzwonić,
biec, głośno, obiad, przyjaciel, jezioro*.

## Exercise — answers

| | prompt | answer | verb | case |
| --- | --- | --- | --- | --- |
| ex. | Marcin i Burek / patrzeć / na / ptak | Marcin i Burek patrzą na ptaka. | | |
| 1 | ja / czytać / list | Czytam list. | -am, ja | acc (no change) |
| 2 | ty / patrzeć / na / kobieta | Patrzysz na kobietę. | -isz, ty (-y) | acc |
| 3 | Sven / kochać / Ewa | Sven kocha Ewę. | -am, on | acc |
| 4 | ja / robić / obiad / z / brat | Robię obiad z bratem. | -isz, ja | acc (no change), ins |
| 5 | my / mieszkać / z / babcia | Mieszkamy z babcią. | -am, my | ins |
| 6 | Ola / uczyć się / z / siostra | Ola uczy się z siostrą. | -isz, ona (-y) | ins |
| 7 | ty / znać / Piotr | Znasz Piotra? | -am, ty | acc, living |
| 8 | my / lubić / czekolada | Lubimy czekoladę. | -isz, my | acc |
| 9 | wy / mieć / kawa / z / mleko | Macie kawę z mlekiem? | -am, wy | acc, ins (-iem) |
| 10 | wy / słyszeć / kot | Słyszycie kota? | -isz, wy (-y) | acc, living |
| 11 | oni / pytać / lekarz | Pytają lekarza. | -am, oni | acc, living |
| 12 | Piotr i Ola / robić / pierogi / z / mięso | Robią pierogi z mięsem. | -isz, oni | acc (no change), ins |

The two verb groups alternate, and each covers all six persons. Accept the
pronoun kept or dropped, and any sensible word order. Checked mechanically:
no answer's verb or noun form is in the story or the questions. The example
is taken from the story on purpose.

## What to watch

- **4 and 12**: *robię* against *robią*, the *ja* and *oni* endings that
  look alike.
- **11 against 12**: *pytają* (*-ją*) against *robią* (*-ą*).
- **1, 4 and 12**: *list, obiad, pierogi* do not change. He may want to
  change them.
- **7, 10 and 11**: *Piotra, kota, lekarza* are living masculines, so *-a*.

## Checked

`tools/storycheck.py` on story, exercise and questions: every word met apart from the five new ones. A
first question, *Gdzie są w sobotę?*, had two right answers (the lake and the
restaurant are both on Saturday); it is now *Co Ewa ma na obiad?*.

## Listening — episode 5, Zakupy

`lessons/2026-11-16-sluchanie-05-zakupy.story.txt` →
`listen/05-zakupy.mp3`, one take, 48 seconds.

On Saturday Marek and Ania go shopping: she buys bread, milk and cheese, and
he buys coffee and chocolate. No fish, because today they are making soup. At
home she makes the soup and he makes tea. The cat eyes the cheese (*Ser nie
jest dla kota!*), and in the evening they have soup and bread with cheese while
the cat drinks milk. Every question is answered by one sentence, in order.

**Replaced on review.** The first story, *Autobus*, had the cat turn up at
the bus stop although it was asleep at home. A second version planted an open
window to explain it, and the teacher still found it confusing. The fault was
the shape, not a missing line: a twist the listener has to infer is a reading
skill. Listening is harder already, so an episode should be a straight line of
concrete events, with nothing to work out except the words.

# Praca domowa — Drugi tydzień

Homework set 2026-08-26, after the lesson built on *Pierwszy tydzień*
(see [[2026-08-26-marek-w-nowym-miescie]]). Student sheet:
`Downloads/flashcards/lessons/2026-08-26-homework-drugi-tydzien.html` — gaps
only, no answers, with the paradigm table underneath.

## What it drills

Only `być` and `mieć`. The vocabulary is not tested at all — reading the
story and following it *is* the vocabulary exercise, which is why nothing
else is blanked.

Every content word is one he has met in the last three weeks or one now
marked `priority: true`, so the story is built entirely from what is live in
his deck right now: 68 headwords, none of them new.

## Why the gaps carry no verb cue

Same reason as [[2026-08-18-homework-w-sklepie]]. The twelve `kind: "form"`
cards name the verb in brackets — `Dziecko ___ (być) w parku` — so they test
the **form** and never the **choice**. Here he has to decide `być` or `mieć`
first and only then the person, which is the one thing the cards structurally
cannot ask and the distinction he actually gets wrong.

## Story

Marek mieszka w nowym mieście. To (1) jego drugi tydzień w pracy.

Rano pada zimny deszcz. Marek (2) w łóżku i myśli.

— Ja nie (3) czasu na śniadanie.

Potem jedzie pociągiem do miasta. Na ulicy (4) dużo ludzi i samochodów.

W sklepie Marek kupuje kawę. Płaci kartą, ale nie (5) pieniędzy.

W pracy Marek spotyka nowych ludzi.

— Cześć! Jak ty (6) na imię? — pyta kobieta.

— Ja (7) Marek. A ty?

— Ewa. Czy ty (8) nowy w pracy?

— Tak. To mój drugi tydzień. Czy ty (9) czas na kawę?

— Teraz nie (10) czasu. Praca jest nowa.

Wieczorem Marek wraca do domu. (11) zimny wieczór.

W parku (12) ludzie i psy. Dziecko (13) czerwoną piłkę. Ptaki śpiewają.

Marek siada na ławce. Ewa też siedzi w parku.

— To (14) dobre miejsce — mówi Marek.

— Tak. Teraz my (15) czas — mówi Ewa.

## Answers

| | answer | verb | why only this one |
| --- | --- | --- | --- |
| 1 | jest | być | to + a noun phrase; mieć is impossible here |
| 2 | jest | być | noun subject, locative w łóżku, no object |
| 3 | mam | mieć | explicit ja; genitive czasu after nie |
| 4 | jest | być | dużo takes the genitive and a singular verb |
| 5 | ma | mieć | Marek is still the subject from Płaci; genitive after nie |
| 6 | masz | mieć | explicit ty, and na imię is always mieć |
| 7 | jestem | być | explicit ja, naming himself |
| 8 | jesteś | być | explicit ty, adjective complement |
| 9 | masz | mieć | explicit ty, accusative czas |
| 10 | mam | mieć | answering a ty question about himself; genitive czasu |
| 11 | Jest | być | impersonal: adjective plus noun, no subject |
| 12 | są | być | plural subject, ludzie i psy |
| 13 | ma | mieć | noun subject, accusative object piłkę |
| 14 | jest | być | to + a noun phrase again |
| 15 | mamy | mieć | explicit my, accusative czas |

Eight `być`, seven `mieć`. Forms covered: `jest` ×5, `jestem`, `jesteś`, `są`;
`mam` ×2, `ma` ×2, `masz` ×2, `mamy`. Not covered: `jesteśmy`, `jesteście`,
`macie`, `mają` — second person plural needs a group to address, which a
two-hander cannot supply, and the flashcards cover all six persons anyway.

## What to watch

**Gap 5 is the only one that depends on discourse.** `nie ___ pieniędzy` has
no subject of its own; it carries over from `Płaci kartą` two clauses back.
If he writes `mam` there he has lost the thread rather than the verb.

**Gaps 1 and 14 are the same construction** — `to ___` plus a noun phrase.
Getting one and missing the other is worth asking about.

**Gap 4 is the quiet one.** `dużo` takes the genitive and a singular verb, so
`na ulicy jest dużo ludzi` even though the people are plural. If he writes
`są` he has understood the sentence and not the rule, which is the better
kind of mistake.

## Postscript — three words he had not met

Written 2026-08-26, after the sheet had already gone out.

`drugi`, `dużo` and `pieniądze` are all carded, and at the time this was sent
he had met none of them: no card state, no priority flag. The draft had been
checked against `deck/vocab.csv`, which is the sentence allowlist, and not
against what he has actually met — sets that differ by more than a hundred
words.

`tools/storycheck.py` was written straight afterwards and caught all three on
its first run, which is also how it earned its place.

All three are now `priority: true`, so they arrive within days rather than
whenever the shuffle reaches them. The sheet was left exactly as sent; there
is no point issuing a corrected one for homework already in his hands, and
the words are on their way to him regardless.

The `dużo` clause is worth keeping when this is reused: `dużo` takes the
genitive and a singular verb, so `na ulicy jest dużo ludzi` even though the
people are plural. That is the most interesting grammar on the sheet, and it
only works once he knows the word.

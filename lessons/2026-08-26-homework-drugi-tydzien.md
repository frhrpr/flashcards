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

Marek mieszka w nowym mieście. To (1) jego nowa praca.

Rano pada zimny deszcz. Marek (2) w łóżku i myśli.

— Ja nie (3) czasu na śniadanie.

Potem jedzie pociągiem do miasta. Miasto (4) bardzo duże.

W sklepie Marek (5) kartę. Płaci i kupuje kawę.

W pracy Marek spotyka nowych ludzi.

— Cześć! Jak ty (6) na imię? — pyta kobieta.

— Ja (7) Marek. A ty?

— Ewa. Czy ty (8) nowy w pracy?

— Tak. To moja nowa praca. Czy ty (9) czas na kawę?

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
| 4 | jest | być | noun subject Miasto, adjective complement |
| 5 | ma | mieć | noun subject Marek, accusative object kartę |
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

## Three words this nearly shipped with

The first draft used `drugi`, `dużo` and `pieniądze`. All three are carded,
and all three he has never seen — no card state, no priority flag. The draft
had been checked against `deck/vocab.csv`, which is the sentence allowlist,
not against what he has met, and those are different sets by more than a
hundred words.

`tools/storycheck.py` was written straight afterwards and caught them on its
first run. The lines were rewritten: `jego nowa praca` for the second week,
`Miasto jest bardzo duże` in place of the `dużo ludzi` clause, and Marek
having a card rather than lacking money.

The cost of the rewrite was the `dużo` construction — genitive plus a
singular verb — which was the most interesting grammar on the sheet. It goes
back in once he has met the word.

## What to watch

**Gap 10 is the only one that depends on discourse.** `Teraz nie ___ czasu`
answers a question put to him, so it is first person; nothing in the clause
itself says so.

**Gaps 1 and 14 are the same construction** — `to ___` plus a noun phrase.
Getting one and missing the other is worth asking about.

**Gap 5 has a noun subject and an object**, which is the clearest `mieć` on
the sheet. If he writes `jest` there, the problem is the verb choice rather
than the person, and that is the thing worth a lesson.

# Lekcja 2026-08-29 — iść, chodzić, jechać

Two sheets: `Downloads/flashcards/lessons/2026-08-29-isc-chodzic.html`
(the drill) and `2026-08-29-czytanie.html` (the reading).

## Why this, and not his worst cards

His worst four — chcieć, być, wiedzieć, dziwny — all had their pictures and
audio replaced on 2026-08-28 and none has come up for review since. Teaching
them now would make it impossible to tell whether the lesson or the new cards
did the work. Left alone for a week.

`chodzić` (missed 5 of 13) and `iść` (3 of 8) were chosen instead because they
are the one thing the deck **structurally cannot teach**. Neither carries a
`production` card: shown "to go" there are two right answers and only one is
marked correct. A lesson is the only place this can be fixed. `jechać` is
arriving in the deck now, so all three are live at once.

## The vocabulary problem, and what was added

He could already mark the one-off side — `teraz`, `rano`, `potem`,
`wieczorem` are all met. He had **nothing** for the habitual side: `zawsze`
was carded but never introduced, and `codziennie`, `często`, `czasami`,
`zwykle` and `nigdy` were not in the deck at all. The days of the week are
carded but none is met, so `w poniedziałek` was not available either.

All six are now carded and prioritised. `codziennie` is built on `dzień`,
which he knows. `nigdy` carries a note about the double negative — Polish
wants `nigdy **nie**` — which is a real trap for a Dutch speaker.

The scale is what makes the lesson work: **every one of these points at
`chodzę`**, because they all describe a habit. Only `teraz` points at `idę`,
and a vehicle overrides both.

## Pictures for words that have none

All six are abstract adverbs. They follow the pattern `zawsze` and `bardzo`
already set: the picture illustrates the **sentence's scene**, not the adverb,
and the gloss carries the word. Each was put in a different domain so they
cannot cue each other — a fish counter, a lit house at dusk, a glass under a
tap, a bowl pushed away, a man walking away down a wet street.

`images.py --check` flagged `czasami` and `zwykle` for not depicting the
adverb. That is correct and unfixable: nothing depicts *sometimes*. It is the
same class of flag `zawsze` would draw for a photograph of a market square.

## Story

Marek codziennie chodzi do pracy. Praca jest w mieście, na nowej ulicy.

Rano zwykle pada deszcz. Marek nie chce iść. Czasami chce jechać samochodem, ale nigdy nie ma czasu.

Teraz idzie do sklepu. Często kupuje tam chleb i mleko. Płaci kartą, kasa jest nowa.

W sklepie stoi dziecko. Dziecko ma czerwoną piłkę i bardzo lubi kota.

Na ulicy zawsze czeka pies. Pies jest dziwny: patrzy na ptaki i nigdy nie chce iść do domu.

— Czy ty wiesz, gdzie jest twój dom? — mówi Marek.

Pies nie wie. Pies lubi ulicę.

Wieczorem Marek wraca do domu. Teraz nie pada, a słońce jest bardzo duże.

To jest dobre miejsce. Marek bardzo lubi to miasto.

## How it was checked

`tools/storycheck.py`, twice. The first draft failed on one word —
`codziennie` was not in the deck — which is what prompted carding it. The
final version passes: everything is met or prioritised.

## Ear training — where to aim

Do not drill ś/sz in general. `s` is finished: 45 of 48, and four pairs have
retired. **17 of his 19 sibilant errors are sz↔ś**, and his two worst pairs
are `koś / kosz` (40%) and `paś / pasz` (56%) — both **word-final**, which the
cheat sheet already names as hardest because no vowel follows.

Also arriving: c/cz/ć. `ci / czy` 57%, `car / czar` 67%, `nic / nić` 67%.
Fewer trials, same shape.

The in-app hint sheet has been opened **once, ever** — the day it shipped.
Telling him it exists is probably worth more than any further change to it.

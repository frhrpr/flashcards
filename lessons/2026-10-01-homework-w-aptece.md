# Praca domowa — W aptece

Homework set 2026-10-01, after [[2026-09-27-dziwny-hotel]]. Student sheet:
`Downloads/flashcards/lessons/2026-10-01-homework-w-aptece.html` and `.pdf`
(two pages). -am table and gloss at the top, story, then the exercise in the
lesson's format. No instructions and no questions on it; the teacher gives
those.

## Story

Kobieta w hotelu śpiewa w nocy. Sven nie śpi.

Rano Sven płaci i czeka na pociąg.

— Boli mnie głowa — myśli Sven. — I brzuch. Trzeba szukać apteki. Ale gdzie jest apteka? Nie wiem.

Sven pyta ludzi i szuka. Tam jest apteka!

W aptece jest Ewa.

— Cześć, Sven! Jak się czujesz?

— Boli mnie głowa i brzuch. W hotelu kobieta śpiewa w nocy. Nie śpię!

— Trzeba spać! To jest ważne. I trzeba pić wodę.

— A kawa? Można pić kawę?

— Nie, nie można.

— A mleko?

— Mleko można.

— Czy trzeba być w pracy?

— Nie, dzisiaj nie trzeba. Trzeba być w łóżku.

— Ale w hotelu nie można spać!

— Mam duży dom. Tam można spać.

— A ty śpiewasz?

— Nie. Nigdy nie śpiewam! — mówi Ewa.

Wieczorem Sven jest w łóżku. Ewa nie śpiewa. Sven śpi.

### How it is built

- **Continues *Dziwny hotel***: the singing landlady kept him awake, so he
  wakes ill and goes looking for a pharmacy, where Ewa (from *Szukam psa!*)
  works. She is a friend, so *ty* throughout — no `pan`/`pani` yet.
- **Ewa's advice is a list of rules**, which is what trzeba/można are for:
  *trzeba spać, trzeba pić wodę, kawa — nie można, mleko można, nie trzeba być
  w pracy, trzeba być w łóżku*. All four uses appear.
- **The ending pays off the hotel**: *w hotelu nie można spać* — and Ewa
  *nigdy nie śpiewa*, which also revisits the double negative.
- Trouble cards in context: `czuć` (*jak się czujesz*), `wiedzieć` (*nie
  wiem*), `myśleć`, `być`, `łóżko`, `pociąg`, `płacić`, `ważny`.

### New words

`głowa`, `boleć` (as the chunk *boli mnie*), `noc` (*w nocy*) and `spać` —
all already carded but still in the bank, so they are glossed on the sheet
and set to `priority: true` the same day, so the app brings them out next.
Chosen because the story needs them and because each passes the
ordinary-week test easily. `trzeba`/`można` and `hotel` are from the lesson.

## Exercise — answers

Same format as the lesson: a verb box, each gap takes **trzeba or można plus
one verb**, each crossed off once. `spać` is in the box **×2**.

Box: być, czytać, iść, jeść, mówić, pić, płacić, pytać, spać ×2

| | item | answer |
| --- | --- | --- |
| 1 | — Czy w aptece ___ kartą? — Tak, ale nie trzeba. | **można płacić** |
| 2 | Pies Kot śpiewa w nocy. Nie ___! | **można spać** |
| 3 | — Ewa, czy ___ dzisiaj w aptece? — Nie, ale można. | **trzeba być** |
| 4 | Sven pamięta, gdzie jest apteka. Nie ___ ludzi. | **trzeba pytać** |
| 5 | Boli mnie brzuch. Nie ___, ale można pić wodę. | **można jeść** |
| 6 | — Czy w pociągu w nocy ___? — Tak, ale nie trzeba. | **można spać** |
| 7 | W łóżku nie można śpiewać, ale ___ książki. | **można czytać** |
| 8 | Sven jest w domu. Nie ___ do domu. | **trzeba iść** |
| 9 | — Czy ___ mleko? — Nie, ale można. | **trzeba pić** |
| 10 | Dziecko śpi. Nie ___! | **można mówić** |

trzeba 2, nie trzeba 2, można 3, nie można 3.

The modal is forced by the same two mechanisms as the lesson: a reply that
contradicts the wrong word (1, 3, 6, 9), or a stated reason that makes it
unnecessary (4, 8) or impossible (2, 5, 10). Item 7 is the absurd-obligation
one: *trzeba czytać* as a bedroom rule is nonsense.

**Nothing contradicts the story.** A first draft asked *Czy można pić kawę? —
Tak*, after Ewa had just said no to coffee, and *Czy trzeba pić wodę? — Nie*,
after she had said yes; both were rewritten. Items that copied a story line
outright (*Czy trzeba być w pracy?*, *w hotelu nie można spać*) were moved to
new situations so they cannot be lifted from the page.

**Verbs leaning on elimination**: 6 (*czytać w pociągu* would also fit, until
7 takes czytać), 3 (*spać* is ruled out by the reply's sense, not grammar).
Item 2 is the dog called Kot again, now singing at night.

**No genitive to produce.** The negated objects are *ludzi* (identical to the
accusative) and none else; item 5 has no object.

## Checked

`tools/storycheck.py` on story, clues and box: 62 headwords; unseen only the
intended `głowa`, `boleć`, `noc`, `spać` (now priority), `trzeba`, `można`,
`hotel`. `validate.py` and `smoke.mjs` clean after the priority change.

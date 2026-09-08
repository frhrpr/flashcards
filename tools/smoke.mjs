/* Render every card face and every ear trial against the real deck, in node.
 *
 *     node tools/smoke.mjs
 *
 * `node --check` only parses; it will happily pass a file that calls a
 * function which no longer exists. That is not hypothetical — an edit once
 * deleted the whole rendering block and the app got as far as the Start
 * button before dying on a missing `side()`. This catches that class of
 * fault by actually running the render functions.
 *
 * The code is sliced out of index.html rather than copied, so the test
 * cannot drift from the app. If the markers move, this fails loudly.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const deck = JSON.parse(fs.readFileSync(path.join(ROOT, "deck/notes.json"), "utf8"));
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "ear/manifest.json"), "utf8"));

/* Each slice is [from, to); `to` is left out of the slice. */
const SLICES = [
  ["const WORDS = {", "/* ── end of ear content ──"],
  ["function bankOrder(cards){", "/* ── end of bank order ──"],
  ['const barEl = $("#bar");', "function grade(g){"],
  ["/* ══ ear training ══", "/* ══ boot ══"],
];
const cut = ([from, to]) => {
  const a = src.indexOf(from), b = src.indexOf(to);
  if (a < 0 || b < 0 || b < a) {
    console.error(`smoke: cannot find slice markers in index.html\n` +
                  `  looked for ${JSON.stringify(from)} and ${JSON.stringify(to)}`);
    process.exit(1);
  }
  return src.slice(a, b);
};

/* A DOM element stub rich enough for the render paths: they set innerHTML,
   toggle classes, read children and attach listeners, and nothing else. */
const el = () => ({
  innerHTML: "", textContent: "", className: "", disabled: false,
  style: {}, dataset: {},
  classList: { add(){}, remove(){}, toggle(){} },
  firstElementChild: { style: {} },
  children: new Proxy({}, { get: () => ({ className: "" }) }),
  addEventListener(){}, querySelectorAll: () => [], querySelector: () => el(),
});

const stubs = `
const MS_DAY = 86400000;
const t = (() => { const d = new Date(); d.setHours(0,0,0,0); return d.getTime(); })();
const TEST_MODE = true;
const NOTES = ${JSON.stringify(Object.fromEntries(deck.notes.map(n => [n.id, n])))};
const allCards = ${JSON.stringify(deck.notes.flatMap(n =>
  (n.cards || []).map(c => `${n.id}__${c}`)))};
const noteOf = k => k.slice(0, k.lastIndexOf("__"));
const typeOf = k => k.slice(k.lastIndexOf("__") + 2);
let cardStates = {}, reviewLog = [], fresh = [], lockedCount = 0;
// extraPlan() consults the maturity gate; the real one lives outside
// every slice, and an extra session must respect it exactly as the
// daily bank does.
const unlocked = () => true;
let earStates = {}, doneDays = {}, hintOpens = {};
let queue = [], current = null, revealed = false, writeError = null, earLoadError = null;
const dueCards = [];
let vocabLight = false;
let writeChain = Promise.resolve(), docExists = false;
const docRef = {}, arrayUnion = (...a) => a, FieldPath = function(){};
const READ_ONLY = true, PEEK = false;
const write = { set: async () => {}, update: async () => {} };
const updateDoc = async () => {}, firstWrite = async () => {};
const logBytes = () => JSON.stringify(reviewLog).length;
let rndSeed = 12345;
const rand = () => (rndSeed = (rndSeed * 1103515245 + 12345) % 2147483648) / 2147483648;
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) {
  const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
// Also the preloader's cache-warming call, so preloads still register.
const fetch = async (u) => { if (u) asked.push(u);
  return { ok: true, json: async () => (${JSON.stringify(manifest)}) }; };
let html = "";
const appEl = { set innerHTML(v){ html = v; }, get innerHTML(){ return html; },
  appendChild(el){ html += (el && el.innerHTML) || ''; },
  querySelectorAll: () => [], querySelector: () => ${"({ children: new Proxy({}, { get: () => ({ className: \"\" }) }) })"} };
const countEl = { textContent: "" };
const document = { createElement: () => ({ className: '', id: '', innerHTML: '',
  addEventListener(){}, querySelectorAll: () => [],
  querySelector: () => ({ addEventListener(){} }),
  remove(){}, appendChild(){} }), body: { appendChild(){} } };
const _stub = ${el.toString()};
const $ = sel => sel === "#bar" ? _barStub : _stub();
const _barStub = { className: "", firstElementChild: { style: {} } };
const asked = [];
const Image = function(){ return { set src(v){ asked.push(v); } }; };
const Audio = function(){ let _s = ""; return {
  play: () => Promise.resolve(), pause: () => {}, preload: "", currentTime: 0,
  set src(v){ _s = v; asked.push(v); }, get src(){ return _s; } }; };
const location = { href: "https://example.test/" };
const URL = globalThis.URL;
const grade = () => {};
const renderWarning = () => {};
const renderCard_ = null;
`;

const mod = `${stubs}
${SLICES.map(cut).join("\n")}
export { renderDone, renderLanding, startEar, earPlan, nextEarTrial, answerEar, startVocab, vocabPending , TASK, SUBTASK };
export const state = () => ({ html, PAIRS, livePairs, earQueue, earIdx, earStates, queue, doneDays, vocabLight });
export const requested = () => asked;
export { bankOrder, introducible, interleave, NOTES, openHint, hintOpens, HINT_SETS };
export { cardRetired, RETIRE_IVL, stats, cardStates };
export const forgetPreloads = () => { preloaded.clear(); asked.length = 0; };
export const seed = (due, nw) => { dueCards.length = 0; dueCards.push(...due);
  fresh.length = 0; fresh.push(...nw); queue = [...due, ...nw]; };
export function face(key, side){
  current = key; queue = [key]; revealed = false;
  renderCard();
  if (side === "back") { revealed = false; showBack(); }
  return html;
}`;

const tmp = path.join(ROOT, ".smoke.mjs");
fs.writeFileSync(tmp, mod);
let fail = 0;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); if (!cond) fail++; };

try {
  const m = await import("file://" + tmp);
  for (const n of deck.notes) {
    for (const type of (n.cards || []).filter(c => c !== "listening" || n.audio)) {
      for (const which of ["front", "back"]) {
        let out;
        try {
          out = m.face(`${n.id}__${type}`, which);
        } catch (e) {
          check(false, `${n.id} ${type} ${which} threw: ${e.message}`);
          continue;
        }
        check(out.length > 0 && !out.includes("undefined") && !out.includes("[object"),
              `${n.id} ${type} ${which} renders cleanly`);
      }
    }
  }
  // The whole point of the layouts: a front must not leak its own answer.
  // Compare visible text only — attributes and class names produce false
  // positives ("play-big" contains the gloss of duży) — and compare whole
  // words, not substrings: the listening card's own instruction, "This card
  // is sound only", contains the gloss of samochód.
  // Strip the fixed chrome first. Every listening front carries "What does
  // this word mean?", which contains the gloss of słowo; every card carries
  // its task line. Boilerplate is not a leak, and leaving it in makes the
  // check fire on whichever note happens to collide with the instructions.
  const chrome = [...Object.values(m.TASK), ...Object.values(m.SUBTASK)];
  const text = h => chrome.reduce((s, c) => s.split(c).join(" "),
                                  h.replace(/<[^>]*>/g, " "));
  const toks = s => s.toLowerCase().split(/[^\p{L}]+/u).filter(Boolean);
  const says = (haystack, phrase) => {
    const hay = toks(haystack), want = toks(phrase);
    return want.length > 0 &&
      hay.some((_, i) => want.every((w, j) => hay[i + j] === w));
  };
  for (const n of deck.notes) {
    // Skipped where the English gloss IS the Polish word (park, park) — the
    // card is fine, the string check simply cannot tell them apart.
    if ((n.cards || []).includes("production") && n.gloss !== n.word) {
      const f = text(m.face(`${n.id}__production`, "front"));
      check(!says(f, n.word), `${n.id} production front hides the word`);
    }
    if ((n.cards || []).includes("listening") && n.audio) {
      const f = text(m.face(`${n.id}__listening`, "front"));
      check(!says(f, n.word) && !says(f, n.gloss),
            `${n.id} listening front hides word and gloss`);
    }
  }

  // ── ear training ────────────────────────────────────────────────
  const s0 = m.state();
  check(s0.PAIRS.length > 0, `${s0.PAIRS.length} minimal pairs derived from SETS`);
  check(s0.livePairs.length > 0, `${s0.livePairs.length} of them have recordings`);
  check(s0.PAIRS.every(p => p.length === 2), "every trial is a two-way choice");

  // Drive a whole session: the queue builder, every trial face, grading,
  // the trailing window, and the closing screen.
  m.startEar();
  let guard = 0;
  while (m.state().earIdx < m.state().earQueue.length && guard++ < 200) {
    const st = m.state();
    const tr = st.earQueue[st.earIdx];
    const out = st.html;
    check(out.includes("opt-word") && !out.includes("undefined"),
          `ear ${tr.key} trial renders cleanly`);
    // Alternate right and wrong so both feedback paths and both branches of
    // the retirement rule get exercised.
    m.answerEar(st.earIdx % 2 ? tr.other : tr.target);
    m.nextEarTrial();
  }
  check(guard < 200, "ear session terminates");
  check(m.state().html.includes("done-h"), "ear closing screen renders");
  check(Object.keys(m.state().earStates).length > 0, "ear state was recorded");

  // ── the "just reviews" session ──────────────────────────────────
  const due = deck.notes.slice(0, 3).map(n => `${n.id}__recognition`);
  const nw  = deck.notes.slice(3, 5).map(n => `${n.id}__recognition`);
  m.seed(due, nw);
  m.renderLanding();
  check(m.state().html.includes("go-light"), "landing offers the light session");
  m.startVocab(true);
  check(m.state().queue.length === due.length &&
        nw.every(k => !m.state().queue.includes(k)), "light session drops the new cards");
  m.startVocab(false);
  check(m.state().queue.length === due.length + nw.length, "full session keeps them");

  // Offered only when there is both something to review and something to skip.
  m.seed(due, []);
  m.renderLanding();
  check(!m.state().html.includes("go-light"), "no light option when nothing new is due");
  m.seed([], nw);
  m.renderLanding();
  check(!m.state().html.includes("go-light"), "no light option when nothing is due to review");

  // A finished light session must not re-offer the new cards after a reload:
  // they are still sitting in `fresh`, so only `done` can suppress them.
  m.seed(due, nw);
  const day = String((() => { const d = new Date(); d.setHours(0,0,0,0); return d.getTime(); })());
  check(m.vocabPending() > 0, "vocab is pending before the session");
  m.state().doneDays[day] = ["vocab-light"];
  check(m.vocabPending() === 0, "a finished light session suppresses the new cards");
  m.renderLanding();
  check(m.state().html.includes("reviews only"), "landing says it was reviews only");
  delete m.state().doneDays[day];

  /* Module-scope ordering. Everything above runs against slices with the
     loader stubbed, so the real boot order — which top-level `let` is
     evaluated before which assignment — is never exercised here. It broke:
     extraRuns was declared with the session state and assigned by the loader
     two hundred lines earlier, and the page died on load with "can't access
     lexical declaration before initialization". Nothing caught it but the
     student's browser. */
  const raw = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  const lines = raw.split("\n");
  const declaredAt = name => lines.findIndex(
    l => new RegExp(`^\\s*(let|const|var)\\s+${name}\\b`).test(l));
  let tdz = [];
  lines.forEach((l, i) => {
    const m = l.match(/^\s*([A-Za-z_$][\w$]*)\s*=\s*docExists\s*\?/);
    if (!m) return;
    const d = declaredAt(m[1]);
    if (d < 0 || d > i) tdz.push(`${m[1]} (assigned line ${i + 1}, declared ${d + 1})`);
  });
  /* One module scope, two halves. `retired` already meant pair retirement in
     the ear trainer when card retirement wanted the same name, and a repeat
     top-level declaration is a SyntaxError that kills the page on load — not
     a shadowed variable, the whole app.

     Where two clashing functions both land in a slice, importing the module
     above throws first and this never runs. It earns its place on the rest:
     grade(), stats(), the queue build and the loader are in no slice at all,
     so a duplicate there would reach the browser and nothing else here would
     see it. */
  const topFns = [...raw.matchAll(/^function\s+([A-Za-z_$][\w$]*)\s*\(/gm)]
    .map(m2 => m2[1]);
  const dupes = topFns.filter((n, i) => topFns.indexOf(n) !== i);
  check(dupes.length === 0,
        `no top-level function is declared twice${dupes.length ? ": " + [...new Set(dupes)].join(", ") : ""}`);

  /* Retired cards leave rotation entirely. The dueCards build sits outside
     every slice, so this half is a text check; the behaviour is exercised
     against stats() below. */
  check(/dueCards = shuffle\(allCards\.filter\([\s\S]{0,120}!cardRetired\(k\)/.test(raw),
        "the due queue excludes retired cards");

  /* grade() is not inside any slice, so this is a text check rather than a
     behavioural one — but the invariant is worth pinning: a practice answer
     must not touch cardStates, or it becomes the base the next real answer is
     scheduled from. */
  const gradeBody = raw.slice(raw.indexOf("function grade(g){"),
                              raw.indexOf("// resurface later this session"));
  check(gradeBody.indexOf("extraSaves.has(key)") <
        gradeBody.indexOf("cardStates[key] = next"),
        "grade() only writes card state for cards that are being saved");

  /* Playback must never reuse an element the preloader made: one that has
     never been played inside a user gesture is refused permission, which is
     what silenced whole sessions. One player, made once, is the invariant. */
  // Strip block comments first: the explanation above the player quotes the
  // very expression this counts, and would fail its own test.
  const code = raw.replace(/\/\*[\s\S]*?\*\//g, "");
  const players = (code.match(/new Audio\(/g) || []).length;
  check(players === 2,
        `exactly two Audio elements are constructed — the player and the ear ` +
        `cache (found ${players})`);
  check(!/function preload\(url\)[\s\S]{0,400}new Audio/.test(raw),
        "the preloader does not build media elements");

  check(tdz.length === 0,
        "loader globals are declared before the loader assigns them" +
        (tdz.length ? ` — ${tdz.join("; ")}` : ""));

  /* The all-done landing is where the extra-study button lives, and it is a
     branch nothing else here reaches: the template only evaluates
     extraAvailable() when both modes are satisfied, so a fault in it would
     ship unseen. */
  m.seed([], []);
  m.state().doneDays[day] = ["vocab", "ear"];
  m.renderLanding();
  check(m.state().html.includes("All done for today"), "the all-done landing renders");
  check(m.state().html.includes("sz.html"), "and carries the sibilant drill link");
  delete m.state().doneDays[day];
  // Preloading: the cards behind the current one must already have been
  // requested, or every flip waits on a round trip it could have started.
  const withImg = deck.notes.filter(n => n.image).slice(0, 5);
  m.forgetPreloads();
  m.seed(withImg.map(n => `${n.id}__recognition`), []);
  m.startVocab(false);
  const got = m.requested();
  const ahead = withImg.slice(1, 4).filter(n => got.includes(n.image));
  check(ahead.length === 3,
        `preloads the next 3 cards' images (got ${ahead.length} of 3)`);
  check(!got.includes(withImg[4].image),
        "does not pull the whole session down at once");

  // Priority pulls a word out of the bank first, and nothing else.
  const ids = deck.notes.filter(n => n.kind !== "form").slice(0, 6).map(n => n.id);
  const bank = ids.map(i => `${i}__recognition`);
  const plain = m.bankOrder(bank);
  check(plain.join() === bank.join(), "no priority leaves the order alone");
  m.NOTES[ids[4]].priority = true;
  const withPrio = m.bankOrder(bank);
  check(withPrio[0] === `${ids[4]}__recognition`, "a prioritised word comes out first");
  check(withPrio.slice(1).join() ===
        bank.filter(k => k !== `${ids[4]}__recognition`).join(),
        "everything else keeps its shuffled order");
  m.NOTES[ids[1]].priority = true;
  const two = m.bankOrder(bank);
  check(two.slice(0, 2).sort().join() ===
        [`${ids[1]}__recognition`, `${ids[4]}__recognition`].sort().join(),
        "two prioritised words both come first");
  check(two[0] === `${ids[1]}__recognition`,
        "and keep their relative order — the sort is stable");

  /* An unread note must never be introduced. The app is served straight out
     of the repo, so this is the only thing standing between a half-written
     sentence and the student. */
  const nid = ids[0], key = `${nid}__recognition`;
  m.NOTES[nid].reviewed = true;
  check(m.introducible(key) === true, "an approved note can be introduced");
  m.NOTES[nid].reviewed = false;
  check(m.introducible(key) === false, "an unapproved note cannot be introduced");
  delete m.NOTES[nid].reviewed;
  check(m.introducible(key) === false,
        "and neither can one whose flag has gone missing");
  m.NOTES[nid].reviewed = true;
  check(deck.notes.every(n => typeof n.reviewed === "boolean"),
        "every note in the real deck carries a boolean reviewed flag");

  /* Retirement. Derived from the interval, so there is nothing to migrate and
     the constant can be moved either way; the tests pin the boundary and the
     effect on the two summary screens. */
  const rk = `${ids[2]}__recognition`, lk = `${ids[3]}__recognition`;
  check(m.cardRetired(rk) === false, "a card with no state is not retired");
  m.cardStates[rk] = { ivl: m.RETIRE_IVL - 1, ease: 2.5, reps: 6, due: 0 };
  check(m.cardRetired(rk) === false, "one interval short of the threshold is not");
  m.cardStates[rk] = { ivl: m.RETIRE_IVL, ease: 2.5, reps: 6, due: 0 };
  check(m.cardRetired(rk) === true, "exactly at the threshold is");
  m.cardStates[lk] = { ivl: 6, ease: 2.5, reps: 2, due: 0 };
  const sr = m.stats();
  check(sr.due === 1, "a retired card is not due, an ordinary overdue one is");
  check(sr.retired === 1, "and it is counted as retired");
  check(sr.started === 2, "but it still counts as started — he did learn it");
  /* The bug this guards: nextDue reading a retired card's due date and the
     closing screen saying "come back in eight months". */
  m.cardStates[lk] = { ivl: 6, ease: 2.5, reps: 2, due: Date.now() + 3 * 86400000 };
  m.cardStates[rk] = { ivl: 400, ease: 2.5, reps: 8, due: Date.now() + 400 * 86400000 };
  check(m.stats().nextDue === m.cardStates[lk].due,
        "nextDue ignores retired cards");
  delete m.cardStates[rk]; delete m.cardStates[lk];

  /* New cards must not all land at the end: that put the gapped production
     cards, which unlock latest and so are new most often, where he is most
     tired. */
  const rev = Array.from({ length: 40 }, (_, i) => `r${i}__recognition`);
  const fresh8 = Array.from({ length: 8 }, (_, i) => `n${i}__production`);
  const q = m.interleave(rev, fresh8);
  check(q.length === 48, "interleave keeps every card");
  check(new Set(q).size === 48, "and duplicates none");
  check(q.filter(k => k.startsWith("r")).join() === rev.join(),
        "due cards keep their order");
  const at = q.map((k, i) => (k.startsWith("n") ? i : -1)).filter(i => i >= 0);
  check(at.every(i => i >= 3), "no new card before the warm-up");
  check(at[at.length - 1] < q.length - 3,
        "and the last new card is not at the very end");
  const gaps = at.slice(1).map((v, i) => v - at[i]);
  check(Math.max(...gaps) - Math.min(...gaps) <= 2, "they are evenly spread");
  check(m.interleave([], fresh8).length === 8 && m.interleave(rev, []).length === 40,
        "an empty side on either hand is fine");
  delete m.NOTES[ids[1]].priority; delete m.NOTES[ids[4]].priority;

  // The hint sheet: every word it offers must actually have audio, or it
  // shows a dead button on a card whose whole point is the sound.
  const haveAudio = new Set(Object.keys(JSON.parse(
    fs.readFileSync(path.join(ROOT, "ear/manifest.json"), "utf8")).words));
  const hinted = m.HINT_SETS.flat();
  check(hinted.every(w => haveAudio.has(w)),
        `hint sheet only offers words with recordings (${hinted.length} words)`);
  const before = Object.values(m.hintOpens).reduce((a, b) => a + b, 0);
  m.openHint();
  check(Object.values(m.hintOpens).reduce((a, b) => a + b, 0) === before + 1,
        "opening the hint sheet is counted");

  m.renderDone();    check(true, "renderDone runs");
  m.renderLanding(); check(true, "renderLanding runs");
} finally {
  if (!process.env.SMOKE_KEEP) fs.unlinkSync(tmp);
}

console.log(fail ? `\n${fail} FAILED` : `\nall render faces ok`);
process.exit(fail ? 1 : 0);

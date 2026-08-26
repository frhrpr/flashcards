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
const fetch = async () => ({ ok: true, json: async () => (${JSON.stringify(manifest)}) });
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
const Audio = function(){ return { play: () => Promise.resolve(), preload: "",
  set src(v){ asked.push(v); } }; };
const grade = () => {};
const renderWarning = () => {};
const renderCard_ = null;
`;

const mod = `${stubs}
${SLICES.map(cut).join("\n")}
export { renderDone, renderLanding, startEar, earPlan, nextEarTrial, answerEar, startVocab, vocabPending , TASK, SUBTASK };
export const state = () => ({ html, PAIRS, livePairs, earQueue, earIdx, earStates, queue, doneDays, vocabLight });
export const requested = () => asked;
export { bankOrder, NOTES, openHint, hintOpens, HINT_SETS };
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

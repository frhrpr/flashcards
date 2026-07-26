/* Render every card face against the real deck, in node.
 *
 *     node tools/smoke.mjs
 *
 * `node --check` only parses; it will happily pass a file that calls a
 * function which no longer exists. That is not hypothetical — an edit once
 * deleted the whole rendering block and the app got as far as the Start
 * button before dying on a missing `side()`. This catches that class of
 * fault by actually running the render functions.
 *
 * The functions are sliced out of index.html rather than copied, so the test
 * cannot drift from the code. If the markers move, this fails loudly.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const deck = JSON.parse(fs.readFileSync(path.join(ROOT, "deck/notes.json"), "utf8"));

const FROM = 'const barEl = $("#bar");';
const TO = "function grade(g){";
if (!src.includes(FROM) || !src.includes(TO)) {
  console.error(`smoke: cannot find the render block markers in index.html\n` +
                `  looked for ${JSON.stringify(FROM)} and ${JSON.stringify(TO)}`);
  process.exit(1);
}

const stubs = `
const MS_DAY = 86400000;
const t = (() => { const d = new Date(); d.setHours(0,0,0,0); return d.getTime(); })();
const NOTES = ${JSON.stringify(Object.fromEntries(deck.notes.map(n => [n.id, n])))};
const allCards = ${JSON.stringify(deck.notes.flatMap(n =>
  (n.cards || []).map(c => `${n.id}__${c}`)))};
const noteOf = k => k.slice(0, k.lastIndexOf("__"));
const typeOf = k => k.slice(k.lastIndexOf("__") + 2);
let cardStates = {}, reviewLog = [], fresh = [], lockedCount = 0;
let queue = [], current = null, revealed = false, writeError = null;
let html = "";
const appEl = { set innerHTML(v){ html = v; }, get innerHTML(){ return html; } };
const countEl = { textContent: "" };
const _barStub = { className: "", firstElementChild: { style: {} } };
const $ = sel => sel === "#bar" ? _barStub : ({ addEventListener(){} });
const Image = function(){ return { set src(_v){} }; };
const Audio = function(){ return { play: () => Promise.resolve() }; };
const grade = () => {};
const renderWarning = () => {};
`;

const body = src.slice(src.indexOf(FROM), src.indexOf(TO));
const mod = `${stubs}\n${body}
export { renderStart, renderDone };
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
    for (const type of n.cards || []) {
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
  for (const n of deck.notes) {
    if ((n.cards || []).includes("production")) {
      const f = m.face(`${n.id}__production`, "front");
      check(!f.includes(`>${n.word}<`), `${n.id} production front hides the word`);
    }
    if ((n.cards || []).includes("listening")) {
      const f = m.face(`${n.id}__listening`, "front");
      check(!f.includes(`>${n.word}<`) && !f.includes(n.gloss),
            `${n.id} listening front hides word and gloss`);
    }
  }
  m.renderStart(); check(true, "renderStart runs");
  m.renderDone();  check(true, "renderDone runs");
} finally {
  fs.unlinkSync(tmp);
}

console.log(fail ? `\n${fail} FAILED` : `\nall render faces ok`);
process.exit(fail ? 1 : 0);

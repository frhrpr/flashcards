
import fs from "fs";
const deck = JSON.parse(fs.readFileSync("/home/frhrpr/projects/flashcards/deck/notes.json","utf8"));
const NOTES = Object.fromEntries(deck.notes.map(n=>[n.id,n]));
let html = "";
const appEl = { set innerHTML(v){ html = v; }, get innerHTML(){ return html; } };
const $ = () => ({ addEventListener(){} });
const renderCount=()=>{}, renderWarning=()=>{};
const noteOf = k => k.slice(0,k.lastIndexOf("__"));
const typeOf = k => k.slice(k.lastIndexOf("__")+2);
let current=null, revealed=false, writeError=null, queue=[];
const grade=()=>{};
const POS_PL = {
  noun: "rzeczownik", verb: "czasownik", adjective: "przymiotnik",
  adverb: "przysłówek", preposition: "przyimek", conjunction: "spójnik",
  particle: "partykuła", pronoun: "zaimek", interjection: "wykrzyknik",
};

// Anything from the deck could contain < or &; it is rendered via innerHTML.
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* Part of speech only. Declension tables and aspect pairs are deliberately
   not stored — this is a vocabulary trainer, not a grammar reference, and
   the example sentences are free to use whatever form reads naturally. */
function grammar(n){
  return `<div class="gram">${esc(POS_PL[n.pos] || n.pos)}</div>`;
}

let audioSeq = 0;
const audioBtns = [];
function playBtn(src, label, extra){
  if (!src) return "";
  const id = `play${audioSeq++}`;
  audioBtns.push({ id, src });
  return `<button class="play${extra ? " " + extra : ""}" id="${id}" ` +
         `aria-label="${esc(label)}">▶</button>`;
}
function wireAudio(){
  for (const { id, src } of audioBtns.splice(0)) {
    const el = $("#" + id);
    if (el) el.addEventListener("click", () => new Audio(src).play().catch(e => {
      // A rejection with no user gesture is routine; anything else is not.
      if (e.name !== "NotAllowedError") {
        writeError = new Error(`audio failed: ${src}`);
        renderWarning();
      }
    }));
  }
}

/* ── the four card types ────────────────────────────────────────────
   Each note can produce up to four cards, each testing a different
   direction. Which pieces appear where is the whole design:

     recognition  PL word + audio + IPA  ->  meaning, image, sentence
     production   image + English        ->  the Polish word
     listening    the recording alone    ->  everything else
     cloze        the gapped sentence    ->  the missing form

   Nothing is shown on a front that would give the answer away — the
   listening front is deliberately bare, and production withholds both the
   Polish word and its audio. */
const pieces = {
  word:    n => `<div class="front">${esc(n.word)}</div>`,
  ipa:     n => n.ipa ? `<div class="ipa">[${esc(n.ipa)}]</div>` : "",
  gloss:   n => `<div class="back">${esc(n.gloss)}</div>`,
  image:   n => n.image
    ? `<img src="${esc(n.image)}" alt="${esc(n.image_alt || "")}">` : "",
  note:    n => n.note ? `<div class="note">${esc(n.note)}</div>` : "",
  audio:   n => playBtn(n.audio, `play ${n.word}`),
  sentence: n => (n.sentence && n.sentence.pl) ? `
    <div class="sent">
      <div class="sent-pl">${esc(n.sentence.pl)}${playBtn(n.sentence.audio, "play the sentence")}</div>
      <div class="sent-en">${esc(n.sentence.en || "")}</div>
    </div>` : "",
  gapped:  n => (n.sentence && n.sentence.gap) ? `
    <div class="sent"><div class="sent-gap">${esc(n.sentence.gap)}</div></div>` : "",
};

const LAYOUT = {
  recognition: {
    front: ["word", "audio", "ipa"],
    back:  ["word", "ipa", "gloss", "image", "sentence", "note"],
  },
  production: {
    front: ["image", "gloss", "note", "gapped"],
    back:  ["word", "audio", "ipa", "sentence"],
  },
  listening: {
    front: ["audioOnly"],
    back:  ["word", "audio", "ipa", "gloss", "image", "sentence", "note"],
  },
  cloze: {
    front: ["clozeGap"],
    back:  ["answer", "gloss", "sentence"],
  },
};

// Fronts that are not simply a stack of the shared pieces.
const special = {
  audioOnly: n => playBtn(n.audio, `play ${n.word}`, "play-big"),
  clozeGap:  n => `<div class="cloze">${esc((n.sentence || {}).gap || "")}</div>`,
  answer:    n => `<div class="front">${esc((n.sentence || {}).answer || "")}</div>`,
};

function side(n, type, which){
  const names = (LAYOUT[type] || LAYOUT.recognition)[which];
  return names.map(k => (special[k] || pieces[k])(n)).join("\n      ");
}

function renderCard(){
  revealed = false;
  current = queue[0];
  const n = NOTES[noteOf(current)];
  const type = typeOf(current);
  renderCount();
  renderWarning();
  appEl.innerHTML = `
    <div class="card">
      ${side(n, type, "front")}
    </div>
    <button class="reveal" id="reveal">Show answer</button>
  `;
  wireAudio();
  $("#reveal").addEventListener("click", showBack);
}

function showBack(){
  if (revealed) return;
  revealed = true;
  const n = NOTES[noteOf(current)];
  const type = typeOf(current);
  appEl.innerHTML = `
    <div class="card">
      ${side(n, type, "back")}
      ${grammar(n)}
    </div>
    <div class="grades">
      <button class="g-again" id="again">Again</button>
      <button class="g-good" id="good">Good</button>
    </div>
  `;
  wireAudio();
  $("#again").addEventListener("click", () => grade("again"));
  $("#good").addEventListener("click", () => grade("good"));
}


function shot(key, side){
  current=key; queue=[key]; revealed=false;
  renderCard(); if(side==="back"){ revealed=false; showBack(); }
  // strip the reveal/grade buttons; we only want the card face
  return html.replace(/<button class="reveal"[\s\S]*?<\/button>/g,"")
             .replace(/<div class="grades">[\s\S]*?<\/div>\s*$/,"");
}
const css = fs.readFileSync("css.txt","utf8");
const types = [
  ["recognition","PL word + audio + IPA → meaning"],
  ["production","image + English + gapped sentence → the Polish word"],
  ["listening","the recording alone → everything else"],
  ["cloze","the gapped sentence → the missing form"],
];
let out = "";
for (const [t,desc] of types){
  out += `<h2>${t}<em>${desc}</em></h2><div class=pair>
    <div class=col><div class=lbl>front</div>${shot("kot__"+t,"front")}</div>
    <div class=col><div class=lbl>back</div>${shot("kot__"+t,"back")}</div></div>`;
}
fs.writeFileSync("/mnt/c/Users/frhrpr/Downloads/flashcards/review/cards.html",
`<!doctype html><meta charset=utf-8><title>Card types</title><style>${css}
body{max-width:60rem}
h2{font-family:var(--mono);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;
color:var(--ink);margin:2.5rem 0 .75rem}
h2 em{display:block;font-style:normal;letter-spacing:0;text-transform:none;
font-family:var(--sans);font-size:.85rem;color:var(--dim);margin-top:.3rem}
.pair{display:flex;gap:1rem}.col{flex:1;min-width:0}
.lbl{font-family:var(--mono);font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;
color:var(--dim);margin-bottom:.4rem}
.play{pointer-events:none}
</style><div class=wrap style="max-width:60rem">
<p class=eyebrow>All four card types, note "kot" — audio buttons are inert here</p>
${out}</div>`);
console.log("wrote cards.html");

import { load } from "/vendor/cmx-lid/dist/index.js";
import { initI18n } from "/assets/i18n.js";

const i18n = initI18n({
  fr: {
    "page.title": "Identification de langue — bambara, français, anglais · Crommix AI",
    "lid.title": "Quelle langue, mot par mot ?",
    "lid.lede": "Écrivez ou collez un message en bambara, français ou anglais — même mélangés. Chaque mot est coloré selon sa langue.",
    "lid.private": "Tout reste dans votre navigateur",
    "lid.input": "Votre texte",
    "lid.placeholder": "Ex. : n taara l'hôpital kunun, docteur ko n ka kɛnɛ",
    "lid.loading": "Chargement du modèle…",
    "lid.ready": "Prêt · analyse instantanée",
    "lid.failed": "Impossible de charger le modèle. Rechargez la page.",
    "lid.toolong": "Texte long : seuls les {n} premiers caractères sont analysés.",
    "lid.share": "Partager",
    "lid.clear": "Effacer",
    "lid.examples": "Exemples :",
    "lid.main": "Langue principale",
    "lid.mixed": "Mélange",
    "lid.words": "Mots",
    "lid.byword": "Mot par mot",
    "lid.showlabels": "Afficher les étiquettes",
    "lid.uncertain": "hachuré = incertain (< 70 %)",
    "lid.table": "Détails (tableau)",
    "lid.copyjson": "Copier le JSON",
    "lid.col.word": "Mot", "lid.col.lang": "Langue", "lid.col.conf": "Confiance", "lid.col.source": "Décidé par",
    "lid.yes": "Oui", "lid.no": "Non",
    "lid.switches": "{n} changement(s) de langue",
    "lid.single": "une seule langue",
    "lid.wordcount": "{n} ponctuation/nombres ignorés",
    "lid.empty": "Le résultat apparaîtra ici.",
    "lid.none": "Aucun mot à analyser.",
    "lid.share.done": "Lien copié",
    "lid.json.done": "JSON copié",
    "lid.of": "{p} des mots",
    "lang.bam": "Bambara", "lang.fra": "Français", "lang.eng": "Anglais", "lang.univ": "Neutre",
    "src.router": "règle d'écriture", "src.lexicon": "lexique", "src.classifier": "modèle statistique", "src.context": "contexte",
    "tip.conf": "confiance {p}", "tip.by": "décidé par : {s}",
    "about.how": "Comment ça marche", "about.quality": "Qualité mesurée", "about.dev": "Pour les développeurs",
    "about.m1": "Radio malienne (Kunkado) — mots bien classés",
    "about.m2": "… mots français repérés dans du bambara (F1)",
    "about.m3": "Textes bambara/français (BAYƐLƐMABAGA) — exactitude",
    "about.m4": "Bambara en écriture informelle",
    "about.limits": "Limites : les petits mots français isolés (la, de, donc) au milieu du bambara sont parfois manqués ; les messages WhatsApp/SMS n'ont pas encore de jeu de test.",
    "about.devtext": "Même modèle en JavaScript/TypeScript et en Python, sans dépendance. Environ 2 Mo (410 Ko compressé), puis tout fonctionne hors ligne.",
    "about.version": "Modèle cmx-lid {v} · schéma {s}",
  },
  en: {
    "page.title": "Language identification — Bambara, French, English · Crommix AI",
    "lid.title": "Which language, word by word?",
    "lid.lede": "Type or paste a message in Bambara, French or English, even mixed. Each word is coloured by its language.",
    "lid.private": "Everything stays in your browser",
    "lid.input": "Your text",
    "lid.placeholder": "e.g. n taara l'hôpital kunun, docteur ko n ka kɛnɛ",
    "lid.loading": "Loading the model…",
    "lid.ready": "Ready · instant analysis",
    "lid.failed": "Could not load the model. Please reload the page.",
    "lid.toolong": "Long text: only the first {n} characters are analysed.",
    "lid.share": "Share",
    "lid.clear": "Clear",
    "lid.examples": "Examples:",
    "lid.main": "Main language",
    "lid.mixed": "Mixed",
    "lid.words": "Words",
    "lid.byword": "Word by word",
    "lid.showlabels": "Show labels",
    "lid.uncertain": "hatched = uncertain (< 70%)",
    "lid.table": "Details (table)",
    "lid.copyjson": "Copy JSON",
    "lid.col.word": "Word", "lid.col.lang": "Language", "lid.col.conf": "Confidence", "lid.col.source": "Decided by",
    "lid.yes": "Yes", "lid.no": "No",
    "lid.switches": "{n} language switch(es)",
    "lid.single": "one language",
    "lid.wordcount": "{n} punctuation/numbers ignored",
    "lid.empty": "The result will appear here.",
    "lid.none": "No words to analyse.",
    "lid.share.done": "Link copied",
    "lid.json.done": "JSON copied",
    "lid.of": "{p} of words",
    "lang.bam": "Bambara", "lang.fra": "French", "lang.eng": "English", "lang.univ": "Neutral",
    "src.router": "spelling rule", "src.lexicon": "lexicon", "src.classifier": "statistical model", "src.context": "context",
    "tip.conf": "confidence {p}", "tip.by": "decided by: {s}",
    "about.how": "How it works", "about.quality": "Measured quality", "about.dev": "For developers",
    "about.m1": "Malian radio (Kunkado): words correctly labeled",
    "about.m2": "… French words found inside Bambara (F1)",
    "about.m3": "Bambara/French texts (BAYƐLƐMABAGA): accuracy",
    "about.m4": "Bambara in informal spelling",
    "about.limits": "Limits: short French words on their own (la, de, donc) inside Bambara are sometimes missed; WhatsApp/SMS messages don't have a test set yet.",
    "about.devtext": "Same model in JavaScript/TypeScript and Python, no dependencies. About 2 MB (410 KB compressed), then everything works offline.",
    "about.version": "cmx-lid model {v} · schema {s}",
  },
});

const EXAMPLES = [
  "n taara l'hôpital kunun, docteur ko n ka kɛnɛ",
  "réunion bɛ kɛ demain à 10h, i bɛ na wa ?",
  "inchallah n bɛ na sini, a ye lekɔli daminɛ",
  "n bè taa dougou la sini, n bè sogo san",
  "C'est pas possible, a ma se ka na bi",
  "meeting in bɛ kɛ tomorrow, i ka download kɛ",
];
const MAX_CHARS = 20000;
const LANGS = ["bam", "fra", "eng"];
const LOW = 0.7;

const $ = (id) => document.getElementById(id);
const els = {
  text: $("text"), status: $("status"), results: $("results"), hl: $("hl"), tip: $("tip"),
  bar: $("bar"), barLabels: $("bar-labels"), tbody: $("tbody"), showLabels: $("show-labels"),
  tMain: $("t-main"), tMainS: $("t-main-s"), tMix: $("t-mix"), tMixS: $("t-mix-s"),
  tWords: $("t-words"), tWordsS: $("t-words-s"), examples: $("examples"),
  share: $("share"), clear: $("clear"), copyJson: $("copy-json"), version: $("version"),
};

let lid = null;
let last = { text: "", tokens: [] };

const locale = () => (i18n.lang === "fr" ? "fr-FR" : "en-US");
const pct = (x, d = 0) => new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: d }).format(x);
const langName = (l) => i18n.t(`lang.${l}`);

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function swatch(l) {
  return el("i", `sw sw-${l}`);
}

// ---- rendering ---------------------------------------------------------------

function analyze() {
  if (!lid) return;
  let text = els.text.value;
  const tooLong = text.length > MAX_CHARS;
  if (tooLong) text = text.slice(0, MAX_CHARS);
  const tokens = lid.identify(text);
  last = { text, tokens };
  render(tooLong);
}

function render(tooLong = false) {
  const { text, tokens } = last;
  els.results.hidden = false;
  const s = lid.summarize(tokens);
  const nUniv = tokens.length - s.nWords;

  // tiles
  els.tMain.replaceChildren();
  if (s.dominant) {
    els.tMain.append(swatch(s.dominant), document.createTextNode(langName(s.dominant)));
    els.tMainS.textContent = i18n.t("lid.of", { p: pct(s.proportions[s.dominant]) });
  } else {
    els.tMain.textContent = "—";
    els.tMainS.textContent = "";
  }
  els.tMix.textContent = s.nWords ? i18n.t(s.codeSwitched ? "lid.yes" : "lid.no") : "—";
  els.tMixS.textContent = s.nWords ? (s.codeSwitched ? i18n.t("lid.switches", { n: s.nSwitches }) : i18n.t("lid.single")) : "";
  els.tWords.textContent = new Intl.NumberFormat(locale()).format(s.nWords);
  els.tWordsS.textContent = tooLong ? i18n.t("lid.toolong", { n: MAX_CHARS.toLocaleString(locale()) })
    : nUniv ? i18n.t("lid.wordcount", { n: nUniv }) : "";

  // proportion bar (fixed language order so colours never move) + direct labels
  const present = LANGS.filter((l) => s.proportions[l]);
  els.bar.replaceChildren(...present.map((l) => {
    const seg = el("span");
    seg.style.flex = String(s.proportions[l]);
    seg.style.background = `var(--lang-${l})`;
    seg.dataset.tip = `${langName(l)} · ${pct(s.proportions[l], 1)}`;
    return seg;
  }));
  els.bar.setAttribute("aria-label", present.map((l) => `${langName(l)} ${pct(s.proportions[l])}`).join(", "));
  els.barLabels.replaceChildren(...present.map((l) => {
    const sp = el("span");
    sp.append(swatch(l), el("b", "", pct(s.proportions[l])), document.createTextNode(langName(l)));
    return sp;
  }));

  // highlighted text, keeping the user's spacing and line breaks
  const frag = document.createDocumentFragment();
  let pos = 0;
  tokens.forEach((t, i) => {
    if (t.start > pos) frag.append(text.slice(pos, t.start));
    if (t.label === "univ") {
      frag.append(t.text);
    } else {
      const w = el("span", `w l-${t.label}${t.confidence < LOW ? " low" : ""}`, t.text);
      w.dataset.i = String(i);
      w.dataset.tag = t.label.toUpperCase();
      frag.append(w);
    }
    pos = t.end;
  });
  if (pos < text.length) frag.append(text.slice(pos));
  els.hl.replaceChildren(frag);
  if (!tokens.length) els.hl.append(el("span", "empty", text.trim() ? i18n.t("lid.none") : i18n.t("lid.empty")));

  // table
  els.tbody.replaceChildren(...tokens.filter((t) => t.label !== "univ").map((t, k) => {
    const tr = el("tr");
    const lang = el("td");
    lang.append(swatch(t.label), document.createTextNode(" " + langName(t.label)));
    tr.append(el("td", "num", String(k + 1)), el("td", "", t.text), lang,
      el("td", "num", pct(t.confidence)), el("td", "", i18n.t(`src.${t.source}`)));
    return tr;
  }));
}

// ---- tooltip (mouse, touch and keyboard focus) -------------------------------

function showTip(target) {
  if (target.classList.contains("w")) {
    const t = last.tokens[Number(target.dataset.i)];
    if (!t) return;
    els.tip.replaceChildren();
    const row = el("div", "row");
    row.append(swatch(t.label), el("b", "", `${t.text} — ${langName(t.label)}`));
    els.tip.append(row, el("div", "", i18n.t("tip.conf", { p: pct(t.confidence) })),
      el("div", "", i18n.t("tip.by", { s: i18n.t(`src.${t.source}`) })));
    document.querySelectorAll(".w.active").forEach((x) => x.classList.remove("active"));
    target.classList.add("active");
  } else if (target.dataset.tip) {
    els.tip.textContent = target.dataset.tip;
  } else return;
  els.tip.hidden = false;
  const r = target.getBoundingClientRect();
  const tr = els.tip.getBoundingClientRect();
  let x = Math.min(Math.max(8, r.left + r.width / 2 - tr.width / 2), window.innerWidth - tr.width - 8);
  let y = r.top - tr.height - 8;
  if (y < 8) y = r.bottom + 8;
  els.tip.style.left = `${x}px`;
  els.tip.style.top = `${y}px`;
}
function hideTip() {
  els.tip.hidden = true;
  document.querySelectorAll(".w.active").forEach((x) => x.classList.remove("active"));
}
for (const root of [els.hl, els.bar]) {
  root.addEventListener("pointerover", (e) => {
    const t = e.target.closest(".w, [data-tip]");
    if (t) showTip(t);
  });
  root.addEventListener("pointerout", (e) => {
    if (!e.relatedTarget?.closest?.(".w, [data-tip]")) hideTip();
  });
  root.addEventListener("click", (e) => {
    const t = e.target.closest(".w, [data-tip]");
    if (t) showTip(t); else hideTip();
  });
}
window.addEventListener("scroll", hideTip, { passive: true });

// ---- controls ------------------------------------------------------------------

function toast(msg) {
  const t = el("div", "toast", msg);
  document.body.append(t);
  setTimeout(() => t.remove(), 1600);
}
async function copy(text, done) {
  try { await navigator.clipboard.writeText(text); toast(done); }
  catch { window.prompt("", text); }
}

let timer = 0;
els.text.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(analyze, 60);
});
els.clear.addEventListener("click", () => { els.text.value = ""; analyze(); els.text.focus(); });
els.share.addEventListener("click", () => {
  const url = new URL(location.href);
  url.search = "";
  url.hash = "";
  if (els.text.value.trim()) url.searchParams.set("t", els.text.value.slice(0, 1500));
  copy(url.toString(), i18n.t("lid.share.done"));
});
els.copyJson.addEventListener("click", () => copy(JSON.stringify(last.tokens, null, 2), i18n.t("lid.json.done")));
els.showLabels.addEventListener("change", () => els.hl.classList.toggle("labels", els.showLabels.checked));

for (const ex of EXAMPLES) {
  const b = el("button", "chip", ex);
  b.type = "button";
  b.title = ex;
  b.addEventListener("click", () => { els.text.value = ex; analyze(); });
  els.examples.append(b);
}

function formatMetrics() {
  for (const n of document.querySelectorAll("[data-pct]")) n.textContent = pct(Number(n.dataset.pct), 1);
  for (const n of document.querySelectorAll("[data-dec]")) {
    n.textContent = new Intl.NumberFormat(locale(), { minimumFractionDigits: 2 }).format(Number(n.dataset.dec));
  }
}
function setStatus(kind) {
  els.status.replaceChildren();
  if (kind === "loading") els.status.append(el("span", "spinner"), el("span", "", i18n.t("lid.loading")));
  else if (kind === "ready") els.status.append(el("span", "", i18n.t("lid.ready")));
  else els.status.append(el("span", "error", i18n.t("lid.failed")));
  els.status.dataset.kind = kind;
}
function setVersion() {
  if (lid) els.version.textContent = i18n.t("about.version", { v: lid.modelVersion, s: lid.schemaVersion });
}

i18n.onChange(() => {
  setStatus(els.status.dataset.kind || "loading");
  formatMetrics();
  setVersion();
  if (lid) render();
});
formatMetrics();
setStatus("loading");

// ---- start -------------------------------------------------------------------

try {
  lid = await load();
  const shared = new URLSearchParams(location.search).get("t");
  els.text.value = shared ?? EXAMPLES[0];
  for (const b of [els.text, els.share, els.clear]) b.disabled = false;
  setStatus("ready");
  setVersion();
  analyze();
} catch (err) {
  console.error(err);
  setStatus("error");
}

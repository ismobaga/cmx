// Router, lexicon, Naive Bayes classifier and context decoder:
// mirror of cmx_lid/router.py, lexicon.py, classifier.py, decode.py.
import type { Bundle, LangLabel } from "./types.js";
import { Text, type RawToken } from "./text.js";

export interface Route {
  label: LangLabel | "univ";
  confidence: number;
  final: boolean;
}

const inRange = (cp: number, ranges: [number, number][]) =>
  ranges.some(([a, b]) => cp >= a && cp <= b);
const ARABIC: [number, number][] = [
  [0x0600, 0x06ff], [0x0750, 0x077f], [0x08a0, 0x08ff], [0xfb50, 0xfdff], [0xfe70, 0xfeff],
];
const NKO: [number, number][] = [[0x07c0, 0x07ff]];

export class Router {
  private bamLetters: Set<string>;
  private bamTones: Set<string>;
  private fraMarks: Set<string>;
  private fraClitics: Set<string>;
  private bamClitics: Set<string>;

  constructor(private text: Text, rules: Bundle["rules"]) {
    this.bamLetters = new Set(rules.bam_letters);
    this.bamTones = new Set(rules.bam_tone_vowels);
    this.fraMarks = new Set(rules.fra_marks);
    this.fraClitics = new Set(rules.fra_clitics);
    this.bamClitics = new Set(rules.bam_clitics);
  }

  hard(tok: RawToken): Route | null {
    if (tok.kind === "UNIV" || Text.isRoman(tok.text)) return { label: "univ", confidence: 1, final: true };
    const norm = this.text.normalize(tok.text);
    const cps = Array.from(norm);
    if (cps.some((c) => inRange(c.codePointAt(0)!, NKO))) return { label: "bam", confidence: 0.999, final: true };
    if (cps.some((c) => inRange(c.codePointAt(0)!, ARABIC))) return { label: "univ", confidence: 1, final: true };
    if (cps.some((c) => this.bamLetters.has(c))) return { label: "bam", confidence: 0.999, final: true };
    return null;
  }

  orthographic(tok: RawToken, frenchFinal: boolean): Route | null {
    const norm = this.text.normalize(tok.text);
    if (tok.kind === "CLITIC") {
      if (this.fraClitics.has(norm)) return { label: "fra", confidence: 0.95, final: false };
      if (this.bamClitics.has(norm)) return { label: "bam", confidence: 0.95, final: false };
      return null;
    }
    const cps = Array.from(norm);
    if (cps.some((c) => this.fraMarks.has(c))) return { label: "fra", confidence: 0.97, final: frenchFinal };
    if (cps.some((c) => this.bamTones.has(c))) return { label: "bam", confidence: 0.9, final: false };
    return null;
  }
}

export class Lexicon {
  constructor(private text: Text, private entries: Bundle["lexicon"]) {}

  lookup(form: string): Partial<Record<LangLabel, number>> | null {
    const norm = this.text.normalize(form);
    let hit = Object.prototype.hasOwnProperty.call(this.entries, norm) ? this.entries[norm] : undefined;
    if (hit === undefined) {
      const folded = this.text.foldOldOrthography(norm);
      if (folded !== norm && Object.prototype.hasOwnProperty.call(this.entries, folded)) hit = this.entries[folded];
    }
    return hit ? { ...hit } : null;
  }
}

export class NaiveBayes {
  readonly labels: LangLabel[];
  private m: Bundle["model"];
  private logDenoms: number[];
  private cache = new Map<string, Record<string, number>>();

  constructor(private text: Text, model: Bundle["model"]) {
    this.m = model;
    this.labels = model.labels;
    const denomV = model.alpha * (model.vocab_size + 1);
    this.logDenoms = model.totals.map((t) => t + denomV);
  }

  grams(word: string): string[] {
    const w = Array.from(`<${this.text.normalize(word)}>`);
    const out: string[] = [];
    for (let n = this.m.n_min; n <= this.m.n_max; n++) {
      for (let i = 0; i + n <= w.length; i++) {
        const g = w.slice(i, i + n).join("");
        if (g !== "<" && g !== ">") out.push(g);
      }
    }
    return out;
  }

  predictProba(word: string): Record<string, number> {
    const cached = this.cache.get(word);
    if (cached) return { ...cached };
    const grams = this.grams(word);
    const K = this.labels.length;
    let result: Record<string, number>;
    if (grams.length === 0) {
      result = Object.fromEntries(this.labels.map((l) => [l, 1 / K]));
    } else {
      const temp = grams.length ** this.m.temp_power;
      const scores = this.labels.map((_, k) => {
        let ll = 0;
        for (const g of grams) {
          const c = this.m.grams[g]?.[k] ?? 0;
          ll += Math.log((c + this.m.alpha) / this.logDenoms[k]);
        }
        return this.m.log_priors[k] + ll / temp;
      });
      const mx = Math.max(...scores);
      const ex = scores.map((s) => Math.exp(s - mx));
      const z = ex.reduce((a, b) => a + b, 0);
      result = Object.fromEntries(this.labels.map((l, k) => [l, ex[k] / z]));
    }
    if (this.cache.size < 200_000) this.cache.set(word, result);
    return { ...result };
  }
}

const FLOOR = 1e-4;

function lse(xs: number[]): number {
  const m = Math.max(...xs);
  let s = 0;
  for (const x of xs) s += Math.exp(x - m);
  return m + Math.log(s);
}

/** Forward-backward posteriors with a "stay in the same language" transition prior. */
export function posteriors(emissions: Record<string, number>[], labels: string[], stay: number): Record<string, number>[] {
  const T = emissions.length, K = labels.length;
  if (T === 0) return [];
  const ls = Math.log(stay), lw = Math.log((1 - stay) / (K - 1));
  const tr = (i: number, j: number) => (i === j ? ls : lw);
  const E = emissions.map((e) => labels.map((l) => Math.log(Math.max(e[l] ?? 0, FLOOR))));
  const a: number[][] = Array.from({ length: T }, () => new Array(K).fill(0));
  for (let k = 0; k < K; k++) a[0][k] = -Math.log(K) + E[0][k];
  for (let t = 1; t < T; t++)
    for (let k = 0; k < K; k++) {
      const xs: number[] = [];
      for (let j = 0; j < K; j++) xs.push(a[t - 1][j] + tr(j, k));
      a[t][k] = E[t][k] + lse(xs);
    }
  const b: number[][] = Array.from({ length: T }, () => new Array(K).fill(0));
  for (let t = T - 2; t >= 0; t--)
    for (let j = 0; j < K; j++) {
      const xs: number[] = [];
      for (let k = 0; k < K; k++) xs.push(tr(j, k) + E[t + 1][k] + b[t + 1][k]);
      b[t][j] = lse(xs);
    }
  return a.map((row, t) => {
    const s = row.map((v, k) => v + b[t][k]);
    const z = lse(s);
    return Object.fromEntries(labels.map((l, k) => [l, Math.exp(s[k] - z)]));
  });
}

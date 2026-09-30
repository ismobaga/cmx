// Pipeline + message-level views: mirror of cmx_lid/pipeline.py and summary.py.
import type { Bundle, Config, LangLabel, Segment, Source, Summary, Token } from "./types.js";
import { Text, type RawToken } from "./text.js";
import { Lexicon, NaiveBayes, Router, posteriors } from "./model.js";

interface Decision {
  emission: Record<string, number>;
  source: Source;
  forced: LangLabel | "univ" | null;
}

const argmax = (d: Record<string, number>, order: string[]) => {
  let best = order[0], bv = -Infinity;
  for (const l of order) if ((d[l] ?? 0) > bv) { bv = d[l] ?? 0; best = l; }
  return best;
};

function isUpper(s: string): boolean {
  let cased = false;
  for (const ch of s) {
    const lo = ch.toLowerCase(), up = ch.toUpperCase();
    if (lo !== up) {
      cased = true;
      if (ch !== up) return false;
    }
  }
  return cased;
}

export class CmxLid {
  readonly schemaVersion: string;
  /** cmx-lid version that produced the model (e.g. "0.5.0"). */
  readonly modelVersion: string;
  readonly config: Config;
  private text: Text;
  private router: Router;
  private lexicon: Lexicon;
  private nb: NaiveBayes;
  private langs: LangLabel[];
  private sentenceEnd: Set<string>;

  /** Build from a model bundle (the JSON object in model/cmx-lid.json). */
  constructor(bundle: Bundle, config: Partial<Config> = {}) {
    if (!bundle?.format?.startsWith("cmx-lid-js/")) throw new Error("not a cmx-lid model bundle");
    this.schemaVersion = bundle.schema_version;
    this.modelVersion = bundle.version ?? "unknown";
    this.config = { ...bundle.config, ...config };
    this.langs = bundle.lang_labels;
    this.text = new Text(bundle.rules);
    this.router = new Router(this.text, bundle.rules);
    this.lexicon = new Lexicon(this.text, bundle.lexicon);
    this.nb = new NaiveBayes(this.text, bundle.model);
    this.sentenceEnd = new Set(bundle.rules.sentence_end);
  }

  // ---- simple API ---------------------------------------------------------

  /** [[word, label], ...]; punctuation/numbers/emoji left out unless includePunct. */
  tag(text: string, includePunct = false): [string, Token["label"]][] {
    return this.identify(text)
      .filter((t) => includePunct || t.label !== "univ")
      .map((t) => [t.text, t.label]);
  }

  /** Main language of the text ('bam' | 'fra' | 'eng'), or null if it has no words. */
  detect(text: string): LangLabel | null {
    return this.summarize(text).dominant;
  }

  /** True if the text mixes languages. */
  isCodeSwitched(text: string): boolean {
    return this.summarize(text).codeSwitched;
  }

  // ---- full API -----------------------------------------------------------

  identify(text: string): Token[] {
    return this.identifyTokens(this.text.tokenize(text));
  }

  /** Label words that are already split (e.g. gold data); offsets assume single spaces. */
  identifyPretokenized(words: string[]): Token[] {
    let pos = 0;
    const raw: RawToken[] = words.map((w) => {
      const t = { text: w, start: pos, end: pos + w.length, kind: this.text.kindOf(w) };
      pos += w.length + 1;
      return t;
    });
    return this.identifyTokens(raw);
  }

  summarize(input: string | Token[]): Summary {
    const tokens = typeof input === "string" ? this.identify(input) : input;
    const words = tokens.map((t) => t.label).filter((l): l is LangLabel => l !== "univ");
    const n = words.length;
    const proportions: Partial<Record<LangLabel, number>> = {};
    for (const l of this.langs) {
      const c = words.filter((w) => w === l).length;
      if (c) proportions[l] = c / n;
    }
    let dominant: LangLabel | null = null;
    for (const l of Object.keys(proportions) as LangLabel[]) {
      if (dominant === null) { dominant = l; continue; }
      const a = proportions[l]!, b = proportions[dominant]!;
      if (a > b || (a === b && l === "bam" && dominant !== "bam")) dominant = l;
    }
    let nSwitches = 0;
    for (let i = 1; i < n; i++) if (words[i] !== words[i - 1]) nSwitches++;
    return { dominant, proportions, codeSwitched: Object.keys(proportions).length > 1, nWords: n, nSwitches };
  }

  /** Runs of same-language words; punctuation never splits a run. */
  segments(input: string | Token[]): Segment[] {
    const tokens = typeof input === "string" ? this.identify(input) : input;
    const out: Segment[] = [];
    for (const t of tokens) {
      if (t.label === "univ") continue;
      const last = out[out.length - 1];
      if (last && last.label === t.label) {
        last.end = t.end;
        last.nWords += 1;
      } else out.push({ label: t.label, start: t.start, end: t.end, nWords: 1 });
    }
    return out;
  }

  // ---- internals ----------------------------------------------------------

  private onehot(label: string, conf: number): Record<string, number> {
    const rest = (1 - conf) / (this.langs.length - 1);
    return Object.fromEntries(this.langs.map((l) => [l, l === label ? conf : rest]));
  }

  private decide(tok: RawToken, mid: boolean): Decision {
    const cfg = this.config;
    const hard = this.router.hard(tok);
    if (hard) {
      if (hard.label === "univ") return { emission: {}, source: "router", forced: "univ" };
      return { emission: this.onehot(hard.label, hard.confidence), source: "router", forced: hard.label };
    }
    const lex = this.lexicon.lookup(tok.text);
    if (lex) {
      const labels = Object.keys(lex) as LangLabel[];
      if (labels.length === 1) {
        return { emission: this.onehot(labels[0], cfg.lexicon_confidence), source: "lexicon", forced: null };
      }
      if (!cfg.ambiguous_use_classifier) {
        return { emission: Object.fromEntries(this.langs.map((l) => [l, lex[l] ?? 0])), source: "lexicon", forced: null };
      }
      const clf = this.nb.predictProba(tok.text);
      const mixed: Record<string, number> = {};
      let z = 0;
      for (const l of labels) { mixed[l] = lex[l]! * Math.max(clf[l] ?? 0, 1e-3); z += mixed[l]; }
      return { emission: Object.fromEntries(this.langs.map((l) => [l, (mixed[l] ?? 0) / z])), source: "lexicon", forced: null };
    }
    const orth = this.router.orthographic(tok, cfg.french_orthography_final);
    if (orth) {
      return { emission: this.onehot(orth.label, orth.confidence), source: "router", forced: orth.final ? orth.label : null };
    }
    if (tok.kind === "CLITIC") return { emission: { bam: 0.5, fra: 0.5 }, source: "context", forced: null };

    let dist = this.nb.predictProba(tok.text);
    dist = Object.fromEntries(this.langs.map((l) => [l, dist[l] ?? 0]));
    const first = Array.from(tok.text)[0] ?? "";
    if (cfg.names_follow_context && mid && isUpper(first) && !isUpper(tok.text)) {
      const w = cfg.name_classifier_weight;
      const flat = 1 / this.langs.length;
      return {
        emission: Object.fromEntries(this.langs.map((l) => [l, w * (dist[l] ?? 0) + (1 - w) * flat])),
        source: "context", forced: null,
      };
    }
    return { emission: dist, source: "classifier", forced: null };
  }

  private identifyTokens(raw: RawToken[]): Token[] {
    const decisions = new Map<number, Decision>();
    let mid = false;
    raw.forEach((t, i) => {
      if (t.kind === "UNIV") {
        if (this.sentenceEnd.has(t.text)) mid = false;
        return;
      }
      decisions.set(i, this.decide(t, mid));
      mid = true;
    });
    const univ = new Set<number>();
    raw.forEach((t, i) => {
      if (t.kind === "UNIV" || decisions.get(i)?.forced === "univ") univ.add(i);
    });
    const chain = raw.map((_, i) => i).filter((i) => !univ.has(i));
    const post = posteriors(chain.map((i) => decisions.get(i)!.emission), this.langs, this.config.stay_prob);
    const postBy = new Map(chain.map((i, k) => [i, post[k]]));

    return raw.map((t, i): Token => {
      if (univ.has(i)) return { text: t.text, start: t.start, end: t.end, label: "univ", confidence: 1, source: "router" };
      const d = decisions.get(i)!, p = postBy.get(i)!;
      let label: LangLabel, conf: number, source: Source;
      if (d.forced && d.forced !== "univ") {
        label = d.forced;
        source = "router";
        conf = Math.max(p[label], d.emission[label]);
      } else {
        label = argmax(p, this.langs) as LangLabel;
        conf = p[label];
        source = label === argmax(d.emission, Object.keys(d.emission)) ? d.source : "context";
      }
      return { text: t.text, start: t.start, end: t.end, label, confidence: Math.round(conf * 1e4) / 1e4, source };
    });
  }
}

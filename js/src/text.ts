// Tokenizer + normalization: mirror of cmx_lid/tokenize.py and normalize.py.
import type { Bundle } from "./types.js";

export type Kind = "WORD" | "CLITIC" | "UNIV";
export interface RawToken {
  text: string;
  start: number;
  end: number;
  kind: Kind;
}

// Python's [^\W\d_] (letters), \w and \d, as Unicode property classes.
const L = String.raw`[\p{L}\p{Nl}\p{No}]`;
const M = String.raw`[̀-ͯ߫-ߵ߽]`; // combining tones (Latin, N'Ko)
const LM = `(?:${L}|${M})`;
const W = String.raw`[\p{L}\p{N}_]`;
const D = String.raw`\p{Nd}`;
const APOS = "'’ʼ";

const TOKEN_RE = new RegExp(
  [
    String.raw`(?<url>(?:https?:\/\/|www\.)\S+)`,
    String.raw`(?<email>[\p{L}\p{N}_.+\-]+@[\p{L}\p{N}_\-]+\.[\p{L}\p{N}_.\-]+)`,
    `(?<tag>[@#]${W}+)`,
    `(?<num>${D}+(?:[.,:/]${D}+)*(?:${LM}+${D}*)*)`,
    `(?<word>${L}${LM}*(?:[${APOS}\\-]${L}${LM}*)*)`,
    String.raw`(?<other>\S)`,
  ].join("|"),
  "gu",
);

const CLITIC_RE = new RegExp(
  `^((?:jusqu|lorsqu|puisqu|presqu|quoiqu|qu|${L}{1,2})[${APOS}])(${L}.*)$`,
  "iu",
);
const WORD_FULL = new RegExp(`^${L}${LM}*(?:[${APOS}\\-]${L}${LM}*)*$`, "u");
const CLITIC_FULL = new RegExp(`^${L}{1,6}[${APOS}]$`, "u");
const ROMAN = /^(?=[IVXLCDM]{2,}$|[VXLCDM]$)M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$/;

export class Text {
  private apos: Record<string, string>;
  private oldOrth: Record<string, string>;
  private enSuffixes: Set<string>;

  constructor(rules: Bundle["rules"]) {
    this.apos = rules.apostrophes;
    this.oldOrth = rules.old_orthography;
    this.enSuffixes = new Set(rules.en_contraction_suffixes);
  }

  /** NFC, unify apostrophes, lowercase. */
  normalize(s: string): string {
    let out = "";
    for (const ch of s.normalize("NFC")) out += this.apos[ch] ?? ch;
    return out.toLowerCase();
  }

  foldOldOrthography(s: string): string {
    let out = "";
    for (const ch of s) out += this.oldOrth[ch] ?? ch;
    return out;
  }

  tokenize(text: string): RawToken[] {
    const out: RawToken[] = [];
    for (const m of text.matchAll(TOKEN_RE)) {
      const start = m.index ?? 0;
      const s = m[0];
      if (m.groups?.word !== undefined) out.push(...this.splitWord(s, start));
      else out.push({ text: s, start, end: start + s.length, kind: "UNIV" });
    }
    return out;
  }

  private splitWord(text: string, start: number): RawToken[] {
    const m = CLITIC_RE.exec(text);
    if (m && !this.enSuffixes.has(this.normalize(m[2]))) {
      const head = m[1], rest = m[2];
      const cut = start + head.length;
      return [
        { text: head, start, end: cut, kind: "CLITIC" },
        { text: rest, start: cut, end: cut + rest.length, kind: "WORD" },
      ];
    }
    return [{ text, start, end: start + text.length, kind: "WORD" }];
  }

  kindOf(word: string): Kind {
    if (CLITIC_FULL.test(word)) return "CLITIC";
    if (WORD_FULL.test(word)) return "WORD";
    return "UNIV";
  }

  static isRoman(s: string): boolean {
    return ROMAN.test(s);
  }
}

/** Exposed for tests: the character classes used above. */
export const CHAR_CLASSES = {
  letter: new RegExp(`^${L}$`, "u"),
  word: new RegExp(`^${W}$`, "u"),
  digit: new RegExp(`^${D}$`, "u"),
};

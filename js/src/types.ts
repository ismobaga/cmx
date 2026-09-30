/** Labels of schema 2.0.0. `univ` = punctuation, numbers, emoji, links, roman numerals. */
export type Label = "bam" | "fra" | "eng" | "univ";
export type LangLabel = "bam" | "fra" | "eng";
/** Which pipeline stage decided the label. */
export type Source = "router" | "lexicon" | "classifier" | "context";

export interface Token {
  text: string;
  /** UTF-16 offsets into the input: `input.slice(start, end) === text`. */
  start: number;
  end: number;
  label: Label;
  /** Posterior probability of `label`, 0..1 (4 decimals). */
  confidence: number;
  source: Source;
}

export interface Segment {
  label: LangLabel;
  start: number;
  end: number;
  nWords: number;
}

export interface Summary {
  /** Main language, or null if the text has no words. */
  dominant: LangLabel | null;
  /** Share of words per language (only languages present). */
  proportions: Partial<Record<LangLabel, number>>;
  codeSwitched: boolean;
  nWords: number;
  /** Language changes between consecutive words. */
  nSwitches: number;
}

export interface Config {
  stay_prob: number;
  lexicon_confidence: number;
  french_orthography_final: boolean;
  ambiguous_use_classifier: boolean;
  names_follow_context: boolean;
  name_classifier_weight: number;
}

/** The model file produced by `python -m cmx_lid.export_js`. */
export interface Bundle {
  format: string;
  /** cmx-lid version that produced the bundle. */
  version?: string;
  schema_version: string;
  labels: Label[];
  lang_labels: LangLabel[];
  config: Config;
  rules: {
    apostrophes: Record<string, string>;
    old_orthography: Record<string, string>;
    bam_letters: string;
    bam_tone_vowels: string;
    fra_marks: string;
    fra_clitics: string[];
    bam_clitics: string[];
    en_contraction_suffixes: string[];
    sentence_end: string[];
  };
  lexicon: Record<string, Partial<Record<LangLabel, number>>>;
  model: {
    labels: LangLabel[];
    n_min: number;
    n_max: number;
    alpha: number;
    temp_power: number;
    vocab_size: number;
    log_priors: number[];
    totals: number[];
    grams: Record<string, number[]>;
  };
}

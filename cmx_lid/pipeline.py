"""router -> lexicon -> orthography -> classifier -> context decoder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import paths
from .classifier import WordClassifier, load_classifier
from .decode import posteriors
from .lexicon import Lexicon
from .router import route_hard, route_orthographic
from .schema import LANG_LABELS, Token
from .tokenize import CLITIC, UNIV, RawToken, kind_of, tokenize


@dataclass(frozen=True)
class Config:
    stay_prob: float = 0.8              # P(next token keeps the same language)
    # Curated single-label entries must survive one-word insertions
    # ("n bɛ download kɛ"), so context can only flip them on strong evidence.
    lexicon_confidence: float = 0.995
    french_orthography_final: bool = True  # French spelling always wins ("hôpital" -> fra)
    # Ambiguous short words (la, a, de, in): n-gram classifiers are unreliable on
    # 1-3 letters, so by default only the lexicon prior and context decide.
    ambiguous_use_classifier: bool = False
    # Capitalized words mid-sentence that nothing else recognizes are usually
    # names (Segu, Kulubali, Krista). The schema has no name label, so their
    # classifier guess is flattened and they take the language around them,
    # instead of creating fake switch points.
    names_follow_context: bool = True
    name_classifier_weight: float = 0.3


_SENTENCE_END = frozenset({".", "!", "?", "…", ":", "\n", '."', '!"', '?"'})


@dataclass
class _Decision:
    emission: dict[str, float]
    source: str
    forced: str | None = None


def _onehot(label: str, conf: float) -> dict[str, float]:
    rest = (1 - conf) / (len(LANG_LABELS) - 1)
    return {l: (conf if l == label else rest) for l in LANG_LABELS}


class Identifier:
    def __init__(self, lexicon: Lexicon, model: WordClassifier, config: Config = Config()):
        self.lexicon, self.model, self.config = lexicon, model, config

    @classmethod
    def load(cls, lexicon_path: str | Path = paths.LEXICON_PATH,
             model_path: str | Path = paths.MODEL_PATH, config: Config = Config()) -> "Identifier":
        if not Path(model_path).exists():
            raise FileNotFoundError(f"model not found: {model_path}\n"
                                    "Build it once with:  python -m cmx_lid.build")
        return cls(Lexicon.load(lexicon_path), load_classifier(model_path), config)

    # -- per-token evidence -------------------------------------------------
    def _classifier_dist(self, word: str) -> dict[str, float]:
        cache = self.__dict__.setdefault("_cache", {})
        hit = cache.get(word)
        if hit is None:
            p = self.model.predict_proba(word)
            hit = {l: p.get(l, 0.0) for l in LANG_LABELS}
            if len(cache) < 200_000:
                cache[word] = hit
        return dict(hit)

    def _decide(self, tok: RawToken, mid_sentence: bool = False) -> _Decision:
        hard = route_hard(tok)
        if hard is not None:
            if hard.label == "univ":
                return _Decision({}, "router", "univ")
            return _Decision(_onehot(hard.label, hard.confidence), "router", hard.label)

        lex = self.lexicon.lookup(tok.text)
        if lex is not None:
            if len(lex) == 1:
                label = next(iter(lex))
                return _Decision(_onehot(label, self.config.lexicon_confidence), "lexicon")
            if not self.config.ambiguous_use_classifier:
                return _Decision({l: lex.get(l, 0.0) for l in LANG_LABELS}, "lexicon")
            clf = self._classifier_dist(tok.text)
            mixed = {l: w * max(clf.get(l, 0.0), 1e-3) for l, w in lex.items()}
            z = sum(mixed.values())
            return _Decision({l: mixed.get(l, 0.0) / z for l in LANG_LABELS}, "lexicon")

        orth = route_orthographic(tok, self.config.french_orthography_final)
        if orth is not None:
            return _Decision(_onehot(orth.label, orth.confidence), "router",
                             orth.label if orth.final else None)

        if tok.kind == CLITIC:  # shared clitic (n' m' t' s'): let context decide
            return _Decision({"bam": 0.5, "fra": 0.5}, "context")

        dist = self._classifier_dist(tok.text)
        if (self.config.names_follow_context and mid_sentence and tok.text[:1].isupper()
                and not tok.text.isupper()):
            w = self.config.name_classifier_weight
            flat = {l: 1 / len(LANG_LABELS) for l in LANG_LABELS}
            dist = {l: w * dist.get(l, 0.0) + (1 - w) * flat[l] for l in LANG_LABELS}
            return _Decision(dist, "context")
        return _Decision(dist, "classifier")

    # -- public API ---------------------------------------------------------
    def identify_tokens(self, raw: Sequence[RawToken]) -> list[Token]:
        decisions: dict[int, _Decision] = {}
        mid = False
        for i, t in enumerate(raw):
            if t.kind == UNIV:
                if t.text in _SENTENCE_END:
                    mid = False
                continue
            decisions[i] = self._decide(t, mid)
            mid = True
        # the router can also send word-shaped tokens to univ (roman numerals)
        univ = {i for i, t in enumerate(raw) if t.kind == UNIV or decisions[i].forced == "univ"}
        chain_idx = [i for i in range(len(raw)) if i not in univ]
        post = posteriors([decisions[i].emission for i in chain_idx], LANG_LABELS,
                          self.config.stay_prob)
        post_by_idx = dict(zip(chain_idx, post))

        out: list[Token] = []
        for i, t in enumerate(raw):
            if i in univ:
                out.append(Token(t.text, t.start, t.end, "univ", 1.0, "router"))
                continue
            d, p = decisions[i], post_by_idx[i]
            if d.forced:
                label, source = d.forced, "router"
                conf = max(p[label], d.emission[label])
            else:
                label = max(p, key=p.get)
                conf = p[label]
                source = d.source if label == max(d.emission, key=d.emission.get) else "context"
            out.append(Token(t.text, t.start, t.end, label, round(conf, 4), source))
        return out

    def identify(self, text: str) -> list[Token]:
        return self.identify_tokens(tokenize(text))

    def identify_pretokenized(self, words: Sequence[str]) -> list[Token]:
        raw, pos = [], 0
        for w in words:
            raw.append(RawToken(w, pos, pos + len(w), kind_of(w)))
            pos += len(w) + 1
        return self.identify_tokens(raw)


_default: Identifier | None = None


def identify(text: str) -> list[Token]:
    """Label every token in `text` using the default lexicon and model."""
    global _default
    if _default is None:
        _default = Identifier.load()
    return _default.identify(text)

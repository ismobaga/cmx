# cmx-lid model card (v0.3.0, 2026-09-29)

Word-level language ID for Bambara text with French/English switches.
Labels: `bam fra eng univ` (frozen schema 2.0.0; `ara` dropped). Labels follow usage, not etymology.

## Models

| File | Backend | Size | Needs |
|---|---|---|---|
| `models/cmx-lid-nb.json` (**default**) | char 1–5-gram Naive Bayes | 1.4 MB (`--prune 2` → 0.9 MB) | nothing (pure Python, portable JSON) |
| `models/cmx-lid-ft.ftz` | fastText, dim 16, quantized | 1.3 MB | `fasttext-wheel` |

Both models sit behind the same pipeline: router → lexicon → orthography
rules → classifier → context decoder (stay-probability 0.8).

## Training data (33.5k word types)

- BAYƐLƐMABAGA **train split** only (37.6k Bambara–French sentence pairs,
  CC-BY-SA-4.0). Word types are kept if they occur ≥3 times with ≥90%
  of their occurrences on one language side.
- FrequencyWords English top 10k (MIT).
- Seed lexicon (`data/lexicon.tsv`).
- Informal-spelling augmentation: every Bambara word is also trained as
  `ɛ→e/è`, `ɔ→o/ò`, `ɲ→ny/gn`, `ŋ→ng`, and colonial-style spellings
  (`u→ou`, `j→dj`, `c→tch`), unless that form is already a real French or
  English word.
- Words seen under two labels (fr/en `or`, `son`) are kept under both, and
  context decides.

## Held-out results: BAYƐLƐMABAGA test split (never trained or tuned on)

`python -m cmx_lid.benchmark --split test [--model …]`. Accuracy is at word
level; punctuation and numbers are excluded.

| Suite | What it is | NB acc | fastText acc |
|---|---|---|---|
| bam | 4.7k real Bambara sentences (standard + informal spellings) | 0.982 | 0.986 |
| fra | the aligned French sentences | 0.992 | 0.994 |
| bam-inf | same Bambara re-spelled informally (be, mogo, dougou, tche) | 0.981 | 0.981 |
| cs-synth | Bambara + 1–3 French words spliced in; **French-word F1** | 0.868 | 0.883 |
| | macro accuracy | 0.976 | 0.980 |

Dev split (used for tuning), NB: macro 0.990, cs-synth French F1 0.904.
Before this round of improvements, the same dev suites scored macro 0.974,
bam-inf 0.968 and cs F1 0.885.

Tuned on dev: n-gram 1–5, α=0.1, likelihood tempering #grams^0.5,
stay-probability 0.8. fastText is about 1.5 F1 points better at spotting
switches. NB stays the default because it needs no dependencies and ports to
any device.

## How to read these numbers (limitations)

- **In-domain and edited text.** BAYƐLƐMABAGA comes from books, periodicals
  and religious text. Informal chat (WhatsApp, SMS) will score lower. No
  real annotated chat data exists yet; collecting it is the top priority.
- **Silver gold.** In the `bam`/`fra` suites every word is assumed to be one
  language. Real switches and names inside them are counted as errors, so
  those scores are slightly pessimistic.
- **Synthetic switching.** `cs-synth` splices real French words into
  Bambara. The splice points are random, not natural. Kunkado radio
  transcripts (real, annotated switches) are the next benchmark: see DATA.md.
- **Short ambiguous words** (`la`, `de`, `a`, `si`, `ce`) depend on the
  lexicon prior and their neighbours. A single inserted French `la`/`de` is
  usually tagged `bam`.
- **Names** have no label of their own. A capitalized unknown word mid-sentence
  takes the language around it (`Config(names_follow_context=False)` turns
  this off). That costs about 1 F1 point on cs-synth but avoids fake switches
  on names like Kulubali and Segu.
- English is covered by a word list only. English switches have no benchmark.
- N'Ko handling is rule-based and untested on real text. Arabic script is
  not expected and is labeled `univ`.

## Reproduce

```bash
python -m cmx_lid.ingest.wordlist --text bam=data/raw/bayelemabaga/train/train.bam \
    --text fra=data/raw/bayelemabaga/train/train.fr --out data/silver/wl-bayelemabaga.tsv
python -m cmx_lid.ingest.wordlist --freq eng=data/raw/frequencywords/en_50k.txt --limit 10000 \
    --out data/silver/wl-en-top10k.tsv
python -m cmx_lid.train --wordlist data/silver/wl-bayelemabaga.tsv --wordlist data/silver/wl-en-top10k.tsv
python -m cmx_lid.train --wordlist data/silver/wl-bayelemabaga.tsv --wordlist data/silver/wl-en-top10k.tsv --backend fasttext
python -m cmx_lid.benchmark --split test
```

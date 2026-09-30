# cmx-lid

Token-level language identification for Bambara text with French and English
switches. It's the first module of the `cmx` on-device suite. Pure Python,
no dependencies, and the model is a small JSON file.

## Quick start

```powershell
pip install -e .                      # once: installs the `cmx-lid` command (no dependencies)
python -m cmx_lid.build               # once: downloads public data, trains, benchmarks (~1 min;
                                      #   +10 min the first time if Hugging Face is reachable)
cmx-lid "n taara l'hôpital kunun"
```

```text
[bam] n taara  [fra] l'hôpital  [bam] kunun
  -> Bambara 60%, French 40% (code-switched, 2 switches)
```

Run `cmx-lid` with no text for an interactive prompt. `cmx-lid --words "..."`
prints one word per line with confidence, and `cmx-lid --json < file.txt`
emits JSON lines for scripts.

In Python:

```python
import cmx_lid
cmx_lid.tag("n taara l'hôpital kunun")   # [('n','bam'), ('taara','bam'), ("l'",'fra'), ('hôpital','fra'), ('kunun','bam')]
cmx_lid.detect("je suis fatigué")        # 'fra'  (main language; None if no words)
cmx_lid.is_code_switched("réunion bɛ kɛ demain")   # True
cmx_lid.identify(text)                   # full Token objects: offsets, confidence, source
```

Labels: `bam`, `fra`, `eng`, and `univ` (punctuation, numbers, emoji, links).

**Web demo:** `site/` is a static site (hub + `/lid/` demo, FR/EN) meant
for **ai.crommixmali.com**, deployed with Docker on Dokploy. See
**[deploy/DEPLOY.md](deploy/DEPLOY.md)** for deploying, previewing locally
and adding future models.

**JavaScript / TypeScript:** the `js/` folder is a zero-dependency npm
package that gives the same results as Python (Node and browsers). See
**[js/README.md](js/README.md)**.

```ts
import { load } from "@crommix/lid";
const lid = await load();
lid.tag("n taara l'hôpital kunun");   lid.detect("je suis fatigué");   // "fra"
```

**Build options:** `--fasttext` also trains the optional fastText model
(`pip install fasttext-wheel`). `--no-hf` skips Hugging Face. `--refresh`
re-downloads everything. Set `HF_TOKEN` to include the gated djelia dataset.
Interrupted Kunkado downloads are detected and fetched again on the next
build.

Results: **[MODEL_CARD.md](MODEL_CARD.md)** and `models/report.json`.
Data sources and licenses: **[DATA.md](DATA.md)**. Tests:
`python -m unittest discover -s tests -t .`

## Labeling policy (usage, not etymology)

| Case | Example | Label |
|---|---|---|
| Arabic loans written in Latin script | inchallah, al-hamdoulillah | `bam` |
| Fully nativized French | lopital, taabali, lekɔli | `bam` |
| Live French switch (French spelling or elision) | **l'hôpital** in "n taara l'hôpital" | `fra` |
| Bambara phonology and spelling | opital in "n taara opital la" | `bam` |
| French spelling without elision | hôpital in "n taara hôpital la" | `fra` (spelling wins; set `Config(french_orthography_final=False)` to let context decide) |
| Punctuation, numbers, emoji, URLs, @/#tags, roman numerals, Arabic script (not expected) | | `univ` |

The frozen output contract is in `cmx_lid/schema.py` and `schema/token.schema.json`.
Its fingerprint is pinned in `tests/test_schema.py`.

## Pipeline

1. **Tokenizer**: splits text into tokens and keeps character offsets. It also
   splits clitics off their host word (`l'`+`hôpital`, `k'`+`a`) but leaves
   English contractions whole.
2. **Hard router**: `univ` tokens, N'Ko script (→ `bam`), Arabic script (→ `univ`), and the Bambara letters ɛ ɔ ɲ ŋ.
3. **Lexicon** (`data/lexicon.tsv`): a usage-labeled word list. Ambiguous forms
   (`la`, `a`, `ni`, `don`…) carry weights, and context resolves them. Lookups
   fall back to old spellings (`bè`→`bɛ`).
4. **Orthography rules**: French-only diacritics (é ô ç…) mean `fra`.
   `è` and `ò` are excluded because older Bambara spelling uses them. French
   and Bambara clitic tables also apply here.
5. **Classifier**: character n-gram Naive Bayes (default, no dependencies) or
   fastText (optional), for words that none of the steps above decided.
6. **Context decoder**: forward-backward over the token sequence with a
   "stay in the same language" prior. It resolves ambiguous and weak tokens.

Each token reports its `source`, the stage that decided its label.

## Loanword origin side table

`data/loanword_origin.tsv` records where a loanword came from
(`inchallah → ara`, `lekɔli → fra`). The model always tags these words `bam`,
so the side table is **metadata only**. Tests enforce three things:

- no classification or training module reads it (only `cmx_lid/origins.py` and
  the CLI's `--origins` flag do);
- the table has no label column;
- every form in it is labeled `bam`, and only `bam`, in the lexicon.

To use it, run `OriginTable.load().annotate(tokens)` after labeling, or
`by_origin("ara")` to pull, for example, religious vocabulary.

## ⚠ Seed files are still placeholders

The classifier now trains on real corpora (see MODEL_CARD.md), but
`data/seed/*.conll`, `lexicon.tsv` and `loanword_origin.tsv` are still small,
hand-written and unreviewed, and the etymologies still need checking. Use
`python -m cmx_lid.benchmark`, not the seed dev file, to judge quality.

## Open questions

- Proper names (Ismail, Bamako) have no dedicated label. Capitalized unknown
  words mid-sentence take the label of the words around them.
- Words that switch language mid-word (a French stem with a Bambara suffix,
  e.g. `réunionw`) get a single label.
- A Bambara postposition right after a French word (`hôpital la`) comes out
  `bam` today, but only because of the lexicon weights on `la`. Real data
  should confirm that.

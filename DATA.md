# Data sources for cmx-lid

Checked Sept 2026. **Licenses matter**: Crommix is a company, so anything
marked *NC* (non-commercial) can be used for research but not in a shipped
model. Not legal advice. Check each card yourself before using it.

## Tier 1: use now

| Source | What it gives cmx-lid | License | How |
|---|---|---|---|
| [RobotsMali/kunkado](https://huggingface.co/datasets/RobotsMali/kunkado) | ~160 h of Malian radio transcripts. **French switches are marked `__…__` and written in French spelling**, which is exactly our usage policy. That gives word-level code-switch labels for free. ~39k human-reviewed segments | CC-BY-SA-4.0 | `python -m cmx_lid.ingest.kunkado` |
| [BAYƐLƐMABAGA](https://github.com/RobotsMali-AI/datasets) (**ungated, on GitHub**, already downloaded to `data/raw/bayelemabaga/`) | 47k aligned Bambara–French sentences from the reference corpus, in standard and informal spellings, split into train/valid/test. Train builds the word list; dev and test feed `cmx_lid.benchmark`. Built into `data/silver/wl-bayelemabaga.tsv` | CC-BY-SA-4.0 | `--text bam=… --text fra=…` (below) |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) English 50k (downloaded to `data/raw/frequencywords/`) | English vocabulary, since no Bambara source has much English | MIT | `--freq eng=… --limit 10000` |
| [djelia/bambara-mt-dataset](https://huggingface.co/datasets/djelia/bambara-mt-dataset) (**gated; access granted**: set `$env:HF_TOKEN`) | Bambara↔French/English sentence pairs from RobotsMali's EGAFE children's books and an ethnographic study. Modern, simple Bambara, and the only source here with real English alongside | CC-BY-SA-4.0 | `--hf djelia/bambara-mt-dataset --split all` (rows are `source_text`/`target_text` pairs; languages come from `source_lang`/`target_lang`) |
| [oza75/bambara-mt](https://huggingface.co/datasets/oza75/bambara-mt) (gated; **access not granted**, so not used) | Larger parallel set, if access is ever granted | MIT, with subsets derived from non-commercial sources | see `wordlist --help` |

## Tier 2: good, but check license or access

| Source | Use | Caveat |
|---|---|---|
| [Bamadaba](https://github.com/maslinych/bamadaba) (Bambara–French dictionary) | Lexicon expansion: thousands of vetted Bambara headwords | CC BY-NC-SA 3.0 FR: **non-commercial** |
| [Corpus Bambara de Référence](http://cormand.huma-num.fr/) | 11M words, 1.7M disambiguated. Best source of standard written Bambara | Accessed through a search interface; the site doesn't state a license. Ask the maintainers (build code: [corbama-build](https://github.com/maslinych/corbama-build)) |
| [MAFAND-MT](https://github.com/masakhane-io/lafand-mt) en–bam news | Word lists, English side | CC-BY-4.0-**NC** |
| [Glot500 bam_Latn](https://huggingface.co/datasets/cis-lmu/Glot500/tree/main/bam_Latn) | Crawled monolingual Bambara | Mixed sources and licenses; noisy |
| Bambara news: [RFI Mandenkan](https://www.rfi.fr/ma/), [VOA Bambara](https://www.voabambara.com), [Jɛmukan](https://jemukanmalitelegraph.wordpress.com), [Kanjamadi](http://kanjamadi.org) (N'Ko) | Real written Bambara in varied spellings (VOA spelling is ad hoc, which is useful for robustness) | Scrape only within each site's terms. Filter with GlotLID first |

## Tools

- [GlotLID](https://huggingface.co/cis-lmu/glotlid) (fastText, Apache-2.0 + notices):
  use it to filter crawled text **per message**, never per word. Expect
  confusion with Dyula/Mandinka.
- [MaskLID](https://github.com/cisnlp/MaskLID): a code-switching language ID
  method built on fastText. Worth reading before designing a sentence-level
  cmx-lid mode.

## Your own data (the real gap)

None of the sources above is informal *written* Bambara: WhatsApp, Facebook,
SMS, with French-style spellings like `bè`, `tchè`, `dougou`. That is exactly
where cmx-lid will run. Yan Courant reports and the Bambara data platform
can collect it with user consent. Hand-labeling even 500–1,000 real
messages is worth more than any extra silver data, because it gives you an
honest test set.

## Already done (2026-09-29)

```bash
# TRAIN split only: valid/ and test/ are kept for python -m cmx_lid.benchmark
python -m cmx_lid.ingest.wordlist --text bam=data/raw/bayelemabaga/train/train.bam \
    --text fra=data/raw/bayelemabaga/train/train.fr --out data/silver/wl-bayelemabaga.tsv
python -m cmx_lid.ingest.wordlist --freq eng=data/raw/frequencywords/en_50k.txt --limit 10000 \
    --out data/silver/wl-en-top10k.tsv
python -m cmx_lid.train --wordlist data/silver/wl-bayelemabaga.tsv --wordlist data/silver/wl-en-top10k.tsv
```

## Recommended pipeline

Run these on a machine that can reach huggingface.co.

```bash
pip install pyarrow                 # parquet downloads (avoids 429s)
pip install fasttext-wheel          # optional, only for --backend fasttext
python -m cmx_lid.ingest.kunkado --split train --out data/silver/kunkado-train.conll
python -m cmx_lid.ingest.kunkado --split test  --out data/silver/kunkado-test.conll
python -m cmx_lid.ingest.wordlist --hf djelia/bambara-mt-dataset --split all \
    --out data/silver/wl-djelia.tsv   # needs HF_TOKEN

# train both backends on the same data, compare on the Kunkado test split
python -m cmx_lid.train --conll data/silver/kunkado-train.conll \
    --wordlist data/silver/wl-bayelemabaga.tsv --wordlist data/silver/wl-en-top10k.tsv --wordlist data/silver/wl-djelia.tsv
python -m cmx_lid.train --conll data/silver/kunkado-train.conll \
    --wordlist data/silver/wl-bayelemabaga.tsv --wordlist data/silver/wl-en-top10k.tsv --wordlist data/silver/wl-djelia.tsv --backend fasttext
python -m cmx_lid.evaluate --dev data/silver/kunkado-test.conll
python -m cmx_lid.evaluate --dev data/silver/kunkado-test.conll --model models/cmx-lid-ft.ftz
python -m cmx_lid.benchmark --split test    # check nothing regressed
```

Notes:
- The Kunkado scores are on **transcribed speech**, not typed text, so treat
  them as a proxy. Kunkado also only marks French, so it says nothing about
  English.
- Gated datasets only work through the API with a token from an account that
  has been granted access: `$env:HF_TOKEN = "hf_..."`
  (huggingface.co/settings/tokens, read access is enough).
- `--split all` asks Hugging Face for every config/split and reads them all.
- Install `pyarrow` (`pip install pyarrow`). The word-list script then
  downloads each split as one parquet file instead of paging the rows API
  100 rows at a time, which is what triggers `HTTP 429 Too Many Requests`.
  Force a path with `--via parquet` or `--via rows`.
- Kunkado always uses the rows API, because its parquet files contain the
  audio (gigabytes). The script waits and retries on 429, honouring
  `Retry-After` and backing off up to 4 minutes, so a run can pause for a
  while but should finish.
- The Kunkado tag regex in `cmx_lid/ingest/kunkado.py` is a guess (brackets,
  angle brackets). Check the dataset card and adjust it after the first run.

# @crommix/lid (JavaScript / TypeScript)

Word-level language identification for Bambara with French and English
code-switching. It's a TypeScript port of the Python `cmx_lid` package and
gives identical results (checked by `npm test` on 700+ texts). It has no
dependencies and runs in Node 18+ and browsers.

```ts
import { load } from "@crommix/lid";

const lid = await load();                        // loads the bundled model (~2 MB, 410 KB gzipped)

lid.tag("n taara l'hôpital kunun");
// [["n","bam"], ["taara","bam"], ["l'","fra"], ["hôpital","fra"], ["kunun","bam"]]
lid.detect("je suis fatigué");                   // "fra"   (main language, or null)
lid.isCodeSwitched("réunion bɛ kɛ demain");      // true
lid.segments("n taara l'hôpital kunun");         // runs: bam "n taara" | fra "l'hôpital" | bam "kunun"
lid.summarize("…");                              // { dominant, proportions, codeSwitched, nWords, nSwitches }
lid.identify("…");                               // Token[]: { text, start, end, label, confidence, source }
```

Labels: `bam`, `fra`, `eng`, and `univ` (punctuation, numbers, emoji, links).
Offsets are JavaScript string offsets, so `text.slice(t.start, t.end) === t.text`,
including around emoji.

## Install

```bash
npm install @crommix/lid
```

## Loading the model

| Setup | Code |
|---|---|
| Node | `await load()` reads the bundled `model/cmx-lid.json` |
| Vite, webpack 5, Parcel | `await load()` works: the bundler emits the model file as an asset |
| Any other bundler, or a CDN | host `cmx-lid.json` yourself: `await load("/assets/cmx-lid.json")` |
| Bundle the model into your JS | `import model from "@crommix/lid/model.json"` then `new CmxLid(model)` (synchronous) |

Load once and reuse the instance: loading takes about 100–300 ms, and after
that it tags around 50k words/s.

Options (same as Python's `Config`):
`await load(undefined, { french_orthography_final: false })`.

## Updating the model

The model is trained in Python. `python -m cmx_lid.build` retrains it and
re-exports `js/model/cmx-lid.json` together with the parity fixtures. Then
run:

```bash
cd js && npm test     # builds, then checks JS == Python on every fixture
```

Loanword origin metadata (`cmx_lid.origins`) and the fastText backend are
Python-only (`pip install cmx-lid`).

## License

The code is Apache-2.0. `model/cmx-lid.json` is CC BY-SA 4.0, because it was
built from CC BY-SA 4.0 data (BAYƐLƐMABAGA and Kunkado by RobotsMali,
bambara-mt-dataset by Djelia). See NOTICE. © Crommix Mali S.A.

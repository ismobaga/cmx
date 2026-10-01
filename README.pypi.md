<p><img src="https://ai.crommixmali.com/assets/brand/logo.png" alt="cmx" height="56"></p>

# cmx-lid

Word-level language identification for **Bambara** text with **French** and
**English** code-switching. It's small (a 1.7 MB model), has no dependencies
and runs offline.

**Live demo:** [ai.crommixmali.com/lid](https://ai.crommixmali.com/lid/)

```bash
pip install cmx-lid
```

```python
import cmx_lid

cmx_lid.tag("n taara l'hôpital kunun")
# [('n', 'bam'), ('taara', 'bam'), ("l'", 'fra'), ('hôpital', 'fra'), ('kunun', 'bam')]
cmx_lid.detect("je suis fatigué")                    # 'fra'
cmx_lid.is_code_switched("réunion bɛ kɛ demain")     # True
cmx_lid.identify(text)   # Tokens with offsets, confidence and the stage that decided
```

```text
$ cmx-lid "n taara l'hôpital kunun"
[bam] n taara  [fra] l'hôpital  [bam] kunun
  -> Bambara 60%, French 40% (code-switched, 2 switches)
```

Labels: `bam`, `fra`, `eng`, and `univ` (punctuation, numbers, emoji, links).

## Labeling policy: usage, not etymology

- Integrated loanwords count as Bambara: *inchallah*, *lekɔli*, *lopitali*.
- A word written the French way is French: *l'hôpital* in "n taara l'hôpital".
- Informal spellings are handled: *be*, *bè*, *dougou*, *tche*.

## Quality (held-out data)

| Test | Words correctly labeled |
|---|---|
| Edited Bambara and French texts (BAYƐLƐMABAGA) | 97.7% |
| Bambara in informal spelling | 98.3% |
| Malian radio with French switches (Kunkado) | 97.3% (French-word F1 0.79) |

Short French words on their own inside Bambara (*la*, *de*, *donc*) are
sometimes missed. There is no test set of WhatsApp/SMS messages yet.

The same model is also available for JavaScript/TypeScript on npm as
`@crommix/lid`, and gives identical results.

## License

The code is Apache-2.0. The bundled model and lexicon are CC BY-SA 4.0,
because they were built from CC BY-SA 4.0 data: BAYƐLƐMABAGA and Kunkado
(RobotsMali) and bambara-mt-dataset (Djelia). See NOTICE for attributions.

© Crommix Mali S.A.

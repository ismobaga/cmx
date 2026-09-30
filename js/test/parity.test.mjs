// The JS port must label exactly like Python. Fixtures come from
// `python -m cmx_lid.export_js` (real, informal, code-switched and edge-case texts).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { load } from "../dist/index.js";
import { CHAR_CLASSES } from "../dist/text.js";

const fixtures = JSON.parse(await readFile(new URL("./fixtures.json", import.meta.url), "utf8"));
const classes = JSON.parse(await readFile(new URL("./charclass.json", import.meta.url), "utf8"));
const lid = await load();

test("labels, sources and confidences match Python on every fixture", () => {
  let tokens = 0;
  const diffs = [];
  for (const fx of fixtures) {
    const got = lid.identify(fx.text);
    assert.equal(got.length, fx.tokens.length, `token count differs for ${JSON.stringify(fx.text)}`);
    got.forEach((t, i) => {
      const [text, label, conf, source] = fx.tokens[i];
      tokens++;
      assert.equal(t.text, text);
      assert.equal(fx.text.slice(t.start, t.end), t.text, "offsets must slice the input");
      if (t.label !== label || t.source !== source || Math.abs(t.confidence - conf) > 2e-3) {
        diffs.push({ text: fx.text, token: text, py: [label, conf, source], js: [t.label, t.confidence, t.source] });
      }
    });
    const s = lid.summarize(got);
    assert.equal(s.dominant, fx.dominant, fx.text);
    assert.equal(s.codeSwitched, fx.code_switched, fx.text);
    assert.equal(s.nSwitches, fx.n_switches, fx.text);
  }
  assert.deepEqual(diffs.slice(0, 5), [], `${diffs.length}/${tokens} tokens differ`);
});

function mismatches(rx, ranges, skip) {
  const inside = (cp, rs) => rs.some(([a, b]) => cp >= a && cp <= b);
  let n = 0;
  const examples = [];
  for (let cp = 0; cp <= 0x10ffff; cp++) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue; // lone surrogates
    if (inside(cp, skip)) continue; // unassigned in Python's Unicode version
    if (rx.test(String.fromCodePoint(cp)) !== inside(cp, ranges)) {
      n++;
      if (examples.length < 5) examples.push(cp.toString(16));
    }
  }
  return { n, examples };
}

test("character classes match Python's regex classes", () => {
  for (const name of ["letter", "word", "digit"]) {
    const { n, examples } = mismatches(CHAR_CLASSES[name], classes[name], classes.unassigned);
    assert.equal(n, 0, `${name}: ${n} code points differ, e.g. ${examples} ` +
      `(Python Unicode ${classes.unicode_version})`);
  }
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { load, CmxLid } from "../dist/index.js";

const lid = await load();

test("tag / detect / isCodeSwitched", () => {
  assert.deepEqual(lid.tag("n taara l'hôpital, kunun"),
    [["n", "bam"], ["taara", "bam"], ["l'", "fra"], ["hôpital", "fra"], ["kunun", "bam"]]);
  assert.ok(lid.tag("a ko, n bɛ na", true).some(([w, l]) => w === "," && l === "univ"));
  assert.equal(lid.detect("n bɛ taa sugu la sini"), "bam");
  assert.equal(lid.detect("je suis fatigué aujourd'hui"), "fra");
  assert.equal(lid.detect("... 123 🙂"), null);
  assert.equal(lid.isCodeSwitched("réunion bɛ kɛ demain"), true);
  assert.equal(lid.isCodeSwitched("n bɛ taa so"), false);
});

test("segments and emoji-safe offsets", () => {
  const text = "🙂 n taara l'hôpital kunun";
  const segs = lid.segments(text);
  assert.deepEqual(segs.map((s) => [s.label, text.slice(s.start, s.end)]),
    [["bam", "n taara"], ["fra", "l'hôpital"], ["bam", "kunun"]]);
});

test("load from a parsed bundle, from a path, and config overrides", async () => {
  const path = new URL("../model/cmx-lid.json", import.meta.url);
  const bundle = JSON.parse(await readFile(path, "utf8"));
  const a = new CmxLid(bundle);
  const b = await load(path);
  const c = await load(bundle, { french_orthography_final: false });
  assert.deepEqual(a.tag("n taara l'hôpital"), b.tag("n taara l'hôpital"));
  assert.equal(c.config.french_orthography_final, false);
  assert.throws(() => new CmxLid({}), /not a cmx-lid model bundle/);
});

test("empty input", () => {
  assert.deepEqual(lid.identify(""), []);
  assert.equal(lid.summarize("").nWords, 0);
});

test("load over HTTP (the browser path)", async () => {
  const { createServer } = await import("node:http");
  const body = await readFile(new URL("../model/cmx-lid.json", import.meta.url));
  const srv = createServer((req, res) => { res.setHeader("content-type", "application/json"); res.end(body); });
  await new Promise((r) => srv.listen(0, "127.0.0.1", r));
  try {
    const remote = await load(`http://127.0.0.1:${srv.address().port}/cmx-lid.json`);
    assert.equal(remote.detect("n bɛ taa so"), "bam");
  } finally {
    srv.close();
  }
});

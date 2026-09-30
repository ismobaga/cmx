/**
 * cmx-lid: word-level language identification for Bambara with French/English
 * code-switching. Zero dependencies; runs in Node (>=18) and browsers.
 *
 * ```ts
 * import { load } from "@crommix/lid";
 * const lid = await load();                     // bundled model
 * lid.tag("n taara l'hôpital kunun");           // [["n","bam"], ..., ["hôpital","fra"], ["kunun","bam"]]
 * lid.detect("je suis fatigué");                // "fra"
 * lid.isCodeSwitched("réunion bɛ kɛ demain");   // true
 * ```
 */
import { CmxLid } from "./lid.js";
import type { Bundle, Config } from "./types.js";

export { CmxLid };
export type { Bundle, Config, Label, LangLabel, Segment, Source, Summary, Token } from "./types.js";

declare const process: { versions?: { node?: string } } | undefined;
const isNode = typeof process !== "undefined" && !!process?.versions?.node;

/** URL of the model file shipped with this package (bundlers turn it into an asset). */
export const DEFAULT_MODEL_URL = new URL("../model/cmx-lid.json", import.meta.url);

async function readJson(source: string | URL): Promise<Bundle> {
  const url = source instanceof URL ? source : /^[a-z][a-z0-9+.-]*:/i.test(source) ? new URL(source) : null;
  if (isNode && (url === null || url.protocol === "file:")) {
    // Non-literal specifier so browser bundlers don't try to resolve a Node built-in.
    const fsModule = "node:fs/promises";
    const fs = await import(/* webpackIgnore: true */ /* @vite-ignore */ fsModule);
    const data = await (fs as any).readFile(url ?? source, "utf8");
    return JSON.parse(data);
  }
  const res = await fetch(url ?? source);
  if (!res.ok) throw new Error(`could not load cmx-lid model from ${String(source)}: HTTP ${res.status}`);
  return (await res.json()) as Bundle;
}

/**
 * Load a model and return a ready identifier.
 * - no argument: the model bundled with the package (Node: read from disk; browser: fetched)
 * - a URL or path string: fetch/read that model file
 * - an already-parsed bundle object (e.g. `import model from "@crommix/lid/model.json"`)
 */
export async function load(source?: string | URL | Bundle, config: Partial<Config> = {}): Promise<CmxLid> {
  const bundle = source && typeof source === "object" && !(source instanceof URL)
    ? source
    : await readJson(source ?? DEFAULT_MODEL_URL);
  return new CmxLid(bundle, config);
}

export default load;

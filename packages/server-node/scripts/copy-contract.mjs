// Copy the shared tool contract into build/ so the published npm package is
// self-contained: build/index.js reads build/contract.json at runtime.
// Run automatically after `tsc` (see package.json "build").
import { copyFileSync, mkdirSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const here = dirname(fileURLToPath(import.meta.url)); // packages/server-node/scripts
const src = join(here, "..", "..", "..", "contract", "tools.json");
const outDir = join(here, "..", "build");
const dest = join(outDir, "contract.json");

mkdirSync(outDir, { recursive: true });
copyFileSync(src, dest);
console.error(`copied contract -> ${dest}`);

// Post-`tsc` build step: stage everything build/index.js reads at runtime, so the
// published npm package is self-contained.
//
//   build/contract.json  — the shared tool contract (canonical: /contract/tools.json)
//   build/version.json   — the package version (canonical: package.json)
//
// Both are single-sourced: nothing downstream hardcodes a copy. See package.json
// "build".
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const here = dirname(fileURLToPath(import.meta.url)); // packages/server-node/scripts
const pkgRoot = join(here, "..");
const outDir = join(pkgRoot, "build");

mkdirSync(outDir, { recursive: true });

const contractDest = join(outDir, "contract.json");
copyFileSync(join(pkgRoot, "..", "..", "contract", "tools.json"), contractDest);
console.error(`copied contract -> ${contractDest}`);

const { version } = JSON.parse(readFileSync(join(pkgRoot, "package.json"), "utf8"));
if (!version) throw new Error("package.json has no version");
const versionDest = join(outDir, "version.json");
writeFileSync(versionDest, `${JSON.stringify({ version }, null, 2)}\n`);
console.error(`wrote version ${version} -> ${versionDest}`);

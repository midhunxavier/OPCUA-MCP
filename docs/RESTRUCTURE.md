# Restructure Plan: OPC UA MCP

A phased plan to turn the repo into a clean monorepo, eliminate tool-definition
drift between the two servers, and rename the npm package. Each phase is
independently committable and ends with a green test suite.

## Decisions (locked)

1. **Keep both servers, share a tool contract.** Keep the Python and TypeScript
   runtimes, but make tool **names, descriptions, input schemas, and capability
   mapping** single-sourced so they cannot drift. The small per-tool *logic* stays
   duplicated per language.
2. **Group everything under `packages/`** — a proper monorepo layout.
3. **Rename the npm package** `opcua-mcp-npx-server` → **`opcua-mcp-server`**
   (confirmed available on npm), with short `bin` command `opcua-mcp`.
4. **uv workspace, single lockfile** for the three Python projects.

## Target end-state structure

```
opcua-mcp/
├── README.md  CONTRIBUTING.md  CHANGELOG.md  LICENSE
├── CODE_OF_CONDUCT.md  SECURITY.md
├── .gitignore                 # authoritative: owns all build/dep artifacts
├── .mcp.json                  # gitignored (local, machine-specific paths)
├── .mcp.json.example          # committed template
├── pyproject.toml             # uv WORKSPACE root          (Phase 2)
├── uv.lock                    # single lockfile            (Phase 2)
├── .github/workflows/ci.yml   # build (copies contract) + parity test
├── contract/tools.json        # SINGLE SOURCE OF TRUTH     (Phase 4)
│     (Node copies it into build/ at build time; Python reads it directly)
├── docs/{testing.md, examples.md, RESTRUCTURE.md}
├── packages/
│   ├── mock-server/           # was opcua-local-server
│   ├── server-python/         # was opcua-mcp-server
│   └── server-node/           # was opcua-mcp-npx-server
└── tests/                     # E2E + contract parity
```

## The shared contract (Phase 4 — core value)

There is exactly one source of truth, `contract/tools.json` (per-tool `name`,
`description`, `inputSchema`, `capability` = `null` | `history` | `aggregate`, plus
the capability probe node IDs). Implemented **simpler than the original copy+sync
plan**: nothing is duplicated, so the two servers cannot drift and no sync-check is
needed.

- **Node**: builds `tools/list` directly from the contract, filtered by the runtime
  capability probes (history/aggregate). `npm run build` runs
  `packages/server-node/scripts/copy-contract.mjs`, copying the contract into
  `build/contract.json` so the published npm package is self-contained.
- **Python (FastMCP)**: reads tool descriptions and the capability node IDs straight
  from `contract/tools.json` (resolved relative to the package). Input schemas stay
  signature-derived and are checked against the contract by the parity test.
- `tests/test_contract_parity.py` lists tools on both servers and asserts each
  advertises exactly the contract's applicable tools, with matching descriptions
  and parameter sets. Runs as part of the normal suite (and CI).

What stays duplicated (accepted): ~10 lines of per-tool logic per language.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 0 | Baseline & branch | ✅ done |
| 1 | Folder reorg, behavior-neutral | ✅ done |
| 2 | Python: uv workspace + real package | ✅ done |
| 3 | npm rename across all leak points | ✅ done |
| 4 | Shared contract + parity test | ✅ done |
| 5 | Docs consolidation | ✅ done |
| 6 | Final validation & PR | ✅ done |

### Phase 1 — Folder reorg (done)
- `git mv` the three projects into `packages/` (`mock-server`, `server-python`,
  `server-node`); `git mv` `TESTING.md`/`EXAMPLES.md` into `docs/`.
- Deleted the dead `server-python/main.py` stub.
- Single authoritative root `.gitignore`; removed redundant per-folder ones.
- Updated all path references: `tests/conftest.py`, `tests/test_mcp_e2e.py`,
  `.github/workflows/ci.yml`, `packages/server-node/package.json` (`repository.directory`),
  README/CONTRIBUTING/docs links and `cd` paths.
- Added `.mcp.json.example`; updated local `.mcp.json` to the new paths.
- No behavior change; npm package name and Python entry filename untouched (Phases 3/2).

### Phase 2 — Python: uv workspace + real package
- Root `pyproject.toml` with `[tool.uv.workspace] members = [...]`; single `uv.lock`.
- Rename `packages/server-python/opcua-mcp-server.py` → an importable package
  `src/opcua_mcp_server/server.py` with a `main()`; add console-script entry points.
- Fold `mock-server/main.py` into `__main__.py`; remove per-folder `uv.lock`/`.venv`.

### Phase 3 — npm rename (4 leak points)
`package.json` `name` → `opcua-mcp-server`; `bin` → `{ "opcua-mcp": ... }`; fix
`main` → `build/index.js`; `new Server({ name })` in `src/index.ts`; folder already
moved. On release: publish `opcua-mcp-server`, then `npm deprecate opcua-mcp-npx-server`.

### Phase 4 — Shared contract
See above. Add the sync script, contract, parity test, and CI sync-check.

### Phase 5 — Docs consolidation
Trim the root README to overview + quickstart + links; per-package READMEs to
package-specific content; single tool reference in `docs/examples.md`; rewrite the
CONTRIBUTING "add a tool" flow to go through `contract/tools.json`.

### Phase 6 — Final validation & PR
Full green (`uv run --no-sync pytest`, `npm run build`, parity + sync jobs); update CHANGELOG;
open PR.

## Out of scope
No security/auth changes, no new tools or behavior changes, neither server dropped.
The TS/Python internal module split is optional (pairs with Phase 4).

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
├── .github/workflows/ci.yml   # + contract-sync + parity   (Phase 4)
├── contract/tools.json        # SINGLE SOURCE OF TRUTH     (Phase 4)
├── scripts/sync-contract.mjs  # propagate contract         (Phase 4)
├── docs/{testing.md, examples.md, RESTRUCTURE.md}
├── packages/
│   ├── mock-server/           # was opcua-local-server
│   ├── server-python/         # was opcua-mcp-server
│   └── server-node/           # was opcua-mcp-npx-server
└── tests/                     # E2E + contract parity
```

## The shared contract (Phase 4 — core value)

A file at the repo root does **not** travel inside a published npm tarball or pip
wheel, so "both load the same file" needs propagation, not just a relative path.

- `contract/tools.json` is the source of truth: per-tool `name`, `description`,
  `inputSchema`, and `capability` (`null` | `history` | `aggregate`), plus the
  capability probe node IDs (`ns=0;i=11193`, `ns=0;i=2997`).
- `scripts/sync-contract.mjs` copies it into `packages/server-node/src/contract.json`
  and `packages/server-python/src/opcua_mcp_server/contract.json`. The copies are
  committed (so a fresh clone builds) but generated; CI re-runs sync and fails on
  any `git diff`.
- **TS**: `ListTools` returns `contract.tools` filtered by passed capability probes
  (`resolveJsonModule` is already on). Build copies the JSON into `build/`.
- **Python (FastMCP)**: reads descriptions + capability node IDs from the contract;
  a **parity test** asserts the FastMCP-derived schema equals the contract.
- `tests/test_contract_parity.py` loads the contract, lists tools on both servers,
  and asserts both advertise exactly the contract's tools with identical schemas.

What stays duplicated (accepted): ~10 lines of per-tool logic per language.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 0 | Baseline & branch | ✅ done |
| 1 | Folder reorg, behavior-neutral | ✅ done |
| 2 | Python: uv workspace + real package | ⬜ todo |
| 3 | npm rename across all leak points | ⬜ todo |
| 4 | Shared contract + parity test | ⬜ todo |
| 5 | Docs consolidation | ⬜ todo |
| 6 | Final validation & PR | ⬜ todo |

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
Full green (`uv run pytest`, `npm run build`, parity + sync jobs); update CHANGELOG;
open PR.

## Out of scope
No security/auth changes, no new tools or behavior changes, neither server dropped.
The TS/Python internal module split is optional (pairs with Phase 4).

# Roadmap: v0.2.0 — maintainability & first `opcua-mcp-server` release

A phased plan to turn the post-restructure repo into a maintainable open-source
project and ship the renamed package. Each phase is independently committable and
ends with a green test suite — the same working style as
[`RESTRUCTURE.md`](RESTRUCTURE.md).

## Decisions (locked)

1. **npm package name is `opcua-mcp-server`**, not `opcua-mcp`. `opcua-mcp` is free
   on npm but **already taken on PyPI by a different project with the same
   purpose**. `opcua-mcp-server` is free on *both* registries and already matches
   the Python distribution name, so one name covers both ecosystems. The short
   `opcua-mcp` command alias is kept via `bin`, so users lose no ergonomics.
2. **"Node", not "npx", is the name of the second implementation.** `npx` is a
   runner, not an implementation. `npx` survives only where it is literally the
   command being typed.
3. **Publishing is the last step.** Everything else lands first so a half-finished
   rename is never shipped.

## Registry state at time of writing

| Name | npm | PyPI |
|------|-----|------|
| `opcua-mcp-npx-server` | **published, 0.1.2** (to be deprecated) | free |
| `opcua-mcp-server` | free — *never published* | free |
| `opcua-mcp` | free | **taken by an unrelated project** |

> **Known-broken until Phase 10:** the README npm badges and the
> `npx opcua-mcp-server` quick start currently 404, because the repo was renamed
> to `opcua-mcp-server` but only `opcua-mcp-npx-server@0.1.2` was ever published.

## Baseline

`uv sync --all-packages`, `npm ci && npm run build`, `pytest` → **25 passed,
1 skipped**. The skip is `read_aggregate_opcua_node`, which is Node-only (Phase 7).

## Phases

| # | Phase | Risk | Status |
|---|-------|------|--------|
| 1 | Terminology: npx → Node | low | ✅ done |
| 2 | Version single-sourcing | low | ✅ done |
| — | Name-claim pre-release (optional) | irreversible | ⏸ awaiting decision |
| 3 | Quality gates (ruff / prettier / tsc) | low, noisy diff | ✅ done |
| 4 | Unit-test layer | low | ☐ |
| 5 | Packaging correctness + module split | **high** | ☐ |
| 6 | Python floor + CI matrix | medium | ☐ |
| 7 | Aggregate parity in Python | medium | ☐ |
| 8 | Docs consolidation | low | ☐ |
| 9 | Repo furniture | low | ✅ done |
| 10 | 0.2.0 release + publish | **irreversible** | ☐ |

### Phase 1 — Terminology: "npx" → "Node"

Behaviour-neutral. `npx` is kept only where it is the literal command
(`npx opcua-mcp-server`, `npx @modelcontextprotocol/inspector`).

- Tests: the parametrisation `["python", "npx"]` → `["python", "node"]`;
  `NPX_BUILD` → `NODE_BUILD`. The documented selector becomes **`-k "[node]"`**,
  not `-k node` — plain `node` substring-matches test *names* too (it collected
  17 of 26 tests instead of 13). Brackets pin it to the parametrisation id.
- Docs/prose: README headings, `CONTRIBUTING.md`, `docs/*.md`, package READMEs,
  CI job names, issue/PR templates.
- Config examples: the `opcua-npx` MCP server key → `opcua-node`.

### Phase 2 — Version single-sourcing

Four copies of the version existed (`src/index.ts`, `package.json`, two
`pyproject.toml`s). Now:

- **Node** reads `build/version.json`, emitted at build time by
  `scripts/prepare-build.mjs` — the same self-contained pattern already used for
  `contract.json`.
- **Python** uses `importlib.metadata.version()` with a source-tree fallback.
- Both servers now also identify as `opcua-mcp-server` over MCP; the Python
  server previously called itself `OPCUA-Control` and reported no version.
- `tests/test_version_parity.py` guards all of it: manifests in lockstep, no
  hardcoded literal in `src/index.ts`, and each running server reporting its
  manifest version in the handshake. All three guards were mutation-tested.

### Name-claim pre-release (optional, recommended)

`opcua-mcp-server` is unclaimed on both registries *today*, but `opcua-mcp` on
PyPI shows same-purpose names do get taken. Publishing a `0.2.0-rc.1` to npm and
PyPI immediately after Phase 2 reserves both names and un-breaks the README
badges, with the real `0.2.0` still landing at Phase 10.

### Phase 3 — Quality gates

Ruff (lint + format) for Python; Prettier + `tsc --noEmit` for TypeScript;
`.editorconfig`; a fast `lint` CI job parallel to `e2e`. ESLint is deliberately
deferred until after the Phase 5 module split.

> Land the config and the mechanical reformat as **separate commits** — ruff will
> flag pre-existing issues (imports after executable code, duplicate `typing`
> imports) and the reformat would otherwise bury the substantive diff.

### Phase 4 — Unit-test layer

Every test today needs a live mock server, a prior `npm run build`, and a 6s
history warm-up. Add `tests/unit/` (splitting the existing suite into
`tests/e2e/`) covering the pure logic that has actually broken before: `toDate` /
`_parse_iso_datetime` ISO-8601 handling, boolean/value coercion, contract loading
and capability gating. Node uses the built-in `node:test` — no new dependencies.

### Phase 5 — Packaging correctness *(highest risk, highest payoff)*

- **5c first** — artifact smoke tests in CI: `npm pack` → install the tarball →
  run the bin; `uv build` → install the wheel into a clean venv **outside** the
  repo → import and list tools. The `FileNotFoundError` fixed in the changelog was
  invisible to the current suite, which runs from the source tree.
- **5a** — Python flat module → real `src/opcua_mcp_server/` package. This removes
  the `force-include` hack that installs *two top-level files* into `site-packages`.
- **5b** — split the 805-line `src/index.ts` into `contract.ts` / `client.ts` /
  `tools/*.ts`.

### Phase 6 — Python floor + CI matrix

Lower `requires-python` from `>=3.13` to `>=3.10` (no 3.11+ syntax is used; the
newest construct is `str | None`) and matrix CI over Python 3.10/3.13 and Node
18/20/22 — `engines` claims `>=18` but CI has only ever tested 20. Verify by
running the matrix, not by grepping.

### Phase 7 — Aggregate parity in Python

`read_aggregate_opcua_node` is Node-only, so the README's "two interchangeable
implementations" claim is false. Either implement it in Python with the same
capability gating used by `read_history_opcua_node`, or drop the parity claim and
document the gap. Implementing is preferred.

### Phase 8 — Docs consolidation

Archive `RESTRUCTURE.md` (a finished internal plan, now inaccurate — it marks
Phase 2 done when the Python package was never created); trim the README of
dependency lists that restate the manifests; collapse the three competing MCP
config examples into one; move `Media/ss.png` → `docs/assets/` and
`packages/mock-server/client_example.py` → `examples/`; add
`docs/architecture.md`.

### Phase 9 — Repo furniture

`dependabot.yml` (npm + pip + github-actions), `CODEOWNERS`,
`.github/ISSUE_TEMPLATE/config.yml`.

### Phase 10 — 0.2.0 release + publish

1. Cut `[Unreleased]` → `[0.2.0]` in the changelog; add the missing comparison
   links.
2. Add tag-triggered `publish-npm.yml` (with `--provenance`) and
   `publish-pypi.yml` (trusted publishing), retiring the manual publish that could
   silently skip `prepare-build.mjs`.
3. Maintainer steps: configure npm OIDC / PyPI trusted publisher, push `v0.2.0`.
4. `npm deprecate opcua-mcp-npx-server "Renamed to opcua-mcp-server — …"`.
   **Do not unpublish** — it breaks existing installs and npm blocks it after 72h.

## PR sequencing

| PR | Phases |
|----|--------|
| 1 | 1 + 2 — mechanical, prerequisites for publishing |
| 2 | 3 + 9 — config-only, shares the CI edit |
| 3 | 4 + 5c — test infrastructure |
| 4 | 5a + 5b — the refactor, protected by PR 3 |
| 5 | 6 + 7 — compatibility and parity |
| 6 | 8 — docs, once the structure is final |
| 7 | 10 — release |

## Out of scope

No new tools beyond closing the aggregate gap; no OPC UA security-model change
(`SecurityPolicy.None` stays the default, though making it configurable is a
strong candidate for 0.3.0); neither runtime is dropped.

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-09-09

First release published as **`opcua-mcp-server`**. The previously published
`opcua-mcp-npx-server` is deprecated in favour of this name.

### Changed
- Renamed the npm package `opcua-mcp-npx-server` → `opcua-mcp-server` (the old
  name will be deprecated on npm with a pointer to the new one).
- The Python server now identifies itself over MCP as `opcua-mcp-server` instead
  of `OPCUA-Control`, matching the Node server — both runtimes are the same
  product and now say so. Purely informational in the MCP handshake; it does not
  affect the server key in your client config.
- The Python server now reports a real version in the MCP handshake (it
  previously reported none).
- Both servers now single-source their version: Node from `package.json` (staged
  into `build/version.json` at build time), Python from its installed
  distribution metadata. The version literal in `src/index.ts` is gone, and
  `tests/test_version_parity.py` fails the build if the manifests drift apart or
  a hardcoded version is reintroduced.
- Documentation and code now call the second implementation the **Node** server
  rather than the "npx" server; `npx` refers only to the command. The pytest
  selector is now `-k "[node]"` / `-k "[python]"` — plain `-k node` would also
  match test names like `test_read_opcua_node`.
- Restructured the repository into a `packages/` monorepo layout with a single
  uv workspace.

### Added
- `docs/architecture.md` — how the two runtimes, the shared contract and the
  capability gating fit together, plus the three invariants that are easy to
  break (stdout is the transport, nothing hardcodes a version, the published
  artifact is what users get).
- `read_aggregate_opcua_node` is now implemented on the **Python** server too,
  with the same capability gating and the same error wording as the Node server.
  It was previously Node-only, which made the README's "two interchangeable
  implementations" claim untrue.
- **Python 3.10+ is now supported** (was 3.13+). Nothing in the codebase needed
  3.11 or newer; the floor simply excluded most installed Pythons, including the
  3.9–3.11 common in industrial environments. Verified by installing and driving
  the server on 3.10, not by inspection.
- CI now runs the end-to-end suite across the versions the manifests actually
  claim — Python 3.10/3.13 and Node 18/20/22 — instead of only Python 3.13 and
  Node 20.
- The Node server is split from one 857-line `index.ts` into `config`,
  `contract`, `dates`, `connection` (client/session lifecycle plus the capability
  probes), `tools` (the tool implementations and dispatch) and `index` (MCP
  wiring and the entry point). Adding a tool now touches `tools.ts` and the
  contract, nothing else.
- The Python server is now a real package (`src/opcua_mcp_server/`) split into
  `config`, `contract`, `datetimes`, `capabilities` and `server`, instead of a
  single 505-line flat module. The wheel now installs exactly one top-level name;
  it previously dropped two files (`opcua_mcp_server.py` and
  `opcua_mcp_server_contract.json`) directly into `site-packages`, which is why
  the bundled contract needed a namespaced filename to avoid colliding with other
  distributions. The contract now ships inside the package.
- Unit-test tier (`tests/unit/` and `packages/server-node/test/`) covering the
  pure logic — ISO-8601 parsing, contract invariants, version manifests — with no
  OPC UA server and no MCP transport. 42 Python unit tests run in ~0.2s against
  ~50s for the end-to-end suite. The Node tests use the built-in `node:test`
  runner, so the package gains no dependency.
- The Node server module is now importable without starting a server: the entry
  point is guarded, and `toDate`/`OPCUAMCPServer` are exported for testing. The
  guard resolves symlinks, because `npx` invokes the `node_modules/.bin` shim and
  a naive `import.meta.url === process.argv[1]` check would never match.
- Artifact smoke tests (`tests/smoke/`): build the npm tarball and the Python
  wheel, install each into an isolated location, and drive the installed entry
  point over MCP from a working directory outside the repo. Run as their own CI
  job; deselected from the default suite with `-m "not smoke"`.
- Lint, format and typecheck gates: ruff for Python, Prettier + `tsc --noEmit`
  for TypeScript, wired into a fast `lint` CI job that runs alongside the
  end-to-end suite. Plus `.editorconfig`, Dependabot, `CODEOWNERS` and an issue
  template chooser.
- `read_history_opcua_node` tool — read historical (timestamped) values for a node.
- `read_aggregate_opcua_node` tool — server-side aggregate reads, exposed only
  when the server advertises aggregate function support (capability gating).
- End-to-end test suite (`tests/`) driving both the Python and Node servers over
  stdio against the mock OPC UA server.
- `CONTRIBUTING.md`, `TESTING.md`, and `EXAMPLES.md` documentation.
- `LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and CI workflow.

### Known issues
- Neither server's aggregate *happy path* has end-to-end coverage: the bundled
  mock OPC UA server advertises no aggregate functions, so the tool is gated off
  in the suite on both runtimes. The name/node-ID mapping and the validation
  messages are unit-tested; the read itself is not. Giving the mock aggregate
  support would close this.

### Fixed
- **The Node server no longer silently returns data for the wrong day.**
  `toDate` relied on V8's `Date` parser, which rolls an out-of-range day over
  into the next month, so a history read for `2026-02-30` quietly returned
  `2026-03-02` data instead of failing. It now validates the calendar date
  arithmetically — which also restores parity with the Python server, whose
  `datetime.fromisoformat` always rejected these.
- **The Python server no longer breaks on a fresh install.** Its `mcp[cli]>=1.9.1`
  dependency had no upper bound, so a clean `pip`/`uvx` install resolved mcp 2.x,
  where `FastMCP` was renamed to `MCPServer` — the server then died on import with
  `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. Pinned to `<2`.
  The committed `uv.lock` pinned 1.x, so every existing test and CI run passed
  while installs from the published package would have failed; the new artifact
  smoke tests are what surfaced it.
- Boolean and value handling across the server and clients.
- OPC UA method calls.
- Python `read_history_opcua_node` now takes `start_time`/`end_time` as ISO-8601
  strings and rejects malformed input with the same message as the Node server
  (`Invalid date/time: … Use ISO 8601, e.g. 2026-04-23T17:40:00Z`).
- The shared tool contract is now bundled inside the Python wheel, so a
  pip/uvx-installed `opcua-mcp-server` no longer fails on import with
  `FileNotFoundError` when run outside the repo layout.

## [0.1.2] — published as `opcua-mcp-npx-server`

Initial published versions on npm, under the old name `opcua-mcp-npx-server`,
with the seven core OPC UA tools (read, write, browse, read/write multiple, call
method, get all variables). This is the only name published to date; the rename
to `opcua-mcp-server` ships with the next release.

[Unreleased]: https://github.com/midhunxavier/OPCUA-MCP/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/midhunxavier/OPCUA-MCP/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/midhunxavier/OPCUA-MCP/releases/tag/v0.1.2

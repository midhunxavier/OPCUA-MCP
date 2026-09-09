# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- `read_history_opcua_node` tool — read historical (timestamped) values for a node.
- `read_aggregate_opcua_node` tool — server-side aggregate reads, exposed only
  when the server advertises aggregate function support (capability gating).
- End-to-end test suite (`tests/`) driving both the Python and Node servers over
  stdio against the mock OPC UA server.
- `CONTRIBUTING.md`, `TESTING.md`, and `EXAMPLES.md` documentation.
- `LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and CI workflow.

### Fixed
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

[Unreleased]: https://github.com/midhunxavier/OPCUA-MCP/compare/main...HEAD

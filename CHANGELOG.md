# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `read_history_opcua_node` tool — read historical (timestamped) values for a node.
- `read_aggregate_opcua_node` tool — server-side aggregate reads, exposed only
  when the server advertises aggregate function support (capability gating).
- End-to-end test suite (`tests/`) driving both the Python and npx servers over
  stdio against the mock OPC UA server.
- `CONTRIBUTING.md`, `TESTING.md`, and `EXAMPLES.md` documentation.
- `LICENSE`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and CI workflow.

### Fixed
- Boolean and value handling across the server and clients.
- OPC UA method calls.

## [0.1.2] — npx server

Initial published versions of `opcua-mcp-npx-server` on npm with the seven core
OPC UA tools (read, write, browse, read/write multiple, call method, get all
variables).

[Unreleased]: https://github.com/midhunxavier/OPCUA-MCP/compare/main...HEAD

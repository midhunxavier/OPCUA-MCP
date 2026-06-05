# Contributing to OPC UA MCP

Thanks for your interest in contributing! This repo provides **two MCP servers**
(Python and TypeScript/npx) that bridge AI assistants to OPC UA servers, plus a
**mock industrial OPC UA server** for local development and testing.

- **[docs/testing.md](docs/testing.md)** — how to test (automated suite, MCP Inspector, AI agents)
- **[docs/examples.md](docs/examples.md)** — per-tool inputs/outputs and node-ID reference

## Repository layout

| Path | What it is |
|------|------------|
| `packages/mock-server/` | Mock "Industrial Control System" OPC UA server (the simulated PLC/sensors) |
| `packages/server-python/` | **Python** MCP server (FastMCP + `opcua`/FreeOpcUa) |
| `packages/server-node/` | **npx** MCP server (TypeScript + `@modelcontextprotocol/sdk` + `node-opcua`) |
| `tests/` | End-to-end pytest suite driving both servers via the `mcp` SDK |
| `docs/` | Usage and testing docs (`examples.md`, `testing.md`) |

```
AI assistant / MCP client  ──stdio──►  MCP server (Python OR npx)  ──OPC UA/TCP──►  mock server :4840
```

The two MCP servers share a single tool contract ([`contract/tools.json`](contract/tools.json)): the Node server builds its `tools/list` from it and the Python server reads descriptions and capability node IDs from it, so they cannot drift (`tests/test_contract_parity.py` enforces this).

## Prerequisites

- **Python 3.13+** and [`uv`](https://docs.astral.sh/uv/)
- **Node.js 18+** and **npm**
- No OPC UA broker needed — the mock server is included.

## Local development

Start the mock server first (it's the data source for everything else):

```bash
uv sync --all-packages          # one-time: set up the workspace env
uv run --no-sync opcua-mock-server
# listens on opc.tcp://0.0.0.0:4840/freeopcua/server/  (history enabled)
```

### Python MCP server
```bash
OPCUA_SERVER_URL=opc.tcp://localhost:4840/freeopcua/server/ \
  uv run --no-sync opcua-mcp-server
```

### npx MCP server
```bash
cd packages/server-node
npm install
npm run build        # compiles src/index.ts -> build/index.js
OPCUA_SERVER_URL=opc.tcp://localhost:4840/freeopcua/server/ node build/index.js
```

Both servers read the endpoint from `OPCUA_SERVER_URL` (default
`opc.tcp://localhost:4840`). They speak MCP over **stdio**, so keep `stdout`
clean — write all logs to `stderr`.

## Running the tests

```bash
uv sync --all-packages              # one-time workspace setup
cd tests && uv run --no-sync pytest -v   # both servers
```

See [tests/README.md](tests/README.md) for details and selectors
(`-k python` / `-k npx`). For manual testing with the MCP Inspector or an AI
agent, see **[docs/testing.md](docs/testing.md)**.

## Adding a new MCP tool

The tool surface is defined once in [`contract/tools.json`](contract/tools.json); both servers derive from it, and `tests/test_contract_parity.py` fails if they diverge. To add a tool `foo`:

1. **Contract** (`contract/tools.json`): add an entry under `tools` with its `name`, `description`, `inputSchema` (JSON Schema), and `capability` (`null`, or `"history"`/`"aggregate"` if it depends on a server capability).
2. **Node** (`packages/server-node/src/index.ts`): add a `case "foo"` to the `CallToolRequestSchema` switch and implement the handler. You do **not** edit `tools/list` — it is generated from the contract. Run `npm run build` (this also copies the contract into `build/`).
3. **Python** (`packages/server-python/opcua_mcp_server.py`): add a function decorated with `@mcp.tool(description=_DESC["foo"])`, with typed args (FastMCP derives the input schema from them — keep it matching the contract) and `ctx: Context`. For a capability-gated tool, register it conditionally like `read_history_opcua_node`.
4. **Test**: add an end-to-end test in `tests/test_mcp_e2e.py` (it runs against both servers). The contract-parity test will automatically check that both servers advertise the new tool with the contract's description and parameters.
5. **Document it** in `docs/examples.md` (the central per-tool reference).

## Code style

- **Python**: follow the surrounding style; type-hint tool signatures (FastMCP
  derives the schema from them). Avoid `print()` to `stdout` — use
  `print(..., file=sys.stderr)`.
- **TypeScript**: `npm run build` must pass (`tsc`). Don't write to `stdout`
  except via the MCP transport; the server already routes stray `console.log` to
  `stderr`.
- Convert/validate inputs explicitly (e.g. date strings → `Date`) and return
  clear error messages.

## Commit & PR conventions

- Branch off `main`; keep commits focused with descriptive messages.
- Run the suite (`uv sync --all-packages`, then `cd tests && uv run --no-sync pytest`) before opening a PR.
- Reference related issues/PRs (e.g. "Fixes #1").
- If a change was AI-assisted, keep the `Co-Authored-By:` trailer.
- PRs from forks: enable **"Allow edits by maintainers"** so reviewers can rebase.

## Security note

The servers connect with `SecurityPolicy.None` / `MessageSecurityMode.None` for
local development. Do **not** use this configuration against production OPC UA
systems — add certificate-based auth, encryption, and input validation first.

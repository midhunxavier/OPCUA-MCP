# OPC UA MCP — End-to-End Test Suite

Drives the **actual** MCP servers (Python and npx) over stdio with the official
`mcp` client SDK, against the mock industrial OPC UA server. Every test runs
against **both** server implementations.

## What it covers

| Test | What it verifies |
|------|------------------|
| `test_lists_core_tools` | All 7 core tools are advertised |
| `test_history_tool_exposed_when_supported` | History tool appears because the mock enables history |
| `test_aggregate_tool_hidden_when_unsupported` | Aggregate tool is **hidden** (mock advertises no aggregate functions) — capability gating |
| `test_aggregate_tool_exposed_when_supported` | Aggregate tool **appears** against the aggregate-capable mock |
| `test_aggregate_average_values_are_correct` | `Average` over a known ramp advances by exactly one interval per bucket |
| `test_aggregate_default_end_time_is_utc` | Omitting `end_time` does not overshoot the window on a non-UTC host (#24) |
| `test_aggregate_rejects_unknown_function` | An unsupported aggregate name is rejected, listing what the server offers |
| `test_read_single_node` | `read_opcua_node` returns a value |
| `test_read_multiple_nodes` | `read_multiple_opcua_nodes` returns all requested nodes |
| `test_get_all_variables` | `get_all_variables` discovers the address space |
| `test_browse_children` | `browse_opcua_node_children` lists the four folders |
| `test_write_numeric_node` | Writing a `Double` actuator succeeds |
| `test_write_boolean_node` | Writing a `Boolean` node with `"true"` succeeds (bool-handling regression) |
| `test_call_method_start_then_stop` | `call_opcua_method` drives `StartProduction`/`StopProduction` and `SystemMode` reacts |
| `test_read_history` | The history tool (`read_history_opcua_node`) returns timestamped records |

Both servers expose the history tool under the same name, `read_history_opcua_node`,
and only when the server advertises `AccessHistoryDataCapability`.

## Mock servers

Two are used, on purpose:

| Mock | Port | Role |
|------|------|------|
| `packages/mock-server` (python-opcua) | 4840 | Industrial address space, history, methods. Advertises **no** aggregate functions — this is what makes the capability-gating assertions meaningful. |
| `packages/mock-server-aggregate` (node-opcua) | 4841 | Advertises aggregate functions and genuinely implements `ReadProcessedDetails`. Ramps `Temperature` (`ns=1;i=1001`) by +1.0/second so aggregates are verifiable arithmetically. |

The main mock cannot serve aggregates even in principle: python-opcua answers
`ReadProcessedDetails` with `BadNotImplemented`.

## Prerequisites

- `uv`, `node` (>=18), `npm`
- Set up the workspace once (from the repo root): `uv sync --all-packages`
- Build the npx server once: `cd packages/server-node && npm install && npm run build`
  (npx tests are **skipped** if `build/index.js` is missing).
- Install the aggregate mock once: `cd packages/mock-server-aggregate && npm install`
  (aggregate tests are **skipped** if its `node_modules` is missing).

## Running

```bash
cd tests
uv run --no-sync pytest -v
```

The suite reuses mock OPC UA servers already listening on `:4840` and `:4841`; if
none is running it starts them for the session (and waits a few seconds for
history to accumulate). To force specific endpoints:

```bash
OPCUA_SERVER_URL="opc.tcp://localhost:4840/freeopcua/server/" uv run --no-sync pytest -v
OPCUA_AGGREGATE_SERVER_URL="opc.tcp://localhost:4841/UA/Aggregate" uv run --no-sync pytest -v
```

Select a single implementation:

```bash
uv run --no-sync pytest -v -k python
uv run --no-sync pytest -v -k npx
```

## Notes

- The mock server's method callbacks update internal state; OPC UA node values
  are propagated by its 1 Hz simulation loop, so tests poll (see
  `wait_for_node_value`) rather than reading immediately after a method call.
- Writes to sensor/actuator nodes may be overwritten within ~1s by the
  simulation loop; only the command variables (`StartProductionCommand`, …) and
  methods persist.

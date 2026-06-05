# Testing the OPC UA MCP Servers

Three ways to test, from fully automated to fully interactive:

1. [Automated end-to-end suite](#1-automated-end-to-end-suite) (`pytest`)
2. [MCP Inspector](#2-mcp-inspector) — point-and-click or one-line CLI
3. [AI agents](#3-ai-agents) — Claude Code, Claude Desktop, Cursor

> **All three need the mock OPC UA server running first** — it is the simulated
> device the MCP servers talk to.
>
> ```bash
> uv sync --all-packages            # one-time, from the repo root
> uv run --no-sync opcua-mock-server
> # opc.tcp://localhost:4840/freeopcua/server/  (history enabled on all variables)
> ```
>
> Build the npx server once: `cd packages/server-node && npm install && npm run build`.

A handy node-ID reference and per-tool examples live in [examples.md](examples.md).
Common nodes: Temperature `ns=2;i=3`, PumpEnabled `ns=2;i=12`, ValvePosition
`ns=2;i=13`, SystemMode `ns=2;i=19`, Methods folder `ns=2;i=27`, StartProduction
`ns=2;i=28`.

---

## 1. Automated end-to-end suite

Drives **both** servers over stdio with the official `mcp` client SDK and asserts
on real responses. 22 tests (11 cases × Python + npx).

```bash
uv sync --all-packages         # one-time, from the repo root
cd tests
uv run --no-sync pytest -v
uv run --no-sync pytest -v -k python     # only the Python server
uv run --no-sync pytest -v -k npx        # only the npx server
```

The suite reuses a mock server already on `:4840`, or starts its own. See
[../tests/README.md](../tests/README.md) for the full matrix.

---

## 2. MCP Inspector

[`@modelcontextprotocol/inspector`](https://github.com/modelcontextprotocol/inspector)
is the standard tool for exercising an MCP server by hand.

### UI mode (interactive)

```bash
# npx server
OPCUA_SERVER_URL=opc.tcp://localhost:4840/freeopcua/server/ \
  npx @modelcontextprotocol/inspector node packages/server-node/build/index.js

# Python server
OPCUA_SERVER_URL=opc.tcp://localhost:4840/freeopcua/server/ \
  npx @modelcontextprotocol/inspector uv --directory packages/server-python run opcua-mcp-server
```

It prints a `http://localhost:6274/?...` URL. In the browser:

1. Click **Connect** (status should turn green).
2. Open the **Tools** tab → **List Tools**.
   - Seeing **`read_history_opcua_node`** confirms the server detected history
     support on the mock and exposed the tool.
3. Select a tool, fill the form, click **Run Tool**, read the result pane.

Things to try:

| Tool | Arguments | Expected |
|------|-----------|----------|
| `read_opcua_node` | `node_id` = `ns=2;i=3` | `Node ns=2;i=3 value: 26.x` |
| `get_all_variables` | *(none)* | `Found 22 variables: …` |
| `read_history_opcua_node` | `node_id` = `ns=2;i=3`, `num_values` = `5` | array of 5 timestamped records, status `Good` |
| `read_history_opcua_node` | `node_id` = `ns=2;i=3`, `start_time` = `2026-01-01T00:00:00Z` | records within the window |
| `read_history_opcua_node` | `node_id` = `ns=2;i=3`, `start_time` = `nope` | clear error: *Use ISO 8601…* |
| `write_opcua_node` | `node_id` = `ns=2;i=13`, `value` = `80` | `Successfully wrote 80…` |
| `call_opcua_method` | `object_node_id` = `ns=2;i=27`, `method_node_id` = `ns=2;i=28`, `arguments` = `["60"]` | `…Result: true` (SystemMode → AUTO within ~1s) |

### CLI mode (scriptable, no browser)

```bash
URL=opc.tcp://localhost:4840/freeopcua/server/
BIN="npx -y @modelcontextprotocol/inspector --cli node packages/server-node/build/index.js -e OPCUA_SERVER_URL=$URL"

# list tools
$BIN --method tools/list

# read history (note: quote node IDs because ';' is a shell separator)
$BIN --method tools/call --tool-name read_history_opcua_node \
     --tool-arg 'node_id=ns=2;i=3' --tool-arg 'num_values=5'

# call a method
$BIN --method tools/call --tool-name call_opcua_method \
     --tool-arg 'object_node_id=ns=2;i=27' --tool-arg 'method_node_id=ns=2;i=28' \
     --tool-arg 'arguments=["60"]'
```

For the Python server, swap the command for
`uv --directory packages/server-python run opcua-mcp-server`.

---

## 3. AI agents

The end goal: an assistant calls these tools from natural language.

### Claude Code

Register both servers at **project scope** (writes `.mcp.json` in the repo root):

```bash
ROOT=$(pwd)
URL=opc.tcp://localhost:4840/freeopcua/server/
claude mcp add opcua-python -s project -e OPCUA_SERVER_URL=$URL \
  -- uv --directory "$ROOT/packages/server-python" run opcua-mcp-server
claude mcp add opcua-npx -s project -e OPCUA_SERVER_URL=$URL \
  -- node "$ROOT/packages/server-node/build/index.js"
```

Then, in a **new** Claude Code session started in this directory:

1. Approve `opcua-python` / `opcua-npx` when prompted (project servers require
   one-time approval). You can also manage them with the `/mcp` command.
2. Run `/mcp` to confirm both are **connected** and list their tools.
3. Ask away — example prompts:
   - *"List the OPC UA tools you have available."*
   - *"Read the current temperature from the OPC UA server."*
   - *"Show me the last 5 temperature history readings."* → `read_history_opcua_node`
   - *"Give me a full inventory of all variables on the server."*
   - *"Start production at 60 units/hour, check the system mode, then stop it."*
   - *"Use the opcua-npx server to read node ns=2;i=4 history between 11:00 and 12:00 UTC today."*

> Both servers expose the same tool names (namespaced `opcua-python` /
> `opcua-npx`); name a server in your prompt to target one specifically.

### Claude Desktop

Add to `claude_desktop_config.json`
(`~/Library/Application Support/Claude/` on macOS) and restart the app:

```json
{
  "mcpServers": {
    "opcua-npx": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/OPCUA-MCP/packages/server-node/build/index.js"],
      "env": { "OPCUA_SERVER_URL": "opc.tcp://localhost:4840/freeopcua/server/" }
    }
  }
}
```

### Cursor

Add the same `mcpServers` block to your Cursor MCP settings (Settings → MCP), then
ask Cursor's assistant the prompts above.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| **List Tools is empty or errors** | Mock server not running → `uv run --no-sync opcua-mock-server` |
| **`read_history_opcua_node` not listed** | Connected to a server without history, or wrong `OPCUA_SERVER_URL` |
| **`read_aggregate_opcua_node` not listed** | Expected — the bundled mock advertises no aggregate functions, so the tool is correctly hidden |
| **`Address already in use` on :4840** | A mock server is already running; reuse it, or `lsof -tiTCP:4840 -sTCP:LISTEN \| xargs kill` |
| **Project MCP servers `⏸ Pending approval`** | Normal — approve them in a new `claude` session or via `/mcp` |
| **Values "snap back" after a write** | Expected — the mock republishes sensor/actuator state every ~1s; use command variables/methods for lasting changes |
| **Node value lags after a method call** | The mock propagates method effects via its 1 Hz loop; re-read after ~1s |

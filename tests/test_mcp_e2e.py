"""End-to-end tests for the OPC UA MCP servers.

Each test runs against BOTH the Python and the npx MCP server (parameterised via
the ``mcp_session`` fixture), driving them over stdio with the official ``mcp``
client SDK, against the mock industrial OPC UA server.

Run:
    cd tests && uv run pytest -v
    # only one implementation:
    cd tests && uv run pytest -v -k python
    cd tests && uv run pytest -v -k npx
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import ROOT

# --- Stable node IDs in the mock server's address space (namespace 2) ----------
# Sensors / actuators / status keep fixed identifiers; method identifiers below
# depend on the method argument nodes and are validated dynamically in the
# call-method test rather than hard-trusted.
NODE = {
    "Temperature": "ns=2;i=3",
    "Pressure": "ns=2;i=4",
    "MotorSpeed": "ns=2;i=10",
    "PumpEnabled": "ns=2;i=12",  # Boolean actuator
    "ValvePosition": "ns=2;i=13",  # Double actuator
    "SystemMode": "ns=2;i=19",
    "ProductionRate": "ns=2;i=21",
    "StartProductionCommand": "ns=2;i=23",  # Double command variable
    "StopProductionCommand": "ns=2;i=24",  # Boolean command variable
    "IndustrialControlSystem": "ns=2;i=1",
    "Methods": "ns=2;i=27",
}

CORE_TOOLS = {
    "read_opcua_node",
    "write_opcua_node",
    "browse_opcua_node_children",
    "read_multiple_opcua_nodes",
    "write_multiple_opcua_nodes",
    "call_opcua_method",
    "get_all_variables",
}

# Both implementations expose the history tool under the same name.
HISTORY_TOOL = {
    "python": "read_history_opcua_node",
    "npx": "read_history_opcua_node",
}

NPX_BUILD = ROOT / "packages" / "server-node" / "build" / "index.js"


def _server_params(impl: str, url: str) -> StdioServerParameters:
    env = {**os.environ, "OPCUA_SERVER_URL": url}
    if impl == "python":
        return StdioServerParameters(
            command="uv",
            args=["--directory", str(ROOT), "run", "--no-sync", "opcua-mcp-server"],
            env=env,
        )
    if impl == "npx":
        return StdioServerParameters(command="node", args=[str(NPX_BUILD)], env=env)
    raise ValueError(impl)


@pytest.fixture(params=["python", "npx"])
def server(request, opcua_server):
    """The ``(impl_name, StdioServerParameters)`` for each server implementation.

    This is a *sync* fixture on purpose: the stdio/anyio client context is opened
    and closed inside each test's own task (via ``connect`` below) so that anyio
    cancel scopes are not entered and exited across different tasks.
    """
    impl = request.param
    if impl == "npx" and not NPX_BUILD.exists():
        pytest.skip("npx server not built — run `npm install && npm run build` in packages/server-node")
    return impl, _server_params(impl, opcua_server)


@asynccontextmanager
async def connect(params: StdioServerParameters):
    """Open an initialised MCP ClientSession over stdio."""
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


# --- helpers -------------------------------------------------------------------

def text_of(result) -> str:
    """Concatenate all text content blocks of a CallToolResult."""
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


async def tool_names(session) -> set[str]:
    res = await session.list_tools()
    return {t.name for t in res.tools}


async def wait_for_node_value(session, node_id: str, expected: str, attempts: int = 8, delay: float = 1.0) -> str:
    """Poll a node until its value contains ``expected``.

    The mock server's method callbacks mutate internal state; the OPC UA node
    values are propagated by the 1 Hz simulation loop, so there is up to ~1s of
    lag between calling a method and seeing the node change.
    """
    text = ""
    for _ in range(attempts):
        result = await session.call_tool("read_opcua_node", {"node_id": node_id})
        text = text_of(result)
        if expected in text:
            return text
        await asyncio.sleep(delay)
    return text


# --- tests ---------------------------------------------------------------------

async def test_lists_core_tools(server):
    impl, params = server
    async with connect(params) as session:
        names = await tool_names(session)
    assert CORE_TOOLS <= names, f"{impl}: missing core tools: {CORE_TOOLS - names}"


async def test_history_tool_exposed_when_supported(server):
    """The mock server enables history, so each server should expose its history tool."""
    impl, params = server
    async with connect(params) as session:
        names = await tool_names(session)
    assert HISTORY_TOOL[impl] in names


async def test_aggregate_tool_hidden_when_unsupported(server):
    """The mock server advertises no aggregate functions, so the npx aggregate
    tool must NOT be exposed (capability gating)."""
    impl, params = server
    async with connect(params) as session:
        names = await tool_names(session)
    assert "read_aggregate_opcua_node" not in names


async def test_aggregate_direct_call_errors_cleanly(server):
    """Calling read_aggregate_opcua_node directly (no prior tools/list) must not
    crash or wrongly report 'Invalid aggregate function' due to an empty cache —
    it should recompute support on demand and return a clear message. npx-only."""
    impl, params = server
    if impl != "npx":
        pytest.skip("aggregate tool is npx-only")
    async with connect(params) as session:
        result = await session.call_tool(
            "read_aggregate_opcua_node",
            {
                "node_id": NODE["Temperature"],
                "start_time": "2026-01-01T00:00:00Z",
                "aggregate_function": "Average",
                "processing_interval": 60000,
            },
        )
    # The mock advertises no aggregate functions, so we expect a clear,
    # aggregate-related error rather than a crash or a misleading message.
    assert "aggregate" in text_of(result).lower()


async def test_read_single_node(server):
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool("read_opcua_node", {"node_id": NODE["Temperature"]})
    assert not result.isError
    text = text_of(result)
    assert NODE["Temperature"] in text
    assert "value" in text.lower()


async def test_read_multiple_nodes(server):
    impl, params = server
    ids = [NODE["Temperature"], NODE["Pressure"], NODE["PumpEnabled"]]
    async with connect(params) as session:
        result = await session.call_tool("read_multiple_opcua_nodes", {"node_ids": ids})
    assert not result.isError
    text = text_of(result)
    for nid in ids:
        assert nid in text


async def test_get_all_variables(server):
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool("get_all_variables", {})
    assert not result.isError
    text = text_of(result)
    assert "Found" in text and "variables" in text
    assert "Temperature" in text


async def test_browse_children(server):
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool(
            "browse_opcua_node_children", {"node_id": NODE["IndustrialControlSystem"]}
        )
    assert not result.isError
    text = text_of(result)
    for folder in ("Sensors", "Actuators", "SystemStatus", "Methods"):
        assert folder in text


async def test_write_numeric_node(server):
    """Writing a Double actuator should succeed (the sim may overwrite it later)."""
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool(
            "write_opcua_node", {"node_id": NODE["ValvePosition"], "value": "80"}
        )
    assert not result.isError, text_of(result)
    assert "Success" in text_of(result) or "wrote" in text_of(result).lower()


async def test_write_boolean_node(server):
    """Writing a Boolean node with 'true' must succeed (regression: bool handling)."""
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool(
            "write_opcua_node", {"node_id": NODE["StopProductionCommand"], "value": "true"}
        )
    assert not result.isError, text_of(result)
    assert "Success" in text_of(result) or "wrote" in text_of(result).lower()


async def test_call_method_start_then_stop(server):
    """Drive production via the StartProduction / StopProduction methods and check
    that SystemMode reacts. Exercises call_opcua_method + the method callbacks."""
    impl, params = server
    async with connect(params) as session:
        methods = _discover_methods(await _browse_json(session, NODE["Methods"]))
        assert "StartProduction" in methods and "StopProduction" in methods

        start = await session.call_tool(
            "call_opcua_method",
            {
                "object_node_id": NODE["Methods"],
                "method_node_id": methods["StartProduction"],
                "arguments": ["60"],
            },
        )
        assert not start.isError, text_of(start)

        mode = await wait_for_node_value(session, NODE["SystemMode"], "AUTO")
        assert "AUTO" in mode

        stop = await session.call_tool(
            "call_opcua_method",
            {"object_node_id": NODE["Methods"], "method_node_id": methods["StopProduction"]},
        )
        assert not stop.isError, text_of(stop)

        mode2 = await wait_for_node_value(session, NODE["SystemMode"], "MANUAL")
        assert "MANUAL" in mode2


async def test_read_history(server):
    """Read recent history for the Temperature sensor and assert we get records."""
    impl, params = server
    async with connect(params) as session:
        result = await session.call_tool(
            HISTORY_TOOL[impl], {"node_id": NODE["Temperature"], "num_values": 5}
        )
    assert not result.isError, text_of(result)
    text = text_of(result)
    # Both implementations surface a Good status and a timestamp per record.
    assert "Good" in text or "sourceTimestamp" in text or "timestamp" in text
    assert text.strip() not in ("", "[]")


# --- browse parsing (server output formats differ) -----------------------------

async def _browse_json(session, node_id: str):
    """Return a list of {node_id, browse_name} dicts from a browse call.

    The Python server emits a Python ``repr`` of the list while the npx server
    emits JSON; this normalises both.
    """
    result = await session.call_tool("browse_opcua_node_children", {"node_id": node_id})
    text = text_of(result)
    blob = text[text.index("[") : text.rindex("]") + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        import ast

        return ast.literal_eval(blob)


def _discover_methods(children) -> dict[str, str]:
    """Map method browse-name -> node_id from browse output."""
    out = {}
    for child in children:
        name = str(child["browse_name"]).split(":")[-1]
        out[name] = child["node_id"]
    return out

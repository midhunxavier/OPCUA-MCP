"""Contract-parity tests: both MCP servers must agree with contract/tools.json.

The Node server builds its tools/list directly from the contract; the Python
server sources its tool descriptions and capability node IDs from it. This test
asserts that, against the mock server, BOTH servers advertise exactly the
contract's applicable tools, with matching descriptions and parameter sets — so
the two implementations cannot silently drift.

Run as part of the normal suite:
    uv sync --all-packages && cd tests && uv run --no-sync pytest -v
"""

from __future__ import annotations

import json

import pytest

from conftest import ROOT
from test_mcp_e2e import _server_params, connect, NPX_BUILD

CONTRACT = json.loads((ROOT / "contract" / "tools.json").read_text())

# The bundled mock server enables history but advertises no aggregate functions,
# so the contract tools applicable here are those with no capability + history.
_MOCK_CAPS = {None, "history"}
EXPECTED = {t["name"]: t for t in CONTRACT["tools"] if t["capability"] in _MOCK_CAPS}


def _props_required(schema: dict) -> tuple[set, set]:
    schema = schema or {}
    return set(schema.get("properties", {})), set(schema.get("required", []))


@pytest.fixture(params=["python", "npx"])
def impl_params(request, opcua_server):
    impl = request.param
    if impl == "npx" and not NPX_BUILD.exists():
        pytest.skip("npx server not built")
    return impl, _server_params(impl, opcua_server)


async def test_servers_match_contract(impl_params):
    impl, params = impl_params
    async with connect(params) as session:
        listed = await session.list_tools()
    advertised = {t.name: t for t in listed.tools}

    # 1) Exact tool-name parity with the contract (gated to the mock's caps).
    assert set(advertised) == set(EXPECTED), (
        f"{impl}: advertised tools diverge from contract; "
        f"missing={set(EXPECTED) - set(advertised)} extra={set(advertised) - set(EXPECTED)}"
    )

    # 2) Description + parameter parity per tool. Descriptions must match exactly
    #    (both servers source them from the contract). Schemas are compared by
    #    property names + required set to tolerate FastMCP vs node-opcua schema
    #    representation differences while still catching real parameter drift.
    for name, spec in EXPECTED.items():
        tool = advertised[name]
        assert tool.description == spec["description"], (
            f"{impl}/{name}: description differs from contract"
        )
        want_props, want_req = _props_required(spec["inputSchema"])
        got_props, got_req = _props_required(getattr(tool, "inputSchema", {}) or {})
        assert got_props == want_props, (
            f"{impl}/{name}: params {got_props} != contract {want_props}"
        )
        assert got_req == want_req, (
            f"{impl}/{name}: required {got_req} != contract {want_req}"
        )

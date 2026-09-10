"""Structural invariants of the shared tool contract.

contract/tools.json is the single source of truth both servers derive from, so a
malformed entry breaks both at once. The e2e parity test catches drift *between*
the servers but needs a running mock server and can only compare what the servers
actually advertised; these checks are on the file itself and run in milliseconds.
"""

from __future__ import annotations

import json

import pytest
from conftest import ROOT

CONTRACT = json.loads((ROOT / "contract" / "tools.json").read_text())
TOOLS = CONTRACT["tools"]
CAPABILITIES = CONTRACT["capabilities"]
RESULT_SHAPES = {k: v for k, v in CONTRACT["resultShapes"].items() if not k.startswith("$")}
TOOL_IDS = [t["name"] for t in TOOLS]
SHAPE_IDS = sorted(RESULT_SHAPES)


def test_tool_names_are_unique():
    assert len(TOOL_IDS) == len(set(TOOL_IDS)), "duplicate tool name in the contract"


@pytest.mark.parametrize("tool", TOOLS, ids=TOOL_IDS)
def test_tool_has_required_fields(tool):
    for field in ("name", "capability", "description", "inputSchema"):
        assert field in tool, f"{tool.get('name')} is missing {field!r}"
    assert tool["description"].strip(), f"{tool['name']} has an empty description"


@pytest.mark.parametrize("tool", TOOLS, ids=TOOL_IDS)
def test_capability_is_declared(tool):
    """A tool may only be gated on a capability the contract actually defines."""
    capability = tool["capability"]
    assert capability is None or capability in CAPABILITIES, (
        f"{tool['name']} gated on unknown capability {capability!r}; known: {sorted(CAPABILITIES)}"
    )


@pytest.mark.parametrize("tool", TOOLS, ids=TOOL_IDS)
def test_input_schema_is_coherent(tool):
    schema = tool["inputSchema"]
    assert schema.get("type") == "object", f"{tool['name']} inputSchema must be an object"
    properties = schema.get("properties", {})
    missing = set(schema.get("required", [])) - set(properties)
    assert not missing, f"{tool['name']} requires undeclared properties: {sorted(missing)}"
    for name, spec in properties.items():
        assert spec.get("description", "").strip(), (
            f"{tool['name']}.{name} has no description — the model relies on it"
        )


@pytest.mark.parametrize("name", sorted(CAPABILITIES), ids=sorted(CAPABILITIES))
def test_capability_probe_is_well_formed(name):
    probe = CAPABILITIES[name]
    for field in ("nodeId", "browseName", "check"):
        assert probe.get(field), f"capability {name} is missing {field!r}"
    assert probe["check"] in {"readBooleanTrue", "browseNonEmpty"}, (
        f"capability {name} has unknown check {probe['check']!r}"
    )


def test_python_server_sources_every_description_from_the_contract():
    """The Python server must not carry its own copy of any description."""
    from opcua_mcp_server import DESC

    assert set(DESC) == set(TOOL_IDS)
    for tool in TOOLS:
        assert DESC[tool["name"]] == tool["description"]


@pytest.mark.parametrize("tool", TOOLS, ids=TOOL_IDS)
def test_result_shape_is_declared(tool):
    """A tool may only name a result shape the contract actually defines."""
    shape = tool.get("resultShape")
    assert shape is None or shape in RESULT_SHAPES, (
        f"{tool['name']} declares unknown resultShape {shape!r}; known: {SHAPE_IDS}"
    )


@pytest.mark.parametrize("name", SHAPE_IDS, ids=SHAPE_IDS)
def test_result_shape_is_referenced(name):
    """An unreferenced shape binds nothing and would silently stop being checked."""
    assert any(tool.get("resultShape") == name for tool in TOOLS), (
        f"resultShape {name!r} is defined but no tool declares it"
    )


@pytest.mark.parametrize("name", SHAPE_IDS, ids=SHAPE_IDS)
def test_result_shape_records_are_coherent(name):
    """The record schema must be strict enough for the parity test to enforce it."""
    shape = RESULT_SHAPES[name]
    assert shape["type"] == "array", f"{name} must describe an array of records"
    record = shape["items"]
    assert record["type"] == "object"
    properties = record["properties"]
    assert set(record["required"]) == set(properties), (
        f"{name}: every field must be required, so neither server may omit one"
    )
    assert record.get("additionalProperties") is False, (
        f"{name}: extra fields must be forbidden, or the servers can still diverge"
    )
    for field, spec in properties.items():
        assert spec.get("description", "").strip(), (
            f"{name}.{field} has no description — the model relies on it"
        )


def test_the_history_family_shares_one_result_shape():
    """The divergence in #23 was two tools, both servers; one shape covers all four."""
    history_family = {t["name"]: t.get("resultShape") for t in TOOLS if t["capability"]}
    assert history_family == {
        "read_history_opcua_node": "historyRecords",
        "read_aggregate_opcua_node": "historyRecords",
    }

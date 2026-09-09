"""Unit tests for aggregate-function handling.

These matter more than usual because the bundled mock OPC UA server advertises
**no** aggregate functions, so `read_aggregate_opcua_node` is capability-gated
off in the end-to-end suite on both runtimes. Nothing else exercises this logic.
"""

from __future__ import annotations

import pytest
from opcua import ua
from opcua_mcp_server.aggregates import (
    aggregate_node_id,
    known_aggregate_names,
    validate_aggregate_function,
)


def test_known_names_cover_the_common_aggregates():
    names = known_aggregate_names()
    assert {"Average", "Minimum", "Maximum", "Count", "Total"} <= names


@pytest.mark.parametrize(
    ("name", "identifier"),
    [("Average", 2342), ("Minimum", 2346), ("Maximum", 2347), ("Count", 2352)],
)
def test_maps_names_to_the_spec_node_ids(name, identifier):
    """These identifiers are fixed by the OPC UA spec in namespace 0."""
    assert aggregate_node_id(name) == ua.NodeId(identifier, 0)


def test_unknown_name_is_rejected_before_hitting_the_wire():
    with pytest.raises(ValueError, match="Unknown aggregate function: Nonsense"):
        aggregate_node_id("Nonsense")


def test_accepts_a_supported_function():
    validate_aggregate_function("Average", ["Average", "Minimum"])


def test_reports_when_the_server_advertises_none():
    """Wording is mirrored verbatim by the Node server."""
    with pytest.raises(ValueError) as excinfo:
        validate_aggregate_function("Average", [])
    assert str(excinfo.value) == "Server does not advertise any aggregate functions"


def test_lists_the_supported_functions_when_the_name_is_wrong():
    with pytest.raises(ValueError) as excinfo:
        validate_aggregate_function("Bogus", ["Average", "Minimum"])
    assert str(excinfo.value) == "Invalid aggregate function. Supported: Average, Minimum"

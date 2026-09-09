"""Mapping between OPC UA aggregate function names and their node IDs.

The OPC UA spec defines aggregate functions as well-known nodes in namespace 0
(``AggregateFunction_Average`` = ``i=2342`` and friends). A server advertises the
subset it implements by exposing them under ``Server/ServerCapabilities/
AggregateFunctions``; this module turns the browse names found there back into
the node IDs a ``ReadProcessedDetails`` request needs.
"""

from __future__ import annotations

from collections.abc import Collection

from opcua import ua

_PREFIX = "AggregateFunction_"


def known_aggregate_names() -> frozenset[str]:
    """Every aggregate function name defined by the OPC UA spec."""
    return frozenset(name[len(_PREFIX) :] for name in dir(ua.ObjectIds) if name.startswith(_PREFIX))


def spec_aggregate_node_ids() -> dict[str, ua.NodeId]:
    """Every spec-defined aggregate function name mapped to its node ID."""
    return {
        name.removeprefix(_PREFIX): ua.NodeId(identifier, 0)
        for name, identifier in vars(ua.ObjectIds).items()
        if name.startswith(_PREFIX)
    }


def aggregate_node_id(name: str) -> ua.NodeId:
    """Node ID for a spec-defined aggregate function name.

    Raises ValueError for anything not in the spec, so an unknown name fails
    before a request is put on the wire.
    """
    try:
        identifier = getattr(ua.ObjectIds, f"{_PREFIX}{name}")
    except AttributeError:
        raise ValueError(f"Unknown aggregate function: {name}") from None
    return ua.NodeId(identifier, 0)


def validate_aggregate_function(name: str, supported: Collection[str]) -> None:
    """Raise unless ``name`` is one the connected server advertises.

    The two messages are mirrored verbatim by the Node server, so both runtimes
    reject the same input the same way.
    """
    if name in supported:
        return
    raise ValueError(
        "Server does not advertise any aggregate functions"
        if not supported
        else f"Invalid aggregate function. Supported: {', '.join(supported)}"
    )

"""Runtime probes for optional OPC UA server capabilities.

Tools that depend on a capability are only registered when the connected
server actually advertises it, mirroring the Node server's gating.
"""

from __future__ import annotations

from opcua import Client

from .aggregates import known_aggregate_names
from .contract import AGGREGATE_NODE_ID, HISTORY_NODE_ID


def server_supports_history(url: str) -> bool:
    """Probe the server's AccessHistoryDataCapability (ns=0;i=11193).

    Used to expose `read_history_opcua_node` only when the server actually
    supports historical reads, matching the Node server's behaviour.
    """
    try:
        probe = Client(url)
        probe.connect()
        try:
            return bool(probe.get_node(HISTORY_NODE_ID).get_value())
        finally:
            probe.disconnect()
    except Exception:
        return False


def server_aggregate_functions(url: str) -> list[str]:
    """Names of the aggregate functions the server advertises.

    Browses ``Server/ServerCapabilities/AggregateFunctions`` and keeps the
    children that name a spec-defined aggregate, mirroring how the Node server
    builds the same list. Best-effort: any failure yields an empty list rather
    than breaking tools/list, so a transient outage still leaves the core tools
    advertised.
    """
    known = known_aggregate_names()
    try:
        probe = Client(url)
        probe.connect()
        try:
            children = probe.get_node(AGGREGATE_NODE_ID).get_children()
            return [name for child in children if (name := child.get_browse_name().Name) in known]
        finally:
            probe.disconnect()
    except Exception:
        return []

"""Runtime probes for optional OPC UA server capabilities.

Tools that depend on a capability are only registered when the connected
server actually advertises it, mirroring the Node server's gating.
"""

from __future__ import annotations

from opcua import Client

from .contract import HISTORY_NODE_ID


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

"""OPC UA MCP server (Python runtime).

Exposes OPC UA read/write/browse/method/history operations as MCP tools. The
tool surface is defined once in ``contract/tools.json`` and shared with the Node
runtime; see ``contract.py``.

Importing this package connects to the configured OPC UA server once, to probe
which capability-gated tools to register (see ``capabilities``).
"""

from __future__ import annotations

from .config import SERVER_URL
from .contract import CONTRACT, DESC, HISTORY_NODE_ID, load_contract
from .datetimes import parse_iso_datetime
from .server import main, mcp

__all__ = [
    "CONTRACT",
    "DESC",
    "HISTORY_NODE_ID",
    "SERVER_URL",
    "load_contract",
    "main",
    "mcp",
    "parse_iso_datetime",
]

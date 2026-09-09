"""Runtime configuration, read from the environment."""

from __future__ import annotations

import os

#: OPC UA endpoint both the server and the capability probes connect to.
SERVER_URL = os.getenv("OPCUA_SERVER_URL", "opc.tcp://localhost:4840")

"""Shared pytest fixtures for the OPC UA MCP end-to-end suite.

The suite drives the *actual* MCP servers (Python and npx) over stdio using the
official `mcp` client SDK, pointed at the mock industrial OPC UA server. A single
session-scoped fixture makes sure a mock server is available: if one is already
listening on :4840 it is reused, otherwise one is started for the test session.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER_URL = os.environ.get(
    "OPCUA_SERVER_URL", "opc.tcp://localhost:4840/freeopcua/server/"
)
HOST = "localhost"
PORT = 4840

# Seconds of runtime to allow the mock server to accumulate history before tests
# read it back. The mock writes one history record per variable per second.
HISTORY_WARMUP_SECONDS = 6


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def opcua_server() -> str:
    """Ensure a mock OPC UA server is reachable; reuse an existing one if present.

    Yields the server endpoint URL.
    """
    if _port_open(HOST, PORT):
        # Something is already serving on :4840 — assume it is the mock server.
        yield SERVER_URL
        return

    proc = subprocess.Popen(
        ["uv", "run", "--no-sync", "opcua-mock-server"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if _port_open(HOST, PORT):
                break
            if proc.poll() is not None:
                raise RuntimeError("mock OPC UA server exited during startup")
            time.sleep(1)
        else:
            raise RuntimeError("mock OPC UA server did not start within 60s")

        time.sleep(HISTORY_WARMUP_SECONDS)  # let some history build up
        yield SERVER_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

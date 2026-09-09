"""Version-parity tests: the two servers must report one version, from one source.

The version used to be hardcoded in four places (`src/index.ts`, `package.json`,
and both `pyproject.toml`s), which is exactly the kind of thing that silently
drifts across a release. Now:

  * Node reads ``build/version.json``, generated from ``package.json`` by
    ``scripts/prepare-build.mjs``.
  * Python reads its installed distribution metadata via ``importlib.metadata``.

These tests pin both halves: that the manifests agree with each other (static),
and that each running server actually reports its manifest version over MCP
(end-to-end). The packages in this repo are released as a unit, so all three
manifests are expected to carry the same version.
"""

from __future__ import annotations

import json
import tomllib

import pytest
from conftest import ROOT
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from test_mcp_e2e import NODE_BUILD, _server_params

NODE_PKG = ROOT / "packages" / "server-node" / "package.json"
PYTHON_PYPROJECT = ROOT / "packages" / "server-python" / "pyproject.toml"
MOCK_PYPROJECT = ROOT / "packages" / "mock-server" / "pyproject.toml"


def _node_version() -> str:
    return json.loads(NODE_PKG.read_text())["version"]


def _py_version(pyproject) -> str:
    return tomllib.loads(pyproject.read_text())["project"]["version"]


def test_manifests_agree_on_version():
    """All three package manifests carry the same version (released as a unit)."""
    versions = {
        "server-node/package.json": _node_version(),
        "server-python/pyproject.toml": _py_version(PYTHON_PYPROJECT),
        "mock-server/pyproject.toml": _py_version(MOCK_PYPROJECT),
    }
    assert len(set(versions.values())) == 1, f"version drift across manifests: {versions}"


def test_no_hardcoded_version_in_node_source():
    """The Node source must not re-declare a version literal.

    Regression guard: `src/index.ts` used to hardcode `version: "0.1.2"` next to
    package.json, so the server advertised a stale version after every release.
    """
    src = (ROOT / "packages" / "server-node" / "src" / "index.ts").read_text()
    assert 'version: "' not in src, "hardcoded version literal in src/index.ts"


@pytest.mark.parametrize("impl", ["python", "node"])
async def test_server_reports_manifest_version(impl, opcua_server):
    """Each running server reports its manifest version in the MCP handshake.

    Uses its own connection rather than the shared ``connect`` helper, because
    that helper discards the ``InitializeResult`` and a server may reject a
    second ``initialize`` on the same session.
    """
    if impl == "node" and not NODE_BUILD.exists():
        pytest.skip("Node server not built")
    expected = _node_version() if impl == "node" else _py_version(PYTHON_PYPROJECT)

    async with stdio_client(_server_params(impl, opcua_server)) as (read, write):
        async with ClientSession(read, write) as session:
            info = (await session.initialize()).serverInfo

    assert info.name == "opcua-mcp-server", f"{impl} server identifies as {info.name!r}"
    assert info.version == expected, f"{impl} reports {info.version!r}, manifest says {expected!r}"

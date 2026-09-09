"""Version-parity checks that need no running server.

The version used to be hardcoded in four places (`src/index.ts`, `package.json`,
and both `pyproject.toml`s), which is exactly the kind of thing that silently
drifts across a release. These are the static halves of that guard; the
handshake half lives in e2e/test_version_parity.py.

The packages in this repo are released as a unit, so all three manifests are
expected to carry the same version.
"""

from __future__ import annotations

import json
import tomllib

from conftest import ROOT

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
    """No Node module may re-declare a version literal.

    Regression guard: `src/index.ts` used to hardcode `version: "0.1.2"` next to
    package.json, so the server advertised a stale version after every release.
    Scans every module, not just index.ts, since the source is now split.
    """
    offenders = [
        path.name
        for path in sorted((ROOT / "packages" / "server-node" / "src").glob("*.ts"))
        if 'version: "' in path.read_text()
    ]
    assert not offenders, f"hardcoded version literal in: {offenders}"

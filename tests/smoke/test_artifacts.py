"""Smoke tests against the *packaged* artifacts, not the source tree.

Everything else in this suite runs from the repo, where relative paths happen to
resolve. Users get a tarball or a wheel, where they may not. That gap is not
hypothetical: `opcua-mcp-server` shipped a release whose Python wheel raised
`FileNotFoundError` on import because the shared tool contract resolved via
`Path(__file__).parents[2]`, which is only the repo root in a source checkout.

So these tests build the real artifacts, install them somewhere isolated, and
drive the installed entry point over MCP:

  * npm: `npm pack` → install the tarball into a scratch project → run the
    ``node_modules/.bin`` shim. The shim is a **symlink**, which is deliberate —
    it is what `npx` invokes, and it is the case most likely to break an
    entry-point guard that compares `import.meta.url` to `process.argv[1]`.
  * Python: `uv build` → install the wheel into a fresh venv → run the console
    script with a cwd *outside* the repo, so a path that only resolves in the
    source tree cannot accidentally pass.

Marked ``smoke``; they are slow (npm install + venv creation) and run as their
own CI job. Deselect with ``-m "not smoke"``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

import pytest
from conftest import ROOT
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

pytestmark = pytest.mark.smoke

# Populated by the wheel_venv fixture so the sdist test can reuse the build.
_DIST_DIRS: list = []

NODE_PKG_DIR = ROOT / "packages" / "server-node"
PY_PKG_DIR = ROOT / "packages" / "server-python"

# Tools every build must advertise regardless of server capabilities. Capability
# -gated tools (history/aggregate) are covered by the e2e suite instead.
CORE_TOOLS = {
    "read_opcua_node",
    "write_opcua_node",
    "browse_opcua_node_children",
    "read_multiple_opcua_nodes",
    "write_multiple_opcua_nodes",
    "call_opcua_method",
    "get_all_variables",
}


def _run(cmd, cwd, **kw):
    """Run a command, surfacing stdout/stderr in the failure message."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600, **kw)
    if proc.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(map(str, cmd))}\n"
            f"cwd: {cwd}\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return proc


async def _list_tools(params: StdioServerParameters) -> set[str]:
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        return {t.name for t in (await session.list_tools()).tools}


@pytest.fixture(scope="module")
def npm_install(tmp_path_factory):
    """Pack the npm tarball and install it into a scratch project."""
    if shutil.which("npm") is None:
        pytest.skip("npm not available")

    staging = tmp_path_factory.mktemp("npm-pack")
    out = _run(["npm", "pack", "--pack-destination", str(staging)], cwd=NODE_PKG_DIR)
    tarball = staging / out.stdout.strip().splitlines()[-1]
    assert tarball.is_file(), f"npm pack did not produce {tarball}"

    project = tmp_path_factory.mktemp("npm-consumer")
    _run(["npm", "init", "-y"], cwd=project)
    _run(["npm", "install", str(tarball)], cwd=project)
    return project


def test_npm_tarball_contains_runtime_assets(npm_install):
    """The published package must carry everything index.js reads at runtime."""
    pkg = npm_install / "node_modules" / "opcua-mcp-server"
    for asset in ("build/index.js", "build/contract.json", "build/version.json"):
        assert (pkg / asset).is_file(), f"{asset} missing from the npm package"


def test_npm_bin_shims_are_installed(npm_install):
    """Both documented commands must exist as executable shims."""
    bindir = npm_install / "node_modules" / ".bin"
    for name in ("opcua-mcp-server", "opcua-mcp"):
        shim = bindir / name
        assert shim.exists(), f"bin shim {name} not installed"


async def test_npm_installed_server_lists_tools(npm_install, opcua_server):
    """The installed shim must start and serve tools/list over MCP.

    Runs the ``.bin`` symlink from a cwd outside the repo — the exact shape of
    invocation `npx` uses.
    """
    shim = npm_install / "node_modules" / ".bin" / "opcua-mcp-server"
    params = StdioServerParameters(
        command=str(shim),
        args=[],
        env={**os.environ, "OPCUA_SERVER_URL": opcua_server},
        cwd=str(npm_install),
    )
    assert await _list_tools(params) >= CORE_TOOLS


@pytest.fixture(scope="module")
def wheel_venv(tmp_path_factory):
    """Build the Python wheel and install it into a fresh, isolated venv."""
    if shutil.which("uv") is None:
        pytest.skip("uv not available")

    dist = tmp_path_factory.mktemp("wheel")
    _DIST_DIRS.append(dist)
    # Plain `uv build`, not `--wheel`: it builds the sdist and then the wheel
    # *from that sdist*, which is what PyPI publishing and `pip install <sdist>`
    # do. Building only the wheel skips that path entirely — and that is how a
    # release shipped with a `force-include` that resolved in a checkout but not
    # in an sdist, failing the publish job.
    _run(["uv", "build", "--out-dir", str(dist)], cwd=PY_PKG_DIR)
    wheels = list(dist.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"

    # `uv venv` rather than stdlib `venv`: uv-managed interpreters ship without a
    # working `ensurepip`, so `venv.create(with_pip=True)` aborts on them.
    env_dir = tmp_path_factory.mktemp("wheel-venv") / "venv"
    _run(["uv", "venv", str(env_dir)], cwd=dist)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / ("python.exe" if sys.platform == "win32" else "python")
    _run(["uv", "pip", "install", "--python", str(python), str(wheels[0])], cwd=dist)
    return bindir


def test_wheel_imports_outside_source_tree(wheel_venv, tmp_path):
    """Importing the installed module must not depend on the repo layout.

    Regression guard for the shipped `FileNotFoundError`: the contract was
    resolved relative to the source checkout, so the wheel worked in-repo and
    failed everywhere else. `cwd` is deliberately outside the repo.
    """
    python = wheel_venv / ("python.exe" if sys.platform == "win32" else "python")
    proc = _run(
        [
            str(python),
            "-c",
            "import opcua_mcp_server as m; import json; print(json.dumps(sorted(m.DESC)))",
        ],
        cwd=tmp_path,
    )
    assert set(json.loads(proc.stdout)) >= CORE_TOOLS


def test_sdist_is_self_contained(wheel_venv, tmp_path_factory):
    """A wheel must be buildable from the sdist alone, outside any checkout.

    Regression guard for the failed 0.2.0 PyPI publish: the contract was
    force-included from `../../contract/tools.json`, a path that exists in the
    repo but can never exist inside an sdist.
    """
    dist = next(iter(_DIST_DIRS))
    sdists = list(dist.glob("*.tar.gz"))
    assert len(sdists) == 1, f"expected exactly one sdist, got {sdists}"

    # Unpack somewhere with no repo above it, then build a wheel from it.
    workdir = tmp_path_factory.mktemp("sdist-only")
    with tarfile.open(sdists[0]) as tar:
        # `filter` is only available from 3.12 (and 3.10/3.11 point releases);
        # the floor here is 3.10, so pass it only where it certainly exists.
        extra = {"filter": "data"} if sys.version_info >= (3, 12) else {}
        tar.extractall(workdir, **extra)
    unpacked = next(p for p in workdir.iterdir() if p.is_dir())

    out = workdir / "out"
    _run(["uv", "build", "--wheel", "--out-dir", str(out)], cwd=unpacked)
    built = list(out.glob("*.whl"))
    assert len(built) == 1, f"expected one wheel from the sdist, got {built}"

    with zipfile.ZipFile(built[0]) as zf:
        assert "opcua_mcp_server/tools.json" in zf.namelist(), (
            "wheel built from the sdist is missing the bundled tool contract"
        )


def test_wheel_does_not_pollute_site_packages(wheel_venv):
    """The distribution must install exactly one importable top-level name.

    The contract used to be force-included at the *wheel root*, so installing
    dropped two top-level files into site-packages and the contract needed a
    namespaced filename to avoid colliding with other distributions. It now ships
    inside the package.
    """
    site_packages = next((wheel_venv.parent / "lib").glob("python*/site-packages"))
    record = next(site_packages.glob("opcua_mcp_server-*.dist-info/RECORD")).read_text()

    top_level = {line.split("/")[0] for line in record.splitlines() if line.strip()}
    # Drop metadata and the console script, which RECORD lists as ../../../bin/...
    importable = {t for t in top_level if not t.endswith(".dist-info") and t != ".."}

    assert importable == {"opcua_mcp_server"}, (
        f"wheel installs unexpected top-level entries: {sorted(importable)}"
    )


def test_wheel_console_script_installed(wheel_venv):
    script = wheel_venv / (
        "opcua-mcp-server.exe" if sys.platform == "win32" else "opcua-mcp-server"
    )
    assert script.exists(), "console script `opcua-mcp-server` not installed by the wheel"


async def test_wheel_installed_server_lists_tools(wheel_venv, opcua_server, tmp_path):
    """The installed console script must start and serve tools/list over MCP."""
    script = wheel_venv / (
        "opcua-mcp-server.exe" if sys.platform == "win32" else "opcua-mcp-server"
    )
    params = StdioServerParameters(
        command=str(script),
        args=[],
        env={**os.environ, "OPCUA_SERVER_URL": opcua_server},
        cwd=str(tmp_path),
    )
    assert await _list_tools(params) >= CORE_TOOLS

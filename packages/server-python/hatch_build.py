"""Build hook that stages the shared tool contract inside the wheel.

The canonical contract lives at the repo root (`/contract/tools.json`), outside
this package. A static `force-include` pointing at `../../` works when building
from a checkout, but breaks when the wheel is built *from an sdist* — which is
what `uv build` and `pip install <sdist>` do — because an sdist cannot contain
files from outside its own root:

    FileNotFoundError: Forced include not found: .../contract/tools.json

So the sdist carries its own copy at `contract/tools.json` (see the sdist
force-include in pyproject.toml), and this hook injects whichever copy exists
into the wheel at build time. It adds to `build_data` rather than writing into
the source tree, so building never leaves artefacts behind.
"""

from __future__ import annotations

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

#: Where the wheel expects to find it; `contract.py` reads this path.
WHEEL_PATH = "opcua_mcp_server/tools.json"


class ContractBuildHook(BuildHookInterface):
    PLUGIN_NAME = "opcua-contract"

    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel":
            return

        root = Path(self.root)
        candidates = (
            root.parents[1] / "contract" / "tools.json",  # repo checkout
            root / "contract" / "tools.json",  # unpacked sdist
        )
        for candidate in candidates:
            if candidate.is_file():
                build_data["force_include"][str(candidate)] = WHEEL_PATH
                return

        raise FileNotFoundError(
            "Shared tool contract not found; looked in " + ", ".join(str(c) for c in candidates)
        )

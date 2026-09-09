"""The shared tool contract — the single source of truth both servers derive from."""

from __future__ import annotations

import json
from pathlib import Path


def load_contract() -> dict:
    """Load the shared tool contract (single source of truth).

    Two locations, in order:

    1. ``tools.json`` inside this package — how it ships in the wheel (see the
       ``force-include`` in pyproject.toml). Bundling it *inside* the package
       rather than at the install root keeps the distribution from adding
       top-level files to ``site-packages``.
    2. ``/contract/tools.json`` at the repo root — the canonical source, used when
       running from a checkout (dev, editable installs, tests).

    Without (1) a pip/uvx install would raise FileNotFoundError on import, because
    the repo-root path does not exist outside a checkout.
    """
    here = Path(__file__).resolve()
    candidates = (
        here.parent / "tools.json",  # bundled inside the wheel
        here.parents[4] / "contract" / "tools.json",  # repo-root source layout
    )
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError(
        "Shared tool contract not found; looked in " + ", ".join(str(p) for p in candidates)
    )


# Shared tool contract so tool descriptions and capability node IDs stay in sync
# with the Node server.
CONTRACT = load_contract()
DESC = {t["name"]: t["description"] for t in CONTRACT["tools"]}
HISTORY_NODE_ID = CONTRACT["capabilities"]["history"]["nodeId"]

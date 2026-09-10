"""The canonical record shape for the history family of tools.

``contract/tools.json`` -> ``resultShapes.historyRecords`` is the specification;
this module is the Python implementation of it, and ``src/records.ts`` in the
Node server is the other. Both servers must emit comparable records: a client —
or a model — that has learned one server's output has to be able to read the
other's. The two used to diverge (this server returned flat stringified records,
the Node server raw ``DataValue`` JSON); see issue #23.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite
from typing import Any

from .datetimes import format_iso_utc

#: An absent StatusCode means Good in OPC UA, so name it rather than return None.
_DEFAULT_STATUS = "Good"


def json_value(value: Any) -> Any:
    """An OPC UA value as JSON, without the Variant wrapper.

    Values that JSON can carry (number, boolean, string, and sequences of those)
    pass through as themselves, so a consumer gets ``51.75`` rather than
    ``"51.75"`` — and an empty aggregate interval gets ``null`` rather than the
    string ``"None"``. Anything else — a datetime, a NodeId, an ExtensionObject —
    becomes its string form, which is lossy but always serialisable.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        # NaN and ±inf are not JSON. json.dumps emits bare `NaN`, which is not
        # parseable by a strict client, so send the string form instead.
        return value if isfinite(value) else str(value)
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return str(value)


def history_record(data_value: Any) -> dict:
    """One opcua ``DataValue`` as a canonical record."""
    variant = getattr(data_value, "Value", None)
    status = getattr(data_value, "StatusCode", None)
    return {
        "value": json_value(getattr(variant, "Value", None)),
        "timestamp": format_iso_utc(getattr(data_value, "SourceTimestamp", None)),
        "status": str(status.name) if status is not None else _DEFAULT_STATUS,
    }


def history_records(data_values: Iterable[Any] | None) -> list[dict]:
    """A history/aggregate result as canonical records."""
    return [history_record(data_value) for data_value in data_values or ()]

"""Unit tests for the Python server's ISO-8601 handling.

No OPC UA server and no MCP transport: this is the pure conversion layer that
sits between what MCP delivers (strings) and what the opcua client needs
(datetimes). It has broken before — the history tool originally accepted a
different shape and reported errors differently from the Node server.

The Node equivalent lives in packages/server-node/test/unit.test.mjs; the two
files deliberately assert the same error wording.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from opcua_mcp_server import _parse_iso_datetime

# Must stay byte-identical to the Node server's `toDate` message.
EXPECTED_ERROR = 'Invalid date/time: "{value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z'


def test_none_passes_through():
    """None means 'unset' over MCP and must not become an error."""
    assert _parse_iso_datetime(None) is None


def test_parses_utc_z_suffix():
    assert _parse_iso_datetime("2026-04-23T17:40:00Z") == datetime(2026, 4, 23, 17, 40, tzinfo=UTC)


def test_preserves_non_utc_offset():
    """An offset must shift the instant, not be silently dropped."""
    parsed = _parse_iso_datetime("2026-04-23T19:40:00+02:00")
    assert parsed.astimezone(UTC) == datetime(2026, 4, 23, 17, 40, tzinfo=UTC)


@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "",
        "23/04/2026",
        "2026-13-01T00:00:00Z",  # month out of range
        "2026-02-30T00:00:00Z",  # day out of range for the month
    ],
)
def test_rejects_malformed_input_with_shared_wording(value):
    with pytest.raises(ValueError) as excinfo:
        _parse_iso_datetime(value)
    assert str(excinfo.value) == EXPECTED_ERROR.format(value=value)


def test_error_does_not_leak_the_underlying_exception():
    """`raise ... from None` keeps the low-level message out of the model's view."""
    with pytest.raises(ValueError) as excinfo:
        _parse_iso_datetime("nope")
    assert excinfo.value.__cause__ is None

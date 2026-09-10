"""Unit tests for the canonical history-family record shape (Python side).

`contract/tools.json` -> `resultShapes.historyRecords` defines one shape for
`read_history_opcua_node` / `read_aggregate_opcua_node` on both servers; this
file pins the Python implementation of it. The Node equivalent is the
"history records" suite in packages/server-node/test/unit.test.mjs, and the two
deliberately assert the same records.

No OPC UA server and no MCP transport: `DataValue` is stood in for by a stub
exposing the three attributes the mapper reads.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from opcua_mcp_server import format_iso_utc, history_record, history_records, json_value

TIMESTAMP = datetime(2026, 9, 9, 13, 36, 1, 468000)


def data_value(value, *, timestamp=TIMESTAMP, status="Good"):
    """A stand-in for an opcua `DataValue` — the attributes the mapper reads."""
    return SimpleNamespace(
        Value=SimpleNamespace(Value=value),
        SourceTimestamp=timestamp,
        StatusCode=None if status is None else SimpleNamespace(name=status),
    )


def test_flattens_a_data_value():
    assert history_records([data_value(51.25)]) == [
        {"value": 51.25, "timestamp": "2026-09-09T13:36:01.468000Z", "status": "Good"}
    ]


@pytest.mark.parametrize("value", [51.25, 3, True, False, "AUTO", None, [1.0, 2.0]])
def test_json_native_values_pass_through_unstringified(value):
    """The value used to be `str(...)`, so a number arrived as `"51.25"`."""
    assert json_value(value) == value


def test_empty_aggregate_interval_is_null_not_the_string_none():
    """An interval the server has no data for previously came back as `"None"`."""
    record = history_record(data_value(None, status="BadNoData"))
    assert record["value"] is None
    assert record["status"] == "BadNoData"


def test_absent_status_code_means_good():
    assert history_record(data_value(1, status=None))["status"] == "Good"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_become_strings(value):
    """`json.dumps` would emit a bare `NaN`, which strict JSON parsers reject."""
    assert json_value(value) == str(value)


def test_values_json_cannot_carry_become_their_string_form():
    assert json_value(datetime(2026, 9, 9, 13, 36)) == "2026-09-09 13:36:00"
    assert json_value({"a": 1}) == "{'a': 1}"


def test_no_data_values_is_an_empty_record_list():
    assert history_records(None) == []
    assert history_records([]) == []


# --- format_iso_utc -----------------------------------------------------------


def test_naive_timestamps_are_labelled_utc_not_reinterpreted_as_local():
    """python-opcua decodes OPC UA DateTimes to naive datetimes already in UTC."""
    assert format_iso_utc(TIMESTAMP) == "2026-09-09T13:36:01.468000Z"


def test_aware_timestamps_are_converted_to_utc():
    kolkata = timezone(timedelta(hours=5, minutes=30))
    assert format_iso_utc(TIMESTAMP.replace(tzinfo=kolkata)) == "2026-09-09T08:06:01.468000Z"


def test_none_passes_through():
    assert format_iso_utc(None) is None


def test_round_trips_through_the_parser_the_tools_accept():
    """The tools accept ISO-8601 for start_time/end_time; they now return it too."""
    from opcua_mcp_server import parse_iso_datetime

    assert parse_iso_datetime(format_iso_utc(TIMESTAMP)) == TIMESTAMP.replace(tzinfo=timezone.utc)

"""Conversion between the ISO-8601 strings MCP delivers and datetimes."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse an optional ISO-8601 string into a datetime.

    MCP delivers these as strings, so they are converted here before being handed
    to the opcua client. Mirrors the Node server's ``toDate`` error wording so both
    servers reject malformed input identically.
    """
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError(
            f'Invalid date/time: "{value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z'
        ) from None


def format_iso_utc(value: datetime | None) -> str | None:
    """Render a datetime as ISO-8601 UTC with a trailing ``Z``.

    The inverse of :func:`parse_iso_datetime`, and the format the history-family
    tools return (``contract/tools.json`` -> ``resultShapes.historyRecords``).
    Previously these timestamps were ``str(datetime)`` — ``"2026-09-09 13:36:01.468000"``,
    space-separated and with no zone — which is not what the same tools *accept*
    for ``start_time``/``end_time``, and not what the Node server emitted.

    python-opcua decodes OPC UA DateTimes into naive datetimes that are already
    UTC, so a naive value is labelled UTC rather than reinterpreted as local time.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

"""Conversion between the ISO-8601 strings MCP delivers and datetimes."""

from __future__ import annotations

from datetime import datetime


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

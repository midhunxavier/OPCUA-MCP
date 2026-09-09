// Conversion between the ISO-8601 strings MCP delivers and Date objects.

// Parse an optional ISO-8601 date/time string into a Date. MCP delivers these as
// strings, so they must be converted before being handed to node-opcua.
export function toDate(value: string | Date | undefined): Date | undefined {
  if (value === undefined || value === null) return undefined;
  if (value instanceof Date) return value;
  const d = new Date(value);
  if (isNaN(d.getTime())) {
    throw new Error(`Invalid date/time: "${value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z`);
  }
  return d;
}

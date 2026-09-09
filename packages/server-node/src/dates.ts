// Conversion between the ISO-8601 strings MCP delivers and Date objects.

/** Matches the leading calendar date of an ISO-8601 string. */
const ISO_CALENDAR_DATE = /^(\d{4})-(\d{2})-(\d{2})/;

/** True when the string starts with a calendar date that does not exist.
 *
 * V8's Date parser rolls out-of-range days over into the next month, so
 * `new Date("2026-02-30")` yields March 2 rather than an error. For a history
 * read that is worse than failing: the caller silently receives real data for a
 * different day than they asked for. Python's `datetime.fromisoformat` rejects
 * these, so accepting them also broke parity between the two servers.
 *
 * The check is plain arithmetic on the string's own Y-M-D rather than a Date
 * round-trip, for two reasons: a timezone offset legitimately shifts the parsed
 * UTC date (so comparing UTC components would produce false positives), and
 * `Date.UTC` maps two-digit years into the 1900s, which would wrongly reject a
 * year like 0026.
 */
function daysInMonth(year: number, month: number): number {
  if (month === 2) {
    const isLeapYear = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
    return isLeapYear ? 29 : 28;
  }
  return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
}

function hasImpossibleCalendarDate(value: string): boolean {
  const match = ISO_CALENDAR_DATE.exec(value);
  if (!match) return false; // Not this shape; leave validation to Date itself.

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);

  if (month < 1 || month > 12) return true;
  return day < 1 || day > daysInMonth(year, month);
}

/** Parse an optional ISO-8601 date/time string into a Date.
 *
 * MCP delivers these as strings, so they must be converted before being handed
 * to node-opcua. The error wording is mirrored verbatim by the Python server's
 * `parse_iso_datetime`, so both runtimes reject malformed input identically.
 */
export function toDate(value: string | Date | undefined): Date | undefined {
  if (value === undefined || value === null) return undefined;
  if (value instanceof Date) return value;
  const d = new Date(value);
  if (isNaN(d.getTime()) || hasImpossibleCalendarDate(value)) {
    throw new Error(`Invalid date/time: "${value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z`);
  }
  return d;
}

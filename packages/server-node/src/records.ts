// The canonical record shape for the history family of tools.
//
// `contract/tools.json` -> resultShapes.historyRecords is the specification;
// this module is the Node implementation of it, and `records.py` in the Python
// server is the other. Both servers must emit byte-comparable records: a client
// — or a model — that has learned one server's output has to be able to read the
// other's. This file previously did not exist; the Node server returned raw
// node-opcua `DataValue` JSON (`{"statusCode":{"value":1},"sourceTimestamp":…}`)
// while the Python server returned flat records. See issue #23.
import { DataValue } from "node-opcua";

export interface HistoryRecord {
  /** JSON-native when the OPC UA type maps onto JSON, else its string form. */
  value: unknown;
  /** ISO-8601 UTC with a trailing `Z`, or null when the server supplied none. */
  timestamp: string | null;
  /** OPC UA status code name, e.g. `Good` / `BadNoData`. */
  status: string;
}

/** An OPC UA value as JSON, without the Variant wrapper.
 *
 * Values that JSON can carry (number, boolean, string, and arrays of those) pass
 * through as themselves, so a consumer gets `51.75` rather than `"51.75"`.
 * Anything else — a DateTime, a NodeId, an ExtensionObject — becomes its string
 * form, which is lossy but always serialisable; returning it raw would leak
 * node-opcua's internal representation back into the response.
 */
export function toJsonValue(value: unknown): unknown {
  if (value === null || value === undefined) return null;

  switch (typeof value) {
    case "boolean":
    case "string":
      return value;
    // NaN and ±Infinity are not JSON; JSON.stringify would silently emit `null`
    // and lose the distinction between "no data" and "not a number".
    case "number":
      return Number.isFinite(value) ? value : String(value);
    case "bigint":
      return Number.isSafeInteger(Number(value)) ? Number(value) : value.toString();
  }

  // Typed arrays (Float64Array & friends) are how node-opcua carries array
  // variants; Array.from normalises them to a plain array.
  if (Array.isArray(value) || ArrayBuffer.isView(value)) {
    return Array.from(value as ArrayLike<unknown>, toJsonValue);
  }
  if (value instanceof Date) return value.toISOString();

  return String(value);
}

/** A timestamp as ISO-8601 UTC, mirroring the Python server's `format_iso_utc`. */
export function toIsoUtc(value: Date | null | undefined): string | null {
  if (!(value instanceof Date) || isNaN(value.getTime())) return null;
  return value.toISOString();
}

/** One `DataValue` as a canonical record. */
export function toHistoryRecord(dataValue: DataValue): HistoryRecord {
  return {
    value: toJsonValue(dataValue?.value?.value),
    timestamp: toIsoUtc(dataValue?.sourceTimestamp),
    // An absent status code means Good in OPC UA, so say so rather than null.
    status: dataValue?.statusCode?.name ?? "Good",
  };
}

/** The history/aggregate `DataValue` array as canonical records. */
export function toHistoryRecords(dataValues: DataValue[] | null | undefined): HistoryRecord[] {
  return (dataValues ?? []).map(toHistoryRecord);
}

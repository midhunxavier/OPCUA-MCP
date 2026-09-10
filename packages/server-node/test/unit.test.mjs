// Unit tests for the Node server's pure logic — no OPC UA server, no MCP
// transport, no build of the mock. Uses the built-in `node:test` runner so the
// package gains no dependency.
//
// Run: npm test   (requires `npm run build` first — these import build/index.js)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import test, { describe } from "node:test";
import { fileURLToPath } from "node:url";

import { toDate } from "../build/dates.js";
import { toHistoryRecords, toIsoUtc, toJsonValue } from "../build/records.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

describe("toDate", () => {
  test("passes through undefined and null (both mean 'unset' over MCP)", () => {
    assert.equal(toDate(undefined), undefined);
    assert.equal(toDate(null), undefined);
  });

  test("returns Date instances unchanged", () => {
    const d = new Date("2026-04-23T17:40:00Z");
    assert.equal(toDate(d), d);
  });

  test("parses ISO-8601 strings, which is how MCP delivers timestamps", () => {
    assert.equal(toDate("2026-04-23T17:40:00Z").toISOString(), "2026-04-23T17:40:00.000Z");
  });

  test("preserves a non-UTC offset rather than reinterpreting the wall time", () => {
    assert.equal(toDate("2026-04-23T19:40:00+02:00").toISOString(), "2026-04-23T17:40:00.000Z");
  });

  // The Python server mirrors this wording verbatim so both runtimes reject bad
  // input identically; see _parse_iso_datetime in opcua_mcp_server.py.
  test("rejects malformed input with the wording shared with the Python server", () => {
    assert.throws(
      () => toDate("not-a-date"),
      (err) => {
        assert.equal(
          err.message,
          'Invalid date/time: "not-a-date". Use ISO 8601, e.g. 2026-04-23T17:40:00Z'
        );
        return true;
      }
    );
  });

  test("rejects an out-of-range month", () => {
    assert.throws(() => toDate("2026-13-01T00:00:00Z"), /Invalid date\/time/);
  });

  // Was a divergence from the Python server: V8 rolls an out-of-range day over
  // into the next month, so this silently returned data for 2026-03-02. Python's
  // datetime.fromisoformat rejects it, and now so does this.
  test("rejects an out-of-range day instead of rolling it over", () => {
    assert.throws(() => toDate("2026-02-30T00:00:00Z"), /Invalid date\/time/);
    assert.throws(() => toDate("2026-04-31T00:00:00Z"), /Invalid date\/time/);
  });

  test("accepts a real leap day and rejects a fake one", () => {
    assert.equal(toDate("2028-02-29T00:00:00Z").toISOString(), "2028-02-29T00:00:00.000Z");
    assert.throws(() => toDate("2026-02-29T00:00:00Z"), /Invalid date\/time/);
  });

  test("accepts a two-digit-looking year (no Date.UTC 1900s remapping)", () => {
    assert.equal(toDate("0026-01-15T00:00:00Z").toISOString(), "0026-01-15T00:00:00.000Z");
  });

  test("a timezone offset that shifts the UTC date is still accepted", () => {
    // 2026-03-01T01:00+02:00 is 2026-02-28T23:00Z — the UTC day differs from the
    // string's day, which must not be mistaken for an impossible date.
    assert.equal(toDate("2026-03-01T01:00:00+02:00").toISOString(), "2026-02-28T23:00:00.000Z");
  });
});

// The canonical history-family record shape (contract -> resultShapes.historyRecords).
// The Python server's equivalent tests are in tests/unit/test_records.py; both
// assert the same shape, because a client must be able to read either server.
describe("history records", () => {
  /** A minimal DataValue stand-in — the fields toHistoryRecord actually reads. */
  const dataValue = (value, { timestamp = new Date("2026-09-09T13:36:01.139Z"), status } = {}) => ({
    value: value === undefined ? undefined : { value },
    sourceTimestamp: timestamp,
    statusCode: status === undefined ? undefined : { name: status },
  });

  test("flattens a DataValue to {value, timestamp, status}", () => {
    assert.deepEqual(toHistoryRecords([dataValue(51.75, { status: "Good" })]), [
      { value: 51.75, timestamp: "2026-09-09T13:36:01.139Z", status: "Good" },
    ]);
  });

  test("keeps the value JSON-native rather than stringifying it", () => {
    assert.equal(toJsonValue(51.75), 51.75);
    assert.equal(toJsonValue(true), true);
    assert.equal(toJsonValue("AUTO"), "AUTO");
    assert.deepEqual(toJsonValue(new Float64Array([1, 2])), [1, 2]);
  });

  test("an empty aggregate interval is null, not a stringified placeholder", () => {
    const [record] = toHistoryRecords([dataValue(undefined, { status: "BadNoData" })]);
    assert.equal(record.value, null);
    assert.equal(record.status, "BadNoData");
  });

  test("an absent status code means Good", () => {
    assert.equal(toHistoryRecords([dataValue(1)])[0].status, "Good");
  });

  test("stringifies values JSON cannot carry", () => {
    assert.equal(toJsonValue(NaN), "NaN");
    assert.equal(toJsonValue(Infinity), "Infinity");
    assert.equal(toJsonValue({ toString: () => "ns=2;i=3" }), "ns=2;i=3");
  });

  test("timestamps are ISO-8601 UTC with a trailing Z", () => {
    assert.equal(toIsoUtc(new Date("2026-09-09T15:36:01.468+02:00")), "2026-09-09T13:36:01.468Z");
    assert.equal(toIsoUtc(undefined), null);
    assert.equal(toIsoUtc(new Date("nope")), null);
  });

  test("no data values is an empty record list", () => {
    assert.deepEqual(toHistoryRecords(undefined), []);
    assert.deepEqual(toHistoryRecords([]), []);
  });
});

describe("build assets", () => {
  test("version.json matches package.json", () => {
    const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
    const built = JSON.parse(readFileSync(join(ROOT, "build", "version.json"), "utf8"));
    assert.equal(built.version, pkg.version);
  });

  test("build/contract.json is byte-identical to the canonical contract", () => {
    const canonical = readFileSync(join(ROOT, "..", "..", "contract", "tools.json"), "utf8");
    const staged = readFileSync(join(ROOT, "build", "contract.json"), "utf8");
    assert.equal(staged, canonical, "build/contract.json drifted from contract/tools.json");
  });
});

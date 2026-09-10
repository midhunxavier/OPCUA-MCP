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
import {
  DataType,
  LocalizedText,
  NodeId,
  QualifiedName,
  StatusCodes,
  Variant,
  VariantArrayType,
  coerceNodeId,
} from "node-opcua";

import { toDate } from "../build/dates.js";
import { toHistoryRecords, toIsoUtc, variantToJson } from "../build/records.js";

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
// The Python equivalents are in tests/unit/test_records.py.
//
// The per-type value encoding is not restated here — it lives in
// tests/fixtures/value-encoding.json, which both suites read. Each side builds
// the *native* value for a case (that is the whole problem: a Buffer here,
// `bytes` there) and asserts the same JSON comes out.
const FIXTURE = JSON.parse(
  readFileSync(join(ROOT, "..", "..", "tests", "fixtures", "value-encoding.json"), "utf8")
);
const CASES = Object.fromEntries(FIXTURE.cases.map((c) => [c.name, c]));

const scalar = (dataType, value) => new Variant({ dataType, value });
// Int64/UInt64 need an explicit arrayType: their scalar form is itself a
// [high, low] pair, so node-opcua refuses to guess whether an array is one
// value or many. That ambiguity is exactly why the encoder keys on the variant.
const int64 = (dataType, value) =>
  new Variant({ dataType, arrayType: VariantArrayType.Scalar, value });
const array = (dataType, value) =>
  new Variant({ dataType, arrayType: VariantArrayType.Array, value });

// The native node-opcua value for each case in the fixture. The Python suite has
// its own table of the same names holding python-opcua values; the two produce
// the same JSON, which is the point.
const NATIVE = {
  boolean: scalar(DataType.Boolean, true),
  int32: scalar(DataType.Int32, 42),
  int64_small: int64(DataType.Int64, 5),
  int64_negative: int64(DataType.Int64, -5),
  int64_beyond_double: int64(DataType.Int64, [0x200000, 1]), // 2^53 + 1, exact only as a pair
  uint64_max: int64(DataType.UInt64, [0xffffffff, 0xffffffff]),
  double: scalar(DataType.Double, 51.75),
  double_nan: scalar(DataType.Double, NaN),
  double_infinity: scalar(DataType.Double, Infinity),
  string: scalar(DataType.String, "AUTO"),
  datetime: scalar(DataType.DateTime, new Date("2026-09-09T13:36:01.468Z")),
  guid: scalar(DataType.Guid, "72962B91-FA75-4AE6-8D28-B404DC7DAF63"),
  bytestring: scalar(DataType.ByteString, Buffer.from("abc")),
  nodeid: scalar(DataType.NodeId, coerceNodeId("ns=2;i=3")),
  statuscode: scalar(DataType.StatusCode, StatusCodes.Good),
  qualifiedname: scalar(
    DataType.QualifiedName,
    new QualifiedName({ name: "Temperature", namespaceIndex: 2 })
  ),
  localizedtext: scalar(DataType.LocalizedText, new LocalizedText({ text: "Ambient temperature" })),
  double_array: array(DataType.Double, [1.5, 2.5]),
  byte_array: array(DataType.Byte, [97, 98, 99]),
  int64_array: array(DataType.Int64, [5, [0x200000, 1]]),
  bytestring_array: array(DataType.ByteString, [Buffer.from("ab"), Buffer.from("c")]),
  empty_array: array(DataType.Double, []),
  null: scalar(DataType.Null, null),
};

describe("value encoding (shared fixture)", () => {
  test("every fixture case has a native value", () => {
    // A case with no entry above would pass by never being run.
    assert.deepEqual(Object.keys(NATIVE).sort(), Object.keys(CASES).sort());
  });

  for (const [name, expectation] of Object.entries(CASES)) {
    test(`${name} matches the shared fixture`, () => {
      const encoded = variantToJson(NATIVE[name]);
      if (expectation.expectedPattern) {
        assert.match(String(encoded), new RegExp(expectation.expectedPattern));
      } else {
        assert.deepEqual(encoded, expectation.expected);
      }
    });
  }

  // Regression guards for the divergences that prompted the shared fixture:
  // node-opcua splits an Int64 into a [high, low] pair and carries a ByteString
  // as a Buffer, neither of which resembles what python-opcua hands over.
  test("an Int64 is a number, not node-opcua's [high, low] pair", () => {
    assert.equal(variantToJson(NATIVE.int64_negative), -5);
  });

  test("a ByteString is base64, not a list of byte values", () => {
    assert.equal(variantToJson(NATIVE.bytestring), "YWJj");
  });

  test("a Byte array stays an array of numbers", () => {
    assert.deepEqual(variantToJson(NATIVE.byte_array), [97, 98, 99]);
  });
});

// The canonical record shape (contract -> resultShapes.historyRecords).
describe("history records", () => {
  /** A minimal DataValue stand-in — the fields toHistoryRecord actually reads. */
  const dataValue = (
    variant,
    { timestamp = new Date("2026-09-09T13:36:01.139Z"), status } = {}
  ) => ({
    value: variant,
    sourceTimestamp: timestamp,
    statusCode: status === undefined ? undefined : { name: status },
  });

  test("flattens a DataValue to {value, timestamp, status}", () => {
    assert.deepEqual(toHistoryRecords([dataValue(NATIVE.double, { status: "Good" })]), [
      { value: 51.75, timestamp: "2026-09-09T13:36:01.139Z", status: "Good" },
    ]);
  });

  test("an empty aggregate interval is null, not a stringified placeholder", () => {
    const [record] = toHistoryRecords([dataValue(undefined, { status: "BadNoData" })]);
    assert.equal(record.value, null);
    assert.equal(record.status, "BadNoData");
  });

  test("an absent status code means Good", () => {
    assert.equal(toHistoryRecords([dataValue(NATIVE.int32)])[0].status, "Good");
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

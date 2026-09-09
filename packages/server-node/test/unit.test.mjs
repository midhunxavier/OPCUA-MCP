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

import { toDate } from "../build/index.js";

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

  // KNOWN DIVERGENCE from the Python server, asserted here so it cannot change
  // unnoticed. V8's Date parser rolls an out-of-range day over into the next
  // month, so the Node server silently accepts 2026-02-30 as 2026-03-02, while
  // Python's datetime.fromisoformat raises "day is out of range for month".
  // A history read for a nonexistent date therefore returns real data for the
  // wrong day instead of erroring. Tracked as parity work (roadmap phase 7).
  test("KNOWN DIVERGENCE: rolls an out-of-range day over instead of rejecting", () => {
    assert.equal(toDate("2026-02-30T00:00:00Z").toISOString(), "2026-03-02T00:00:00.000Z");
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

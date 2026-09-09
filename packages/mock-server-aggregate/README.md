# Aggregate-capable mock OPC UA server

A small `node-opcua` server used by the end-to-end test suite to exercise
`read_aggregate_opcua_node` on both MCP servers. Listens on **:4841**
(`opc.tcp://localhost:4841/UA/Aggregate`).

## Why a second mock

The main mock (`packages/mock-server`) stays deliberately aggregate-free:

- It advertises **no** aggregate functions, which is what lets the suite assert
  that both MCP servers *hide* the aggregate tool when the server cannot support
  it (`test_aggregate_tool_hidden_when_unsupported`).
- It could not serve aggregates anyway — python-opcua's history manager answers
  `ReadProcessedDetails` with `BadNotImplemented`.

This server covers the positive cases. `node-opcua-aggregates` publishes the
standard aggregate function nodes under `ServerCapabilities/AggregateFunctions`
and provides a real `ReadProcessedDetails` implementation, so both MCP servers
expose the tool against it and compute genuine values.

## Address space

| Node | Node ID | Notes |
|---|---|---|
| `Plant/Temperature` | `ns=1;i=1001` | `Double`, historized, ramps **+1.0 per second** |

The ramp is deliberate and linear so aggregates can be checked arithmetically:
consecutive `Average` buckets must differ by exactly `processing_interval / 1000`.
`AccessHistoryDataCapability` is set, so the raw history tool is exposed too.

## Running

```bash
npm install
npm start          # or: node server.mjs
```

Override the port with `AGGREGATE_MOCK_PORT`. The test fixture reuses an
instance already listening on :4841 and otherwise starts one for the session.

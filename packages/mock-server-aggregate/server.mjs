/**
 * Aggregate-capable mock OPC UA server for the end-to-end test suite.
 *
 * The bundled Python mock (`packages/mock-server`) deliberately advertises no
 * aggregate functions, which is what lets the suite assert that both MCP servers
 * *hide* `read_aggregate_opcua_node` when the server cannot support it. It also
 * cannot serve aggregates even if it wanted to: python-opcua's history manager
 * answers `ReadProcessedDetails` with `BadNotImplemented`.
 *
 * This server covers the other half. `node-opcua-aggregates` provides a real
 * `ReadProcessedDetails` implementation and publishes the standard aggregate
 * function nodes under `ServerCapabilities/AggregateFunctions`, so both MCP
 * servers expose the aggregate tool against it and compute real values.
 *
 * `Temperature` climbs by RAMP_STEP every RAMP_INTERVAL_MS, so aggregates are
 * verifiable by hand: with a +1.0/second ramp, consecutive Average buckets of
 * `processing_interval` ms must differ by exactly `processing_interval / 1000`.
 */
import { OPCUAServer, DataType, Variant, coerceNodeId } from "node-opcua";
import { addAggregateSupport } from "node-opcua-aggregates";

const PORT = Number(process.env.AGGREGATE_MOCK_PORT ?? 4841);
const RESOURCE_PATH = "/UA/Aggregate";

// A deterministic +1.0/second ramp: predictable aggregates, no random walk.
const RAMP_STEP = 0.5;
const RAMP_INTERVAL_MS = 500;

const server = new OPCUAServer({
  port: PORT,
  resourcePath: RESOURCE_PATH,
  buildInfo: { productName: "OPC UA Aggregate Mock" },
});

await server.initialize();

const addressSpace = server.engine.addressSpace;
addAggregateSupport(addressSpace);

const namespace = addressSpace.getOwnNamespace();
const plant = namespace.addObject({
  organizedBy: addressSpace.rootFolder.objects,
  browseName: "Plant",
});

let temperature = 20.0;
const temperatureNode = namespace.addVariable({
  componentOf: plant,
  browseName: "Temperature",
  dataType: "Double",
  minimumSamplingInterval: RAMP_INTERVAL_MS,
  value: {
    get: () => new Variant({ dataType: DataType.Double, value: temperature }),
  },
});

addressSpace.installHistoricalDataNode(temperatureNode);

// Advertise historical access the same way the Python mock does, so the history
// tool is exposed here too and aggregate-vs-raw tool selection can be exercised.
const historyCapability = addressSpace.findNode(coerceNodeId("ns=0;i=11193"));
if (historyCapability) {
  historyCapability.setValueFromSource({
    dataType: DataType.Boolean,
    value: true,
  });
}

setInterval(() => {
  temperature += RAMP_STEP;
  temperatureNode.setValueFromSource({
    dataType: DataType.Double,
    value: temperature,
  });
}, RAMP_INTERVAL_MS);

await server.start();

// The test fixture waits for this line before connecting. Keep the prefix stable.
console.log(
  `READY endpoint=opc.tcp://localhost:${PORT}${RESOURCE_PATH} ` +
    `nodeId=${temperatureNode.nodeId.toString()} ` +
    `rampPerSecond=${(RAMP_STEP * 1000) / RAMP_INTERVAL_MS}`,
);

// Runtime configuration, read from the environment.

/** OPC UA endpoint the server and its capability probes connect to. */
export const SERVER_URL = process.env.OPCUA_SERVER_URL || "opc.tcp://localhost:4840";

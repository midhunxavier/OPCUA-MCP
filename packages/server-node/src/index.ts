#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import {
  OPCUAClient,
  MessageSecurityMode,
  SecurityPolicy,
  AttributeIds,
  ClientSession,
  DataType,
  Variant,
  DataValue,
  StatusCodes,
  CallMethodResult,
  BrowseResult,
  ReferenceDescription,
  HistoryData,
  AggregateFunction,
} from "node-opcua";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

// Keep stdout pristine for the MCP stdio JSON-RPC transport: route any stray
// library logging (e.g. node-opcua PKI/certificate messages) to stderr.
console.log = (...args: any[]) => console.error(...args);

// OPC UA client configuration
const SERVER_URL = process.env.OPCUA_SERVER_URL || "opc.tcp://localhost:4840";

// Shared tool contract: single source of truth in /contract/tools.json, copied
// to build/contract.json at build time (see scripts/copy-contract.mjs) and read
// here at runtime. Keeps tool names/descriptions/schemas in lockstep with the
// Python server (enforced by tests/test_contract_parity.py).
const CONTRACT: {
  capabilities: Record<string, { nodeId: string; browseName: string; check: string }>;
  tools: Array<{ name: string; capability: string | null; description: string; inputSchema: any }>;
} = JSON.parse(
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), "contract.json"), "utf8")
);

// Parse an optional ISO-8601 date/time string into a Date. MCP delivers these as
// strings, so they must be converted before being handed to node-opcua.
function toDate(value: string | Date | undefined): Date | undefined {
  if (value === undefined || value === null) return undefined;
  if (value instanceof Date) return value;
  const d = new Date(value);
  if (isNaN(d.getTime())) {
    throw new Error(`Invalid date/time: "${value}". Use ISO 8601, e.g. 2026-04-23T17:40:00Z`);
  }
  return d;
}

class OPCUAMCPServer {
  private server: Server;
  private opcuaClient: OPCUAClient | null = null;
  private session: ClientSession | null = null;
  private aggregateFunctions: string[] = [];

  constructor() {
    this.server = new Server(
      {
        name: "opcua-mcp-server",
        version: "0.1.2",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupLifecycle();
  }

  private setupLifecycle() {
    // Handle shutdown gracefully
    process.on('SIGINT', async () => {
      await this.disconnect();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      await this.disconnect();
      process.exit(0);
    });
  }

  private async connect(): Promise<void> {
    try {
      if (this.opcuaClient && this.session) {
        return; // Already connected
      }

      this.opcuaClient = OPCUAClient.create({
        applicationName: "OPC UA MCP Client",
        connectionStrategy: {
          initialDelay: 1000,
          maxRetry: 1
        },
        securityMode: MessageSecurityMode.None,
        securityPolicy: SecurityPolicy.None,
        endpoint_must_exist: false,
      });

      await this.opcuaClient.connect(SERVER_URL);
      console.error("Connected to OPC UA server");

      this.session = await this.opcuaClient.createSession();
      console.error("OPC UA session created");
    } catch (error) {
      console.error("Failed to connect to OPC UA server:", error);
      throw error;
    }
  }

  private async disconnect(): Promise<void> {
    try {
      if (this.session) {
        await this.session.close();
        this.session = null;
        console.error("OPC UA session closed");
      }

      if (this.opcuaClient) {
        await this.opcuaClient.disconnect();
        this.opcuaClient = null;
        console.error("Disconnected from OPC UA server");
      }
    } catch (error) {
      console.error("Error during disconnect:", error);
    }
  }

  private async ensureConnection(): Promise<void> {
    if (!this.opcuaClient || !this.session) {
      await this.connect();
    }
  }

  private async accessHistoryDataCapability(): Promise<boolean> {
    // Best-effort: never let an optional capability probe break tools/list. A
    // transient OPC UA outage should still leave the core tools advertised.
    try {
      await this.ensureConnection();
      const dataValue = await this.session!.readVariableValue(CONTRACT.capabilities.history.nodeId);
      return (
        dataValue.statusCode === StatusCodes.Good &&
        dataValue.value?.value === true
      );
    } catch (error) {
      console.error("accessHistoryDataCapability probe failed:", error);
      return false;
    }
  }

  private async serverCapabilitiesAggregateFunctions(): Promise<string[]> {
    // Best-effort: any failure (incl. a connection error) yields no aggregate
    // functions rather than breaking tools/list.
    let aggregateFunctions: string[] = [];
    try {
      await this.ensureConnection();
      const browseResult = await this.session!.browse({
        nodeId: CONTRACT.capabilities.aggregate.nodeId,
        browseDirection: 0, // Forward
        resultMask: 63, // All information (including BrowseName)
      });
      if (
        browseResult.statusCode === StatusCodes.Good &&
        browseResult.references
      ) {
        for (const reference of browseResult.references) {
          // Map the string BrowseName to the AggregateFunction
          if (reference.browseName.name) {
            const name = reference.browseName.name.toString();
            if (name in AggregateFunction) {
              aggregateFunctions.push(name);
            }
          }
        }
      }
    } catch (error) {
      console.error(
        "Error during serverCapabilitiesAggregateFunctions:",
        error,
      );
    }
    return aggregateFunctions;
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      // Build the advertised tools from the shared contract, gated by the
      // server's runtime capabilities (history / aggregate).
      const historyOk = await this.accessHistoryDataCapability();
      this.aggregateFunctions = await this.serverCapabilitiesAggregateFunctions();
      const aggregateOk = this.aggregateFunctions.length > 0;

      const tools = CONTRACT.tools
        .filter(
          (t) =>
            t.capability === null ||
            (t.capability === "history" && historyOk) ||
            (t.capability === "aggregate" && aggregateOk)
        )
        .map((t) => {
          // Preserve the dynamic aggregate_function help text (lists the
          // aggregate functions the server actually advertises).
          if (t.name === "read_aggregate_opcua_node") {
            const inputSchema = JSON.parse(JSON.stringify(t.inputSchema));
            inputSchema.properties.aggregate_function.description =
              t.inputSchema.properties.aggregate_function.description +
              ", one of: " +
              [...this.aggregateFunctions].join(", ");
            return { name: t.name, description: t.description, inputSchema };
          }
          return { name: t.name, description: t.description, inputSchema: t.inputSchema };
        }) satisfies Tool[];

      return { tools };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        await this.ensureConnection();

        switch (name) {
          case "read_opcua_node":
            return await this.readOpcuaNode(args?.node_id as string);

          case "read_history_opcua_node":
            return await this.readHistoryOpcuaNode(
              args?.node_id as string,
              args?.start_time as string | undefined,
              args?.end_time as string | undefined,
              (args?.num_values as number) || 0,
            );

          case "read_aggregate_opcua_node":
            return await this.readAggregateOpcuaNode(
              args?.node_id as string,
              args?.start_time as string,
              args?.end_time as string | undefined,
              args?.aggregate_function as string,
              (args?.processing_interval as number) || 0,
            );

          case "write_opcua_node":
            return await this.writeOpcuaNode(args?.node_id as string, args?.value as string);

          case "browse_opcua_node_children":
            return await this.browseOpcuaNodeChildren(args?.node_id as string);

          case "read_multiple_opcua_nodes":
            return await this.readMultipleOpcuaNodes(args?.node_ids as string[]);

          case "write_multiple_opcua_nodes":
            return await this.writeMultipleOpcuaNodes(args?.nodes_to_write as Array<{node_id: string, value: string}>);

          case "call_opcua_method":
            return await this.callOpcuaMethod(
              args?.object_node_id as string,
              args?.method_node_id as string,
              args?.arguments as string[]
            );

          case "get_all_variables":
            return await this.getAllVariables();

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error instanceof Error ? error.message : String(error)}`
            }
          ]
        };
      }
    });
  }

  private async readOpcuaNode(nodeId: string) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      const dataValue = await this.session.readVariableValue(nodeId);

      if (dataValue.statusCode !== StatusCodes.Good) {
        throw new Error(`Read failed with status: ${dataValue.statusCode.toString()}`);
      }

      const value = dataValue.value?.value;
      return {
        content: [
          {
            type: "text",
            text: `Node ${nodeId} value: ${value}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to read node ${nodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async readHistoryOpcuaNode(
    nodeId: string,
    start: string | undefined,
    end: string | undefined,
    numValuesPerNode: number,
  ) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      const historyValues = await this.session.readHistoryValue(
        [nodeId],
        toDate(start) as any,
        toDate(end) as any,
        {
          numValuesPerNode,
        },
      );
      if (historyValues.length !== 1) {
        throw new Error(`Read history failed`);
      }
      if (historyValues[0].statusCode !== StatusCodes.Good) {
        throw new Error(`Read history failed with status: ${historyValues[0].statusCode.toString()}`);
      }
      const dataValues = (historyValues[0].historyData as HistoryData).dataValues;
      return {
        content: [
          {
            type: "text",
            text: `${JSON.stringify(dataValues, null, 2)}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to read node ${nodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async readAggregateOpcuaNode(
    nodeId: string,
    start: string,
    end: string | undefined,
    aggregate_fn: string,
    processing_interval: number,
  ) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    // Don't depend on a prior tools/list having populated the cache: a client may
    // call this tool directly after connecting. Recompute on demand if empty.
    if (this.aggregateFunctions.length === 0) {
      this.aggregateFunctions = await this.serverCapabilitiesAggregateFunctions();
    }

    if (!this.aggregateFunctions.includes(aggregate_fn)) {
      throw new Error(
        this.aggregateFunctions.length === 0
          ? "Server does not advertise any aggregate functions"
          : `Invalid aggregate function. Supported: ${this.aggregateFunctions.join(", ")}`,
      );
    }

    try {
      const aggregateFn = AggregateFunction[aggregate_fn as keyof typeof AggregateFunction];
      const historyValues = await this.session.readAggregateValue(
        { nodeId },
        toDate(start) as any,
        (toDate(end) ?? new Date()) as any,
        aggregateFn,
        processing_interval,
      );
      if (historyValues.statusCode !== StatusCodes.Good) {
        throw new Error(`Read aggregate failed with status: ${historyValues.statusCode.toString()}`);
      }
      const dataValues = (historyValues.historyData as HistoryData).dataValues;
      return {
        content: [
          {
            type: "text",
            text: `${JSON.stringify(dataValues, null, 2)}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to read node ${nodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async writeOpcuaNode(nodeId: string, value: string) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      // First read the current value to determine the data type
      const currentDataValue = await this.session.readVariableValue(nodeId);

      let convertedValue: any;
      const currentValue = currentDataValue.value?.value;
      // Coerce to string first: a client may send a non-string (e.g. boolean/number) value.
      const valueStr = String(value);

      // Convert value based on the current type
      if (typeof currentValue === 'number') {
        convertedValue = parseFloat(valueStr);
        if (isNaN(convertedValue)) {
          throw new Error(`Cannot convert "${valueStr}" to number`);
        }
      } else if (typeof currentValue === 'boolean') {
        convertedValue = valueStr.toLowerCase() === 'true' || valueStr === '1';
      } else {
        convertedValue = valueStr; // Keep as string
      }

      const nodeToWrite = {
        nodeId: nodeId,
        attributeId: AttributeIds.Value,
        value: new DataValue({
          value: new Variant({ dataType: currentDataValue.value?.dataType || DataType.String, value: convertedValue })
        })
      };

      const statusCode = await this.session.write(nodeToWrite);

      if (statusCode !== StatusCodes.Good) {
        throw new Error(`Write failed with status: ${statusCode.toString()}`);
      }

      return {
        content: [
          {
            type: "text",
            text: `Successfully wrote ${value} to node ${nodeId}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to write to node ${nodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async browseOpcuaNodeChildren(nodeId: string) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      const browseResult = await this.session.browse(nodeId);

      if (browseResult.statusCode !== StatusCodes.Good) {
        throw new Error(`Browse failed with status: ${browseResult.statusCode.toString()}`);
      }

      const childrenInfo = browseResult.references?.map((ref: ReferenceDescription) => ({
        node_id: ref.nodeId.toString(),
        browse_name: `${ref.browseName.namespaceIndex}:${ref.browseName.name}`
      })) || [];

      return {
        content: [
          {
            type: "text",
            text: `Children of ${nodeId}: ${JSON.stringify(childrenInfo, null, 2)}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to browse children of node ${nodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async readMultipleOpcuaNodes(nodeIds: string[]) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      const nodesToRead = nodeIds.map(nodeId => ({
        nodeId: nodeId,
        attributeId: AttributeIds.Value
      }));

      const dataValues = await this.session.read(nodesToRead);

      const results: { [key: string]: any } = {};

      dataValues.forEach((dataValue, index) => {
        const nodeId = nodeIds[index];
        if (dataValue.statusCode === StatusCodes.Good) {
          results[nodeId] = dataValue.value?.value;
        } else {
          results[nodeId] = `Error: ${dataValue.statusCode.toString()}`;
        }
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(results, null, 2)
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to read multiple nodes: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async writeMultipleOpcuaNodes(nodesToWrite: Array<{node_id: string, value: string}>) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      // First, read current values to determine data types
      const nodeIds = nodesToWrite.map(item => item.node_id);
      const nodesToRead = nodeIds.map(nodeId => ({
        nodeId: nodeId,
        attributeId: AttributeIds.Value
      }));

      const currentDataValues = await this.session.read(nodesToRead);

      const writeNodes = nodesToWrite.map((item, index) => {
        const currentDataValue = currentDataValues[index];
        const currentValue = currentDataValue.value?.value;

        let convertedValue: any;
        // Coerce to string first: a client may send a non-string (e.g. boolean/number) value.
        const valueStr = String(item.value);

        // Convert value based on the current type
        if (typeof currentValue === 'number') {
          convertedValue = parseFloat(valueStr);
          if (isNaN(convertedValue)) {
            throw new Error(`Cannot convert "${valueStr}" to number for node ${item.node_id}`);
          }
        } else if (typeof currentValue === 'boolean') {
          convertedValue = valueStr.toLowerCase() === 'true' || valueStr === '1';
        } else {
          convertedValue = valueStr; // Keep as string
        }

        return {
          nodeId: item.node_id,
          attributeId: AttributeIds.Value,
          value: new DataValue({
            value: new Variant({
              dataType: currentDataValue.value?.dataType || DataType.String,
              value: convertedValue
            })
          })
        };
      });

      const statusCodes = await this.session.write(writeNodes);

      const results = statusCodes.map((statusCode, index) => ({
        node_id: nodesToWrite[index].node_id,
        status: statusCode === StatusCodes.Good ? 'Success' : `Error: ${statusCode.toString()}`
      }));

      return {
        content: [
          {
            type: "text",
            text: `Write operation results:\n${JSON.stringify(results, null, 2)}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to write multiple nodes: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async callOpcuaMethod(objectNodeId: string, methodNodeId: string, methodArgs?: string[]) {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      // Convert string arguments to appropriate types
      const convertedArgs: Variant[] = [];

      if (methodArgs) {
        for (const arg of methodArgs) {
          // Try to convert to appropriate type
          let convertedValue: any;

          // Try float first
          const floatValue = parseFloat(arg);
          if (!isNaN(floatValue)) {
            convertedValue = floatValue;
          } else {
            // Try int
            const intValue = parseInt(arg);
            if (!isNaN(intValue)) {
              convertedValue = intValue;
            } else {
              // Keep as string
              convertedValue = arg;
            }
          }

          convertedArgs.push(new Variant({
            dataType: typeof convertedValue === 'number' ? DataType.Double : DataType.String,
            value: convertedValue
          }));
        }
      }

      const methodToCall = {
        objectId: objectNodeId,
        methodId: methodNodeId,
        inputArguments: convertedArgs
      };

      const callResult: CallMethodResult = await this.session.call(methodToCall);

      if (callResult.statusCode !== StatusCodes.Good) {
        throw new Error(`Method call failed with status: ${callResult.statusCode.toString()}`);
      }

      return {
        content: [
          {
            type: "text",
            text: `Method call successful. Object: ${objectNodeId}, Method: ${methodNodeId}, Result: ${JSON.stringify(callResult.outputArguments)}`
          }
        ]
      };
    } catch (error) {
      throw new Error(`Failed to call method ${methodNodeId} on object ${objectNodeId}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async getAllVariables() {
    if (!this.session) {
      throw new Error("No OPC UA session available");
    }

    try {
      const variablesInfo: Array<{
        name: string;
        nodeid: string;
        object_id: string;
        value: any;
        data_type: string;
        description: string;
      }> = [];

      // Start browsing from the Objects folder (ns=0;i=85)
      const objectsNodeId = "ns=0;i=85";

      const searchVariables = async (nodeId: string): Promise<void> => {
        try {
          const browseResult = await this.session!.browse(nodeId);

          if (browseResult.statusCode !== StatusCodes.Good || !browseResult.references) {
            return;
          }

          for (const ref of browseResult.references) {
            try {
              const childNodeId = ref.nodeId.toString();
              const browseName = ref.browseName.name;

              // Skip the entire "Server" subtree
              if (browseName === "Server") {
                continue;
              }

              // Read the node class to determine if it's a variable or object
              const nodeClassResults = await this.session!.read({
                nodeId: childNodeId,
                attributeId: AttributeIds.NodeClass
              });

              const nodeClass = nodeClassResults.value?.value;

              if (nodeClass === 2) { // NodeClass.Variable = 2
                // This is a variable node
                let value: any;
                let dataType = "";
                let description = "";
                let objectId = nodeId;

                try {
                  const valueResult = await this.session!.readVariableValue(childNodeId);
                  value = valueResult.value?.value;
                } catch {
                  value = null;
                }

                try {
                  const dataTypeResults = await this.session!.read({
                    nodeId: childNodeId,
                    attributeId: AttributeIds.DataType
                  });
                  dataType = dataTypeResults.value?.value?.toString() || "";
                } catch {
                  dataType = "";
                }

                try {
                  const descResults = await this.session!.read({
                    nodeId: childNodeId,
                    attributeId: AttributeIds.Description
                  });
                  description = descResults.value?.value?.text || "";
                } catch {
                  description = "";
                }

                variablesInfo.push({
                  name: browseName || "",
                  nodeid: childNodeId,
                  object_id: objectId,
                  value: value,
                  data_type: dataType,
                  description: description
                });
              } else if (nodeClass === 1) { // NodeClass.Object = 1
                // This is an object node, recursively search its children
                await searchVariables(childNodeId);
              }
            } catch (error) {
              // Continue with next reference if this one fails
              console.error(`Error processing reference: ${error}`);
            }
          }
        } catch (error) {
          // Continue if browse fails for this node
          console.error(`Error browsing node ${nodeId}: ${error}`);
        }
      };

      await searchVariables(objectsNodeId);

      if (variablesInfo.length > 0) {
        let result = `Found ${variablesInfo.length} variables:\n`;
        for (const variable of variablesInfo) {
          result += `\n- Name: ${variable.name}\n`;
          result += `  NodeID: ${variable.nodeid}\n`;
          result += `  Object ID: ${variable.object_id}\n`;
          result += `  Value: ${variable.value}\n`;
          result += `  Data Type: ${variable.data_type}\n`;
          result += `  Description: ${variable.description}\n`;
        }

        return {
          content: [
            {
              type: "text",
              text: result
            }
          ]
        };
      } else {
        return {
          content: [
            {
              type: "text",
              text: "No variables found in the OPC UA server."
            }
          ]
        };
      }
    } catch (error) {
      throw new Error(`Failed to get all variables: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("OPC UA MCP Server running on stdio");
  }
}

// Run the server
const server = new OPCUAMCPServer();
server.run().catch(console.error);

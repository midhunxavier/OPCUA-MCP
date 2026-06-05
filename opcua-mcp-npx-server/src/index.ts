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
  ReferenceDescription
} from "node-opcua";

// OPC UA client configuration
const SERVER_URL = process.env.OPCUA_SERVER_URL || "opc.tcp://localhost:4840";

class OPCUAMCPServer {
  private server: Server;
  private opcuaClient: OPCUAClient | null = null;
  private session: ClientSession | null = null;

  constructor() {
    this.server = new Server(
      {
        name: "opcua-mcp-npx-server",
        version: "0.1.0",
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

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "read_opcua_node",
            description: "Read the value of a specific OPC UA node",
            inputSchema: {
              type: "object",
              properties: {
                node_id: {
                  type: "string",
                  description: "The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'. Example: 'ns=2;i=2'."
                }
              },
              required: ["node_id"]
            }
          },
          {
            name: "write_opcua_node",
            description: "Write a value to a specific OPC UA node",
            inputSchema: {
              type: "object",
              properties: {
                node_id: {
                  type: "string",
                  description: "The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'. Example: 'ns=2;i=3'."
                },
                value: {
                  type: "string",
                  description: "The value to write to the node. Will be converted based on node type."
                }
              },
              required: ["node_id", "value"]
            }
          },
          {
            name: "browse_opcua_node_children",
            description: "Browse the children of a specific OPC UA node",
            inputSchema: {
              type: "object",
              properties: {
                node_id: {
                  type: "string",
                  description: "The OPC UA node ID to browse (e.g., 'ns=0;i=85' for Objects folder)."
                }
              },
              required: ["node_id"]
            }
          },
          {
            name: "read_multiple_opcua_nodes",
            description: "Read the values of multiple OPC UA nodes in a single request",
            inputSchema: {
              type: "object",
              properties: {
                node_ids: {
                  type: "array",
                  items: {
                    type: "string"
                  },
                  description: "A list of OPC UA node IDs to read (e.g., ['ns=2;i=2', 'ns=2;i=3'])."
                }
              },
              required: ["node_ids"]
            }
          },
          {
            name: "write_multiple_opcua_nodes",
            description: "Write values to multiple OPC UA nodes in a single request",
            inputSchema: {
              type: "object",
              properties: {
                nodes_to_write: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      node_id: {
                        type: "string"
                      },
                      value: {
                        type: "string"
                      }
                    },
                    required: ["node_id", "value"]
                  },
                  description: "A list of objects containing 'node_id' and 'value'. Example: [{'node_id': 'ns=2;i=2', 'value': '10.5'}, {'node_id': 'ns=2;i=3', 'value': 'active'}]"
                }
              },
              required: ["nodes_to_write"]
            }
          },
          {
            name: "call_opcua_method",
            description: "Call a method on a specific OPC UA object node",
            inputSchema: {
              type: "object",
              properties: {
                object_node_id: {
                  type: "string",
                  description: "The OPC UA node ID of the object that contains the method. Example: 'ns=2;i=1' for the Methods folder."
                },
                method_node_id: {
                  type: "string",
                  description: "The OPC UA node ID of the method to call. Example: 'ns=2;i=2' for StartProduction method."
                },
                arguments: {
                  type: "array",
                  items: {
                    type: "string"
                  },
                  description: "List of arguments to pass to the method. Arguments will be converted to appropriate OPC UA variants."
                }
              },
              required: ["object_node_id", "method_node_id"]
            }
          },
          {
            name: "get_all_variables",
            description: "Get all available variables from the OPC UA server, excluding those under the built-in 'Server' object",
            inputSchema: {
              type: "object",
              properties: {},
              required: []
            }
          }
        ] satisfies Tool[]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        await this.ensureConnection();

        switch (name) {
          case "read_opcua_node":
            return await this.readOpcuaNode(args?.node_id as string);

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
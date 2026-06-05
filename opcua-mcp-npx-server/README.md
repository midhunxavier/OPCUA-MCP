# OPC UA MCP NPX Server

An NPX-based Model Context Protocol (MCP) server for OPC UA operations. This server provides a set of tools to interact with OPC UA servers, including reading/writing variables, browsing nodes, calling methods, and performing batch operations.

## Features

- **Read OPC UA Nodes**: Read values from individual or multiple OPC UA nodes
- **Write OPC UA Nodes**: Write values to individual or multiple OPC UA nodes  
- **Browse Node Children**: Explore the OPC UA address space by browsing node children
- **Call OPC UA Methods**: Execute methods on OPC UA objects with parameters
- **Batch Operations**: Perform multiple read/write operations in single requests
- **Get All Variables**: Discover all available variables in the OPC UA server address space
- **Automatic Type Conversion**: Intelligent conversion of values based on node data types
- **Connection Management**: Automatic connection handling with graceful disconnection
- **Read History OPC UA Node**: Read the historical values of a specific OPC UA node (if supported by the server)
- **Read Aggregate OPC UA Node**: Calculate the historical aggregates (if supported by the server)

## Installation & Usage

### Using NPX (Recommended)

You can run the server directly using NPX without installing it globally:

```bash
npx opcua-mcp-npx-server
```

### Global Installation

```bash
npm install -g opcua-mcp-npx-server
opcua-mcp-npx-server
```

### Local Development

```bash
git clone <repository>
cd opcua-mcp-npx-server
npm install
npm run build
npm start
```

## Configuration

The server connects to an OPC UA server using the following environment variable:

- `OPCUA_SERVER_URL`: The OPC UA server endpoint (default: `opc.tcp://localhost:4840`)

Example:
```bash
OPCUA_SERVER_URL=opc.tcp://192.168.1.100:4840 npx opcua-mcp-npx-server
```

## MCP Tools

### 1. read_opcua_node

Read the value of a specific OPC UA node.

**Parameters:**
- `node_id` (string): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'

**Example:**
```json
{
  "node_id": "ns=2;i=1"
}
```

### 2. write_opcua_node

Write a value to a specific OPC UA node.

**Parameters:**
- `node_id` (string): The OPC UA node ID
- `value` (string): The value to write (automatically converted to the correct type)

**Example:**
```json
{
  "node_id": "ns=2;i=2",
  "value": "75.5"
}
```

### 3. browse_opcua_node_children

Browse the children of a specific OPC UA node.

**Parameters:**
- `node_id` (string): The OPC UA node ID to browse

**Example:**
```json
{
  "node_id": "ns=2;i=3"
}
```

### 4. read_multiple_opcua_nodes

Read values from multiple OPC UA nodes in a single request.

**Parameters:**
- `node_ids` (array): List of OPC UA node IDs to read

**Example:**
```json
{
  "node_ids": [
    "ns=2;i=4", 
    "ns=2;i=5", 
    "ns=2;i=6"
  ]
}
```

### 5. write_multiple_opcua_nodes

Write values to multiple OPC UA nodes in a single request.

**Parameters:**
- `nodes_to_write` (array): List of objects containing 'node_id' and 'value'

**Example:**
```json
{
  "nodes_to_write": [
    {"node_id": "ns=2;i=7", "value": "50"},
    {"node_id": "ns=2;i=8", "value": "true"}
  ]
}
```

### 6. call_opcua_method

Call a method on a specific OPC UA object node.

**Parameters:**
- `object_node_id` (string): The OPC UA node ID of the object containing the method
- `method_node_id` (string): The OPC UA node ID of the method to call
- `arguments` (array, optional): List of arguments to pass to the method

**Example:**
```json
{
  "object_node_id": "ns=2;i=9",
  "method_node_id": "ns=2;i=10",
  "arguments": ["25.0", "high_quality"]
}
```

### 7. get_all_variables

Get all available variables from the OPC UA server, excluding those under the built-in 'Server' object.

**Parameters:**
- None required

**Example:**
```json
{}
```

**Returns:**
A comprehensive list of all variables with their properties including name, node ID, object ID, current value, data type, and description.

### 8. read_history_opcua_node

Read the historical values of a specific OPC UA node.

**Parameters:**
- `node_id` (string): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'
- `start_time` (datetime)
- `end_time` (datetime)
- `num_values` (int): Number of values to read (default: unlimited)

**Example:**
```json
{
  "node_id": "ns=2;i=1",
  "start_time": "2026-04-23 17:40:00",
  "end_time": "2026-04-23 17:45:00"
}
```

### 9. read_aggregate_opcua_node

Calculate the historical aggregates over a defined time range, divided into smaller chunks defined by the `processing_interval` (in milliseconds). The server divides the [`start_time`, `end_time`] domain into these intervals, returning one aggregated value per interval.

**Parameters:**
- `node_id` (string): The OPC UA node ID in the format 'ns=<namespace>;i=<identifier>'
- `start_time` (datetime): Beginning of the retrieval
- `end_time` (datetime): End of the retrieval (defaults to 'now')
- `aggregate_function` (string): The specific formula, e.g. Average, Minimum, Maximum
- `processing_interval` (number): The duration (ms) for each computed value. If set to 0, the server calculates a single aggregate value for the entire range.

**Example:**
```json
{
  "node_id": "ns=2;i=1",
  "start_time": "2026-04-23 17:40:00",
  "end_time": "2026-04-23 17:45:00",
  "aggregate_function": "Average",
  "processing_interval": "60000"
}
```

## Integration with Cursor/Claude

This server can be integrated with Cursor IDE or Claude Desktop for OPC UA operations. Add the following to your MCP configuration:

### Cursor Configuration

Add to your Cursor settings:

```json
{
  "mcpServers": {
    "opcua-npx": {
      "command": "npx",
      "args": ["opcua-mcp-npx-server"],
      "env": {
        "OPCUA_SERVER_URL": "opc.tcp://localhost:4840"
      }
    }
  }
}
```

### Claude Desktop Configuration

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "opcua-npx": {
      "command": "npx",
      "args": ["opcua-mcp-npx-server"],
      "env": {
        "OPCUA_SERVER_URL": "opc.tcp://localhost:4840"
      }
    }
  }
}
```

## Example Usage in Conversation

Once configured, you can ask Claude to perform real-world OPC UA operations:

### Reading Sensor Values
- "What is the current temperature reading from the reactor vessel?"
- "Check the pressure level in Tank A"
- "Read all temperature sensors in the cooling system"
- "Get the current flow rate on production line B"

### Controlling Equipment
- "Turn on the conveyor motor"
- "Set the mixer speed to 80 RPM"
- "Open valve V-101 to 75% position"
- "Start the circulation pump"
- "Set the heating element to 150°C"

### Production Operations
- "Start production on line 1 with rate 100 units/hour"
- "Stop all motors in emergency mode"
- "Initialize the batch reactor with recipe A"
- "Begin the cleaning cycle for Tank B"

### System Monitoring
- "Show me all alarm states in the system"
- "Read all sensor values from the water treatment plant"
- "Check the status of all pumps and motors"
- "Get the energy consumption readings"
- "Discover all available variables in the OPC UA server"
- "Show me a complete inventory of all sensors and actuators"
- "List all process variables with their current values"

### Real Example Scenarios
```
User: "What's the temperature in reactor R-101?"
Assistant: I'll read the temperature sensor for reactor R-101.
Tool call: read_opcua_node with node_id "ns=2;i=11"
Result: "Reactor R-101 temperature: 87.3°C"

User: "Turn on the main conveyor motor"
Assistant: I'll start the main conveyor motor for you.
Tool call: write_opcua_node with node_id "ns=2;i=12" and value "true"
Result: "Main conveyor motor started successfully"

User: "Set the pump speed to 65%"
Assistant: I'll adjust the pump speed to 65%.
Tool call: write_opcua_node with node_id "ns=2;i=13" and value "65"
Result: "Pump speed set to 65%"

User: "Show me all available variables in the system"
Assistant: I'll get a complete list of all variables in the OPC UA server.
Tool call: get_all_variables
Result: "Found 15 variables:
- Name: Temperature_Sensor_01, NodeID: ns=2;i=101, Value: 87.3°C
- Name: Pressure_Sensor_01, NodeID: ns=2;i=102, Value: 2.5 bar
- Name: Flow_Rate_01, NodeID: ns=2;i=103, Value: 125.8 L/min
..."
```

## Security Considerations

- This server currently connects without security (SecurityPolicy.None)
- For production use, implement appropriate security policies and authentication
- Ensure proper network security when connecting to industrial OPC UA servers
- Validate and sanitize all input parameters

## Error Handling

The server provides detailed error messages for:
- Connection failures
- Invalid node IDs
- Type conversion errors
- Method call failures
- Read/write operation errors

## Dependencies

- `@modelcontextprotocol/sdk`: MCP SDK for Node.js
- `node-opcua`: OPC UA client library for Node.js
- `typescript`: TypeScript compiler

## Contributing

We welcome contributions to improve the OPC UA MCP NPX Server! 

**Repository**: [https://github.com/midhunxavier/OPCUA-MCP](https://github.com/midhunxavier/OPCUA-MCP)

To contribute:

1. Fork the repository at [https://github.com/midhunxavier/OPCUA-MCP](https://github.com/midhunxavier/OPCUA-MCP)
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please feel free to open issues for bug reports, feature requests, or questions.

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/midhunxavier/OPCUA-MCP/issues)
- Check the OPC UA server connectivity
- Verify node IDs are correct
- Ensure proper permissions for OPC UA operations
- Review server logs for detailed error information 
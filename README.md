# OPC UA MCP Server

![OPC UA MCP Server Screenshot](Media/ss.png)

## Overview

Python and TypeScript implementations provide the same core functionality for OPC UA operations through MCP tools, but differ in their implementation approach and deployment model.


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

## Implementation Languages

### Python Version (`opcua-mcp-server`)
- **Language**: Python 3.13+
- **Framework**: FastMCP
- **OPC UA Library**: `opcua` (FreeOpcUa)
- **Transport**: STDIO
- **Entry Point**: `opcua-mcp-server.py`

### NPX Version (`opcua-mcp-npx-server`)
- **Language**: TypeScript/Node.js
- **Framework**: @modelcontextprotocol/sdk
- **OPC UA Library**: `node-opcua`
- **Transport**: STDIO
- **Entry Point**: `src/index.ts` (compiled to `build/index.js`)

## Features Comparison

| Feature | Python Version | NPX Version | Notes |
|---------|----------------|-------------|-------|
| Read Single Node | ✅ | ✅ | Both support automatic type detection |
| Write Single Node | ✅ | ✅ | Both support automatic type conversion |
| Browse Node Children | ✅ | ✅ | Both return JSON formatted results |
| Call OPC UA Methods | ✅ | ✅ | Both support parameter conversion |
| Read Multiple Nodes | ✅ | ✅ | Batch read operations |
| Write Multiple Nodes | ✅ | ✅ | Batch write operations |
| Get All Variables | ✅ | ✅ | Discover all variables in server address space |
| Connection Management | ✅ | ✅ | Both handle lifecycle automatically |
| Error Handling | ✅ | ✅ | Comprehensive error reporting |
| Type Conversion | ✅ | ✅ | Automatic data type conversion |

## Tool Implementations

### Available Tools (Both Versions)

1. **`read_opcua_node`**
   - Read value from a single OPC UA node
   - Parameters: `node_id` (string)
   - Returns: Node value with ID prefix

2. **`write_opcua_node`**
   - Write value to a single OPC UA node
   - Parameters: `node_id` (string), `value` (string)
   - Returns: Success/failure message

3. **`browse_opcua_node_children`**
   - Browse children of an OPC UA node
   - Parameters: `node_id` (string)
   - Returns: Array of child nodes with IDs and browse names

4. **`read_multiple_opcua_nodes`**
   - Read values from multiple nodes in one request
   - Parameters: `node_ids` (array of strings)
   - Returns: Dictionary mapping node IDs to values

5. **`write_multiple_opcua_nodes`**
   - Write values to multiple nodes in one request
   - Parameters: `nodes_to_write` (array of {node_id, value} objects)
   - Returns: Status results for each write operation

6. **`call_opcua_method`**
   - Call a method on an OPC UA object
   - Parameters: `object_node_id`, `method_node_id`, `arguments` (optional)
   - Returns: Method execution result

7. **`get_all_variables`**
   - Get all available variables from the OPC UA server
   - Parameters: None
   - Returns: Comprehensive list of all variables with their properties (name, node ID, value, data type, description)

## Deployment & Installation

### Python Version
```bash
# Installation
cd opcua-mcp-server
uv install  # or pip install

# Usage
uv run opcua-mcp-server.py
# or
python opcua-mcp-server.py
```

### NPX Version
```bash
# Direct usage (recommended)
npx opcua-mcp-npx-server

# Global installation
npm install -g opcua-mcp-npx-server
opcua-mcp-npx-server

# Development
npm install
npm run build
npm start
```

**NPM Package**: https://www.npmjs.com/package/opcua-mcp-npx-server

## Configuration

Both versions use the same environment variable:
- `OPCUA_SERVER_URL`: OPC UA server endpoint (default: `opc.tcp://localhost:4840`)

### Python Configuration Example
```json
{
  "mcpServers": {
    "opcua-python": {
      "command": "/Users/mx/.local/bin/uv",
      "args": [
        "--directory",
        "/path/to/opcua-mcp-server",
        "run",
        "opcua-mcp-server.py"
      ],
      "env": {
        "OPCUA_SERVER_URL": "opc.tcp://localhost:4840"
      }
    }
  }
}
```

### NPX Configuration Example
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

## Dependencies

### Python Version
- `mcp[cli]>=1.9.1`: MCP framework
- `opcua>=0.98.13`: OPC UA client library
- `cryptography>=45.0.2`: Security support
- `httpx>=0.28.1`: HTTP client

### NPX Version
- `@modelcontextprotocol/sdk`: MCP SDK for Node.js
- `node-opcua`: Comprehensive OPC UA library
- `typescript`: TypeScript compiler
- `@types/node`: Node.js type definitions


## Testing

There are three ways to exercise the servers — the automated suite, the MCP
Inspector (UI or CLI), and an AI agent (Claude Code / Desktop / Cursor). Start the
mock server first, then:

```bash
cd tests && uv run pytest -v        # end-to-end suite, both servers
```

See **[TESTING.md](TESTING.md)** for the full guide (Inspector walkthrough, AI-agent
setup, example prompts, troubleshooting) and **[EXAMPLES.md](EXAMPLES.md)** for
per-tool inputs/outputs and a node-ID reference.

## Contributing

Contributions are welcome — see **[CONTRIBUTING.md](CONTRIBUTING.md)** for project
layout, local development, adding a new tool to both servers, and PR conventions.


## Security

Both versions currently connect with:
- `SecurityPolicy.None`
- `MessageSecurityMode.None`

For production use, both should implement:
- Certificate-based authentication
- Encrypted communication
- User authentication
- Input validation


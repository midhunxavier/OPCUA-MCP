# OPC UA MCP Server

A Model Context Protocol (MCP) server that provides seamless integration with OPC UA servers. This server enables AI assistants and other MCP clients to interact with industrial automation systems through standardized OPC UA communication protocols.

## Overview

This MCP server acts as a bridge between AI assistants and OPC UA servers, allowing for:
- Reading sensor data and system variables
- Writing control values to actuators and systems
- Browsing OPC UA node hierarchies
- Calling OPC UA methods for system operations
- Batch operations for multiple nodes

## Tools

See the central per-tool reference in **[../../docs/examples.md](../../docs/examples.md)**; the shared tool surface is defined in **[../../contract/tools.json](../../contract/tools.json)**.

## Features

### Key Capabilities

- **Automatic Connection Management**: Handles OPC UA client lifecycle with proper connection setup and teardown
- **Type-Safe Operations**: Automatic type conversion based on existing node data types
- **Error Handling**: Comprehensive error reporting for debugging and monitoring
- **Async Support**: Built on FastMCP for efficient asynchronous operations
- **Configurable**: Environment-based server URL configuration

## Installation

### Prerequisites

- Python 3.13 or higher
- Access to an OPC UA server (local or remote)
- UV package manager (recommended) or pip

### Setup

1. **Install dependencies for the whole workspace (run from the repo root):**
   ```bash
   uv sync --all-packages
   ```

2. **Configure the OPC UA server URL:**
   ```bash
   export OPCUA_SERVER_URL="opc.tcp://localhost:4840"
   ```

## Usage

### Running the Server

After `uv sync --all-packages` from the repo root:
```bash
uv run --no-sync opcua-mcp-server
```

Or run it directly against this package from anywhere in the repo:
```bash
uv --directory packages/server-python run opcua-mcp-server
```

### Integration with MCP Clients

Add to your MCP client configuration (e.g., `config.json`):

```json
{
  "mcpServers": {
    "opcua-mcp": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/path/to/packages/server-python",
        "run",
        "opcua-mcp-server"
      ],
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
- "What variables are available on this OPC UA server?"
- "Show me all sensors and their current values"

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

User: "What variables are available on this OPC UA server?"
Assistant: I'll retrieve all available variables from the OPC UA server.
Tool call: get_all_variables
Result: Found 5 variables:
- Temperature (ns=2;i=2): 25.3°C - Temperature sensor
- Pressure (ns=2;i=3): 5.0 bar - Pressure sensor  
- MotorSpeed (ns=2;i=4): 1500 RPM - Motor speed
- MotorState (ns=2;i=5): True - Motor ON/OFF state
- ValvePosition (ns=2;i=6): False - Valve OPEN/CLOSED position
```

## API Reference

See the central per-tool reference in **[../../docs/examples.md](../../docs/examples.md)** for full tool signatures, parameters, and return formats. The shared tool surface is defined in **[../../contract/tools.json](../../contract/tools.json)**.
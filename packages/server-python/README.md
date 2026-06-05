# OPC UA MCP Server

A Model Context Protocol (MCP) server that provides seamless integration with OPC UA servers. This server enables AI assistants and other MCP clients to interact with industrial automation systems through standardized OPC UA communication protocols.

## Overview

This MCP server acts as a bridge between AI assistants and OPC UA servers, allowing for:
- Reading sensor data and system variables
- Writing control values to actuators and systems
- Browsing OPC UA node hierarchies
- Calling OPC UA methods for system operations
- Batch operations for multiple nodes

## Features

### Core Tools

- **`read_opcua_node`** - Read the current value of any OPC UA node
- **`read_history_opcua_node`** - Read the historical values of a specific OPC UA node (only exposed if the server supports historical data access)
- **`write_opcua_node`** - Write values to OPC UA nodes with automatic type conversion
- **`browse_opcua_node_children`** - Explore the OPC UA address space and discover available nodes
- **`call_opcua_method`** - Execute OPC UA methods on server objects
- **`read_multiple_opcua_nodes`** - Batch read multiple nodes in a single operation
- **`write_multiple_opcua_nodes`** - Batch write to multiple nodes efficiently
- **`get_all_variables`** - Retrieve all available variables from the OPC UA server with their metadata

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

1. **Clone or download the project:**
   ```bash
   cd packages/server-python
   ```

2. **Install dependencies using UV:**
   ```bash
   uv sync
   ```

   **Or using pip:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the OPC UA server URL:**
   ```bash
   export OPCUA_SERVER_URL="opc.tcp://localhost:4840"
   ```

## Usage

### Running the Server

**With UV:**
```bash
uv run opcua-mcp-server
```

**With Python:**
```bash
python opcua_mcp_server.py
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

### Reading Data

**Read a single node:**
```python
read_opcua_node(node_id="ns=2;i=3")
# Returns: "Node ns=2;i=3 value: 26.57"
```

**Read historical values from a single node:**
```python
read_history_opcua_node(node_id="ns=2;i=3", num_values=1)
# Returns: [ { "value": "26.57", "timestamp": "2026-04-22 18:51:05.163834", "status": "Good" }]
```

**Read multiple nodes:**
```python
read_multiple_opcua_nodes(node_ids=["ns=2;i=3", "ns=2;i=4", "ns=2;i=5"])
# Returns: Multiple node read results with all values
```

**Get all variables:**
```python
get_all_variables()
# Returns: Complete list of all variables with their metadata including:
# - Name, NodeID, Object ID, Current Value, Data Type, Description
# Example output:
# - Name: Temperature, NodeID: ns=2;i=2, Value: 25.3, Data Type: i=11, Description: Temperature sensor (°C)
# - Name: Pressure, NodeID: ns=2;i=3, Value: 5.0, Data Type: i=11, Description: Pressure sensor (bar)
```

### System Discovery
```python
# Explore available sensors
browse_opcua_node_children("ns=2;i=2")  # Sensors folder

# Explore available actuators  
browse_opcua_node_children("ns=2;i=11") # Actuators folder

# Get complete overview of all variables
get_all_variables()  # Returns all variables with metadata
```